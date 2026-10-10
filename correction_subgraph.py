# correction_subgraph.py
from datetime import date, datetime, timedelta
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Send
from langchain_core.messages import HumanMessage

from db import SessionLocal
from models import AuditLog
from llm_setup import llm
from schemas import (
    RecordType,
    CorrectionDateResult,
    CorrectionDateHITLRequest,
    CorrectionDateHITLResponse,
    CorrectionCategoryOption,
    CorrectionCategoryHITLRequest,
    CorrectionCategoryHITLResponse,
    CorrectionRangeOption,
    CorrectionRangeHITLRequest,
    CorrectionRangeHITLResponse,
    CorrectionDetailHITLRequest,
    CorrectionDetailHITLResponse,
    CorrectionDetailResult,
    CorrectionMatchOption,
    CorrectionMatchHITLRequest,
    CorrectionMatchHITLResponse,
    CorrectionConfirmHITLRequest,
    CorrectionConfirmHITLResponse,
    CorrectionActionOption,
    CorrectionActionHITLRequest,
    CorrectionActionHITLResponse,
    CorrectionStatementHITLRequest,
    CorrectionStatementHITLResponse,
)
from state import ChatState
from correction_format import to_view, render_table, TITLES
from llm_setup import TOOLS_MAP
from helpers import insert_audit_log, mark_business_tables_corrected, reverse_entry
from extract_node import extract_node
from grouping_node import grouping_node
from person_role_classification_node import person_role_classification_node
from person_role_hitl_node import person_role_hitl_node
from tool_decision_node import tool_decision_node
from tool_argument_extraction_node import tool_argument_extraction_node
from tool_argument_hitl import _find_missing_arguments, tool_argument_hitl_node
from tool_argument_update import tool_argument_update_node
from final_confirmation_node import final_confirmation_node
from tool_execution_node import tool_execution_node
from material_movement_subgraph import material_movement_subgraph
from standalone_transaction_node import standalone_transaction_node

_date_llm = llm.with_structured_output(CorrectionDateResult)
_detail_llm = llm.with_structured_output(CorrectionDetailResult)

MAX_LIST = 15

import re as _re
_OPENING_WORDS = _re.compile(
    r"opening|purana baaki|purane baaki|pichla baaki|pichli baaki|pehle ka baaki|shuru ka cash|"
    r"shuru mein .*cash|purana udhaar|pehle ka udhaar"
)

CATEGORY_OPTIONS = [
    CorrectionCategoryOption(option_id=1, category="employee", label="Employee (kaam / payment / attendance)"),
    CorrectionCategoryOption(option_id=2, category="customer", label="Customer (sale / payment)"),
    CorrectionCategoryOption(option_id=3, category="supplier", label="Supplier (maal aaya / payment)"),
    CorrectionCategoryOption(option_id=4, category="purchase", label="Purchase (ghar / property deal)"),
    CorrectionCategoryOption(option_id=5, category="expense", label="Expense (kharcha)"),
    CorrectionCategoryOption(option_id=6, category="material_movement", label="Material Movement (maal / work log / stock)"),
    CorrectionCategoryOption(option_id=7, category="opening", label="Opening Balance (purana baaki / shuru ka cash)"),
    CorrectionCategoryOption(option_id=8, category="family", label="Family Kharcha (ghar ke log)"),
]

RANGE_OPTIONS = [
    CorrectionRangeOption(option_id=1, label="Pichle 5 din", days=5),
    CorrectionRangeOption(option_id=2, label="Pichle 10 din", days=10),
    CorrectionRangeOption(option_id=3, label="Pichle 15 din", days=15),
    CorrectionRangeOption(option_id=4, label="Pichla 1 mahina", days=30),
    CorrectionRangeOption(option_id=5, label="Cancel", days=0),
]

