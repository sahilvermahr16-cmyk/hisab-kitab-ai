import asyncio
import os
import uuid
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
    HITLReason,
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
    ReportHITLRequest,
    ReportHITLResponse,
)

from correction_format import render_table, TITLES

# Har statement ka apna naya thread — ek statement (aur uske saare HITL sawaal)
# ek hi thread mein chalte hain. Pehle saari baatein ek hi "test_006" thread mein
# jaati thi: state har baat ke saath badhti gayi aur checkpoints.db 13 GB ho gaya —
# har step pe poori state likhne mein minute lagne lage. Statements ek-doosre pe
# depend nahi karte (router sirf aakhri message padhta hai), isliye naya thread safe hai.
def new_thread_id():
    return f"cli-{uuid.uuid4().hex[:12]}"


def warn_big_checkpoints(limit_mb=500):
    try:
        size = sum(os.path.getsize(f) for f in ("checkpoints.db", "checkpoints.db-wal") if os.path.exists(f))
    except OSError:
        return
    if size > limit_mb * 1024 * 1024:
        print(f"⚠️  checkpoints.db {size / 1024 / 1024 / 1024:.1f} GB ho gaya hai — app slow chalega. "
              f"main.py band karke checkpoints.db, checkpoints.db-wal, checkpoints.db-shm delete kar do "
              f"(isme sirf adhoori baatchit hoti hai, hisab ka data Postgres mein safe hai).")


def _mm_choices(req):
    """Material movement 'kahan se?' ke options: jaani-pehchaani jagahen + aakhri 'Pata nahi'."""
    return list(getattr(req, "suggestions", []) or []) + ["Pata nahi"]


def _print_role_options(req):
    """Role ki list. Naam pehle se mila ho to us category ke aage ✓ — warna AI ka score."""
    known = any(o.found for o in req.options)
    no_scores = all(o.confidence == 0 for o in req.options)   # AI kuch nahi bata paya
    for option in req.options:
        if known or no_scores:
            mark = f"  ✓ ('{req.person}' isme mila)" if option.found else ""
            print(f"{option.option_id}. {option.role.value}{mark}")
        else:
            print(f"{option.option_id}. {option.role.value} ({option.confidence:.2f})")


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

        known = interrupt_value.reason in (HITLReason.KNOWN_PERSON_CONFIRMATION, HITLReason.KNOWN_PERSON_SELECTION)
        if known and interrupt_value.interaction_type == HITLInteractionType.CONFIRMATION:
            top = interrupt_value.options[0]
            print(f"'{interrupt_value.person}' humein {top.role.value} mein mila.")
            print()
            print(f"1. Haan, {top.role.value} hi hai")
            print("2. Nahi, dusri category hai")
        elif known:
            print(f"'{interrupt_value.person}' ek se zyada category mein mila — kiska hisab hai?\n")
            _print_role_options(interrupt_value)
        elif interrupt_value.interaction_type == HITLInteractionType.CONFIRMATION:
            top = interrupt_value.options[0]
            print(f"AI Recommendation : {top.role.value} ({top.confidence:.2f})")
            print()
            print("1. Yes")
            print("2. No")
        else:
            print("Please select the correct role.\n")
            _print_role_options(interrupt_value)

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
            q = ("Maal kahan se aaya / kahan se gaya?" if interrupt_value.missing_field == "source"
                 else "Maal kahan gaya / kahan utra?")
            print(f"\n{q}\n")
            for i, name in enumerate(_mm_choices(interrupt_value), 1):
                print(f"{i}. {name}")
            print("\n(Number chuno, ya jagah ka naam likho)")

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
        print("Sahi, poora statement do — jaise: 'Ram ne 27 ko 700 ka kaam kiya'.")
        print("Shortcuts jaise 'usi din', 'wo nahi ye' mat likho — naam aur amount")
        print("clearly batao. Date nahi doge to purani entry wali date use ho jayegi.")
        print("Chhodne ke liye 'cancel' likho.")

        return

    # ---------------------------------------------
    # Report — har sawaal (kind / role / name / range / language)
    # ---------------------------------------------
    if isinstance(interrupt_value, ReportHITLRequest):

        print("\n" + "=" * 70)
        print("REPORT")
        print("=" * 70)
        if interrupt_value.retry:
            print("\nSamajh nahi aaya, dobara batao.")
        print(f"\n{interrupt_value.question}\n")
        for o in interrupt_value.options:
            print(f"{o.option_id}. {o.label}")
        if interrupt_value.hint:
            print(f"\n({interrupt_value.hint})")
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
                _print_role_options(interrupt_value)

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
            choices = _mm_choices(interrupt_value)
            value = user_response
            if user_response.isdigit():
                k = int(user_response)
                if not 1 <= k <= len(choices):
                    return None
                value = choices[k - 1]
            if value == "Pata nahi" or value.lower() in ("pata nahi", "pta nhi", "skip"):
                value = None
            return MaterialMovementHITLResponse(
                group_id=interrupt_value.group_id,
                provided_value=value,
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
    # Report
    # ---------------------------------------------
    if isinstance(interrupt_value, ReportHITLRequest):
        if user_response.lower() == "cancel":
            return ReportHITLResponse(cancelled=True)
        try:
            selected = int(user_response)
        except ValueError:
            if interrupt_value.allow_text:
                return ReportHITLResponse(answer=user_response)
            return None
        if any(o.option_id == selected for o in interrupt_value.options):
            return ReportHITLResponse(selected_option=selected)
        return None

    # ---------------------------------------------
    # Final Confirmation / anything else
    # ---------------------------------------------
    return user_response

async def main():

    warn_big_checkpoints()
    app = await build_app()

    while True:

        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        config = {
            "configurable": {
                "thread_id": new_thread_id()
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



