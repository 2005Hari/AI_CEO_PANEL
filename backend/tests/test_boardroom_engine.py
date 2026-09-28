"""Tests for the universal AI Boardroom engine (analyzer, architect, engine, API)."""
import json
from typing import Any, Dict, List

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps.auth import get_current_user
from app.boardroom import architect, engine, llm, research
from app.boardroom.schemas import WorkAnalysis
from app.main import app


def _events(body: str) -> List[Dict[str, Any]]:
    return [json.loads(l[6:]) for l in body.splitlines() if l.startswith("data: ")]


class FakeLLM:
    """Scripted model: routes on the system prompt so each pipeline stage gets a plausible answer."""

    def __init__(self, analysis=None, agents=None, gaps=None, quality_ok=True, draft="# Plan\nDo the thing [S1] [S9]."):
        self.analysis = analysis or {
            "objective": "Plan a wedding for 500 guests with a Rs 15 lakh budget", "domain": "event planning",
            "task_types": ["planning"], "complexity": "complex", "constraints": ["budget Rs 15 lakh", "500 guests"],
            "desired_output": "Execution Plan", "needs_live_research": True, "sensitivity": [], "summary": "Wedding plan."}
        self.agents = agents or [
            {"role": "Event Planner", "archetype": "strategist", "domain": "weddings"},
            {"role": "Budget Specialist", "archetype": "financial_analyst", "domain": "weddings"},
            {"role": "Venue Researcher", "archetype": "researcher", "tools": ["web_research"], "research_queries": ["wedding venues 500 guests"]},
            {"role": "Risk Specialist", "archetype": "risk_analyst"},
        ]
        self.gaps = gaps or []
        self.quality_ok = quality_ok
        self.draft = draft
        self.calls: List[str] = []

    async def __call__(self, messages, temperature=0.3, max_tokens=2048):
        system, user = messages[0]["content"], messages[-1]["content"]
        if "Work Analyzer" in system:
            self.calls.append("analyze"); return json.dumps(self.analysis)
        if "Board Architect" in system:
            self.calls.append("architect"); return json.dumps({"rationale": "Because.", "agents": self.agents})
        if "Chairperson of an AI Boardroom. Decide" in system:
            self.calls.append("gaps"); return json.dumps({"gaps": self.gaps})
        if "Quality Reviewer of an AI Boardroom" in system:
            self.calls.append("quality")
            return json.dumps({"passed": self.quality_ok, "score": 0.8, "issues": [] if self.quality_ok else ["Missing budget table"]})
        if "Extract the concrete decisions" in system:
            self.calls.append("extract")
            return json.dumps({"decisions": [{"decision": "Book venue", "rationale": "Capacity"}], "tasks": [{"task": "Shortlist venues", "owner_role": "Venue Researcher", "priority": "high"}]})
        if "producing the final deliverable" in system:
            self.calls.append("revise" if "Revise the draft" in user else "write")
            return "# Revised\nFixed [S1]." if "Revise the draft" in user else self.draft
        if "Challenge the analyses" in user:
            self.calls.append("challenge")
            ids = [t.strip(" '[]") for t in user.split("from:")[1].split("]")[0].split(",")]
            return json.dumps({"challenges": [{"target": ids[0], "challenge": "Your numbers ignore the budget.", "severity": "high"}, {"target": "ghost", "challenge": "x"}]})
        if "Challenges raised against your analysis" in user:
            self.calls.append("respond"); return json.dumps({"response": "Fair point; I revise.", "position_changed": True})
        self.calls.append("analysis")
        return json.dumps({"analysis": "My view [S1] and [S7].", "key_points": ["a", "b"], "confidence": 0.7, "cited": ["S1", "S99"], "open_questions": []})


@pytest.fixture
def fake_search(monkeypatch):
    async def _search(q):
        return [{"title": "Venue guide", "url": "https://example.com/v", "snippet": "Venues"},
                {"title": "Dup", "url": "https://example.com/v", "snippet": "dup"}]
    monkeypatch.setattr(engine, "search_web", _search)


