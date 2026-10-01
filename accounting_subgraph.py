# accounting_subgraph.py
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from extract_node import extract_node
from schemas import RecordType
from state import ChatState

from grouping_node import grouping_node
from person_role_classification_node import person_role_classification_node
from tool_decision_node import tool_decision_node
from tool_argument_extraction_node import tool_argument_extraction_node
from graph_constants import (PERSON_ROLE_CLASSIFICATION, PERSON_ROLE_HITL, TOOL_DECISION, TOOL_ARGUMENT_EXTRACTION, TOOL_ARGUMENT_HITL, TOOL_EXECUTION, FINAL_CONFIRMATION, TOOL_ARGUMENT_UPDATE,)

from person_role_hitl_node import person_role_hitl_node
from tool_argument_update import tool_argument_update_node
from tool_argument_hitl import _find_missing_arguments, tool_argument_hitl_node
from final_confirmation_node import final_confirmation_node
from tool_execution_node import tool_execution_node
from date_resolution_node import date_resolution_node
from material_movement_subgraph import material_movement_subgraph
from standalone_transaction_node import standalone_transaction_node
from correction_node import correction_node
from correction_subgraph import correction_subgraph


def group_dispatcher(state):
    """
    Scatter step (Send API). Every branch is now exactly ONE node
    (material movement's multi-pass loop lives inside its subgraph),
    so each Send gives full per-group isolation.

    Payloads are kept minimal on purpose — each branch only receives
    what it needs, so it doesn't echo unrelated state back up.
    """
    groups = state["grouped_intent"].groups
    if not groups:
        raise ValueError("No Action Groups found after grouping.")

    rankings_by_group = {
        r.group_id: r for r in (state.get("person_role_rankings") or [])
    }

    sends = []
    for group in groups:
        if group.record_type == RecordType.CORRECTION:
            continue   # correction FINAL_CONFIRMATION ke baad chalega
        if group.record_type == RecordType.NEED_PERSON:
            ranking = rankings_by_group.get(group.group_id)
            if ranking is None:
                raise ValueError(f"No person-role ranking found for {group.group_id}.")
            sends.append(Send(PERSON_ROLE_HITL, {
                "single_group": group,
                "person_role_rankings": [ranking],
            }))
        elif group.record_type == RecordType.MATERIAL_MOVEMENT:
            sends.append(Send("material_movement", {"single_group": group}))
        elif group.record_type == RecordType.STANDALONE_TRANSACTION:
            sends.append(Send("standalone_transaction", {"single_group": group}))
        else:
            raise ValueError(f"Unknown RecordType: {group.record_type}")
    # Sirf correction wala message: koi normal branch nahi, seedha correction
    if not sends:
        return ["correction"]

    return sends

def route_after_tool_argument_extraction(state) -> str:

    tool_argument_results = state.get("tool_argument_results")

    if tool_argument_results is None:
        raise ValueError(
            "tool_argument_results not found after tool argument extraction."
        )

    for result in tool_argument_results.results:
        missing_arguments = _find_missing_arguments(
            tool_name=result.tool_name,
            arguments=result.arguments,
        )

        if missing_arguments:
            return TOOL_ARGUMENT_HITL

    return FINAL_CONFIRMATION


accounting_subgraph = StateGraph(ChatState)

accounting_subgraph.add_node("extract", extract_node)
accounting_subgraph.add_node("grouping", grouping_node)
accounting_subgraph.add_node("date_resolution", date_resolution_node)
accounting_subgraph.add_node(PERSON_ROLE_CLASSIFICATION, person_role_classification_node)
accounting_subgraph.add_node(PERSON_ROLE_HITL, person_role_hitl_node)
accounting_subgraph.add_node("material_movement", material_movement_subgraph)
accounting_subgraph.add_node("standalone_transaction", standalone_transaction_node)

# defer=True — Tool Decision runs only after EVERY pending branch has
# finished (including ones paused on interrupts and resumed later).
# This is LangGraph's built-in fan-in for unequal-length branches,
# replacing the hand-made "wait" barrier.
accounting_subgraph.add_node(TOOL_DECISION, tool_decision_node, defer=True)

accounting_subgraph.add_node(TOOL_ARGUMENT_EXTRACTION, tool_argument_extraction_node)
accounting_subgraph.add_node(TOOL_ARGUMENT_UPDATE, tool_argument_update_node)
accounting_subgraph.add_node(TOOL_ARGUMENT_HITL, tool_argument_hitl_node)
accounting_subgraph.add_node(FINAL_CONFIRMATION, final_confirmation_node)
accounting_subgraph.add_node("correction", correction_subgraph)
accounting_subgraph.add_node(TOOL_EXECUTION, tool_execution_node)

accounting_subgraph.add_edge(START, "extract")
accounting_subgraph.add_edge("extract", "grouping")
accounting_subgraph.add_edge("grouping", "date_resolution")
accounting_subgraph.add_edge("date_resolution", PERSON_ROLE_CLASSIFICATION)

# Scatter
accounting_subgraph.add_conditional_edges(
    PERSON_ROLE_CLASSIFICATION,
    group_dispatcher,
)

# Fan-in — simple static edges; defer=True on TOOL_DECISION does the waiting
accounting_subgraph.add_edge(PERSON_ROLE_HITL, TOOL_DECISION)
accounting_subgraph.add_edge("material_movement", TOOL_DECISION)
accounting_subgraph.add_edge("standalone_transaction", TOOL_DECISION)

accounting_subgraph.add_edge(TOOL_DECISION, TOOL_ARGUMENT_EXTRACTION)
accounting_subgraph.add_conditional_edges(
    TOOL_ARGUMENT_EXTRACTION,
    route_after_tool_argument_extraction,
    {
        TOOL_ARGUMENT_HITL: TOOL_ARGUMENT_HITL,
        FINAL_CONFIRMATION: FINAL_CONFIRMATION,
    }
)

accounting_subgraph.add_edge(TOOL_ARGUMENT_HITL, TOOL_ARGUMENT_UPDATE)
accounting_subgraph.add_edge(TOOL_ARGUMENT_UPDATE, FINAL_CONFIRMATION)
accounting_subgraph.add_edge(FINAL_CONFIRMATION, "correction")
accounting_subgraph.add_edge("correction", TOOL_EXECUTION)
accounting_subgraph.add_edge(TOOL_EXECUTION, END)



