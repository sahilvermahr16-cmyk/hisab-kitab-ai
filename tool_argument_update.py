from number_words import normalize_numbers
# tool_argument_update_node.py

from langchain_core.prompts import ChatPromptTemplate
from schemas import (ToolArgumentResult, ToolArgumentExtractionResult, ToolName,)
from tool_argument_models import TOOL_ARGUMENT_MODELS
from llm_setup import llm
import json

PROMPT = """
═══════════════════════════════
ROLE
═══════════════════════════════

You are an AI Tool Argument Update Assistant for a business accounting system.

You will receive:

1. The selected tool.
2. The original user statement.
3. The current structured arguments.
4. The missing required fields.
5. The user's latest update.

The user update may be:

• A complete corrected statement.
• Only the missing information.
• A partial correction.
• A combination of both.

Your responsibility is to update the existing structured arguments.

═══════════════════════════════
OBJECTIVE
═══════════════════════════════

The current structured arguments are the source of truth.
The user update modifies the existing arguments.
It does not replace them.

Use the original user statement and the missing required fields
as contextual information when interpreting the user's latest update.

The current structured arguments remain the primary source of truth.

Your job is to:

• Update only the information supported by the user's latest update.
• Preserve every valid existing value.
• Never remove information unless the user explicitly changes it.
• Never invent new information.
• Return the complete updated structured object.
• The final output must always conform to the provided Pydantic schema.

═══════════════════════════════
UPDATE RULES
═══════════════════════════════

Apply the following rules while updating the existing arguments.

Rule 1
The existing structured arguments are the primary source of truth.

Rule 2
Only modify fields when the user's latest update clearly provides new or corrected information.

Rule 3
If the user does not mention a field, preserve its current value.

Rule 4
Never overwrite an existing value with null, an empty value, or unknown information.

Rule 5
If the user explicitly corrects a previously extracted value, replace the old value with the new one.

Rule 6
If the user only provides the previously missing fields, update only those fields and preserve every other existing value.

Rule 7
Use the following together when producing the final updated arguments:
- the original user statement,
- the current structured arguments,
- the missing required fields,
- the user's latest update.

to produce the final updated arguments.

Rule 8
Never invent information.

Every updated value must be supported by:
- the existing arguments,
- the original user statement, or
- the user's latest update.

Do not infer unsupported values merely because they seem likely.

Rule 9
If a field cannot be updated using the user's latest update,
preserve its existing value unchanged.

Rule 10
Always return the complete updated structured object.

═══════════════════════════════
FIELD PRESERVATION RULES
═══════════════════════════════

The existing structured arguments already contain valuable information.

While updating:

• Treat every existing non-null value as valid unless the user explicitly changes it.

• Do not remove previously extracted information.

• Do not replace valid values with null or empty values.

• Preserve all fields that are unrelated to the user's latest update.

• The user update only modifies the existing arguments.
  It does NOT replace the entire object.

• Always combine:
  - Existing structured arguments
  - User's latest update

to produce one complete updated object.

• If multiple fields need to be updated,
  update all of them together.

• If the user provides only one missing field,
  update only that field.

• If the user's update conflicts with an existing value,
  prefer the user's latest update.

• Preserve the exact field names, data types,
  and schema structure.

• Never modify fields that are unrelated to the user's latest update.  

• Use the original user statement as context for interpreting
  short or incomplete user updates.

• Use the missing required fields to understand which information
  the user's latest update is expected to provide.

• Do not treat the missing fields themselves as values.
  They only identify what information is still unresolved.

═══════════════════════════════
EXAMPLES
═══════════════════════════════

Example 1
---------

Selected Tool:
record_expense

Current Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": null,
    "transaction_date": "2026-08-04",
    "note": ""
}

User Update:

"2500 rupaye"

Updated Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": 2500,
    "transaction_date": "2026-08-04",
    "note": ""
}

Explanation:
Only the missing amount is updated.
Every other field is preserved.


────────────────────────────────

Example 2
---------

Selected Tool:
record_expense

Current Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": null,
    "vehicle": null,
    "transaction_date": "2026-08-04"
}

User Update:

"Tractor me 2500 ka diesel bharvaya."

Updated Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": 2500,
    "vehicle": "tractor",
    "transaction_date": "2026-08-04"
}

Explanation:
The user provided a complete corrected statement.
Update every supported field while preserving existing values.


────────────────────────────────

Example 3
---------

Selected Tool:
record_employee_transaction

Current Arguments:

{
    "employee_name": "Ram",
    "transaction_type": "payment",
    "amount": 500,
    "payment_method": null,
    "transaction_date": "2026-08-04"
}

User Update:

"Cash diye the."

Updated Arguments:

{
    "employee_name": "Ram",
    "transaction_type": "payment",
    "amount": 500,
    "payment_method": "cash",
    "transaction_date": "2026-08-04"
}

Explanation:
Only the payment_method is updated.
All other fields remain unchanged.


────────────────────────────────

Example 4
---------

Selected Tool:
record_purchase

Current Arguments:

{
    "seller_name": "Sharma",
    "total_amount": 50000,
    "amount_paid": null,
    "transaction_date": "2026-08-04"
}

User Update:

"10000 advance diya."

Updated Arguments:

{
    "seller_name": "Sharma",
    "total_amount": 50000,
    "amount_paid": 10000,
    "transaction_date": "2026-08-04"
}

Explanation:
The user supplied only the previously missing field.
The existing values are preserved.

────────────────────────────────

Example 5
---------

Selected Tool:
record_expense

Original User Statement:

"Aaj tractor me 2000 ka diesel bharvaya."

Current Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": 2000,
    "vehicle": "tractor",
    "transaction_date": "2026-08-24"
}

Missing Fields:

[]

User Update:

"Amount 2500 tha."

Updated Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": 2500,
    "vehicle": "tractor",
    "transaction_date": "2026-08-24"
}

Explanation:
The user explicitly corrected the existing amount.
Only the amount is changed.
All other existing values are preserved.

────────────────────────────────

Example 6
---------

Selected Tool:
record_expense

Original User Statement:

"Aaj diesel bharvaya."

Current Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": null,
    "vehicle": null,
    "transaction_date": "2026-08-24"
}

Missing Fields:

[
    "amount",
    "vehicle"
]

User Update:

"2500 tractor"

Updated Arguments:

{
    "category": "fuel",
    "description": "diesel",
    "amount": 2500,
    "vehicle": "tractor",
    "transaction_date": "2026-08-24"
}

Explanation:
The user provided only the missing information.
Interpret the short update using the original statement,
current arguments, and missing required fields.

═══════════════════════════════
IMPORTANT
═══════════════════════════════

If a field still cannot be determined after processing the user's
latest update, preserve its current value, including null if its
current value is null.

Do not guess.

Do not ask for additional information.

The workflow allows only one update attempt.

═══════════════════════════════
FINAL VALIDATION
═══════════════════════════════

Before returning the updated arguments, verify all of the following:

✓ The output conforms to the provided Pydantic schema.

✓ Every field required by the schema is present.

✓ Existing values have been preserved unless explicitly changed by the user.

✓ Only fields supported by the user's latest update have been modified.

✓ No existing value has been overwritten with null or an empty value.

✓ No unsupported or invented information has been added.

✓ All field names, data types, and schema structure remain unchanged.

✓ The output represents one complete, updated structured object.

Return ONLY the structured output.
Do not explain your reasoning.

"""

