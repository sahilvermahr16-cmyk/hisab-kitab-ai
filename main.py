import asyncio
from graph import build_app
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from schemas import (
    ToolArgumentHITLRequest,
    ToolArgumentHITLResponse,
    MaterialMovementHITLRequest,
    MaterialMovementHITLResponse,
    MaterialMovementHITLReason,
    PersonRoleHITLRequest,
    PersonRoleHITLResponse,
    HITLInteractionType,
    CorrectionDateHITLRequest,
    CorrectionDateHITLResponse,
    CorrectionCategoryHITLRequest,
    CorrectionCategoryHITLResponse,
    CorrectionRangeHITLRequest,
    CorrectionRangeHITLResponse,
    CorrectionDetailHITLRequest,
    CorrectionDetailHITLResponse,
    CorrectionMatchHITLRequest,
    CorrectionMatchHITLResponse,
    CorrectionConfirmHITLRequest,
    CorrectionConfirmHITLResponse,
    CorrectionActionHITLRequest,
    CorrectionActionHITLResponse,
    CorrectionStatementHITLRequest,
    CorrectionStatementHITLResponse,
)

from correction_format import render_table, TITLES

THREAD_ID = "test_006"


def display_interrupt(interrupt_value):
    """
    Testing-only display handler.
    Different HITL nodes currently return different payload types.
    """

    # ---------------------------------------------
    # Person Role HITL
    # ---------------------------------------------
    if isinstance(interrupt_value, PersonRoleHITLRequest):

        print("\n" + "=" * 80)
        print(f"Person : {interrupt_value.person}")
        print()

        if interrupt_value.interaction_type == HITLInteractionType.CONFIRMATION:
            top = interrupt_value.options[0]
            print(f"AI Recommendation : {top.role.value} ({top.confidence:.2f})")
            print()
            print("1. Yes")
            print("2. No")
        else:
            print("Please select the correct role.\n")
            for option in interrupt_value.options:
                print(f"{option.option_id}. {option.role.value} ({option.confidence:.2f})")

        return

    # ---------------------------------------------
    # Tool Argument HITL
    # ---------------------------------------------
    if isinstance(interrupt_value, ToolArgumentHITLRequest):

        print("\n" + "=" * 70)
        print("TOOL ARGUMENT UPDATE REQUIRED")
        print("=" * 70)

        print(f"\nTool : {interrupt_value.tool_name.value}")

        print("\nCurrent Arguments:")
        print(interrupt_value.arguments)

        print("\nMissing Information:")

        for field in interrupt_value.missing_arguments:
            print(f"- {field.field_name}: {field.description}")

        print(
            "\nYou can provide only the missing value "
            "or give a complete updated statement."
        )

        return

    # ---------------------------------------------
    # Material Movement HITL
    # ---------------------------------------------
    if isinstance(interrupt_value, MaterialMovementHITLRequest):

        print("\n" + "=" * 70)
        print("MATERIAL MOVEMENT — INFORMATION NEEDED")
        print("=" * 70)

        if interrupt_value.reason == MaterialMovementHITLReason.MISSING_FIELD:
            print(f"\nMissing field: {interrupt_value.missing_field}")
            print("Please provide the value (or type 'skip' to leave it unknown).")

        elif interrupt_value.reason == MaterialMovementHITLReason.LOCATION_TYPE_CONFIRMATION:
            print(f"\nLocation: {interrupt_value.location_name}")
            print("What type of location is this?\n")
            for option in interrupt_value.options:
                print(f"{option.option_id}. {option.location_type.value}")
            print("\n(or type 'skip' to leave it unknown)")

        return

    # ---------------------------------------------
    # Correction — Date
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionDateHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — DATE NEEDED")
        print("=" * 70)
        print(f"\nCorrection: {interrupt_value.text}")
        if interrupt_value.retry:
            print("\nDate samajh nahi aayi.")
        print("\nKis date ki entry galat thi?")
        print("(jaise '2 din pehle', 'kal', '20 september', '2026-09-20')")
        print("Correction chhodne ke liye 'cancel' likho.")

        return

    # ---------------------------------------------
    # Correction — Category
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionCategoryHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — CATEGORY")
        print("=" * 70)
        print("\nKis type ki entry mein galti thi?\n")
        for option in interrupt_value.options:
            print(f"{option.option_id}. {option.label}")
        print("\nCorrection chhodne ke liye 'cancel' likho.")

        return

    # ---------------------------------------------
    # Correction — Range
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionRangeHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — ENTRY NAHI MILI")
        print("=" * 70)
        print("\nIs date par is category ki koi entry nahi mili.")
        print("Kitne din ki report dekhna chahte ho?\n")
        for option in interrupt_value.options:
            print(f"{option.option_id}. {option.label}")

        return

    # ---------------------------------------------
    # Correction — Detail (report ke baad)
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionDetailHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — DETAIL")
        print("=" * 70)
        print(f"\n(Upar pichle {interrupt_value.days} din ki report hai.)")
        print("Report dekh kar batao: kaunsi entry galat hai aur kya theek karna hai?")
        print("(jaise: 'Ram ka 26 Sept wala payment galat hai, 600 hona chahiye')")
        print("Correction chhodne ke liye 'cancel' likho.")

        return

    # ---------------------------------------------
    # Correction — Match select
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionMatchHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — KAUNSI ENTRY?")
        print("=" * 70)
        if interrupt_value.name_dropped:
            print("\nNaam se koi entry nahi mili, is category ki sabhi entries dikha raha hoon.")

        views = [
            {"no": o.option_id, "date": o.date, "party": o.party, "type": o.type_label,
             "entry": o.voucher, "debit": o.debit, "credit": o.credit, "note": o.note}
            for o in interrupt_value.options
        ]
        print()
        print(render_table(
            views, interrupt_value.category, with_no=True, show_total=False,
            heading=TITLES.get(interrupt_value.category, ""),
        ))
        if interrupt_value.total > len(interrupt_value.options):
            print(f"(Sirf latest {len(interrupt_value.options)} dikha raha hoon, "
                  f"kul {interrupt_value.total} hain.)")
        print("\nEk number likho. Chhodne ke liye 'cancel'.")

        return

    # ---------------------------------------------
    # Correction — Confirm entry
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionConfirmHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — CONFIRM")
        print("=" * 70)
        d = "-" if interrupt_value.debit is None else f"{interrupt_value.debit:,.2f}"
        c = "-" if interrupt_value.credit is None else f"{interrupt_value.credit:,.2f}"
        print(f"\n{interrupt_value.date} | {interrupt_value.party} | {interrupt_value.type_label} "
              f"| Debit: {d} | Credit: {c} | {interrupt_value.note}")
        print("\nYehi entry hai? (yes/no)")

        return

    # ---------------------------------------------
    # Correction — Action choice
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionActionHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — KYA KARNA HAI?")
        print("=" * 70)
        for o in interrupt_value.options:
            print(f"{o.option_id}. {o.label}")
        print("\nChhodne ke liye 'cancel' likho.")

        return

    # ---------------------------------------------
    # Correction — New statement
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionStatementHITLRequest):

        print("\n" + "=" * 70)
        print("CORRECTION — NAYA STATEMENT")
        print("=" * 70)
        print(f"\nPurani entry: \"{interrupt_value.old_statement}\"")
        print("Sahi statement kya hai? (jaise: 'Ram ne 27 ko 700 ka kaam kiya')")
        print("Chhodne ke liye 'cancel' likho.")

        return

    # ---------------------------------------------
    # Final Confirmation
    # ---------------------------------------------
    if isinstance(interrupt_value, dict):

        print("\n" + "=" * 70)
        print("FINAL CONFIRMATION")
        print("=" * 70)

        print("\n" + interrupt_value.get("message", ""))

        return

    # ---------------------------------------------
    # Fallback
    # ---------------------------------------------
    print("\n" + "=" * 70)
    print("INTERRUPT")
    print("=" * 70)

    print(interrupt_value)