async def _collect(persisted: List[Dict[str, Any]], objective="wedding", context=""):
    async def persist(f):
        persisted.append(f)
    return [e async for e in engine.run_boardroom(objective, context, persist)]


async def test_full_run_streams_every_stage(monkeypatch, fake_search):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "chat", fake)
    persisted: List[Dict[str, Any]] = []
    events = await _collect(persisted)
    types = [e["type"] for e in events]
    assert types[0] == "stage" and types[-1] == "done"
    for needed in ("analysis", "board", "research_result", "agent_message", "quality", "output"):
        assert needed in types
    stages = [e["stage"] for e in events if e["type"] == "stage"]
    assert stages == ["understand", "assemble", "research", "analysis", "challenge", "output", "quality"]

    board = next(e for e in events if e["type"] == "board")
    assert [a["role"] for a in board["agents"]][:2] == ["Event Planner", "Budget Specialist"]
    assert all(a["perspective"].endswith("Perspective") for a in board["agents"])

    msgs = [e["message"] for e in events if e["type"] == "agent_message"]
    assert {m["kind"] for m in msgs} == {"analysis", "challenge", "response"}
    # Fabricated citations (S99, S7) never survive; the real one does.
    analyses = [m for m in msgs if m["kind"] == "analysis"]
    assert all(m["citations"] == ["S1"] for m in analyses)

    out = next(e for e in events if e["type"] == "output")["output"]
    assert out["artifact_type"] == "Execution Plan"
    assert "[S9]" not in out["content"] and "[S1]" in out["content"]
    assert out["quality"]["removed_invalid_citations"] == []  # already revised away
    assert persisted[-1]["status"] == "complete" and persisted[-1]["decisions"][0]["decision"] == "Book venue"
    assert persisted[-1]["sources"][0]["id"] == "S1" and len(persisted[-1]["sources"]) == 1  # deduped


async def test_invalid_citation_triggers_revision(monkeypatch, fake_search):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "chat", fake)
    events = await _collect([])
    assert "revise" in fake.calls
    assert next(e for e in events if e["type"] == "quality")["quality"]["revised"] is True


async def test_quality_failure_revises_once(monkeypatch, fake_search):
    fake = FakeLLM(quality_ok=False, draft="Clean draft [S1].")
    monkeypatch.setattr(llm, "chat", fake)
    events = await _collect([])
    assert fake.calls.count("revise") == 1
    assert next(e for e in events if e["type"] == "output")["output"]["content"].startswith("# Revised")


async def test_work_determines_the_team(monkeypatch):
    """A different problem yields a different team, artifact and no research when none is needed."""
    fake = FakeLLM(
        analysis={"objective": "Review my resume", "domain": "careers", "task_types": ["review"], "complexity": "simple",
                  "desired_output": "", "needs_live_research": False, "sensitivity": []},
        agents=[{"role": "Recruiter", "archetype": "expert"}, {"role": "ATS Specialist", "archetype": "expert"}])
    monkeypatch.setattr(llm, "chat", fake)
    events = await _collect([], "review my resume")
    board = next(e for e in events if e["type"] == "board")
    assert [a["role"] for a in board["agents"]] == ["Recruiter", "ATS Specialist"]  # 2-agent team, no forced extras
    assert "research" not in [e.get("stage") for e in events]
    assert next(e for e in events if e["type"] == "output")["output"]["artifact_type"] == "Review Report"


async def test_sensitive_work_gets_disclaimer(monkeypatch, fake_search):
    fake = FakeLLM(analysis={"objective": "Review contract compliance", "domain": "compliance", "task_types": ["review"],
                             "complexity": "moderate", "sensitivity": ["legal", "bogus"], "needs_live_research": False})
    monkeypatch.setattr(llm, "chat", fake)
    events = await _collect([])
    out = next(e for e in events if e["type"] == "output")["output"]
    assert "not legal advice" in out["disclaimer"]


