# test_tool_argument_update.py

import asyncio
from pprint import pprint

from tool_argument_update import tool_argument_update_node

from schemas import (
    ToolName,
    MissingArgument,
    ToolArgumentResult,
    ToolArgumentExtractionResult,
    ToolArgumentHITLResponse,
)

from tool_argument_models import RecordExpenseArgs


async def main():

    # --------------------------------------------------
    # 1. Existing arguments
    # --------------------------------------------------

    current_arguments = RecordExpenseArgs(
        category="fuel",
        description="diesel",
        amount=None,
        transaction_date="2026-08-24",
        payment_method=None,
        payment_provider=None,
        note=None,
    )

    # --------------------------------------------------
    # 2. Existing extracted tool result
    # --------------------------------------------------

    tool_argument_results = ToolArgumentExtractionResult(
        results=[
            ToolArgumentResult(
                group_id="group_1",
                tool_name=ToolName.RECORD_EXPENSE,
                arguments=current_arguments,
            )
        ]
    )

    # --------------------------------------------------
    # 3. Missing fields detected by Tool Argument HITL
    # --------------------------------------------------

    missing_arguments = [
        MissingArgument(
            field_name="amount",
            description="Expense amount.",
        )
    ]

    # --------------------------------------------------
    # 4. User's one-time HITL response
    # --------------------------------------------------

    hitl_response = ToolArgumentHITLResponse(
        group_id="group_1",
        updated_statement="2500 rupaye",
        confirmed=None,
    )

    # --------------------------------------------------
    # 5. Fake state
    # --------------------------------------------------

    state = {
        "tool_argument_hitl_response": hitl_response,

        "tool_argument_results": tool_argument_results,

        "original_user_statement": "Aaj diesel bharvaya.",

        "missing_arguments": missing_arguments,
    }

    # --------------------------------------------------
    # 6. BEFORE UPDATE
    # --------------------------------------------------

    print("\n" + "=" * 70)
    print("BEFORE UPDATE")
    print("=" * 70)

    pprint(
        tool_argument_results.model_dump(
            exclude_none=False
        )
    )

    # --------------------------------------------------
    # 7. USER UPDATE
    # --------------------------------------------------

    print("\n" + "=" * 70)
    print("USER UPDATE")
    print("=" * 70)

    print(hitl_response.updated_statement)

    # --------------------------------------------------
    # 8. Run ONLY Tool Argument Update Node
    # --------------------------------------------------

    result = await tool_argument_update_node(state)

    # --------------------------------------------------
    # 9. AFTER UPDATE
    # --------------------------------------------------

    print("\n" + "=" * 70)
    print("AFTER UPDATE")
    print("=" * 70)

    pprint(result)

    # --------------------------------------------------
    # 10. Validation
    # --------------------------------------------------

    updated_results = result["tool_argument_results"]

    updated_argument = updated_results.results[0].arguments

    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    print("Category          :", updated_argument.category)
    print("Description       :", updated_argument.description)
    print("Amount            :", updated_argument.amount)
    print("Transaction Date  :", updated_argument.transaction_date)
    print("Payment Method    :", updated_argument.payment_method)
    print("Payment Provider  :", updated_argument.payment_provider)
    print("Note              :", updated_argument.note)

    # --------------------------------------------------
    # 11. Assertions
    # --------------------------------------------------

    assert updated_argument.amount == 2500

    # Existing values must remain unchanged
    assert updated_argument.category == "fuel"
    assert updated_argument.description == "diesel"
    assert str(updated_argument.transaction_date) == "2026-08-24"

    print("\n" + "=" * 70)
    print("✅ TOOL ARGUMENT UPDATE NODE TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())