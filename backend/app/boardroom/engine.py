"""Boardroom engine: runs the universal workflow and streams progress events.

USER REQUEST -> understand -> assemble team -> research -> individual analysis
-> collaboration/challenge -> (specialists join/leave) -> output -> quality
review -> deliverable. The engine is storage-agnostic: it emits event dicts and
calls ``persist(fields)`` after each stage so a workspace can be resumed.
"""
import asyncio
import re
import uuid
from datetime import date, datetime
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple

from app.boardroom import llm
from app.boardroom.analyzer import analyze_work
from app.boardroom.architect import CHALLENGER_ARCHETYPES, MAX_AGENTS, build_spec, design_board
from app.boardroom.archetypes import (
    ARTIFACT_BY_TASK, ARTIFACT_GUIDANCE, DEFAULT_GUIDANCE, SENSITIVITY_DISCLAIMERS, TOOL_CATALOG,
)
from app.boardroom.research import search_web
from app.boardroom.schemas import AgentSpec, WorkAnalysis

Persist = Callable[[Dict[str, Any]], Awaitable[None]]
Event = Dict[str, Any]

MAX_SEARCHES = 12
MAX_SPECIALISTS = 2
CONCURRENCY = 4
CITE_RE = re.compile(r"\[S(\d+)\]")

USER = {"id": "user", "perspective": "You"}


# ── helpers ─────────────────────────────────────────────────────────────────

def disclaimer_for(sensitivity: List[str]) -> str:
    return " ".join(SENSITIVITY_DISCLAIMERS[s] for s in sensitivity if s in SENSITIVITY_DISCLAIMERS)


def _sources_block(sources: List[Dict[str, Any]]) -> str:
    if not sources:
        return ("No live sources were retrieved. Do NOT cite sources. Treat everything you say as general knowledge "
                "that may be out of date, and say so where it matters.")
    return "\n".join(f"[{s['id']}] {s['title']} ({s['url']}): {s['snippet']}" for s in sources)


def _agent_system(spec: AgentSpec, analysis: WorkAnalysis) -> str:
    return (
        f"You are the {spec.perspective} on an AI Boardroom team. You are an expert PERSPECTIVE, not a real person: "
        "never claim to be a named individual, to hold credentials, or to have real-world experience.\n"
        f"Domain: {spec.domain or analysis.domain}. Expertise: {spec.expertise}.\n"
        f"Behaviour: {spec.behavior}\n"
        f"Objectives: {'; '.join(spec.objectives) or 'serve the team objective'}. "
        f"Priorities: {'; '.join(spec.priorities) or 'accuracy and usefulness'}.\n"
        f"Quality bar: {'; '.join(spec.quality_criteria)}.\n"
        "Be specific to the user's situation and respect their constraints and numbers exactly. "
        "Cite sources only as [S#] using ids you were given; never invent sources, statistics or quotes. "
        "Say plainly when you are unsure. "
        f"Today's date is {date.today().isoformat()}."
    )


def _situation(analysis: WorkAnalysis, context: str) -> str:
    text = (
        f"Objective: {analysis.objective}\nDomain: {analysis.domain}\n"
        f"Constraints: {'; '.join(analysis.constraints) or 'none stated'}\n"
        f"Desired output: {analysis.desired_output}"
    )
    if context.strip():
        text += f"\n\nUser-supplied context:\n{context[:4000]}"
    return text


def _digest(messages: List[Dict[str, Any]], kinds: Tuple[str, ...], limit: int = 1200) -> str:
    return "\n\n".join(
        f"### {m['agent_name']} ({m['agent_id']})\n{m['content'][:limit]}" for m in messages if m["kind"] in kinds
    )


