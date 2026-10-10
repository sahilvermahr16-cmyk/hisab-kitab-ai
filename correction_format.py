# correction_format.py
# Report aur match list ka Tally-jaisa table. Reporting phase mein yahi file upgrade hogi.
from datetime import date

HEADERS = {
    "employee": ("Diya", "Kaam"),
    "customer": ("Bikri", "Mila"),
    "supplier": ("Diya", "Maal"),
    "purchase": ("Diya", "Deal"),
    "expense": ("Kharcha", "Diya"),
    "opening": ("Lena", "Dena"),
    "family": ("Diya", "Liya"),
}
DEFAULT_HEADERS = ("Debit", "Credit")

# (kis column ka farak, kis side mein dikhana, label)
BALANCE = {
    "employee": ("credit_minus_debit", "credit", "unka banta hai"),
    "supplier": ("credit_minus_debit", "credit", "unka banta hai"),
    "purchase": ("credit_minus_debit", "credit", "unka banta hai"),
    "customer": ("debit_minus_credit", "debit", "unse lena hai"),
}

TITLES = {
    "employee": "EMPLOYEE", "customer": "CUSTOMER", "supplier": "SUPPLIER",
    "purchase": "PURCHASE", "expense": "EXPENSE", "material_movement": "MATERIAL / STOCK",
    "opening": "OPENING BALANCE",
    "family": "FAMILY KHARCHA",
}


def _fmt_date(iso):
    if not iso:
        return "-"
    try:
        return date.fromisoformat(iso).strftime("%d-%b-%y")
    except ValueError:
        return iso


def _money(v):
    return "-" if v in (None, 0, 0.0) else f"{v:,.2f}"


def _join(*parts):
    return " ".join(str(p) for p in parts if p not in (None, ""))


def to_view(row: dict) -> dict:
    """audit_log row (dict) -> user ko dikhne wali row. Tool ka naam user ko nahi dikhta."""
    tool = row["tool_name"]
    a = row.get("arguments") or {}
    amount = a.get("amount")
    typ, debit, credit = "-", None, None
    info = []

    if tool == "record_employee_transaction":
        if a.get("transaction_type") == "work":
            typ, credit = "Kaam", amount
        else:
            typ, debit = "Payment", amount
    elif tool == "record_attendance":
        typ = "Attendance"
        info.append(f"Att: {a.get('attendance', '-')}, Drive: {a.get('driving', '-')}")
    elif tool == "record_sale_transaction":
        typ, debit = "Bikri", amount
        info.append(_join(a.get("item_name"), a.get("quantity"), a.get("unit")))
    elif tool == "record_sale_payment":
        typ, credit = "Payment", amount
    elif tool == "record_supplier_transaction":
        typ, credit = "Maal aaya", amount
        info.append(_join(a.get("item_name"), a.get("quantity"), a.get("unit")))
    elif tool == "record_supplier_payment":
        typ, debit = "Payment", amount
    elif tool == "record_purchase":
        typ, credit = "Deal", a.get("total_amount")
        info.append(a.get("description") or "")
    elif tool == "record_purchase_payment":
        typ, debit = "Payment", amount
    elif tool == "record_expense":
        typ, debit = "Kharcha", amount
        info.append(a.get("description") or "")
    elif tool == "record_expense_payment":
        typ, credit = "Payment", amount
        info.append(a.get("description") or "")
    elif tool == "record_material_movement":
        typ = "Maal gaya"
        info.append(
            f"{_join(a.get('item_name'), a.get('quantity'), a.get('unit'))}: "
            f"{a.get('source_name', '')} -> {a.get('destination_name', '')}"
        )
    elif tool == "record_work_log":
        typ = "Kaam log"
        info.append(f"{a.get('description', '')} ({a.get('labour_count') or '-'} labour)")
    elif tool == "record_opening_balance":
        typ = "Purana baaki"
        if a.get("direction") == "dena":
            credit = amount
        else:
            debit = amount
        info.append(f"{a.get('party_type', '')} — {a.get('direction', '')}")
    elif tool == "record_family_transaction":
        if a.get("transaction_type") in ("jama", "liya"):
            typ, credit = "Galle mein aaya", amount
        else:
            typ, debit = "Ghar ko diya", amount
        info.append(a.get("purpose") or "")
    elif tool == "record_adjustment":
        typ = "Stock adj."
        info.append(_join(a.get("item_name"), a.get("quantity_change"), a.get("unit")))

    note = (a.get("note") or "").strip()
    text = "; ".join(x.strip() for x in info + [note] if x and x.strip()) or "-"

    return {
        "date": _fmt_date(row.get("entry_date")),
        "party": row.get("person_name") or a.get("description") or ("Cash" if tool == "record_opening_balance" else "-"),
        "type": typ,
        "entry": row.get("voucher") or f"#{row['id']}",
        "debit": debit or None,
        "credit": credit or None,
        "note": text,
    }


def _line(cells, cols):
    parts = []
    for text, (_, w, al) in zip(cells, cols):
        text = str(text)
        if len(text) > w:
            text = text[: w - 2] + ".."
        parts.append(f"{text:{al}{w}}")
    return "  ".join(parts)


def render_table(views, category, with_no=False, show_total=True, heading=""):
    dh, ch = HEADERS.get(category, DEFAULT_HEADERS)
    cols = []
    if with_no:
        cols.append(("No.", 4, "<"))
    cols += [
        ("Date", 9, "<"), ("Particulars", 14, "<"), ("Type", 11, "<"), ("Entry", 7, "<"),
        (f"Debit ({dh})", 16, ">"), (f"Credit ({ch})", 16, ">"), ("Note", 30, "<"),
    ]
    width = sum(w for _, w, _ in cols) + 2 * (len(cols) - 1)
    out = ["=" * width]
    if heading:
        out += [heading, "=" * width]
    out += [_line([c[0] for c in cols], cols), "-" * width]

    for v in views:
        cells = [v["no"]] if with_no else []
        cells += [v["date"], v["party"], v["type"], v["entry"],
                  _money(v["debit"]), _money(v["credit"]), v["note"]]
        out.append(_line(cells, cols))
    out.append("-" * width)

    if show_total and views:
        prefix = [""] if with_no else []
        d = sum(v["debit"] or 0 for v in views)
        c = sum(v["credit"] or 0 for v in views)
        out.append(_line(prefix + ["", "Total", "", "", _money(d), _money(c), ""], cols))

        parties = {v["party"] for v in views}
        if category in BALANCE and len(parties) == 1:
            mode, side, who = BALANCE[category]
            bal = (c - d) if mode == "credit_minus_debit" else (d - c)
            debit_cell = f"{bal:,.2f}" if side == "debit" else ""
            credit_cell = f"{bal:,.2f}" if side == "credit" else ""
            out.append(_line(
                prefix + ["", "Baaki", "", "", debit_cell, credit_cell, f"is period ka, {who}"], cols
            ))
    out.append("=" * width)
    return "\n".join(out)













    