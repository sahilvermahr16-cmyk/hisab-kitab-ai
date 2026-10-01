# tool_argument_hitl.py
from pydantic import BaseModel
from schemas import (ToolName, MissingArgument, ToolArgumentHITLRequest,)
from tool_argument_models import (TOOL_VALIDATION_RULES, TOOL_ARGUMENT_MODELS,)


def _find_missing_arguments(
    *,
    tool_name: ToolName,
    arguments: BaseModel | dict,
) -> list[MissingArgument]:

    rules = TOOL_VALIDATION_RULES.get(tool_name)

    if rules is None:
        raise ValueError(
            f"No validation rules registered for tool '{tool_name}'."
        )

    missing_arguments = []

    for argument_field in rules["mandatory_fields"]:

        field_name = argument_field.value

        if isinstance(arguments, dict):
            value = arguments.get(field_name)
        else:
            value = getattr(arguments, field_name, None)

        if value is not None:
            continue

        if hasattr(arguments.__class__, "model_fields"):
            field_info = arguments.__class__.model_fields.get(field_name)

            description = (
                field_info.description
                if field_info is not None
                else field_name
            )
        else:
            model_class = TOOL_ARGUMENT_MODELS[tool_name]
            field_info = model_class.model_fields.get(field_name)

            description = (
                field_info.description
                if field_info is not None
                else field_name
            )

        missing_arguments.append(
            MissingArgument(
                field_name=field_name,
                description=description,
            )
        )

    return missing_arguments

def _build_hitl_request(*, group_id: str, tool_name: ToolName, arguments: BaseModel, missing_arguments: list[MissingArgument],) -> ToolArgumentHITLRequest:
    """
    Build a structured Tool Argument HITL request.
    """
    return ToolArgumentHITLRequest(group_id=group_id, tool_name=tool_name, arguments=arguments, missing_arguments=missing_arguments,)


from langgraph.types import interrupt

from schemas import (
    ToolArgumentExtractionResult,
    ToolArgumentHITLResponse,
)

async def tool_argument_hitl_node(state):
    """
    Tool Argument HITL Node

    Asks the user for missing mandatory arguments — once per result
    that has missing fields. Every answer is stored WITH the identity
    of the exact result it belongs to (group_id, action_index,
    tool_name) and that result's OWN missing fields, so the update
    node can apply each answer only to its own tool call.

    Previously only the first answer was returned, paired with the
    last result's missing fields, and the update node applied that
    single answer to every result in the same group.
    """
    tool_argument_results: ToolArgumentExtractionResult | None = (
        state.get("tool_argument_results")
    )
    if tool_argument_results is None:
        raise ValueError("tool_argument_results not found in state.")

    updates = []

    for result in tool_argument_results.results:

        missing_arguments = _find_missing_arguments(
            tool_name=result.tool_name,
            arguments=result.arguments,
        )

        if not missing_arguments:
            continue

        request = _build_hitl_request(
            group_id=result.group_id,
            tool_name=result.tool_name,
            arguments=result.arguments,
            missing_arguments=missing_arguments,
        )

        response: ToolArgumentHITLResponse = interrupt(request)

        updates.append({
            "group_id": result.group_id,
            "action_index": result.action_index,
            "tool_name": result.tool_name.value,
            "missing_arguments": missing_arguments,
            "updated_statement": response.updated_statement,
        })

    return {
        "tool_argument_updates": updates,
        "original_user_statement": (
            state["messages"][-1].content
            if state.get("messages")
            else None
        ),
    }
