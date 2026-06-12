from langgraph.graph import StateGraph, END
from app.orchestrator.state import GraphState
from app.orchestrator.nodes import (
    analyze_intent,
    retrieve_context,
    execute_agents,
    execute_critic,
    synthesize_consensus
)

def create_orchestrator_graph():
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("analyzer", analyze_intent)
    workflow.add_node("retriever", retrieve_context)
    workflow.add_node("parallel_agents", execute_agents)
    workflow.add_node("critic", execute_critic)
    workflow.add_node("synthesizer", synthesize_consensus)
    
    # Define edges
    workflow.set_entry_point("analyzer")
    workflow.add_edge("analyzer", "retriever")
    workflow.add_edge("retriever", "parallel_agents")
    workflow.add_edge("parallel_agents", "critic")
    workflow.add_edge("critic", "synthesizer")
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()

# The compiled graph instance
orchestrator = create_orchestrator_graph()