def _clean_citations(text: str, sources: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Drop citations that do not match a real retrieved source. Returns (text, removed ids)."""
    valid = {s["id"] for s in sources}
    removed: List[str] = []

    def sub(m: "re.Match[str]") -> str:
        sid = f"S{m.group(1)}"
        if sid in valid:
            return m.group(0)
        removed.append(sid)
        return ""

    return CITE_RE.sub(sub, text), removed


def _valid_ids(ids: Any, sources: List[Dict[str, Any]]) -> List[str]:
    valid = {s["id"] for s in sources}
    return [i for i in (ids or []) if isinstance(i, str) and i in valid]


def _conf(v: Any, default: float = 0.6) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return default


async def _stream_parallel(jobs: Dict[str, Awaitable[Any]]) -> AsyncIterator[Tuple[str, Any, Optional[Exception]]]:
    """Run jobs concurrently (bounded); yield (key, result, error) as each finishes."""
    sem = asyncio.Semaphore(CONCURRENCY)

    async def run(key: str, coro: Awaitable[Any]):
        async with sem:
            try:
                return key, await coro, None
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - surfaced per-agent, engine continues
                return key, None, e

    tasks = [asyncio.ensure_future(run(k, c)) for k, c in jobs.items()]
    try:
        for fut in asyncio.as_completed(tasks):
            yield await fut
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()


def _is_config_error(e: Exception) -> bool:
    return isinstance(e, ValueError) and "NVIDIA_API_KEY" in str(e)


# ── the run ─────────────────────────────────────────────────────────────────

class _Run:
    def __init__(self, objective: str, context: str, persist: Persist, state: Optional[Dict[str, Any]] = None):
        self.objective = objective
        self.context = context
        self.persist = persist
        st = state or {}
        self.analysis: Optional[WorkAnalysis] = WorkAnalysis(**st["analysis"]) if st.get("analysis") else None
        self.board: List[AgentSpec] = [AgentSpec(**a) for a in (st.get("board") or {}).get("agents", [])]
        self.rationale: str = (st.get("board") or {}).get("rationale", "")
        self.sources: List[Dict[str, Any]] = list(st.get("sources") or [])
        self.messages: List[Dict[str, Any]] = list(st.get("messages") or [])
        self.decisions: List[Dict[str, Any]] = list(st.get("decisions") or [])
        self.tasks: List[Dict[str, Any]] = list(st.get("tasks") or [])
        self.outputs: List[Dict[str, Any]] = list(st.get("outputs") or [])
        self.history: List[Dict[str, Any]] = list(st.get("history") or [])
        self.searches = 0

    # -- bookkeeping
    def stage(self, name: str, detail: str = "") -> Event:
        self.history.append({"stage": name, "detail": detail, "at": datetime.utcnow().isoformat()})
        return {"type": "stage", "stage": name, "detail": detail}

    def message(self, spec: Any, kind: str, content: str, rnd: int, **extra: Any) -> Dict[str, Any]:
        agent_id = spec.id if hasattr(spec, "id") else spec["id"]
        name = spec.perspective if hasattr(spec, "perspective") else spec["perspective"]
        msg = {"id": uuid.uuid4().hex[:10], "agent_id": agent_id, "agent_name": name, "kind": kind,
               "round": rnd, "content": content, "created_at": datetime.utcnow().isoformat(), **extra}
        self.messages.append(msg)
        return msg

    def snapshot(self, **extra: Any) -> Dict[str, Any]:
        return {
            "analysis": self.analysis.model_dump() if self.analysis else None,
            "board": {"agents": [a.model_dump() for a in self.board], "rationale": self.rationale},
            "sources": self.sources, "messages": self.messages, "decisions": self.decisions,
            "tasks": self.tasks, "outputs": self.outputs, "history": self.history, **extra,
        }

    def by_id(self, agent_id: str) -> Optional[AgentSpec]:
        return next((a for a in self.board if a.id == agent_id), None)

    # -- research
    async def research(self, agents: List[AgentSpec]) -> AsyncIterator[Event]:
        jobs: Dict[str, Awaitable[Any]] = {}
        owners: Dict[str, Tuple[AgentSpec, str]] = {}
        for a in agents:
            if "web_research" not in a.tools:
                continue
            for q in a.research_queries:
                if self.searches >= MAX_SEARCHES:
                    break
                self.searches += 1
                key = f"{a.id}:{len(owners)}"
                owners[key] = (a, q)
                jobs[key] = search_web(q)
        if not jobs:
            return
        for a in {o[0].id: o[0] for o in owners.values()}.values():
            yield {"type": "agent_status", "agent_id": a.id, "status": "researching"}
        seen = {s["url"] for s in self.sources}
        found_any = False
        async for key, results, err in _stream_parallel(jobs):
            agent, query = owners[key]
            new = []
            for r in results or []:
                if not r.get("url") or r["url"] in seen:
                    continue
                seen.add(r["url"])
                src = {"id": f"S{len(self.sources) + 1}", "title": r["title"] or r["url"], "url": r["url"],
                       "snippet": r.get("snippet", ""), "agent_id": agent.id, "query": query}
                self.sources.append(src)
                new.append(src)
            found_any = found_any or bool(new)
            yield {"type": "research_result", "agent_id": agent.id, "query": query, "sources": new}
        for a in {o[0].id: o[0] for o in owners.values()}.values():
            yield {"type": "agent_status", "agent_id": a.id, "status": "idle"}
        if not found_any:
            yield {"type": "notice", "level": "warning",
                   "content": "Live research returned no results. Findings rely on general model knowledge and are not source-backed."}

    # -- individual analysis
    async def analyze_agent(self, spec: AgentSpec, focus: str = "") -> Dict[str, Any]:
        assert self.analysis
        user = (
            f"{_situation(self.analysis, self.context)}\n\nSources:\n{_sources_block(self.sources)}\n\n"
            + (f"Specific issue you were brought in to resolve: {focus}\n\n" if focus else "")
            + "Give your analysis from your role's perspective (max ~300 words, markdown). JSON: "
              '{"analysis": str, "key_points": [3-5 short strings], "confidence": 0.0-1.0, '
              '"cited": [source ids you relied on], "open_questions": [str]}'
        )
        raw = await llm.complete_json(_agent_system(spec, self.analysis), user, max_tokens=1200, fallback_text_key="analysis")
        return raw

    async def challenge_agent(self, challenger: Any, role_desc: str) -> Dict[str, Any]:
        assert self.analysis
        others = [a for a in self.board if a.id != getattr(challenger, "id", "")]
        system = (
            _agent_system(challenger, self.analysis) if isinstance(challenger, AgentSpec)
            else f"You are the Chairperson of an AI Boardroom team. {role_desc}"
        )
        user = (
            f"{_situation(self.analysis, self.context)}\n\nTeam analyses so far:\n{_digest(self.messages, ('analysis',))}\n\n"
            "Challenge the analyses: find the most consequential weaknesses, unsupported claims, conflicts between members, "
            "or ignored constraints. Be specific and constructive; at most 3 challenges. Each must target ONE member by id from: "
            f"{[a.id for a in others]}.\n"
            'JSON: {"challenges": [{"target": id, "challenge": str, "severity": "low"|"medium"|"high"}]}'
        )
        return await llm.complete_json(system, user, max_tokens=900)

    async def respond_agent(self, spec: AgentSpec, challenges: List[Dict[str, Any]]) -> Dict[str, Any]:
        assert self.analysis
        mine = next((m for m in self.messages if m["agent_id"] == spec.id and m["kind"] == "analysis"), None)
        user = (
            f"{_situation(self.analysis, self.context)}\n\nYour earlier analysis:\n{(mine or {}).get('content', '')[:1500]}\n\n"
            "Challenges raised against your analysis:\n"
            + "\n".join(f"- ({c['severity']}) from {c['from']}: {c['challenge']}" for c in challenges)
            + "\n\nRespond honestly: concede valid points, defend with evidence where you disagree, and say what you now recommend. "
              'JSON: {"response": str (max ~180 words), "position_changed": bool}'
        )
        return await llm.complete_json(_agent_system(spec, self.analysis), user, max_tokens=700, fallback_text_key="response")

    async def find_gaps(self) -> List[Dict[str, Any]]:
        assert self.analysis
        roster = "\n".join(f"- {a.id}: {a.role}" for a in self.board)
        system = ("You are the Chairperson of an AI Boardroom. Decide whether the discussion exposed an important issue "
                  "that NO current member is qualified to resolve. Only call in a specialist when it would materially change the outcome; "
                  "otherwise return no gaps.")
        user = (
            f"{_situation(self.analysis, self.context)}\n\nCurrent members:\n{roster}\n\nDiscussion:\n"
            f"{_digest(self.messages, ('analysis', 'challenge', 'response'), 700)}\n\n"
            f'JSON: {{"gaps": [{{"issue": str, "reason": str, "specialist": {{"role": str, "archetype": str, "domain": str, '
            f'"expertise": str, "research_queries": [str]}}}}]}} (max {MAX_SPECIALISTS}; [] if none)'
        )
        try:
            raw = await llm.complete_json(system, user, max_tokens=800)
        except llm.BoardroomParseError:
            return []
        return [g for g in (raw.get("gaps") or []) if isinstance(g, dict) and isinstance(g.get("specialist"), dict)][:MAX_SPECIALISTS]

    # -- output
    def artifact_type(self) -> str:
        assert self.analysis
        return self.analysis.desired_output or ARTIFACT_BY_TASK.get(self.analysis.task_types[0], "Analysis Report")

    def _writer_system(self, artifact: str) -> str:
        guide = ARTIFACT_GUIDANCE.get(artifact, DEFAULT_GUIDANCE)
        return (
            f"You are the Chairperson of an AI Boardroom team, producing the final deliverable: a {artifact}. {guide}\n"
            "Rules: lead with the answer/recommendation; use ONLY facts supported by the team's work or the sources; "
            "cite sources as [S#] only with ids that exist; state assumptions; keep the user's constraints and numbers exact; "
            "report unresolved disagreements honestly instead of smoothing them over; the team members are AI perspectives, "
            "never real people. Output clean markdown only."
        )

    async def write_output(self, artifact: str) -> str:
        assert self.analysis
        user = (
            f"{_situation(self.analysis, self.context)}\n\nSources:\n{_sources_block(self.sources)}\n\n"
            f"Team analyses:\n{_digest(self.messages, ('analysis',), 1500)}\n\n"
            f"Challenges and responses:\n{_digest(self.messages, ('challenge', 'response'), 900) or '(none)'}\n\n"
            f"Write the {artifact}."
        )
        return await llm.complete_text(self._writer_system(artifact), user, max_tokens=3500)

    async def quality_check(self, draft: str) -> Dict[str, Any]:
        assert self.analysis
        system = ("You are the Quality Reviewer of an AI Boardroom. Check a draft deliverable against the user's objective and "
                  "constraints: is every requirement addressed, is it internally consistent, are claims supported, is anything "
                  "material missing? Be strict but fair.")
        user = (f"{_situation(self.analysis, self.context)}\n\nDraft:\n{draft[:9000]}\n\n"
                'JSON: {"passed": bool, "score": 0.0-1.0, "issues": [specific fixes needed]}')
        try:
            raw = await llm.complete_json(system, user, max_tokens=700)
        except llm.BoardroomParseError:
            return {"passed": True, "score": None, "issues": [], "note": "Quality reviewer response could not be parsed."}
        return {"passed": bool(raw.get("passed", True)), "score": _conf(raw.get("score"), 0.0) if raw.get("score") is not None else None,
                "issues": [str(i) for i in raw.get("issues") or []][:8]}

    async def revise(self, artifact: str, draft: str, instructions: str) -> str:
        user = (f"Sources:\n{_sources_block(self.sources)}\n\nCurrent draft:\n{draft}\n\n"
                f"Revise the draft to address the following, keeping everything that already works:\n{instructions}\n\n"
                "Return the complete revised document.")
        return await llm.complete_text(self._writer_system(artifact), user, max_tokens=3500, temperature=0.3)

    async def extract_actions(self, content: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        system = "Extract the concrete decisions and action items from this deliverable. Do not invent any."
        user = (content[:8000] + '\n\nJSON: {"decisions": [{"decision": str, "rationale": str}], '
                '"tasks": [{"task": str, "owner_role": str, "priority": "high"|"medium"|"low"}]} (max 8 each)')
        try:
            raw = await llm.complete_json(system, user, max_tokens=900)
        except llm.BoardroomParseError:
            return [], []
        decisions = [d for d in raw.get("decisions") or [] if isinstance(d, dict) and d.get("decision")][:8]
        tasks = [t for t in raw.get("tasks") or [] if isinstance(t, dict) and t.get("task")][:8]
        return decisions, tasks

    def make_output(self, artifact: str, content: str, quality: Dict[str, Any]) -> Dict[str, Any]:
        assert self.analysis
        content, removed = _clean_citations(content, self.sources)
        used = sorted({f"S{n}" for n in CITE_RE.findall(content)}, key=lambda s: int(s[1:]))
        return {
            "version": len(self.outputs) + 1,
            "artifact_type": artifact,
            "title": self.analysis.objective[:90],
            "content": content,
            "disclaimer": disclaimer_for(self.analysis.sensitivity),
            "sources_used": used,
            "quality": {**quality, "removed_invalid_citations": removed},
            "created_at": datetime.utcnow().isoformat(),
        }


# ── public entry points ─────────────────────────────────────────────────────

async def run_boardroom(objective: str, context: str, persist: Persist) -> AsyncIterator[Event]:
    run = _Run(objective, context, persist)

    # 1. Understand the work
    yield run.stage("understand", "Analyzing the work")
    run.analysis = await analyze_work(objective, context)
    yield {"type": "analysis", "analysis": run.analysis.model_dump()}
    await persist({"title": run.analysis.objective[:120], **run.snapshot(status="running")})

    # 2. Assemble the team
    yield run.stage("assemble", "Designing the team")
    plan = await design_board(run.analysis, context)
    run.board, run.rationale = plan.agents, plan.rationale
    yield {"type": "board", "agents": [a.model_dump() for a in run.board], "rationale": run.rationale,
           "tools": {k: v for k, v in TOOL_CATALOG.items()}}
    await persist(run.snapshot())

    # 3. Research
    if any(a.research_queries for a in run.board):
        yield run.stage("research", "Gathering current evidence")
        async for ev in run.research(run.board):
            yield ev
        await persist(run.snapshot())

    # 4. Individual analysis
    yield run.stage("analysis", "Each member analyses the work")
    for a in run.board:
        yield {"type": "agent_status", "agent_id": a.id, "status": "thinking"}
    failures = 0
    async for aid, raw, err in _stream_parallel({a.id: run.analyze_agent(a) for a in run.board}):
        spec = run.by_id(aid)
        assert spec
        if err:
            if _is_config_error(err):
                raise err
            failures += 1
            yield {"type": "agent_error", "agent_id": aid, "content": f"{spec.perspective} could not complete its analysis."}
            yield {"type": "agent_status", "agent_id": aid, "status": "idle"}
            continue
        msg = run.message(spec, "analysis", str(raw.get("analysis", "")).strip(), 1,
                          key_points=[str(k) for k in raw.get("key_points") or []][:5],
                          confidence=_conf(raw.get("confidence")),
                          citations=_valid_ids(raw.get("cited"), run.sources),
                          open_questions=[str(q) for q in raw.get("open_questions") or []][:3])
        yield {"type": "agent_status", "agent_id": aid, "status": "speaking"}
        yield {"type": "agent_message", "message": msg}
        yield {"type": "agent_status", "agent_id": aid, "status": "idle"}
    if failures == len(run.board):
        raise RuntimeError("No board member could complete an analysis. Please try again.")
    await persist(run.snapshot())

    # 5. Collaboration & challenge
    yield run.stage("challenge", "Members challenge each other")
    challengers: List[Any] = [a for a in run.board if a.archetype in CHALLENGER_ARCHETYPES] or [
        AgentSpec(id="chair", role="Chairperson", perspective="Chairperson", archetype="critic")]
    incoming: Dict[str, List[Dict[str, Any]]] = {}
    for c in challengers:
        yield {"type": "agent_status", "agent_id": c.id, "status": "challenging"}
    async for cid, raw, err in _stream_parallel({c.id: run.challenge_agent(
            c, "Play devil's advocate: stress-test the team's analyses.") for c in challengers}):
        c = next(x for x in challengers if x.id == cid)
        if err:
            if _is_config_error(err):
                raise err
            yield {"type": "agent_status", "agent_id": cid, "status": "idle"}
            continue
        for ch in (raw.get("challenges") or [])[:3]:
            target = run.by_id(str(ch.get("target"))) if isinstance(ch, dict) else None
            if not target or target.id == cid or not ch.get("challenge"):
                continue
            severity = ch.get("severity") if ch.get("severity") in ("low", "medium", "high") else "medium"
            msg = run.message(c, "challenge", str(ch["challenge"]).strip(), 2, target=target.id, severity=severity)
            incoming.setdefault(target.id, []).append({"from": c.perspective, "challenge": msg["content"], "severity": severity})
            yield {"type": "agent_status", "agent_id": cid, "status": "speaking"}
            yield {"type": "agent_message", "message": msg}
        yield {"type": "agent_status", "agent_id": cid, "status": "idle"}

    for tid in incoming:
        yield {"type": "agent_status", "agent_id": tid, "status": "thinking"}
    async for tid, raw, err in _stream_parallel({t: run.respond_agent(run.by_id(t), chs) for t, chs in incoming.items()}):
        spec = run.by_id(tid)
        assert spec
        if err:
            if _is_config_error(err):
                raise err
            yield {"type": "agent_status", "agent_id": tid, "status": "idle"}
            continue
        msg = run.message(spec, "response", str(raw.get("response", "")).strip(), 2,
                          position_changed=bool(raw.get("position_changed", False)))
        yield {"type": "agent_status", "agent_id": tid, "status": "speaking"}
        yield {"type": "agent_message", "message": msg}
        yield {"type": "agent_status", "agent_id": tid, "status": "idle"}
    await persist(run.snapshot())

    # 6. Chairperson: does a specialist need to join?
    joined = 0
    for gap in await run.find_gaps():
        if sum(1 for a in run.board if not a.temporary) >= MAX_AGENTS:
            break
        spec = build_spec(gap["specialist"], {a.id for a in run.board}, temporary=True)
        run.board.append(spec)
        joined += 1
        yield run.stage("join", f"{spec.perspective} joins: {gap.get('issue', '')}")
        yield {"type": "agent_join", "agent": spec.model_dump(), "reason": str(gap.get("issue", "")), "chair_note": str(gap.get("reason", ""))}
        async for ev in run.research([spec]):
            yield ev
        yield {"type": "agent_status", "agent_id": spec.id, "status": "thinking"}
        try:
            raw = await run.analyze_agent(spec, focus=str(gap.get("issue", "")))
            msg = run.message(spec, "analysis", str(raw.get("analysis", "")).strip(), 3,
                              key_points=[str(k) for k in raw.get("key_points") or []][:5],
                              confidence=_conf(raw.get("confidence")),
                              citations=_valid_ids(raw.get("cited"), run.sources), open_questions=[])
            yield {"type": "agent_status", "agent_id": spec.id, "status": "speaking"}
            yield {"type": "agent_message", "message": msg}
        except Exception as e:  # noqa: BLE001
            if _is_config_error(e):
                raise
            yield {"type": "agent_error", "agent_id": spec.id, "content": f"{spec.perspective} could not complete its analysis."}
        yield {"type": "agent_leave", "agent_id": spec.id, "reason": "Issue addressed; specialist leaves the active discussion."}
    if joined:
        await persist(run.snapshot())

    # 7. Create the deliverable, then quality-review it
    artifact = run.artifact_type()
    yield run.stage("output", f"Drafting the {artifact}")
    yield {"type": "agent_status", "agent_id": "chair", "status": "thinking"}
    draft = await run.write_output(artifact)
    yield run.stage("quality", "Quality review")
    quality = await run.quality_check(draft)
    _, bad_cites = _clean_citations(draft, run.sources)
    if bad_cites:
        quality["passed"] = False
        quality["issues"] = quality.get("issues", []) + [f"Remove or fix citations that match no source: {', '.join(sorted(set(bad_cites)))}"]
    revised = False
    if not quality["passed"] and quality["issues"]:
        draft = await run.revise(artifact, draft, "\n".join(f"- {i}" for i in quality["issues"]))
        revised = True
    quality["revised"] = revised
    yield {"type": "quality", "quality": quality}
    output = run.make_output(artifact, draft, quality)
    run.outputs.append(output)
    run.decisions, run.tasks = await run.extract_actions(output["content"])
    yield {"type": "agent_status", "agent_id": "chair", "status": "idle"}
    yield {"type": "output", "output": output, "decisions": run.decisions, "tasks": run.tasks, "sources": run.sources}
    run.stage("complete")
    await persist(run.snapshot(status="complete"))
    yield {"type": "done"}


async def refine_boardroom(state: Dict[str, Any], feedback: str, persist: Persist) -> AsyncIterator[Event]:
    """User review -> refine: the Chairperson revises the latest deliverable with the user's feedback."""
    run = _Run(state.get("objective", ""), state.get("context", ""), persist, state)
    if not run.analysis or not run.outputs:
        raise ValueError("This boardroom has no deliverable to refine yet.")
    yield run.stage("refine", "Refining the deliverable with your feedback")
    yield {"type": "agent_status", "agent_id": "chair", "status": "thinking"}
    latest = run.outputs[-1]
    draft = await run.revise(latest["artifact_type"], latest["content"], f"User feedback:\n{feedback[:3000]}")
    quality = {"passed": True, "score": None, "issues": [], "revised": True}
    output = run.make_output(latest["artifact_type"], draft, quality)
    run.outputs.append(output)
    run.decisions, run.tasks = await run.extract_actions(output["content"])
    run.message(USER, "feedback", feedback[:3000], 4)
    yield {"type": "agent_status", "agent_id": "chair", "status": "idle"}
    yield {"type": "output", "output": output, "decisions": run.decisions, "tasks": run.tasks, "sources": run.sources}
    await persist(run.snapshot(status="complete"))
    yield {"type": "done"}
