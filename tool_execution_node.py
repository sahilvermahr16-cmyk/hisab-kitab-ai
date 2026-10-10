# tool_execution_node.py

from llm_setup import TOOLS_MAP
from datetime import date, datetime
from pydantic import ValidationError
from db import SessionLocal
from helpers import insert_audit_log
import uuid


async def tool_execution_node(state):
    """
    Tool Execution Node

    Responsibilities:
    1. Check final confirmation.
    2. Get the selected tool.
    3. Get the final updated arguments.
    4. Execute the tool.
    5. On success, record an AuditLog entry (Correction Phase
       foundation) — needs a separate DB session since each tool
       function opens/closes its own session internally.
    """

    print("\n🔥 TOOL EXECUTION NODE STARTED 🔥")

    confirmations = state.get("final_confirmation_results") or []
    tool_argument_results = state.get("tool_argument_results")

    # Koi tool select hi nahi hua (correction-only message, ya role ke liye
    # koi tool match nahi hua): execute karne ko kuch nahi hai.
    if tool_argument_results is None or not tool_argument_results.results:
        print("No tools to execute.")
        return {"tool_execution_results": []}

    if not confirmations:
        raise ValueError("final_confirmation_results not found in state.")

    grouped_intent = state.get("grouped_intent")
    full_statement = state.get("original_user_statement", "")

    # group_id -> ActionGroup, for pulling each action's own
    # extract+grouping-stage text (action_statement).
    group_lookup = {
        group.group_id: group
        for group in (grouped_intent.groups if grouped_intent else [])
    }

    confirmation_map = {
        (c["group_id"], c["action_index"], c["tool_name"]): c["confirmed"]
        for c in confirmations
    }

    execution_results = []
    audit_db = SessionLocal()

    run_id = uuid.uuid4().hex

    print("\n========== TOOL EXECUTION DEBUG ==========")
    print("Confirmations:", confirmations)
    print("Number of confirmations:", len(confirmations))
    print("Tool Argument Results:", tool_argument_results.results)
    print("Number of tool results:", len(tool_argument_results.results))
    print("==========================================")

    try:
        for result in tool_argument_results.results:

            confirmation = confirmation_map.get(
                (result.group_id, result.action_index, result.tool_name.value)
            )

            if confirmation is None:
                raise ValueError(
                    f"No confirmation found for group_id={result.group_id}, "
                    f"action_index={result.action_index}, "
                    f"tool={result.tool_name.value}."
                )

            if str(confirmation).strip().lower() != "yes":
                execution_results.append("❌ Tool execution cancelled.")
                continue

            tool_name = result.tool_name.value
            tool = TOOLS_MAP.get(tool_name)

            if tool is None:
                raise ValueError(
                    f"Tool '{tool_name}' not found in TOOLS_MAP."
                )

            arguments = result.arguments

            if hasattr(arguments, "model_dump"):
                arguments = arguments.model_dump()

            if isinstance(arguments.get("attendance_date"), (date, datetime)):
                arguments["attendance_date"] = arguments["attendance_date"].strftime("%Y-%m-%d")

            if isinstance(arguments.get("activity_date"), (date, datetime)):
                arguments["activity_date"] = arguments["activity_date"].strftime("%Y-%m-%d")

            if isinstance(arguments.get("transaction_date"), (date, datetime)):
                arguments["transaction_date"] = arguments["transaction_date"].strftime("%Y-%m-%d")

            for date_field in ["sale_date", "payment_date", "purchase_date",
                                 "expense_date", "adjustment_date", "movement_date"]:
                if isinstance(arguments.get(date_field), (date, datetime)):
                    arguments[date_field] = arguments[date_field].strftime("%Y-%m-%d")

            # Kuch fields tool-function mein empty-string default rakhte
            # hain (unit="", reason=""), lekin agar LLM ne None extract
            # kiya, to use forcefully empty-string bana do — taaki tool
            # ko kabhi None na mile in fields ke liye.
            for field_name in [
                "unit", "reason", "movement_type", "movement_reason",
                "source_type", "destination_type",
            ]:
                if arguments.get(field_name) is None:
                    arguments[field_name] = ""

            # quantity=0 default is only safe for tools where 0 is valid
            # (i.e. it just means "not mentioned"). For tools where quantity
            # must be non-zero (record_material_movement, record_adjustment's
            # quantity_change), leave it as-is and let schema validation
            # catch a genuinely missing value instead of silently forcing 0.
            if tool_name not in ("record_material_movement", "record_adjustment"):
                if arguments.get("quantity") is None:
                    arguments["quantity"] = 0

            # Generic None -> default coalescing, driven by the tool's own
            # args_schema (built from the underlying function's signature).
            if hasattr(tool, "args_schema") and tool.args_schema is not None:
                for field_name, field_info in tool.args_schema.model_fields.items():
                    if (
                        field_name in arguments
                        and arguments[field_name] is None
                        and not field_info.is_required()
                    ):
                        arguments[field_name] = field_info.get_default(call_default_factory=True)

            # Validate arguments before executing the tool.
            try:
                if hasattr(tool, "args_schema") and tool.args_schema is not None:
                    validated_arguments = tool.args_schema.model_validate(arguments)
                    arguments = validated_arguments.model_dump()

            except ValidationError as e:
                print("\n========== TOOL VALIDATION FAILED ==========")
                print("Tool:", tool_name)
                print("Arguments:", arguments)
                print("Validation Error:", e)
                print("============================================")

                execution_results.append(
                    f"❌ {tool_name} could not be executed. "
                    f"Required information is missing or invalid: {e}"
                )
                continue

            print("\n========== BEFORE TOOL INVOKE ==========")
            print("Tool:", tool_name)
            print("Tool object:", tool)
            print("Arguments:", arguments)
            print("========================================")

            execution_result = tool.invoke(arguments)

            # Tools now return a dict on success ({"message", "target_table",
            # "target_id"}) or a plain string on failure/no-op. Only log to
            # AuditLog on the dict (success) path — errors and "nothing to
            # update" cases have nothing worth reversing later.
            if isinstance(execution_result, dict):
                group = group_lookup.get(result.group_id)
                action_statement = (
                    group.actions[result.action_index].text
                    if group is not None
                    else ""
                )

                insert_audit_log(
                    db=audit_db,
                    full_statement=full_statement,
                    action_statement=action_statement,
                    tool_name=tool_name,
                    arguments=arguments,
                    target_table=execution_result["target_table"],
                    target_id=execution_result["target_id"],
                    group_id=result.group_id,
                    action_index=result.action_index,
                    run_id=run_id,
                )
                audit_db.commit()

                execution_results.append(execution_result["message"])
            else:
                execution_results.append(execution_result)

    finally:
        audit_db.close()

    return {
        "tool_execution_results": execution_results
    }





