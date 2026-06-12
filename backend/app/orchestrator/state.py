from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class GraphState(TypedDict):
    """
    Represents the state of our routing and debate graph.
    """
    user_id: str
    project_id: str
    # The conversation history
    messages: List[BaseMessage]
    
    # Analyzer outputs
    intent: str
    active_agents: List[str] # List of agent names, e.g., ["cto", "marketing"]
    
    # Context retrieved from pgvector
    retrieved_context: str
    
    # Drafts from each agent. Key: agent name, Value: JSON structured output
    draft_responses: Dict[str, Any]
    
    # Critiques from the Risk/Critic agent
    critiques: Dict[str, str]
    
    # Synthesized final output
    final_consensus: str
    
    # The active mode: 'advisor' (Strategic Advisor) or 'pitch' (VC Pitch Panel)
    mode: str
