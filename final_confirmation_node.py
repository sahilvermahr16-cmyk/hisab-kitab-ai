# final_confirmation_node.py

from langgraph.types import interrupt

from schemas import (
    ToolArgumentExtractionResult,
    FinalConfirmationRequest,
)


async def final_confirmation_node(state):
    """
    Final Confirmation Node

    Shows each final tool call with its arguments and asks the user
    for confirmation.

    Each confirmation is tagged with (group_id, action_index,
    tool_name). tool_name is required because ONE action can produce
    MULTIPLE tool calls (e.g. record_purchase + record_purchase_payment,
    or a Direct Sale's supplier + sale tools) that share the same
    group_id and action_index.
    """

    tool_argument_results: ToolArgumentExtractionResult | None = (
        state.get("tool_argument_results")
    )

    if tool_argument_results is None:
        raise ValueError("tool_argument_results not found in state.")

    confirmations = []

    for result in tool_argument_results.results:

        arguments = (
            result.arguments.model_dump()
            if hasattr(result.arguments, "model_dump")
            else result.arguments
        )

        request = FinalConfirmationRequest(
            tool_name=result.tool_name,
            action_index=result.action_index,
            arguments=arguments,
        )

        response = interrupt(
            {
                "message": (
                    f"Tool: {request.tool_name.value}\n\n"
                    f"Updated Arguments:\n{request.arguments}\n\n"
                    "Execute this tool? (yes/no)"
                )
            }
        )

        confirmations.append({
            "group_id": result.group_id,
            "action_index": result.action_index,
            "tool_name": result.tool_name.value,
            "confirmed": response,
        })

    return {
        "final_confirmation_results": confirmations
    }