DATE_PROMPT = """
You extract a date from ONE correction sentence in a Hinglish accounting app.
Today's date: {today}

Return a date ONLY if the text explicitly states a date or a relative date:
- "aaj", "aj", "today" -> today's own date (same as {today})
- "kal" -> one day before today, "parso" -> two days before today
- "2 din pehle", "teen din pehle" -> N days before today
- "3 tareekh", "9 August", "2026-09-20", "20/09/2026"
- If only a day is given, use the current month and year; if that lands in
  the future, use the previous month.

These are NOT dates, return null:
- "pichla entry", "purani entry", "pehle wali", "jo dala tha", "last wali"
- ranges or periods such as "pichle hafte", "is mahine"

Return the date as YYYY-MM-DD, or null.
"""

DETAIL_PROMPT = """
The user looked at a report and describes which accounting entry is wrong
(Hinglish). Extract:
- date: the date of the wrong entry as YYYY-MM-DD (resolve "kal", "2 din pehle",
  "26 september" etc. using today's date), or null if no date is stated.
- name: the person/party name mentioned, or null.
Today's date: {today}
Do not guess. Use null when something is not stated.
"""

ACTION_OPTIONS = [
    CorrectionActionOption(option_id=1, label="Poora naya statement doonga"),
    CorrectionActionOption(option_id=2, label="Delete karo"),
]


def _valid_past_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    if parsed > date.today():
        return None
    return value


async def _parse_date(text: str) -> str | None:
    prompt = DATE_PROMPT.format(today=date.today().isoformat())
    result = await _date_llm.ainvoke(f"{prompt}\n\nText:\n{text}")
    return _valid_past_date(result.date)


def _get_correction_group(state):
    for g in state["grouped_intent"].groups:
        if g.record_type == RecordType.CORRECTION:
            return g
    return None


# ---------------- DB search ----------------

def _row_to_dict(r) -> dict:
    args = r.arguments or {}
    amount = (
        args.get("amount")
        or args.get("total_amount")
        or args.get("quantity_change")
        or args.get("quantity")
    )
    return {
        "id": r.id,
        "run_id": r.run_id,
        "group_id": r.group_id,
        "action_index": r.action_index,
        "tool_name": r.tool_name,
        "action_statement": r.action_statement,
        "arguments": args,
        "target_table": r.target_table,
        "target_id": r.target_id,
        "person_name": r.person_name,
        "entry_date": r.entry_date.isoformat() if r.entry_date else None,
        "amount": amount,
    }

def _negate_arguments(arguments: dict) -> dict:
    """
    Same tool, negative numeric fields — taaki cascade-logic (Inventory,
    CashLedger) khud-hi sahi reverse ho jaaye.
    """
    negated = dict(arguments)
    for field in ("amount", "total_amount", "quantity", "quantity_change"):
        if field in negated and negated[field] not in (None, 0):
            negated[field] = -negated[field]
    return negated

def _voucher_map(db, dates: set) -> dict:
    """Us din ki saari audit rows par 1..N (id ke order mein). Number kabhi nahi badalta."""
    if not dates:
        return {}
    rows = (
        db.query(AuditLog.id, AuditLog.entry_date)
        .filter(AuditLog.entry_date.in_(dates))
        .order_by(AuditLog.entry_date, AuditLog.id)
        .all()
    )
    counters, out = {}, {}
    for rid, d in rows:
        counters[d] = counters.get(d, 0) + 1
        out[rid] = f"{d.day:02d}-{counters[d]}"
    return out


