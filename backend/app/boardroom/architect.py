"""Board Architect + Agent Factory: turn the analyzed work into a minimal expert team."""
import re
from typing import Any, Dict, List, Optional

from app.boardroom import llm
from app.boardroom.archetypes import ARCHETYPES, TOOL_CATALOG
from app.boardroom.schemas import AgentSpec, BoardPlan, WorkAnalysis

MAX_AGENTS = 10
MIN_AGENTS = 2
SIZE_GUIDE = {"simple": "2-3", "moderate": "3-5", "complex": "5-8", "very_complex": "8-10"}
CHALLENGER_ARCHETYPES = ("critic", "risk_analyst")

SYSTEM = f"""You are the Board Architect of AI Boardroom. Given an analyzed piece of work, design the MINIMUM team of
expert PERSPECTIVES that gives maximum useful coverage. The work determines the team: never use a fixed template,
and never add a member who would not change the outcome.

Rules:
- Team size guide by complexity: {SIZE_GUIDE}. Hard maximum {MAX_AGENTS}.
- Every agent is an expert PERSPECTIVE, not a real person. Never invent credentials, employers or names.
- Roles must be specific to this work (e.g. "Venue Researcher", not "Researcher").
- Build each agent from one archetype in {list(ARCHETYPES)}. Include at least one challenger (critic or risk_analyst) when there are 3+ agents.
- Choose tools per agent from {list(TOOL_CATALOG)}. Give web_research only to agents that genuinely need current external facts.
- For agents with web_research, give 1-2 concrete "research_queries" (search-engine style, with the domain/place/year where relevant). Use [] otherwise.
- Be candid in "rationale" about why this team, in 1-2 sentences.

Return JSON: {{"rationale": str, "agents": [{{"role": str, "archetype": str, "domain": str, "expertise": str,
"objectives": [str], "priorities": [str], "research_lens": str, "research_queries": [str], "tools": [str],
"constraints": [str]}}]}}"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "agent"


def build_spec(raw: Dict[str, Any], taken: set, temporary: bool = False) -> AgentSpec:
    """Agent Factory: adapt an archetype to this work and validate the result."""
    role = str(raw.get("role") or "Domain Expert").strip()[:60]
    archetype = str(raw.get("archetype") or "expert").lower()
    if archetype not in ARCHETYPES:
        archetype = "expert"
    arche = ARCHETYPES[archetype]

    base = slugify(role)
    agent_id, n = base, 2
    while agent_id in taken:
        agent_id, n = f"{base}_{n}", n + 1
    taken.add(agent_id)

    tools = [t for t in (raw.get("tools") or []) if t in TOOL_CATALOG] or list(arche["tools"])
    lens = str(raw.get("research_lens") or "")
    queries = [str(q).strip() for q in (raw.get("research_queries") or []) if str(q).strip()][:2]
    if "web_research" not in tools:
        queries = []

    def strs(key: str, limit: int = 5) -> List[str]:
        return [str(x) for x in (raw.get(key) or [])][:limit]

    return AgentSpec(
        id=agent_id,
        role=role,
        perspective=f"{role} Perspective",
        archetype=archetype,
        domain=str(raw.get("domain") or ""),
        expertise=str(raw.get("expertise") or arche["label"]),
        objectives=strs("objectives"),
        priorities=strs("priorities"),
        behavior=arche["behavior"],
        research_lens=lens,
        research_queries=queries,
        tools=tools,
        constraints=strs("constraints"),
        quality_criteria=list(arche["quality_criteria"]),
        temporary=temporary,
    )


def _fallback_board(analysis: WorkAnalysis) -> List[Dict[str, Any]]:
    d = analysis.domain if analysis.domain != "general" else "the subject"
    return [
        {"role": f"{d.title()} Expert", "archetype": "expert", "domain": d, "expertise": f"Practical knowledge of {d}"},
        {"role": "Researcher", "archetype": "researcher", "domain": d, "tools": ["web_research"],
         "research_queries": [analysis.objective[:120]]},
        {"role": "Strategist", "archetype": "strategist", "domain": d},
        {"role": "Risk Analyst", "archetype": "risk_analyst", "domain": d},
    ]


def sanitize(raw_agents: List[Dict[str, Any]], analysis: WorkAnalysis) -> List[AgentSpec]:
    taken: set = set()
    specs = [build_spec(a, taken) for a in raw_agents if isinstance(a, dict)][:MAX_AGENTS]
    if len(specs) < MIN_AGENTS:
        specs = [build_spec(a, set()) for a in _fallback_board(analysis)][:MAX_AGENTS]
        taken = {s.id for s in specs}
    if len(specs) >= 3 and not any(s.archetype in CHALLENGER_ARCHETYPES for s in specs):
        if len(specs) >= MAX_AGENTS:
            specs = specs[:-1]
        specs.append(build_spec({"role": "Devil's Advocate", "archetype": "critic", "domain": analysis.domain}, taken))
    return specs


async def design_board(analysis: WorkAnalysis, context: str = "") -> BoardPlan:
    user = "Analyzed work:\n" + analysis.model_dump_json(indent=2)
    if context.strip():
        user += f"\n\nUser-supplied context (excerpt):\n{context[:2000]}"
    try:
        raw = await llm.complete_json(SYSTEM, user, max_tokens=2200)
    except llm.BoardroomParseError:
        raw = {"rationale": "Default team (the architect's response could not be parsed).", "agents": _fallback_board(analysis)}
    agents = sanitize(raw.get("agents") or [], analysis)
    return BoardPlan(agents=agents, rationale=str(raw.get("rationale") or ""))
