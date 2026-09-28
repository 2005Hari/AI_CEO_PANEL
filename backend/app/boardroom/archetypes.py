"""Reusable expert archetypes and the tool catalog.

Agents are generated from these archetypes by the Board Architect and adapted
to the work at hand (e.g. the ``researcher`` archetype becomes a "Policy
Researcher" or a "Competitive Intelligence Researcher").
"""
from typing import Dict, List

ARCHETYPES: Dict[str, Dict] = {
    "expert": {
        "label": "Domain Expert",
        "behavior": "Provides deep, concrete domain knowledge. Explains how things actually work in this field and what good practice looks like.",
        "tools": ["web_research", "document_analysis"],
        "quality_criteria": ["Technically accurate", "Specific to this situation, not generic"],
    },
    "researcher": {
        "label": "Researcher",
        "behavior": "Finds and weighs current evidence. Separates what sources say from inference, and flags where evidence is thin or dated.",
        "tools": ["web_research", "document_analysis"],
        "quality_criteria": ["Claims tied to sources", "Recency and reliability of evidence noted"],
    },
    "critic": {
        "label": "Critic",
        "behavior": "Looks for weaknesses, hidden assumptions and blind spots. Challenges other members constructively and specifically.",
        "tools": ["document_analysis"],
        "quality_criteria": ["Objections are specific and testable", "Distinguishes fatal flaws from nitpicks"],
    },
    "strategist": {
        "label": "Strategist",
        "behavior": "Thinks about long-term implications, trade-offs, sequencing and second-order effects.",
        "tools": ["web_research", "document_analysis"],
        "quality_criteria": ["Explicit trade-offs", "Clear priorities and sequencing"],
    },
    "operator": {
        "label": "Operator",
        "behavior": "Focuses on execution: who does what, by when, with which resources, and what will realistically go wrong on the ground.",
        "tools": ["document_analysis", "spreadsheet_models"],
        "quality_criteria": ["Actionable steps", "Realistic about time, people and resources"],
    },
    "customer": {
        "label": "Customer / Stakeholder",
        "behavior": "Represents the end user, customer or affected stakeholder. Speaks to needs, friction and what they would actually value or reject.",
        "tools": ["web_research"],
        "quality_criteria": ["Grounded in real user needs", "Calls out friction and unmet expectations"],
    },
    "financial_analyst": {
        "label": "Financial Analyst",
        "behavior": "Examines the economics: costs, revenue, budget fit, unit economics, sensitivity and return.",
        "tools": ["spreadsheet_models", "financial_calculations", "python_analysis"],
        "quality_criteria": ["Numbers shown with assumptions", "Budget and constraints respected"],
    },
    "risk_analyst": {
        "label": "Risk Analyst",
        "behavior": "Looks for failure modes, likelihood and impact, dependencies, and what mitigations or contingencies are needed.",
        "tools": ["document_analysis", "web_research"],
        "quality_criteria": ["Risks ranked by likelihood and impact", "Concrete mitigations"],
    },
    "creative": {
        "label": "Creative Specialist",
        "behavior": "Generates alternatives and unconventional options, then narrows to the few worth pursuing.",
        "tools": ["design_tools", "web_research"],
        "quality_criteria": ["Genuinely different options", "Feasible enough to act on"],
    },
    "quality_reviewer": {
        "label": "Quality Reviewer",
        "behavior": "Checks work against the objective and constraints: completeness, consistency, unsupported claims and missing pieces.",
        "tools": ["document_analysis"],
        "quality_criteria": ["Every requirement traced", "No unsupported claims"],
    },
}

# ``implemented`` is honest: only tools the engine can really run are marked
# True. The rest are declared so the Board Architect can record the intended
# toolset, but the engine will not pretend to have run them.
TOOL_CATALOG: Dict[str, Dict] = {
    "web_research": {"label": "Web research", "implemented": True},
    "document_analysis": {"label": "Document analysis (user-supplied context)", "implemented": True},
    "python_analysis": {"label": "Python / data analysis", "implemented": False},
    "spreadsheet_models": {"label": "Spreadsheet modelling", "implemented": False},
    "sql": {"label": "SQL", "implemented": False},
    "code_analysis": {"label": "Code analysis", "implemented": False},
    "repo_access": {"label": "Repository access", "implemented": False},
    "financial_calculations": {"label": "Financial calculations", "implemented": False},
    "market_data": {"label": "Market data", "implemented": False},
    "design_tools": {"label": "Design tools", "implemented": False},
}

TASK_TYPES: List[str] = [
    "research", "decision", "analysis", "creation", "planning", "review",
    "problem_solving", "strategy", "design", "evaluation", "optimization",
    "investigation", "execution",
]

# Sensitive areas where AI analysis must be distinguished from professional advice.
SENSITIVITY_DISCLAIMERS: Dict[str, str] = {
    "legal": "This is AI-generated analysis, not legal advice. Consult a qualified lawyer before acting on it.",
    "medical": "This is operational/informational analysis only, not medical diagnosis or treatment advice. Consult a qualified healthcare professional for medical decisions.",
    "financial": "This is AI-generated analysis, not personalised financial or investment advice. Verify figures and consult a qualified adviser before committing money.",
    "safety": "This is AI-generated analysis, not a safety certification or engineering sign-off. Have qualified professionals validate safety-critical decisions.",
}

# Task type -> the artifact that is most useful by default.
ARTIFACT_BY_TASK: Dict[str, str] = {
    "research": "Research Brief",
    "investigation": "Research Brief",
    "strategy": "Strategy Document",
    "planning": "Execution Plan",
    "execution": "Execution Plan",
    "design": "Creative Brief",
    "analysis": "Analysis Report",
    "evaluation": "Analysis Report",
    "optimization": "Analysis Report",
    "decision": "Decision Brief",
    "review": "Review Report",
    "problem_solving": "Analysis Report",
    "creation": "Finished Draft",
}

ARTIFACT_GUIDANCE: Dict[str, str] = {
    "Research Brief": "Sections: Question, Key Findings (cited), Evidence Quality & Gaps, Implications, Open Questions.",
    "Strategy Document": "Sections: Situation, Objectives, Strategic Options considered, Recommended Strategy, Key Bets & Trade-offs, Risks, First 90 Days.",
    "Execution Plan": "Sections: Goal, Workstreams with owners, Timeline/milestones, Budget & resources, Dependencies, Risks & contingencies, Immediate next steps.",
    "Creative Brief": "Sections: Objective, Audience, Core Idea, Options explored, Recommended Direction, Deliverables, Success Measures.",
    "Analysis Report": "Sections: Summary, Method & Assumptions, Findings, Root Causes / Drivers, Recommendations, Risks & Caveats.",
    "Decision Brief": "Sections: Decision Required, Options, Criteria, Assessment per option, Recommendation, Dissent & Unresolved Concerns, What would change our mind.",
    "Review Report": "Sections: Scope, What works, Issues (ranked by severity), Recommended fixes, Overall assessment.",
    "Finished Draft": "Produce the finished piece itself (not an outline), ready for the user to review and edit.",
    "Technical Design": "Sections: Problem, Constraints, Proposed Design, Alternatives, Trade-offs, Risks, Rollout.",
    "Project Plan": "Sections: Scope, Work breakdown, Timeline, Roles, Budget, Risks, Milestones.",
}
DEFAULT_GUIDANCE = "Choose the sections a professional would expect for this kind of deliverable. Lead with the answer or recommendation."