def _search_audit(category: str, date_from: str, date_to: str, name: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        q = db.query(AuditLog).filter(
            AuditLog.category == category,
            AuditLog.status == "active",
            AuditLog.entry_date >= date.fromisoformat(date_from),
            AuditLog.entry_date <= date.fromisoformat(date_to),
            ~AuditLog.tool_name.startswith("manage_", autoescape=True),
            # [REVERSAL] rows galat entry ka "ulta" hain — inhe dobara correct karne ka sawaal nahi
            ~AuditLog.action_statement.startswith("[REVERSAL]", autoescape=True),
        )
        if name:
            q = q.filter(AuditLog.person_name.ilike(f"%{name}%"))
        rows = q.order_by(AuditLog.entry_date.desc(), AuditLog.id.asc()).all()

        vmap = _voucher_map(db, {r.entry_date for r in rows if r.entry_date})
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["voucher"] = vmap.get(r.id, f"#{r.id}")
            result.append(d)
        return result
    finally:
        db.close()

# ---------------- Step 1: Date ----------------

async def correction_date_extract_node(state):
    group = _get_correction_group(state)
    if group is None:
        return {"correction_data": {"skip": True}}

    text = group.actions[0].text
    key = (group.identity_key or "").strip()
    name = None if key.lower() == "correction" or not key else key

    # Opening balance ki correction: user ko us entry ki date pata nahi hoti
    # (wo pehli entry ki date pe lagta hai) — isliye date/category mat poochho,
    # seedha saari opening entries mein dhoondho.
    if _OPENING_WORDS.search(text.lower()):
        today = date.today().isoformat()
        return {
            "correction_data": {
                "group_id": group.group_id, "text": text, "name": name,
                "date": today, "cancelled": False, "attempts": 0,
                "category": "opening", "matches": [], "selected_ids": [],
                "report_shown": False, "name_dropped": False, "range_days": None,
                "date_from": "2000-01-01", "date_to": today,
            }
        }

    found = await _parse_date(text)
    return {
        "correction_data": {
            "group_id": group.group_id,
            "text": text,
            "name": name,
            "date": found,
            "cancelled": False,
            "attempts": 0,
            "category": None,
            "matches": [],
            "selected_ids": [],
            "report_shown": False,
            "name_dropped": False,
            "range_days": None,
            "date_from": None,
            "date_to": None,
        }
    }


def _after_date(state) -> str:
    data = state["correction_data"]
    if data.get("skip") or data.get("cancelled"):
        return "end"
    if data.get("category"):          # opening balance — category pehle se tay
        return "search"
    if data.get("date"):
        return "category"
    return "ask"


async def correction_date_ask_node(state):
    data = dict(state["correction_data"])

    response = interrupt(
        CorrectionDateHITLRequest(
            group_id=data["group_id"],
            text=data["text"],
            retry=data.get("attempts", 0) > 0,
        )
    )
    answer = response.answer.strip()

    if answer.lower() in ("cancel", "skip"):
        data["cancelled"] = True
        return {"correction_data": data}

    data["date"] = await _parse_date(answer)
    data["attempts"] = data.get("attempts", 0) + 1
    return {"correction_data": data}


# ---------------- Step 2: Category ----------------

async def correction_category_ask_node(state):
    data = dict(state["correction_data"])

    response = interrupt(
        CorrectionCategoryHITLRequest(
            group_id=data["group_id"],
            options=CATEGORY_OPTIONS,
        )
    )

    if response.cancelled or response.selected_option is None:
        data["cancelled"] = True
        return {"correction_data": data}

    chosen = next(o for o in CATEGORY_OPTIONS if o.option_id == response.selected_option)
    data["category"] = chosen.category
    return {"correction_data": data}


def _after_category(state) -> str:
    return "end" if state["correction_data"].get("cancelled") else "search"


# ---------------- Step 3: Search ----------------

async def correction_search_node(state):
    data = dict(state["correction_data"])

    date_from = data.get("date_from") or data["date"]
    date_to = data.get("date_to") or data["date"]
    name = data.get("name")

    matches = _search_audit(data["category"], date_from, date_to, name)
    data["name_dropped"] = False

    # Naam se 0 aaye to naam hata ke dobara (spelling ya galat extract).
    if not matches and name:
        matches = _search_audit(data["category"], date_from, date_to, None)
        data["name_dropped"] = bool(matches)

    data["matches"] = matches
    return {"correction_data": data}


def _after_search(state) -> str:
    data = state["correction_data"]
    if data.get("matches"):
        return "select"
    return "range"


# ---------------- Step 3b: 0 match -> range menu -> report ----------------

async def correction_range_ask_node(state):
    data = dict(state["correction_data"])

    response = interrupt(
        CorrectionRangeHITLRequest(
            group_id=data["group_id"],
            options=RANGE_OPTIONS,
        )
    )

    if response.cancelled or response.selected_option is None:
        data["cancelled"] = True
        return {"correction_data": data}

    chosen = next(o for o in RANGE_OPTIONS if o.option_id == response.selected_option)
    if chosen.days == 0:
        data["cancelled"] = True
        return {"correction_data": data}

    data["range_days"] = chosen.days
    return {"correction_data": data}


def _after_range(state) -> str:
    return "end" if state["correction_data"].get("cancelled") else "report"


def show_report(rows: list[dict], category: str, days: int) -> None:
    """Reporting phase mein yahi function upgrade hoga (PDF)."""
    ordered = sorted(rows, key=lambda r: (r["entry_date"] or "", r["id"]))
    views = [to_view(r) for r in ordered]
    if not views:
        print("\nIs period mein koi entry nahi.")
        return
    today = date.today()
    heading = (
        f"REPORT: {TITLES.get(category, category.upper())}"
        f"     {(today - timedelta(days=days)).strftime('%d-%b-%Y')} se {today.strftime('%d-%b-%Y')}"
    )
    print("\n" + render_table(views, category, with_no=False, show_total=True, heading=heading))

async def correction_report_show_node(state):
    data = dict(state["correction_data"])
    days = data["range_days"]
    today = date.today()
    rows = _search_audit(
        data["category"],
        (today - timedelta(days=days)).isoformat(),
        today.isoformat(),
        None,
    )
    show_report(rows, data["category"], days)
    data["report_shown"] = True
    return {"correction_data": data}

async def correction_detail_ask_node(state):
    data = dict(state["correction_data"])

    response = interrupt(
        CorrectionDetailHITLRequest(
            group_id=data["group_id"],
            days=data["range_days"],
        )
    )
    answer = response.answer.strip()

    if answer.lower() in ("cancel", "skip"):
        data["cancelled"] = True
        return {"correction_data": data}

    prompt = DETAIL_PROMPT.format(today=date.today().isoformat())
    parsed = await _detail_llm.ainvoke(f"{prompt}\n\nUser text:\n{answer}")

    found_date = _valid_past_date(parsed.date)
    today = date.today()
    if found_date:
        data["date_from"] = found_date
        data["date_to"] = found_date
    else:
        # Date nahi di: report wale poore range mein dhoondho.
        data["date_from"] = (today - timedelta(days=data["range_days"])).isoformat()
        data["date_to"] = today.isoformat()

    if parsed.name:
        data["name"] = parsed.name

    return {"correction_data": data}


def _after_detail(state) -> str:
    return "end" if state["correction_data"].get("cancelled") else "search"


# ---------------- Step 4: Match select ----------------

async def correction_select_ask_node(state):
    data = dict(state["correction_data"])
    matches = data["matches"]

    options = []
    for i, m in enumerate(matches[:MAX_LIST], start=1):
        v = to_view(m)
        options.append(
            CorrectionMatchOption(
                option_id=i,
                entry_id=m["id"],
                voucher=v["entry"],
                date=v["date"],
                party=v["party"],
                type_label=v["type"],
                debit=v["debit"],
                credit=v["credit"],
                note=v["note"],
                statement=m["action_statement"],
            )
        )

    response = interrupt(
        CorrectionMatchHITLRequest(
            group_id=data["group_id"],
            category=data["category"],
            options=options,
            total=len(matches),
            name_dropped=data.get("name_dropped", False),
        )
    )

    if response.cancelled or response.selected_option is None:
        data["cancelled"] = True
        return {"correction_data": data}

    chosen = options[response.selected_option - 1]
    data["selected_id"] = chosen.entry_id
    return {"correction_data": data}


def _after_select(state) -> str:
    return "end" if state["correction_data"].get("cancelled") else "confirm"


async def correction_confirm_ask_node(state):
    data = dict(state["correction_data"])
    m = next(x for x in data["matches"] if x["id"] == data["selected_id"])
    v = to_view(m)

    response = interrupt(
        CorrectionConfirmHITLRequest(
            group_id=data["group_id"],
            date=v["date"],
            party=v["party"],
            type_label=v["type"],
            debit=v["debit"],
            credit=v["credit"],
            note=v["note"],
        )
    )

    if not response.confirmed:
        data["cancelled"] = True
    return {"correction_data": data}


def _after_confirm(state) -> str:
    return "end" if state["correction_data"].get("cancelled") else "action"


async def correction_action_ask_node(state):
    data = dict(state["correction_data"])

    response = interrupt(
        CorrectionActionHITLRequest(
            group_id=data["group_id"],
            options=ACTION_OPTIONS,
        )
    )

    if response.cancelled or response.selected_option is None:
        data["cancelled"] = True
        return {"correction_data": data}

    data["action_choice"] = "statement" if response.selected_option == 1 else "delete"
    return {"correction_data": data}

async def correction_execute_delete_node(state):
    data = dict(state["correction_data"])
    m = next(x for x in data["matches"] if x["id"] == data["selected_id"])

    negated_args = _negate_arguments(m["arguments"])

    execution_result = reverse_entry(m["tool_name"], m.get("target_table"), m.get("target_id"),
                                     negated_args, TOOLS_MAP)

    db = SessionLocal()
    try:
        if isinstance(execution_result, dict):
            insert_audit_log(
                db=db,
                full_statement=data["text"],
                action_statement=f"[REVERSAL] {m['action_statement']}",
                tool_name=m["tool_name"],
                arguments=negated_args,
                target_table=execution_result["target_table"],
                target_id=execution_result["target_id"],
                group_id=m["group_id"],
                action_index=m["action_index"],
                run_id=m["run_id"],
            )
            original = db.query(AuditLog).filter(AuditLog.id == m["id"]).first()
            if original:
                original.status = "corrected"

            if original is not None and original.target_table and original.target_id:
                mark_business_tables_corrected(
                    db=db,
                    target_table=original.target_table,
                    old_row_id=original.target_id,
                    new_row_id=execution_result["target_id"],
                )

            db.commit()
            data["delete_done"] = True
        else:
            data["delete_error"] = str(execution_result)
    finally:
        db.close()

    return {"correction_data": data}

def _after_action(state) -> str:
    data = state["correction_data"]
    if data.get("cancelled"):
        return "end"
    if data.get("action_choice") == "delete":
        return "execute_delete"
    return "statement"

async def correction_statement_ask_node(state):
    data = dict(state["correction_data"])
    m = next(x for x in data["matches"] if x["id"] == data["selected_id"])

    response = interrupt(
        CorrectionStatementHITLRequest(
            group_id=data["group_id"],
            old_statement=m["action_statement"],
        )
    )
    answer = response.answer.strip()

    if answer.lower() in ("cancel", "skip"):
        data["cancelled"] = True
        return {"correction_data": data}

    data["new_statement"] = answer
    return {"correction_data": data}

# ---------------- Naya Statement: internal re-run pipeline ----------------

async def correction_statement_prepare_node(state):
    """
    Naya statement ko khud extract+grouping se guzarta hai (jaisa decide
    kiya tha) — poori accounting_subgraph dobara call nahi karte, sirf
    non-interrupt nodes (extract, grouping, person-role classification)
    seedha function-call se.

    - Agar result mein se koi CORRECTION-type group nikle, use silently
      drop kar dete hain (infinite correction-loop se bachne ke liye).
    - Agar kisi action mein explicit date nahi mili, purani (galat) entry
      ki date use karte hain — "aaj" ka default nahi, kyunki yahan date
      ka matlab hai "jis din purani entry hui thi", na ki "aaj".
    """
    data = dict(state["correction_data"])
    new_statement = data["new_statement"]

    extracted = await extract_node({"messages": [HumanMessage(content=new_statement)]})
    grouped = await grouping_node({"extracted_intent": extracted["extracted_intent"]})
    grouped_intent = grouped["grouped_intent"]

    kept_groups = [g for g in grouped_intent.groups if g.record_type != RecordType.CORRECTION]

    if not kept_groups:
        data["statement_dropped"] = True
        return {"correction_data": data}

    m = next(x for x in data["matches"] if x["id"] == data["selected_id"])
    original_date = m["entry_date"]

    for group in kept_groups:
        for action in group.actions:
            explicit_date = await _parse_date(action.text)
            if not explicit_date:
                action.date = original_date

    grouped_intent.groups = kept_groups

    person_role_rankings = []
    if any(g.record_type == RecordType.NEED_PERSON for g in kept_groups):
        ranked = await person_role_classification_node({"grouped_intent": grouped_intent})
        person_role_rankings = ranked["person_role_rankings"]

    return {
        "correction_data": data,
        "grouped_intent": grouped_intent,
        "person_role_rankings": person_role_rankings,
    }


def _statement_dispatch(state):
    """
    Naya-statement ke groups ko (Correction-type already-filtered) unke
    apne branch mein bhejta hai — accounting_subgraph ke group_dispatcher
    jaisa hi pattern, isi subgraph ke andar.
    """
    data = state["correction_data"]
    if data.get("statement_dropped"):
        return "placeholder"

    groups = state["grouped_intent"].groups
    rankings_by_group = {r.group_id: r for r in (state.get("person_role_rankings") or [])}
    sends = []
    for group in groups:
        if group.record_type == RecordType.NEED_PERSON:
            ranking = rankings_by_group.get(group.group_id)
            if ranking is None:
                raise ValueError(f"No person-role ranking found for {group.group_id}.")
            sends.append(Send("statement_person_hitl", {
                "single_group": group,
                "person_role_rankings": [ranking],
            }))
        elif group.record_type == RecordType.MATERIAL_MOVEMENT:
            sends.append(Send("statement_material_movement", {"single_group": group}))
        elif group.record_type == RecordType.STANDALONE_TRANSACTION:
            sends.append(Send("statement_standalone", {"single_group": group}))
    return sends


def _after_statement_tool_argument_extraction(state) -> str:
    tool_argument_results = state.get("tool_argument_results")
    if tool_argument_results is None:
        raise ValueError("tool_argument_results not found after Naya Statement extraction.")
    for result in tool_argument_results.results:
        missing_arguments = _find_missing_arguments(
            tool_name=result.tool_name,
            arguments=result.arguments,
        )
        if missing_arguments:
            return "tool_argument_hitl"
    return "final_confirm"


async def correction_statement_execute_node(state):
    """
    Final-confirmation ke baad: pehle naya statement execute karo, SIRF
    uske successful hone par purani (galat) entry ko reverse+corrected
    karo. Beech mein kahin bhi "no" aaya ho to yahan tak pahunchenge hi
    nahi — purani entry bilkul untouched rehti hai.
    """
    data = dict(state["correction_data"])

    confirmations = state.get("final_confirmation_results") or []
    all_yes = bool(confirmations) and all(
        str(c["confirmed"]).strip().lower() == "yes" for c in confirmations
    )

    if not all_yes:
        data["statement_cancelled"] = True
        # Outer accounting_subgraph ka TOOL_EXECUTION "correction" ke
        # turant baad chalta hai — agar yahan tool_argument_results
        # chhod diya, to woh dobara (ya partially) execute kar dega.
        # Isliye yahin clear kar dete hain: ab kuch bhi execute nahi hona.
        return {"correction_data": data, "tool_argument_results": None}

    exec_state = dict(state)
    exec_state["original_user_statement"] = data["new_statement"]
    exec_result = await tool_execution_node(exec_state)
    execution_results = exec_result.get("tool_execution_results", [])

    failed = (not execution_results) or any(
        isinstance(r, str) and r.startswith("❌") for r in execution_results
    )

    if failed:
        data["statement_execution_failed"] = True
        return {
            "correction_data": data,
            "tool_execution_results": execution_results,
            "tool_argument_results": None,
        }

    # Naya statement successfully execute ho gaya — ab purani entry
    # reverse+corrected karo (Delete-case jaisa hi tareeka).
    m = next(x for x in data["matches"] if x["id"] == data["selected_id"])
    negated_args = _negate_arguments(m["arguments"])
    reversal_result = reverse_entry(m["tool_name"], m.get("target_table"), m.get("target_id"),
                                    negated_args, TOOLS_MAP)

    db = SessionLocal()
    try:
        if isinstance(reversal_result, dict):
            insert_audit_log(
                db=db,
                full_statement=data["text"],
                action_statement=f"[REVERSAL] {m['action_statement']}",
                tool_name=m["tool_name"],
                arguments=negated_args,
                target_table=reversal_result["target_table"],
                target_id=reversal_result["target_id"],
                group_id=m["group_id"],
                action_index=m["action_index"],
                run_id=m["run_id"],
            )
            original = db.query(AuditLog).filter(AuditLog.id == m["id"]).first()
            if original:
                original.status = "corrected"

            if original is not None and original.target_table and original.target_id:
                mark_business_tables_corrected(
                    db=db,
                    target_table=original.target_table,
                    old_row_id=original.target_id,
                    new_row_id=reversal_result["target_id"],
                )

            db.commit()
            data["statement_done"] = True
        else:
            data["statement_reversal_error"] = str(reversal_result)
    finally:
        db.close()

    # Already (ourselves) execute kar chuke — outer TOOL_EXECUTION node
    # ko dobara chalne se rokne ke liye yahan clear karna zaroori hai,
    # warna wahi tool-call ek baar aur execute ho jayega (duplicate TX).
    return {
        "correction_data": data,
        "tool_execution_results": execution_results,
        "tool_argument_results": None,
    }


def _after_statement_ask(state) -> str:
    return "placeholder" if state["correction_data"].get("cancelled") else "prepare"


# ---------------- Placeholder (confirm/edit/delete aane tak) ----------------

async def correction_placeholder_node(state):
    data = state["correction_data"]
    print("\n" + "=" * 60)
    print("CORRECTION (placeholder after Search node)")
    print("=" * 60)
    if data.get("skip"):
        print("No correction group found.")
    elif data.get("cancelled"):
        print("Correction cancelled by user.")
    elif data.get("selected_ids"):
        chosen = [m for m in data["matches"] if m["id"] in data["selected_ids"]]
        print("Category:", data["category"])
        print("Selected entries:")
        for m in chosen:
            print(f"  #{m['id']} | {m['entry_date']} | {m['tool_name']} | "
                  f"{m['person_name']} | {m['amount']} | run_id={m['run_id']}")
    elif data.get("report_shown"):
        print("Report dikha di gayi. Naya, poora statement bhejo correction ke liye.")
    elif data.get("selected_id") and data.get("action_choice"):
        m = next(x for x in data["matches"] if x["id"] == data["selected_id"])
        print("Category:", data["category"])
        print(f"Entry: #{m['id']} | {m['entry_date']} | {m['tool_name']} | "
              f"{m['person_name']} | {m['amount']}")
        if data["action_choice"] == "delete":
            if data.get("delete_done"):
                print("Entry successfully DELETE ho gayi (reversal ke saath).")
            elif data.get("delete_error"):
                print("Delete FAIL hua:", data["delete_error"])
        else:
            print("Action: NAYA STATEMENT")
            print("Naya statement:", data.get("new_statement"))
            if data.get("statement_dropped"):
                print("Naya statement khud ek Correction tha — drop kar diya gaya (infinite loop se bachne ke liye).")
            elif data.get("statement_cancelled"):
                print("Naya statement process cancel ho gaya. Purani entry untouched hai.")
            elif data.get("statement_execution_failed"):
                print("Naya statement execute nahi ho paya. Purani entry untouched hai.")
            elif data.get("statement_reversal_error"):
                print("Naya statement execute ho gaya, par purani entry reverse karte waqt error:", data["statement_reversal_error"])
            elif data.get("statement_done"):
                print("Naya statement successfully execute ho gaya, aur purani entry reverse+corrected ho gayi.")
    elif data.get("selected_id"):
        m = next(x for x in data["matches"] if x["id"] == data["selected_id"])
        print("Category:", data["category"])
        print(f"Selected: #{m['id']} | {m['entry_date']} | {m['tool_name']} | "
              f"{m['person_name']} | {m['amount']}")
    else:
        print("Category:", data.get("category"))
        print("Koi matching entry nahi mili.")
    print("=" * 60)
    return {}


_subgraph = StateGraph(ChatState)
_subgraph.add_node("date_extract", correction_date_extract_node)
_subgraph.add_node("date_ask", correction_date_ask_node)
_subgraph.add_node("category_ask", correction_category_ask_node)
_subgraph.add_node("search", correction_search_node)
_subgraph.add_node("range_ask", correction_range_ask_node)
_subgraph.add_node("report_show", correction_report_show_node)
_subgraph.add_node("select_ask", correction_select_ask_node)
_subgraph.add_node("placeholder", correction_placeholder_node)
_subgraph.add_node("confirm_ask", correction_confirm_ask_node)
_subgraph.add_node("action_ask", correction_action_ask_node)
_subgraph.add_node("statement_ask", correction_statement_ask_node)
_subgraph.add_node("execute_delete", correction_execute_delete_node)
_subgraph.add_node("statement_prepare", correction_statement_prepare_node)
_subgraph.add_node("statement_person_hitl", person_role_hitl_node)
_subgraph.add_node("statement_material_movement", material_movement_subgraph)
_subgraph.add_node("statement_standalone", standalone_transaction_node)
_subgraph.add_node("statement_tool_decision", tool_decision_node, defer=True)
_subgraph.add_node("statement_tool_argument_extraction", tool_argument_extraction_node)
_subgraph.add_node("statement_tool_argument_hitl", tool_argument_hitl_node)
_subgraph.add_node("statement_tool_argument_update", tool_argument_update_node)
_subgraph.add_node("statement_final_confirm", final_confirmation_node)
_subgraph.add_node("statement_execute", correction_statement_execute_node)

_subgraph.add_edge(START, "date_extract")
_subgraph.add_conditional_edges(
    "date_extract", _after_date,
    {"ask": "date_ask", "category": "category_ask", "search": "search", "end": "placeholder"},
)
_subgraph.add_conditional_edges(
    "date_ask", _after_date,
    {"ask": "date_ask", "category": "category_ask", "search": "search", "end": "placeholder"},
)
_subgraph.add_conditional_edges(
    "category_ask", _after_category,
    {"search": "search", "end": "placeholder"},
)
_subgraph.add_conditional_edges(
    "search", _after_search,
    {"select": "select_ask", "range": "range_ask", "end": "placeholder"},
)
_subgraph.add_conditional_edges(
    "range_ask", _after_range,
    {"report": "report_show", "end": "placeholder"},
)
_subgraph.add_edge("report_show", "placeholder")
_subgraph.add_conditional_edges(
    "select_ask", _after_select,
    {"confirm": "confirm_ask", "end": "placeholder"},
)
_subgraph.add_conditional_edges(
    "confirm_ask", _after_confirm,
    {"action": "action_ask", "end": "placeholder"},
)
_subgraph.add_conditional_edges(
    "action_ask", _after_action,
    {"execute_delete": "execute_delete", "statement": "statement_ask", "end": "placeholder"},
)
_subgraph.add_edge("execute_delete", "placeholder")
_subgraph.add_conditional_edges(
    "statement_ask", _after_statement_ask,
    {"placeholder": "placeholder", "prepare": "statement_prepare"},
)
_subgraph.add_conditional_edges("statement_prepare", _statement_dispatch)
_subgraph.add_edge("statement_person_hitl", "statement_tool_decision")
_subgraph.add_edge("statement_material_movement", "statement_tool_decision")
_subgraph.add_edge("statement_standalone", "statement_tool_decision")
_subgraph.add_edge("statement_tool_decision", "statement_tool_argument_extraction")
_subgraph.add_conditional_edges(
    "statement_tool_argument_extraction", _after_statement_tool_argument_extraction,
    {"tool_argument_hitl": "statement_tool_argument_hitl", "final_confirm": "statement_final_confirm"},
)
_subgraph.add_edge("statement_tool_argument_hitl", "statement_tool_argument_update")
_subgraph.add_edge("statement_tool_argument_update", "statement_final_confirm")
_subgraph.add_edge("statement_final_confirm", "statement_execute")
_subgraph.add_edge("statement_execute", "placeholder")
_subgraph.add_edge("placeholder", END)

# Bina apne checkpointer ke compile: parent ka checkpointer inherit hota hai.
correction_subgraph = _subgraph.compile()