def build_resume_value(interrupt_value, user_response):
    """
    Converts the user's raw text into the correct resume object for
    each HITL type. Returns None if the input is invalid, so the
    caller can ask the SAME question again instead of skipping it.
    """

    # ---------------------------------------------
    # Person Role HITL
    # ---------------------------------------------
    if isinstance(interrupt_value, PersonRoleHITLRequest):

        try:
            selected = int(user_response)
        except ValueError:
            return None

        if interrupt_value.interaction_type == HITLInteractionType.CONFIRMATION:

            if selected == 1:
                return PersonRoleHITLResponse(
                    group_id=interrupt_value.group_id,
                    confirmed=True,
                    selected_option=None,
                )

            if selected == 2:
                # "No" — show every ranked option and let the user pick.
                print("\nSelect Correct Role\n")
                for option in interrupt_value.options:
                    print(f"{option.option_id}. {option.role.value} ({option.confidence:.2f})")

                while True:
                    try:
                        corrected = int(input("\nSelect : ").strip())
                    except ValueError:
                        print("Please enter a valid option number.")
                        continue
                    if 1 <= corrected <= len(interrupt_value.options):
                        break
                    print("Option out of range.")

                return PersonRoleHITLResponse(
                    group_id=interrupt_value.group_id,
                    confirmed=False,
                    selected_option=corrected,
                )

            return None

        # SELECTION (medium / low confidence)
        if 1 <= selected <= len(interrupt_value.options):
            return PersonRoleHITLResponse(
                group_id=interrupt_value.group_id,
                confirmed=None,
                selected_option=selected,
            )
        return None

    # ---------------------------------------------
    # Tool Argument HITL
    # ---------------------------------------------
    if isinstance(interrupt_value, ToolArgumentHITLRequest):
        return ToolArgumentHITLResponse(
            group_id=interrupt_value.group_id,
            updated_statement=user_response,
            confirmed=None,
        )

    # ---------------------------------------------
    # Material Movement HITL
    # ---------------------------------------------
    if isinstance(interrupt_value, MaterialMovementHITLRequest):

        if user_response.lower() == "skip":
            return MaterialMovementHITLResponse(
                group_id=interrupt_value.group_id,
                provided_value=None,
                selected_option=None,
            )

        if interrupt_value.reason == MaterialMovementHITLReason.MISSING_FIELD:
            return MaterialMovementHITLResponse(
                group_id=interrupt_value.group_id,
                provided_value=user_response,
                selected_option=None,
            )

        try:
            selected = int(user_response)
        except ValueError:
            return None

        return MaterialMovementHITLResponse(
            group_id=interrupt_value.group_id,
            provided_value=None,
            selected_option=selected,
        )

    # ---------------------------------------------
    # Correction — Date
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionDateHITLRequest):
        return CorrectionDateHITLResponse(
            group_id=interrupt_value.group_id,
            answer=user_response,
        )

    # ---------------------------------------------
    # Correction — Category
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionCategoryHITLRequest):

        if user_response.lower() == "cancel":
            return CorrectionCategoryHITLResponse(
                group_id=interrupt_value.group_id,
                cancelled=True,
            )

        try:
            selected = int(user_response)
        except ValueError:
            return None

        if not any(o.option_id == selected for o in interrupt_value.options):
            return None   # galat number: wahi sawaal dobara

        return CorrectionCategoryHITLResponse(
            group_id=interrupt_value.group_id,
            selected_option=selected,
        )

    # ---------------------------------------------
    # Correction — Range
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionRangeHITLRequest):

        if user_response.lower() == "cancel":
            return CorrectionRangeHITLResponse(
                group_id=interrupt_value.group_id,
                cancelled=True,
            )

        try:
            selected = int(user_response)
        except ValueError:
            return None

        if not any(o.option_id == selected for o in interrupt_value.options):
            return None

        return CorrectionRangeHITLResponse(
            group_id=interrupt_value.group_id,
            selected_option=selected,
        )

    # ---------------------------------------------
    # Correction — Detail
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionDetailHITLRequest):
        return CorrectionDetailHITLResponse(
            group_id=interrupt_value.group_id,
            answer=user_response,
        )

    # ---------------------------------------------
    # Correction — Match select (multi-select: "1,3")
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionMatchHITLRequest):

        if user_response.lower() == "cancel":
            return CorrectionMatchHITLResponse(
                group_id=interrupt_value.group_id,
                cancelled=True,
            )

        try:
            selected = int(user_response)
        except ValueError:
            return None

        if not any(o.option_id == selected for o in interrupt_value.options):
            return None

        return CorrectionMatchHITLResponse(
            group_id=interrupt_value.group_id,
            selected_option=selected,
        )

    # ---------------------------------------------
    # Correction — Confirm entry
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionConfirmHITLRequest):
        ans = user_response.lower()
        if ans not in ("yes", "no"):
            return None
        return CorrectionConfirmHITLResponse(
            group_id=interrupt_value.group_id,
            confirmed=(ans == "yes"),
        )

    # ---------------------------------------------
    # Correction — Action choice
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionActionHITLRequest):
        if user_response.lower() == "cancel":
            return CorrectionActionHITLResponse(
                group_id=interrupt_value.group_id,
                cancelled=True,
            )
        try:
            selected = int(user_response)
        except ValueError:
            return None
        if not any(o.option_id == selected for o in interrupt_value.options):
            return None
        return CorrectionActionHITLResponse(
            group_id=interrupt_value.group_id,
            selected_option=selected,
        )

    # ---------------------------------------------
    # Correction — New statement
    # ---------------------------------------------
    if isinstance(interrupt_value, CorrectionStatementHITLRequest):
        return CorrectionStatementHITLResponse(
            group_id=interrupt_value.group_id,
            answer=user_response,
        )

    # ---------------------------------------------
    # Final Confirmation / anything else
    # ---------------------------------------------
    return user_response