async def test_chairperson_brings_in_and_releases_specialist(monkeypatch, fake_search):
    gaps = [{"issue": "Fire-safety approvals", "reason": "Nobody covers permits",
             "specialist": {"role": "Safety Compliance Specialist", "archetype": "expert", "domain": "safety"}}]
    monkeypatch.setattr(llm, "chat", FakeLLM(gaps=gaps))
    events = await _collect([])
    types = [e["type"] for e in events]
    assert types.index("agent_join") < types.index("agent_leave")
    join = next(e for e in events if e["type"] == "agent_join")
    assert join["agent"]["temporary"] and join["reason"] == "Fire-safety approvals"
    between = events[types.index("agent_join"):types.index("agent_leave")]
    assert any(e["type"] == "agent_message" and e["message"]["round"] == 3 for e in between)


async def test_research_unavailable_is_reported_not_faked(monkeypatch):
    async def none(q):
        return []
    monkeypatch.setattr(engine, "search_web", none)
    monkeypatch.setattr(llm, "chat", FakeLLM())
    events = await _collect([])
    assert any(e["type"] == "notice" and "not source-backed" in e["content"] for e in events)


async def test_missing_api_key_surfaces(monkeypatch):
    async def boom(*a, **k):
        raise ValueError("NVIDIA_API_KEY is not configured.")
    monkeypatch.setattr(llm, "chat", boom)
    with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
        await _collect([])


async def test_agent_failure_does_not_sink_the_board(monkeypatch, fake_search):
    fake = FakeLLM()
    orig = fake.__call__

    async def flaky(messages, temperature=0.3, max_tokens=2048):
        if "Budget Specialist Perspective" in messages[0]["content"]:
            raise RuntimeError("upstream 500")
        return await orig(messages, temperature, max_tokens)
    monkeypatch.setattr(llm, "chat", flaky)
    events = await _collect([])
    assert any(e["type"] == "agent_error" and e["agent_id"] == "budget_specialist" for e in events)
    assert events[-1]["type"] == "done"


async def test_refine_adds_a_new_version(monkeypatch, fake_search):
    monkeypatch.setattr(llm, "chat", FakeLLM())
    persisted: List[Dict[str, Any]] = []
    await _collect(persisted)
    state = {**persisted[-1], "objective": "wedding", "context": ""}

    async def persist(f):
        persisted.append(f)
    events = [e async for e in engine.refine_boardroom(state, "Make it cheaper", persist)]
    out = next(e for e in events if e["type"] == "output")["output"]
    assert out["version"] == 2 and persisted[-1]["outputs"][-1]["version"] == 2 and len(persisted[-1]["outputs"]) == 2
    assert persisted[-1]["messages"][-1]["kind"] == "feedback"


# ── Board Architect / Agent Factory ─────────────────────────────────────────

def _analysis(**kw):
    return WorkAnalysis(objective="x", domain="d", **kw)


def test_architect_caps_team_and_validates_fields():
    raw = [{"role": f"Role {i}", "archetype": "not-real", "tools": ["web_research", "teleport"], "research_queries": ["q"]} for i in range(15)]
    specs = architect.sanitize(raw, _analysis())
    assert len(specs) == architect.MAX_AGENTS
    assert len({s.id for s in specs}) == len(specs)
    assert all(s.archetype in ("expert", "critic") for s in specs)
    assert all("teleport" not in s.tools for s in specs)


def test_architect_guarantees_a_challenger_for_bigger_teams():
    specs = architect.sanitize([{"role": r, "archetype": "expert"} for r in ("A", "B", "C")], _analysis())
    assert any(s.archetype == "critic" for s in specs) and len(specs) == 4


def test_architect_small_team_needs_no_challenger_and_bad_output_falls_back():
    assert len(architect.sanitize([{"role": "A"}, {"role": "B"}], _analysis())) == 2
    fallback = architect.sanitize([], _analysis())
    assert len(fallback) >= 2 and any(s.archetype == "risk_analyst" for s in fallback)