def _build_prompt(
    *,
    tool_name,
    original_user_statement: str,
    arguments,
    missing_arguments,
    updated_statement: str,
):
    return ChatPromptTemplate.from_messages([
        (
            "system",
            PROMPT.replace("{", "{{").replace("}", "}}"),
        ),
        (
            "human",
            """Selected Tool:
{tool_name}

Original User Statement:
{original_user_statement}

Current Arguments:
{arguments}

Missing Required Fields:
{missing_arguments}

User's Latest Update:
{updated_statement}
""",
        ),
    ]).partial(
        tool_name=tool_name,
        original_user_statement=original_user_statement,
        arguments=json.dumps(
            arguments.model_dump(mode="json")
            if hasattr(arguments, "model_dump")
            else arguments,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        missing_arguments="\n".join(
            f"- {item.field_name}: {item.description}"
            for item in missing_arguments
        ),
        updated_statement=updated_statement,
    )

async def tool_argument_update_node(state):
    """
    Applies each HITL answer to EXACTLY the tool call it was asked
    for, matched by (group_id, action_index, tool_name) — never by
    group_id alone, because one group can contain several tool calls
    (e.g. record_expense + record_expense_payment) that each need
    their own answer.

    group_id / action_index / tool_name are always copied from the
    original result; the LLM only returns the tool's argument schema.
    """

    updates = state.get("tool_argument_updates") or []
    if not updates:
        return {}

    update_map = {
        (u["group_id"], u["action_index"], u["tool_name"]): u
        for u in updates
    }

    argument_results = state["tool_argument_results"]
    updated_results = []

    for result in argument_results.results:

        update = update_map.get(
            (result.group_id, result.action_index, result.tool_name.value)
        )

        # No HITL answer for this tool call → keep it exactly as it was
        if update is None or not update["updated_statement"]:
            updated_results.append(result)
            continue

        schema = TOOL_ARGUMENT_MODELS.get(result.tool_name)
        if schema is None:
            raise ValueError(
                f"No argument schema registered for tool '{result.tool_name}'."
            )

        prompt = _build_prompt(
            tool_name=result.tool_name,
            original_user_statement=state["original_user_statement"],
            arguments=result.arguments,
            missing_arguments=update["missing_arguments"],
            updated_statement=normalize_numbers(update["updated_statement"]),
        )

        structured_llm = llm.with_structured_output(
            schema,
            method="function_calling",
        )

        chain = prompt | structured_llm
        updated_arguments = await chain.ainvoke({})

        updated_results.append(
            ToolArgumentResult(
                group_id=result.group_id,
                action_index=result.action_index,
                tool_name=result.tool_name,
                arguments=updated_arguments,
            )
        )

    # Direct Sale: if this update just filled in customer_name on the
    # sale-side tool call, copy it into the supplier-side call too —
    # they represent the SAME event and must agree on the customer.
    # (See _link_direct_sale_tools in tool_argument_extraction_node.py
    # for the full explanation of why these two tools need linking.)
    for group_id in {u["group_id"] for u in updates}:
        supplier_result = None
        sale_result = None
        for r in updated_results:
            if r.group_id != group_id:
                continue
            if r.tool_name == ToolName.RECORD_SUPPLIER_TRANSACTION:
                supplier_result = r
            elif r.tool_name == ToolName.RECORD_SALE_TRANSACTION:
                sale_result = r
        if supplier_result is not None and sale_result is not None:
            sale_args = sale_result.arguments
            customer_name = (
                sale_args.get("customer_name")
                if isinstance(sale_args, dict)
                else getattr(sale_args, "customer_name", None)
            )
            if customer_name:
                if isinstance(supplier_result.arguments, dict):
                    supplier_result.arguments["customer_name"] = customer_name
                else:
                    supplier_result.arguments.customer_name = customer_name

    return {
        "tool_argument_results": ToolArgumentExtractionResult(
            results=updated_results
        )
    }


