"""Work Analyzer: works out what the user is actually trying to accomplish."""
from datetime import date
from typing import Any, Dict, List

from app.boardroom import llm
from app.boardroom.archetypes import ARTIFACT_BY_TASK, SENSITIVITY_DISCLAIMERS, TASK_TYPES
from app.boardroom.schemas import WorkAnalysis

SYSTEM = f"""You are the Work Analyzer of AI Boardroom, a universal work platform. Users bring ANY problem
(business, education, legal/compliance, health administration, events, travel, personal planning, engineering, ...).
Do not assume the user's profession. Work out what they are trying to accomplish.

Return JSON with:
- "objective": one clear sentence
- "domain": the professional/knowledge domain (short, e.g. "event management", "software architecture")
- "task_types": 1-3 from {TASK_TYPES}, primary first
- "complexity": "simple" | "moderate" | "complex" | "very_complex"  (how many distinct perspectives are truly needed)
- "constraints": list of stated or implied constraints (budget, deadline, geography, regulations, skill level, ...); copy numbers/currencies exactly as the user wrote them
- "desired_output": what the user ultimately needs (e.g. "event plan", "decision brief", "resume rewrite")
- "needs_live_research": true if the work depends on current/external facts (prices, news, regulations, competitors, releases)
- "sensitivity": subset of ["legal","medical","financial","safety"] for high-stakes areas where AI analysis must not be presented as professional advice
- "summary": 1-2 sentences restating the work and what a good result looks like
Today's date is {{today}}."""


def _heuristic(objective: str) -> WorkAnalysis:
    words = len(objective.split())
    complexity = "simple" if words < 15 else "moderate" if words < 60 else "complex"
    return WorkAnalysis(objective=objective.strip()[:300], complexity=complexity, summary=objective.strip()[:300])


def normalize(raw: Dict[str, Any], objective: str) -> WorkAnalysis:
    task_types: List[str] = [t for t in (str(x).lower().replace(" ", "_").replace("-", "_") for x in raw.get("task_types") or []) if t in TASK_TYPES]
    complexity = raw.get("complexity")
    if complexity not in ("simple", "moderate", "complex", "very_complex"):
        complexity = "moderate"
    sensitivity = [s for s in (str(x).lower() for x in raw.get("sensitivity") or []) if s in SENSITIVITY_DISCLAIMERS]
    desired = str(raw.get("desired_output") or "").strip()
    return WorkAnalysis(
        objective=str(raw.get("objective") or objective).strip(),
        domain=str(raw.get("domain") or "general").strip(),
        task_types=task_types or ["analysis"],
        complexity=complexity,
        constraints=[str(c) for c in raw.get("constraints") or []][:10],
        desired_output=desired or ARTIFACT_BY_TASK.get((task_types or ["analysis"])[0], "Analysis Report"),
        needs_live_research=bool(raw.get("needs_live_research", False)),
        sensitivity=sensitivity,
        summary=str(raw.get("summary") or objective).strip(),
    )


async def analyze_work(objective: str, context: str = "") -> WorkAnalysis:
    user = f"User request:\n{objective}"
    if context.strip():
        user += f"\n\nAdditional context supplied by the user:\n{context[:4000]}"
    try:
        raw = await llm.complete_json(SYSTEM.replace("{today}", date.today().isoformat()), user, max_tokens=900)
    except llm.BoardroomParseError:
        return _heuristic(objective)
    return normalize(raw, objective)
