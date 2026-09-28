from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class WorkAnalysis(BaseModel):
    objective: str
    domain: str = "general"
    task_types: List[str] = Field(default_factory=lambda: ["analysis"])
    complexity: Literal["simple", "moderate", "complex", "very_complex"] = "moderate"
    constraints: List[str] = Field(default_factory=list)
    desired_output: str = ""
    needs_live_research: bool = False
    sensitivity: List[str] = Field(default_factory=list)  # legal | medical | financial | safety
    summary: str = ""


class AgentSpec(BaseModel):
    id: str
    role: str                      # e.g. "Venue Researcher"
    perspective: str = ""          # e.g. "Venue Researcher Perspective" (never a claim of a real person)
    archetype: str = "expert"
    domain: str = ""
    expertise: str = ""
    objectives: List[str] = Field(default_factory=list)
    priorities: List[str] = Field(default_factory=list)
    behavior: str = ""
    research_lens: str = ""
    research_queries: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    quality_criteria: List[str] = Field(default_factory=list)
    temporary: bool = False        # joined mid-discussion to resolve a specific issue


class BoardPlan(BaseModel):
    agents: List[AgentSpec]
    rationale: str = ""


class Source(BaseModel):
    id: str
    title: str
    url: str
    snippet: str = ""
    agent_id: Optional[str] = None
    query: Optional[str] = None
