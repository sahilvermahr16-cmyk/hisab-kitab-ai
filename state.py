from typing import Annotated, TypedDict, Any
from langgraph.graph.message import add_messages
from schemas import (
    UserIntent,
    GroupedIntent,
    ActionGroup,
    PersonRoleClassificationResult,
    PersonRoleRankingResult,
    PersonRoleHITLRequest,
    PersonRoleHITLResponse,
    PersonRole,
    ToolDecisionResult,
    ToolArgumentExtractionResult,
    TransactionClassifierResult,
)

# Sentinel for per-turn resets. A reducer-backed field can't be reset
# by writing {} or [] (that just merges nothing in), so extract_node
# writes RESET instead, and the reducers below clear the field.
RESET = "__RESET__"


def merge_dicts(existing: dict | None, new) -> dict:
    if new == RESET:
        return {}
    existing = existing or {}
    new = new or {}
    return {**existing, **new}


def merge_lists(existing: list | None, new) -> list:
    if new == RESET:
        return []
    existing = existing or []
    new = new or []
    return existing + new


def keep_last(existing, new):
    """single_group: har branch apna group likhti hai. Do maal-movement ek saath chalein to
    ek hi step mein do jawaab aate hain — aakhri rakh lo (fan-in ke baad isko koi nahi padhta)."""
    return new


def _keep_statement(old, new):
    """Kai parallel material-movement branch ek hi statement wapas likhte hain — ek hi value rakho
    (warna LangGraph: 'Can receive only one value per step')."""
    return new if new else old


class ChatState(TypedDict):

    messages: Annotated[list, add_messages]

    intent: str | None
    extracted_intent: UserIntent | None
    grouped_intent: GroupedIntent | None

    single_group: Annotated[ActionGroup | None, keep_last]
    tool_argument_updates: list | None

    # Annotated must be the OUTERMOST type — never wrap in `| None`.
    person_role_results: Annotated[list[PersonRoleClassificationResult], merge_lists]
    person_role_rankings: Annotated[list[PersonRoleRankingResult], merge_lists]
    person_role_hitl_requests: Annotated[list[PersonRoleHITLRequest], merge_lists]
    person_role_hitl_responses: Annotated[list[PersonRoleHITLResponse], merge_lists]
    resolved_person_roles: Annotated[dict[str, PersonRole], merge_dicts]

    material_movement_results: Annotated[dict[str, dict], merge_dicts]
    material_movement_progress: Annotated[dict[str, dict], merge_dicts]
    transaction_classifier_results: Annotated[dict[str, TransactionClassifierResult], merge_dicts]

    tool_decision_results: list[ToolDecisionResult] | None

    tool_argument_results: Any | None
    tool_argument_hitl_response: Any | None
    final_confirmation_results: list | None
    tool_execution_results: list | None

    planned_tool_calls: list | None

    correction_data: dict | None

    # Reporting Phase — report_subgraph ka apna data (sirf JSON-safe values)
    report_data: dict | None

    execution_result: dict | None
    error: str | None

    original_user_statement: Annotated[str | None, _keep_statement]
    missing_arguments: list | None



    