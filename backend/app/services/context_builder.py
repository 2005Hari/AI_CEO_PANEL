"""
UnifiedContextBuilder — single source of company memory for all agents.

All agent execution paths (boardroom, manager, task engine) must consume this builder.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CompanyOperatingProfile,
    DecisionLog,
    FounderProfile,
    Objective,
    Project,
    Task,
    User,
)
from app.services.embeddings import similarity_search
from app.services.operating_profile import get_or_create_operating_profile, operating_profile_to_dict


@dataclass
class UnifiedContext:
    """Structured + rendered context for agent prompts."""
    structured: Dict[str, Any] = field(default_factory=dict)
    prompt_text: str = ""


class UnifiedContextBuilder:
    @staticmethod
    async def build(
        db: AsyncSession,
        project_id: str,
        *,
        user_id: Optional[str] = None,
        rag_query: Optional[str] = None,
        include_rag: bool = True,
        max_decisions: int = 5,
        max_tasks: int = 5,
        max_objectives: int = 10,
    ) -> UnifiedContext:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        if not project:
            return UnifiedContext(
                structured={"error": "project_not_found"},
                prompt_text="No project context available.",
            )

        profile = await get_or_create_operating_profile(db, project_id)
        profile_data = operating_profile_to_dict(profile)

        founder_data: Dict[str, Any] = {}
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if user:
                result = await db.execute(
                    select(FounderProfile).where(FounderProfile.user_id == user.id)
                )
                fp = result.scalars().first()
                if fp:
                    founder_data = {
                        "display_name": fp.display_name,
                        "timezone": fp.timezone,
                        "expertise": fp.expertise or [],
                        "founding_goals": fp.founding_goals or [],
                        "preferences": fp.preferences or {},
                    }

        result = await db.execute(
            select(Objective)
            .where(Objective.project_id == project_id, Objective.status == "active")
            .order_by(Objective.created_at.desc())
            .limit(max_objectives)
        )
        objectives = [
            {"id": o.id, "title": o.title, "category": o.category, "progress": o.progress}
            for o in result.scalars().all()
        ]

        result = await db.execute(
            select(Task)
            .where(Task.project_id == project_id, Task.status == "completed")
            .order_by(Task.completed_at.desc())
            .limit(max_tasks)
        )
        recent_tasks = [
            {
                "id": t.id,
                "title": t.title,
                "assigned_agent": t.assigned_agent,
                "output_preview": (json.dumps(t.output_result)[:200] if t.output_result else None),
            }
            for t in result.scalars().all()
        ]

        result = await db.execute(
            select(DecisionLog)
            .where(DecisionLog.project_id == project_id)
            .order_by(DecisionLog.created_at.desc())
            .limit(max_decisions)
        )
        decisions = [
            {
                "id": d.id,
                "type": d.decision_type,
                "source": d.source,
                "summary": d.summary,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in result.scalars().all()
        ]

        rag_snippets: List[str] = []
        if include_rag and rag_query:
            try:
                memories = await similarity_search(db, project_id, rag_query, limit=3)
                rag_snippets = [m.content for m in memories]
            except Exception:
                rag_snippets = []

        structured = {
            "project": {
                "id": project.id,
                "name": project.name,
                "operating_mode": project.operating_mode,
                "discovery_completed": project.discovery_completed,
            },
            "operating_profile": profile_data,
            "founder_profile": founder_data,
            "active_objectives": objectives,
            "recent_completed_tasks": recent_tasks,
            "recent_decisions": decisions,
            "rag_snippets": rag_snippets,
        }

        prompt_text = UnifiedContextBuilder._render_prompt(structured)
        return UnifiedContext(structured=structured, prompt_text=prompt_text)

    @staticmethod
    def _render_prompt(structured: Dict[str, Any]) -> str:
        profile = structured.get("operating_profile", {})
        founder = structured.get("founder_profile", {})
        project = structured.get("project", {})

        lines = [
            "=== COMPANY OPERATING CONTEXT ===",
            f"Company: {profile.get('company_name') or project.get('name', 'N/A')}",
            f"Industry: {profile.get('industry', 'N/A')}",
            f"Business Model: {profile.get('business_model', 'N/A')}",
            f"Value Proposition: {profile.get('value_proposition', 'N/A')}",
            f"Target Audience: {profile.get('target_audience', 'N/A')}",
            f"Market Positioning: {profile.get('market_positioning', 'N/A')}",
            f"Growth Stage: {profile.get('growth_stage', 'N/A')}",
            f"Tech Stack: {profile.get('tech_stack', 'N/A')}",
            f"Current Goals: {json.dumps(profile.get('current_goals', []))}",
            f"Current Problems: {json.dumps(profile.get('current_problems', []))}",
            f"Risks: {json.dumps(profile.get('risks', []))}",
        ]

        if founder:
            lines.extend([
                "",
                "=== FOUNDER PROFILE ===",
                f"Display Name: {founder.get('display_name', 'N/A')}",
                f"Expertise: {json.dumps(founder.get('expertise', []))}",
                f"Founding Goals: {json.dumps(founder.get('founding_goals', []))}",
            ])

        objectives = structured.get("active_objectives", [])
        if objectives:
            lines.append("\n=== ACTIVE OBJECTIVES ===")
            for obj in objectives:
                lines.append(f"- [{obj.get('category', 'general')}] {obj.get('title')} ({int((obj.get('progress') or 0) * 100)}%)")

        decisions = structured.get("recent_decisions", [])
        if decisions:
            lines.append("\n=== RECENT DECISIONS ===")
            for dec in decisions:
                lines.append(f"- ({dec.get('source')}) {dec.get('summary')}")

        tasks = structured.get("recent_completed_tasks", [])
        if tasks:
            lines.append("\n=== RECENT COMPLETED TASKS ===")
            for task in tasks:
                lines.append(f"- [{task.get('assigned_agent', 'agent')}] {task.get('title')}")

        rag = structured.get("rag_snippets", [])
        if rag:
            lines.append("\n=== RELEVANT DOCUMENT KNOWLEDGE (RAG) ===")
            for idx, snippet in enumerate(rag, 1):
                lines.append(f"[{idx}] {snippet}")

        return "\n".join(lines)
