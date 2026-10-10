# material_movement_subgraph.py
from langgraph.graph import StateGraph, START, END
from state import ChatState
from material_movement_node import material_movement_node


def _is_resolved(state) -> str:
    """
    Internal loop-check — this decision NEVER leaves the subgraph,
    so the parent graph never sees the loop at all. It only sees
    this whole subgraph as a single node that eventually finishes.
    """
    group = state["single_group"]
    results = state.get("material_movement_results", {})
    if group.group_id not in results:
        return "resolve"
    return END


_subgraph = StateGraph(ChatState)
_subgraph.add_node("resolve", material_movement_node)
_subgraph.add_edge(START, "resolve")
_subgraph.add_conditional_edges(
    "resolve",
    _is_resolved,
    {"resolve": "resolve", END: END},
)

# Compiled WITHOUT its own checkpointer — this makes it automatically
# inherit the parent graph's checkpointer, so interrupt()/resume
# still works correctly across the internal loop.
material_movement_subgraph = _subgraph.compile()