def test_queries_dropped_without_web_tool_and_ids_deduped():
    specs = architect.sanitize([{"role": "Analyst", "archetype": "financial_analyst", "research_queries": ["q"]},
                                {"role": "Analyst", "archetype": "expert"}], _analysis())
    assert specs[0].research_queries == [] and specs[0].id != specs[1].id


async def test_analyzer_falls_back_when_json_is_garbage(monkeypatch):
    async def junk(*a, **k):
        return "I cannot do JSON"
    monkeypatch.setattr(llm, "chat", junk)
    from app.boardroom.analyzer import analyze_work
    result = await analyze_work("Help me pick a laptop")
    assert result.objective == "Help me pick a laptop" and result.task_types == ["analysis"]


def test_json_extraction_tolerates_fences_and_prose():
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.extract_json('Sure! {"a": 1} hope that helps') == {"a": 1}
    assert llm.extract_json("nothing") is None


def test_duckduckgo_parser():
    page = ('<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&amp;rut=1">Hello <b>World</b></a>'
            '<a class="result__snippet" href="x">A &amp; B snippet</a>')
    r = research.parse_duckduckgo(page)
    assert r == [{"title": "Hello World", "url": "https://example.com/a", "snippet": "A & B snippet"}]


# ── API ─────────────────────────────────────────────────────────────────────

async def test_api_run_persist_list_refine_and_isolation(monkeypatch, fake_search, client, second_user):
    monkeypatch.setattr(llm, "chat", FakeLLM())
    r = await client.post("/api/v1/boardrooms/stream", json={"objective": "Plan a wedding for 500 guests", "context": "Mumbai"})
    assert r.status_code == 200
    events = _events(r.text)
    assert events[0]["type"] == "boardroom_created" and events[-1]["type"] == "done"
    bid = events[0]["boardroom_id"]

    detail = (await client.get(f"/api/v1/boardrooms/{bid}")).json()
    assert detail["status"] == "complete" and detail["outputs"][0]["artifact_type"] == "Execution Plan"
    assert detail["board"]["agents"] and detail["messages"] and detail["history"] and detail["tasks"]

    listing = (await client.get("/api/v1/boardrooms")).json()
    assert any(b["id"] == bid and b["team_size"] == 4 for b in listing)

    r = await client.post(f"/api/v1/boardrooms/{bid}/refine", json={"feedback": "Shorter please"})
    assert _events(r.text)[-1]["type"] == "done"
    assert len((await client.get(f"/api/v1/boardrooms/{bid}")).json()["outputs"]) == 2

    async def other():
        return second_user
    app.dependency_overrides[get_current_user] = other
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.get(f"/api/v1/boardrooms/{bid}")).status_code == 404
        assert (await ac.delete(f"/api/v1/boardrooms/{bid}")).status_code == 404
        assert (await ac.get("/api/v1/boardrooms")).json() == []


async def test_api_failure_is_reported_and_stored(monkeypatch, client):
    async def boom(*a, **k):
        raise ValueError("NVIDIA_API_KEY is not configured.")
    monkeypatch.setattr(llm, "chat", boom)
    r = await client.post("/api/v1/boardrooms/stream", json={"objective": "Anything at all"})
    events = _events(r.text)
    assert events[-1]["type"] == "error" and "NVIDIA_API_KEY" in events[-1]["content"]
    bid = events[0]["boardroom_id"]
    detail = (await client.get(f"/api/v1/boardrooms/{bid}")).json()
    assert detail["status"] == "failed" and "NVIDIA_API_KEY" in detail["error"]


async def test_api_refine_requires_deliverable_and_delete(client, db_session, mock_user):
    from app.db.models import Boardroom
    b = Boardroom(user_id=mock_user.id, objective="empty one")
    db_session.add(b)
    await db_session.commit()
    assert (await client.post(f"/api/v1/boardrooms/{b.id}/refine", json={"feedback": "x"})).status_code == 409
    assert (await client.delete(f"/api/v1/boardrooms/{b.id}")).status_code == 204
    assert (await client.get(f"/api/v1/boardrooms/{b.id}")).status_code == 404