async def main():

    app = await build_app()

    while True:

        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        config = {
            "configurable": {
                "thread_id": THREAD_ID
            }
        }

        # --------------------------------------------------
        # Start graph
        # --------------------------------------------------
        result = await app.ainvoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "original_user_statement": user_input,
            },
            config=config
        )

        # --------------------------------------------------
        # Handle HITL interrupts — including MULTIPLE parallel
        # interrupts arriving in the same super-step. Every pending
        # interrupt gets an answer, then all are resumed together
        # via a resume-map keyed by interrupt id.
        # --------------------------------------------------
        while result.get("__interrupt__"):

            interrupts = result["__interrupt__"]
            resume_map = {}

            for interrupt_obj in interrupts:

                interrupt_value = interrupt_obj.value

                # Ask the SAME question again until the answer is valid —
                # never skip an interrupt, or its branch gets abandoned.
                while True:
                    display_interrupt(interrupt_value)
                    user_response = input("\nAap: ").strip()

                    if not user_response:
                        print("\nPlease provide a response.")
                        continue

                    resume_value = build_resume_value(interrupt_value, user_response)

                    if resume_value is None:
                        print("\nInvalid input — please try again.")
                        continue

                    break

                resume_map[interrupt_obj.id] = resume_value

            result = await app.ainvoke(
                Command(resume=resume_map),
                config=config
            )

        # --------------------------------------------------
        # Final bot response
        # --------------------------------------------------
        if result.get("messages"):
            print("\nBot:", result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())



