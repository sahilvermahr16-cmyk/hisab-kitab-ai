# reports/builders.py
"""
Report ka poora DATA banata hai — language-neutral dicts.
Koi LLM nahi, koi formatting nahi: sirf numbers, dates aur DB ke raw text.
render.py (Step 4) inhi dicts ko PDF mein badlega, teen bhasha mein.

Sign convention:  balance > 0 → LENA,  balance < 0 → DENA.

Har public builder ka signature:  build_xxx(db, start, end, ...) → dict
"""
from collections import OrderedDict, defaultdict
from datetime import timedelta

from reports import queries as Q
from reports import ledgers as L


def _n(x):
    return float(x) if x is not None else 0.0


def _uniq(seq):
    out = []
    for s in seq:
        if s and s not in out:
            out.append(s)
    return out


def _next_day(d):
    return d + timedelta(days=1)


# =====================================================================
#                              SUPPLIER
# =====================================================================
def _supplier_txn_row(t, sup):
    return dict(
        id=t.id, date=t.transaction_date, bill_id=t.bill_id,
        supplier_id=t.supplier_id, supplier=sup.name if sup else None,
        item=t.item_name, qty=t.quantity, unit=t.unit, rate=t.rate, amount=_n(t.amount),
        driver=t.driver_name, destination=t.destination_location,
        direct_customer_id=t.customer_id, note=t.note,
    )


def _supplier_pay_row(p, sup):
    return dict(
        id=p.id, date=p.payment_date, bill_id=p.bill_id,
        supplier_id=p.supplier_id, supplier=sup.name if sup else None,
        amount=_n(p.amount), mode="cash", note=p.note,
    )


def build_supplier_ledger(db, supplier_id, start, end):
    sup = Q.suppliers(db).get(supplier_id)
    opening = L.supplier_balance_before(db, supplier_id, start)

    events = []
    for o in Q.opening_balances(db, "supplier", supplier_id, start, end):
        events.append((o.as_of_date, 0, dict(vtype="opening", date=o.as_of_date, signed=Q.opening_signed(o),
                                             debit=0.0, credit=0.0, note=o.note)))
    for t in Q.supplier_transactions(db, start, end, supplier_id):
        r = _supplier_txn_row(t, sup)
        r.update(vtype="maal_in", debit=0.0, credit=r["amount"], signed=-r["amount"])
        events.append((t.transaction_date, 1, r))
    for p in Q.supplier_payments(db, start, end, supplier_id):
        r = _supplier_pay_row(p, sup)
        r.update(vtype="payment_out", debit=r["amount"], credit=0.0, signed=r["amount"])
        events.append((p.payment_date, 2, r))
    events.sort(key=lambda e: (e[0], e[1], e[2].get("id", 0)))

    bal, rows, dr, cr = opening, [], 0.0, 0.0
    for _, _, r in events:
        bal += r["signed"]
        if r["vtype"] == "opening":       # opening entry beech mein aayi
            r["debit"] = max(r["signed"], 0)
            r["credit"] = max(-r["signed"], 0)
        dr += r["debit"]; cr += r["credit"]
        r["balance"] = bal
        rows.append(r)

    return dict(
        kind="supplier_ledger", start=start, end=end,
        party=dict(id=supplier_id, name=sup.name if sup else None, type=sup.supplier_type if sup else None,
                   phone=sup.phone if sup else None, address=sup.address if sup else None),
        opening=opening, rows=rows, total_debit=dr, total_credit=cr, closing=bal,
        has_history=_has_history(db, "supplier", supplier_id, end),
    )


# =====================================================================
#                              CUSTOMER
# =====================================================================
def _sale_row(t, cus):
    return dict(
        id=t.id, date=t.sale_date, bill_id=t.bill_id,
        customer_id=t.customer_id, customer=cus.name if cus else None,
        item=t.item_name, qty=t.quantity, unit=t.unit, rate=t.rate, amount=_n(t.amount),
        amount_missing=t.amount is None,
        source=t.source, destination=t.destination_name, driver=t.driver_name, note=t.note,
    )


def _sale_pay_row(p, cus):
    return dict(
        id=p.id, date=p.payment_date, bill_id=p.bill_id,
        customer_id=p.customer_id, customer=cus.name if cus else None,
        amount=_n(p.amount), mode="cash", note=p.note,
    )


def build_customer_ledger(db, customer_id, start, end):
    cus = Q.customers(db).get(customer_id)
    opening = L.customer_balance_before(db, customer_id, start)

    events = []
    for o in Q.opening_balances(db, "customer", customer_id, start, end):
        events.append((o.as_of_date, 0, dict(vtype="opening", date=o.as_of_date, signed=Q.opening_signed(o),
                                             debit=0.0, credit=0.0, note=o.note)))
    for t in Q.sales_transactions(db, start, end, customer_id):
        r = _sale_row(t, cus)
        r.update(vtype="sale", debit=r["amount"], credit=0.0, signed=r["amount"])
        events.append((t.sale_date, 1, r))
    for p in Q.sales_payments(db, start, end, customer_id):
        r = _sale_pay_row(p, cus)
        r.update(vtype="payment_in", debit=0.0, credit=r["amount"], signed=-r["amount"])
        events.append((p.payment_date, 2, r))
    events.sort(key=lambda e: (e[0], e[1], e[2].get("id", 0)))

    bal, rows, dr, cr = opening, [], 0.0, 0.0
    for _, _, r in events:
        bal += r["signed"]
        if r["vtype"] == "opening":
            r["debit"] = max(r["signed"], 0)
            r["credit"] = max(-r["signed"], 0)
        dr += r["debit"]; cr += r["credit"]
        r["balance"] = bal
        rows.append(r)

    return dict(
        kind="customer_ledger", start=start, end=end,
        party=dict(id=customer_id, name=cus.name if cus else None, phone=cus.phone if cus else None,
                   address=cus.address if cus else None),
        opening=opening, rows=rows, total_debit=dr, total_credit=cr, closing=bal,
        has_history=_has_history(db, "customer", customer_id, end),
    )


# =====================================================================
#                              EMPLOYEE
# =====================================================================
def _employee_days(txns, emps):
    """
    Ek din + ek employee ki saari entries → ek row.
    kaam (work)  = humein dena hua   → credit
    liya (payment/advance) = humne diya → debit
    """
    days = OrderedDict()
    for t in txns:
        days.setdefault((t.transaction_date, t.employee_id), []).append(t)

    rows = []
    for (d, eid), items in days.items():
        e = emps.get(eid)
        work = [t for t in items if t.transaction_type == "work"]
        paid = [t for t in items if t.transaction_type in ("payment", "advance")]
        rows.append(dict(
            date=d, employee_id=eid, employee=e.name if e else None, role=e.role if e else None,
            work_amount=sum(_n(t.amount) for t in work),
            work_breakdown=[_n(t.amount) for t in work],
            work_notes=_uniq([t.note for t in work]),
            paid_amount=sum(_n(t.amount) for t in paid),
            paid_breakdown=[_n(t.amount) for t in paid],
            paid_types=_uniq([t.transaction_type for t in paid]),
            modes=_uniq([t.payment_method for t in paid]),
            providers=_uniq([t.payment_provider for t in paid]),
            paid_notes=_uniq([t.note for t in paid]),
            ids=[t.id for t in items],
        ))
    return rows


def build_employee_ledger(db, employee_id, start, end):
    emps = Q.employees(db)
    e = emps.get(employee_id)
    opening = L.employee_balance_before(db, employee_id, start)

    obs = Q.opening_balances(db, "employee", employee_id, start, end)
    days = _employee_days(Q.employee_transactions(db, start, end, employee_id), emps)

    events = [(o.as_of_date, 0, dict(vtype="opening", date=o.as_of_date, signed=Q.opening_signed(o),
                                     note=o.note)) for o in obs]
    events += [(r["date"], 1, dict(r, vtype="day", signed=r["paid_amount"] - r["work_amount"])) for r in days]
    events.sort(key=lambda x: (x[0], x[1]))

    bal, rows, tw, tp = opening, [], 0.0, 0.0
    for _, _, r in events:
        bal += r["signed"]
        if r["vtype"] == "day":
            tw += r["work_amount"]; tp += r["paid_amount"]
        r["balance"] = bal
        rows.append(r)

    return dict(
        kind="employee_ledger", start=start, end=end,
        party=dict(id=employee_id, name=e.name if e else None, role=e.role if e else None,
                   phone=e.phone if e else None, address=e.address if e else None),
        opening=opening, rows=rows, total_work=tw, total_paid=tp, closing=bal,
        payment_days=sum(1 for r in days if r["paid_amount"]),
        has_history=_has_history(db, "employee", employee_id, end),
    )


# =====================================================================
#                          PURCHASE / EXPENSE
# =====================================================================
def _pay_detail(payments):
    return [dict(date=p.payment_date, amount=_n(p.amount), note=p.note) for p in payments]


def build_purchase_register(db, start, end):
    purs = Q.purchases(db, start, end)
    ids = [p.id for p in purs]
    pays_upto_end = Q.purchase_payments(db, end=end, purchase_ids=ids)
    by_pur = defaultdict(list)
    for p in pays_upto_end:
        by_pur[p.purchase_id].append(p)

    rows = []
    for p in purs:
        paid = sum(_n(x.amount) for x in by_pur[p.id])
        rows.append(dict(
            id=p.id, date=p.purchase_date, seller=p.seller_name, phone=p.seller_phone,
            description=p.description, location=p.location, total=_n(p.total_amount),
            total_missing=p.total_amount is None,
            paid=paid, baaki=_n(p.total_amount) - paid, payments=_pay_detail(by_pur[p.id]), note=p.note,
        ))

    # Is period mein PURANI kharid (period se pehle wali) ki payments
    in_range = Q.purchase_payments(db, start, end)
    old = [p for p in in_range if p.purchase_id not in set(ids)]
    all_pur = {p.id: p for p in Q.purchases(db)}
    old_rows = [dict(id=p.id, date=p.payment_date, amount=_n(p.amount), note=p.note,
                     purchase_id=p.purchase_id,
                     seller=all_pur[p.purchase_id].seller_name if p.purchase_id in all_pur else None,
                     description=all_pur[p.purchase_id].description if p.purchase_id in all_pur else None)
                for p in old]

    return dict(kind="purchase_register", start=start, end=end, rows=rows, old_payments=old_rows,
                total=sum(r["total"] for r in rows), paid=sum(r["paid"] for r in rows),
                baaki=sum(r["baaki"] for r in rows),
                cash_out_in_period=sum(_n(p.amount) for p in in_range))


def build_expense_register(db, start, end):
    exps = Q.expenses(db, start, end)
    ids = [e.id for e in exps]
    by_exp = defaultdict(list)
    for p in Q.expense_payments(db, end=end, expense_ids=ids):
        by_exp[p.expense_id].append(p)

    rows, by_cat = [], OrderedDict()
    for e in exps:
        paid = sum(_n(x.amount) for x in by_exp[e.id])
        rows.append(dict(id=e.id, date=e.expense_date, category=e.category, description=e.description,
                         total=_n(e.amount), paid=paid, baaki=_n(e.amount) - paid,
                         payments=_pay_detail(by_exp[e.id]), note=e.note))
        by_cat[e.category] = by_cat.get(e.category, 0.0) + _n(e.amount)

    in_range = Q.expense_payments(db, start, end)
    all_exp = {e.id: e for e in Q.expenses(db)}
    other = [dict(id=p.id, date=p.payment_date, amount=_n(p.amount), note=p.note, expense_id=p.expense_id,
                  category=all_exp[p.expense_id].category if p.expense_id in all_exp else None,
                  description=all_exp[p.expense_id].description if p.expense_id in all_exp else None)
             for p in in_range if p.expense_id not in set(ids)]

    total = sum(r["total"] for r in rows)
    return dict(kind="expense_register", start=start, end=end, rows=rows, other_payments=other,
                by_category=[dict(category=k, amount=v, share=(v / total if total else 0)) for k, v in by_cat.items()],
                total=total, paid=sum(r["paid"] for r in rows), baaki=sum(r["baaki"] for r in rows),
                cash_out_in_period=sum(_n(p.amount) for p in in_range))


# =====================================================================
#                          WORK LOG / MATERIAL
# =====================================================================
def build_work_log(db, start, end):
    grp = OrderedDict()
    for w in Q.work_logs(db, start, end):
        grp.setdefault((w.activity_date, w.location_type, w.location_name), []).append(w)
    rows = []
    for (d, lt, ln), items in grp.items():
        rows.append(dict(date=d, location_type=lt, location=ln, entries=len(items),
                         labour=sum((w.labour_count or 0) for w in items),
                         works=[dict(description=w.description, labour=w.labour_count) for w in items],
                         notes=_uniq([w.note for w in items])))
    return dict(kind="work_log", start=start, end=end, rows=rows)


def build_material_movement(db, start, end):
    rows = [dict(id=m.id, date=m.movement_date, item=m.item_name, qty=m.quantity, unit=m.unit,
                 source_type=m.source_type, source=m.source_name,
                 destination_type=m.destination_type, destination=m.destination_name,
                 movement_type=m.movement_type, reason=m.movement_reason, note=m.note)
            for m in Q.material_movements(db, start, end)]
    return dict(kind="material_movement", start=start, end=end, rows=rows)


# =====================================================================
#                     FAMILY KHARCHA (ghar ke log)
# =====================================================================
def _fam_out(t):
    """Family entry galle se BAHAR gayi? (kharcha; purana naam 'diya')"""
    return t.transaction_type in ("kharcha", "diya")


def build_family_report(db, start, end, member_id=None):
    """
    Family kharcha — lena-dena nahi, sirf kitna galle se ghar gaya (diya) aur kitna wapas aaya (liya).
    member_id None = poori family.
    """
    mems = Q.family_members(db)
    rows = []
    for t in Q.family_transactions(db, start, end, member_id):
        m = mems.get(t.member_id)
        amt = _n(t.amount)
        rows.append(dict(id=t.id, date=t.transaction_date, member_id=t.member_id, member=m.name if m else None,
                         relation=m.relation if m else None, type=t.transaction_type, purpose=t.purpose,
                         note=t.note, diya=amt if _fam_out(t) else 0.0,
                         liya=0.0 if _fam_out(t) else amt))
    summary = OrderedDict()
    for r in rows:
        x = summary.setdefault(r["member_id"], dict(id=r["member_id"], name=r["member"], relation=r["relation"],
                                                    diya=0.0, liya=0.0, count=0))
        x["diya"] += r["diya"]; x["liya"] += r["liya"]; x["count"] += 1
    summary = sorted(summary.values(), key=lambda x: -x["diya"])
    for x in summary:
        x["net"] = x["diya"] - x["liya"]
    months = OrderedDict()
    for r in rows:
        ym = L.ym_of(r["date"])
        mm = months.setdefault(ym, dict(ym=ym, diya=0.0, liya=0.0))
        mm["diya"] += r["diya"]; mm["liya"] += r["liya"]
    td, tl = sum(r["diya"] for r in rows), sum(r["liya"] for r in rows)
    member = mems.get(member_id) if member_id else None
    has_history = True
    if member_id:
        has_history = bool(Q.family_transactions(db, end=end, member_id=member_id))
    return dict(kind="family_report", start=start, end=end, member=member.name if member else None,
                member_id=member_id, rows=rows, summary=summary, months=list(months.values()),
                total_diya=td, total_liya=tl, net=td - tl, has_history=has_history, empty=not rows)


# =====================================================================
#                              CASH BOOK
# =====================================================================
def _cash_party(db, row, src, cache):
    t = row.source_table
    if src is None:
        return None
    if t == "employee_transactions":
        return cache["emp"].get(src.employee_id).name if src.employee_id in cache["emp"] else None
    if t == "sales_payments":
        return cache["cus"].get(src.customer_id).name if src.customer_id in cache["cus"] else None
    if t == "supplier_payments":
        return cache["sup"].get(src.supplier_id).name if src.supplier_id in cache["sup"] else None
    if t == "purchase_payments":
        p = cache["pur"].get(src.purchase_id)
        return p.seller_name if p else None
    if t == "expense_payments":
        e = cache["exp"].get(src.expense_id)
        return (e.description or e.category) if e else None
    if t == "family_transactions":
        m = cache["fam"].get(src.member_id)
        return m.name if m else None
    return None


def build_cash_book(db, start, end):
    cache = dict(emp=Q.employees(db), cus=Q.customers(db), sup=Q.suppliers(db),
                 pur={p.id: p for p in Q.purchases(db)}, exp={e.id: e for e in Q.expenses(db)},
                 fam=Q.family_members(db))
    opening = L.cash_balance_before(db, start)

    events = []
    for o in Q.opening_balances(db, "cash", 0, start, end):
        events.append((o.as_of_date, 0, 0, dict(date=o.as_of_date, category="opening_balance", party=None, mode=None,
                                               source_table="opening_balances", source_id=o.id, note=o.note,
                                               direction="in", amount=_n(o.amount))))
    for row, src in Q.cash_entries(db, start, end):
        mode = None
        if row.source_table == "employee_transactions" and src is not None:
            mode = src.payment_method
            if src.payment_provider:
                mode = f"{mode or ''} ({src.payment_provider})".strip()
        events.append((row.entry_date, 1 if row.direction == "in" else 2, row.id, dict(
            date=row.entry_date, category=row.category, party=_cash_party(db, row, src, cache), mode=mode or "cash",
            source_table=row.source_table, source_id=row.source_id, note=row.note,
            direction=row.direction, amount=_n(row.amount))))
    events.sort(key=lambda e: e[:3])

    bal, rows, tin, tout = opening, [], 0.0, 0.0
    for *_, r in events:
        if r["direction"] == "in":
            bal += r["amount"]; tin += r["amount"]
        else:
            bal -= r["amount"]; tout += r["amount"]
        r["balance"] = bal
        rows.append(r)
    return dict(kind="cash_book", start=start, end=end, opening=opening, rows=rows,
                total_in=tin, total_out=tout, closing=bal)


# =====================================================================
#                   HISAB HAI YA NAHI (empty-data checks)
# =====================================================================
def _has_history(db, ledger_type, ledger_id, upto):
    """Is party ka KABHI bhi (upto tak) koi hisab hai?"""
    if Q.opening_balances(db, ledger_type, ledger_id, end=upto):
        return True
    if ledger_type == "supplier":
        return bool(Q.supplier_transactions(db, end=upto, supplier_id=ledger_id)
                    or Q.supplier_payments(db, end=upto, supplier_id=ledger_id))
    if ledger_type == "customer":
        return bool(Q.sales_transactions(db, end=upto, customer_id=ledger_id)
                    or Q.sales_payments(db, end=upto, customer_id=ledger_id))
    if ledger_type == "employee":
        return bool(Q.employee_transactions(db, end=upto, employee_id=ledger_id))
    if ledger_type == "family":
        return bool(Q.family_transactions(db, end=upto, member_id=ledger_id or None))
    return False


def last_entry_date(db, ledger_type, ledger_id):
    """Party ki aakhri entry kab thi — 'is duration mein hisab nahi' message ke liye."""
    dates = [o.as_of_date for o in Q.opening_balances(db, ledger_type, ledger_id)]
    if ledger_type == "supplier":
        dates += [t.transaction_date for t in Q.supplier_transactions(db, supplier_id=ledger_id)]
        dates += [p.payment_date for p in Q.supplier_payments(db, supplier_id=ledger_id)]
    elif ledger_type == "customer":
        dates += [t.sale_date for t in Q.sales_transactions(db, customer_id=ledger_id)]
        dates += [p.payment_date for p in Q.sales_payments(db, customer_id=ledger_id)]
    elif ledger_type == "employee":
        dates += [t.transaction_date for t in Q.employee_transactions(db, employee_id=ledger_id)]
    elif ledger_type == "family":
        dates += [t.transaction_date for t in Q.family_transactions(db, member_id=ledger_id or None)]
    return max(dates) if dates else None


def report_is_empty(report):
    k = report["kind"]
    if k in ("supplier_ledger", "customer_ledger", "employee_ledger"):
        return not report["rows"]
    if k == "cash_book":
        return not report["rows"]
    if k == "purchase_register":
        return not report["rows"] and not report["old_payments"]
    if k == "expense_register":
        return not report["rows"] and not report["other_payments"]
    if k in ("work_log", "material_movement", "family_report"):
        return not report["rows"]
    if k in ("overall", "overall_period") or k.endswith("_period"):
        return report["empty"]
    return False


# =====================================================================
#                         OVERALL BUSINESS REPORT
# =====================================================================
def _party_summary(db, ledger_type, masters, start, end, period_fn):
    """Har party ki ek row: opening, is period ka (+)/(−), closing."""
    rows = []
    for pid, m in masters.items():
        opening = L.balance_before(db, ledger_type, pid, start)
        plus, minus, ob_in_period = period_fn(pid)
        closing = opening + ob_in_period + plus - minus
        if abs(opening) < 0.005 and abs(plus) < 0.005 and abs(minus) < 0.005 and abs(closing) < 0.005:
            continue
        rows.append(dict(id=pid, name=m.name, opening=opening, plus=plus, minus=minus,
                         opening_in_period=ob_in_period, closing=closing, master=m))
    return rows


def build_overall(db, start, end):
    sups, cuss, emps = Q.suppliers(db), Q.customers(db), Q.employees(db)

    # ---------- A. Supplier
    s_txn = [_supplier_txn_row(t, sups.get(t.supplier_id)) for t in Q.supplier_transactions(db, start, end)]
    s_pay = [_supplier_pay_row(p, sups.get(p.supplier_id)) for p in Q.supplier_payments(db, start, end)]

    def sup_period(sid):
        ob = sum(Q.opening_signed(o) for o in Q.opening_balances(db, "supplier", sid, start, end))
        maal = sum(r["amount"] for r in s_txn if r["supplier_id"] == sid)
        paid = sum(r["amount"] for r in s_pay if r["supplier_id"] == sid)
        return paid, maal, ob            # (+) paid  (−) maal   [sign: lena +]
    sup_rows = _party_summary(db, "supplier", sups, start, end, sup_period)
    for r in sup_rows:
        r["maal"], r["paid"] = r["minus"], r["plus"]
        r["type"], r["phone"] = r["master"].supplier_type, r["master"].phone
        del r["master"]

    # ---------- B. Employee
    e_days = _employee_days(Q.employee_transactions(db, start, end), emps)

    def emp_period(eid):
        ob = sum(Q.opening_signed(o) for o in Q.opening_balances(db, "employee", eid, start, end))
        paid = sum(r["paid_amount"] for r in e_days if r["employee_id"] == eid)
        work = sum(r["work_amount"] for r in e_days if r["employee_id"] == eid)
        return paid, work, ob
    emp_rows = _party_summary(db, "employee", emps, start, end, emp_period)
    for r in emp_rows:
        r["paid"], r["work"] = r["plus"], r["minus"]
        r["role"], r["phone"] = r["master"].role, r["master"].phone
        r["payment_days"] = sum(1 for d in e_days if d["employee_id"] == r["id"] and d["paid_amount"])
        del r["master"]

    # ---------- C / D
    purchase = build_purchase_register(db, start, end)
    expense = build_expense_register(db, start, end)

    # ---------- E. Customer sale
    c_txn = [_sale_row(t, cuss.get(t.customer_id)) for t in Q.sales_transactions(db, start, end)]
    c_pay = [_sale_pay_row(p, cuss.get(p.customer_id)) for p in Q.sales_payments(db, start, end)]

    def cus_period(cid):
        ob = sum(Q.opening_signed(o) for o in Q.opening_balances(db, "customer", cid, start, end))
        sale = sum(r["amount"] for r in c_txn if r["customer_id"] == cid)
        rec = sum(r["amount"] for r in c_pay if r["customer_id"] == cid)
        return sale, rec, ob
    cus_rows = _party_summary(db, "customer", cuss, start, end, cus_period)
    for r in cus_rows:
        r["sale"], r["received"] = r["plus"], r["minus"]
        r["phone"], r["address"] = r["master"].phone, r["master"].address
        del r["master"]

    # ---------- F. Family kharcha
    family = build_family_report(db, start, end)

    # ---------- G. Overall balance
    cash = build_cash_book(db, start, end)
    emp_paid = sum(r["paid_amount"] for r in e_days)
    emp_work = sum(r["work_amount"] for r in e_days)
    heads = dict(
        supplier=dict(bill=sum(r["amount"] for r in s_txn), out=sum(r["amount"] for r in s_pay),
                      closing=sum(r["closing"] for r in sup_rows)),
        employee=dict(bill=emp_work, out=emp_paid, closing=sum(r["closing"] for r in emp_rows)),
        purchase=dict(bill=purchase["total"], out=purchase["cash_out_in_period"], closing=-purchase["baaki"]),
        expense=dict(bill=expense["total"], out=expense["cash_out_in_period"], closing=-expense["baaki"]),
        sale=dict(bill=sum(r["amount"] for r in c_txn), inn=sum(r["amount"] for r in c_pay),
                  closing=sum(r["closing"] for r in cus_rows)),
        family=dict(out=family["total_diya"], inn=family["total_liya"]),
    )

    final = build_final_hisab(db, end, cash_closing=cash["closing"])

    empty = not any([s_txn, s_pay, e_days, purchase["rows"], purchase["old_payments"], expense["rows"],
                     expense["other_payments"], c_txn, c_pay, family["rows"], cash["rows"]])

    return dict(
        kind="overall", start=start, end=end, empty=empty,
        supplier=dict(transactions=s_txn, payments=s_pay, summary=sup_rows),
        employee=dict(days=e_days, summary=emp_rows),
        purchase=purchase, expense=expense,
        sale=dict(transactions=c_txn, payments=c_pay, summary=cus_rows),
        family=family,
        heads=heads,
        cash=dict(opening=cash["opening"], total_in=cash["total_in"], total_out=cash["total_out"],
                  closing=cash["closing"]),
        cash_book=cash,
        final=final,
    )


# =====================================================================
#              FINAL HISAB — kisko dena hai, kisse lena hai
# =====================================================================
def build_final_hisab(db, as_of, cash_closing=None):
    """
    'as_of' tareekh tak ka poora lena-dena (sirf is period ka nahi —
    shuru se aaj tak ka baaki). Har item: party, kis cheez ka, amount.
    """
    after = _next_day(as_of)
    give, take = [], []

    for sid, s in Q.suppliers(db).items():
        b = L.supplier_balance_before(db, sid, after)
        if b < -0.005:
            give.append(dict(party=s.name, ledger="supplier", reason="supplier_balance", amount=-b))
        elif b > 0.005:
            take.append(dict(party=s.name, ledger="supplier", reason="supplier_advance", amount=b))

    for eid, e in Q.employees(db).items():
        b = L.employee_balance_before(db, eid, after)
        if b < -0.005:
            give.append(dict(party=e.name, ledger="employee", reason="employee_wages_due", amount=-b))
        elif b > 0.005:
            take.append(dict(party=e.name, ledger="employee", reason="employee_advance", amount=b))

    purs = Q.purchases(db, end=as_of)
    paid = defaultdict(float)
    for p in Q.purchase_payments(db, end=as_of, purchase_ids=[x.id for x in purs]):
        paid[p.purchase_id] += _n(p.amount)
    for p in purs:
        due = _n(p.total_amount) - paid[p.id]
        if due > 0.005:
            give.append(dict(party=p.seller_name, ledger="purchase", reason="purchase_balance",
                             detail=p.description, amount=due))

    exps = Q.expenses(db, end=as_of)
    epaid = defaultdict(float)
    for p in Q.expense_payments(db, end=as_of, expense_ids=[x.id for x in exps]):
        epaid[p.expense_id] += _n(p.amount)
    for e in exps:
        due = _n(e.amount) - epaid[e.id]
        if due > 0.005:
            give.append(dict(party=e.category, ledger="expense", reason="expense_balance",
                             detail=e.description, amount=due))

    for cid, c in Q.customers(db).items():
        b = L.customer_balance_before(db, cid, after)
        if b > 0.005:
            take.append(dict(party=c.name, ledger="customer", reason="customer_udhaar", amount=b))
        elif b < -0.005:
            give.append(dict(party=c.name, ledger="customer", reason="customer_advance", amount=-b))

    if cash_closing is None:
        cash_closing = L.cash_balance_before(db, after)

    total_give = sum(x["amount"] for x in give)
    total_take = sum(x["amount"] for x in take)
    return dict(as_of=as_of, give=give, take=take, total_give=total_give, total_take=total_take,
                cash=cash_closing, net=total_take - total_give,
                after_settlement=cash_closing + total_take - total_give)


# =====================================================================
#        LAMBI DURATION (> 1 mahina): mahine-wise summary + aakhri mahina detail
# =====================================================================
DETAIL_MAX_DAYS = 31


def _segments(start, end):
    """[start, end] ko calendar-mahinon mein todo: [(ym, seg_start, seg_end, full_month)]."""
    from reports import closing as C
    out = []
    for ym in C.months_between(start, end):
        ms, me = C.month_bounds(ym)
        s, e = max(ms, start), min(me, end)
        out.append((ym, s, e, s == ms and e == me))
    return out


def _segment_effects(db, ym, s, e, full):
    """
    {(ledger_type, ledger_id): (debit, credit)} ek segment ke liye.
    Poora + closed mahina → monthly_closing se (tez); warna live.
    """
    from models import MonthClose, MonthlyClosing
    if full:
        mc = db.query(MonthClose).filter(MonthClose.business_id == Q.BUSINESS_ID, MonthClose.year_month == ym).first()
        if mc is not None and mc.status == "closed":
            return {(r.ledger_type, r.ledger_id): (r.debit_total, r.credit_total)
                    for r in db.query(MonthlyClosing).filter(MonthlyClosing.business_id == Q.BUSINESS_ID,
                                                             MonthlyClosing.year_month == ym).all()}
    return {k: (v[0], v[1]) for k, v in L.all_effects(db, s, e).items()}


def _month_rows(db, segs, cash_open):
    """Har mahine (segment) ki ek summary row + party-wise totals."""
    months, cash = [], cash_open
    party_tot = defaultdict(lambda: [0.0, 0.0])
    for ym, s, e, full in segs:
        eff = _segment_effects(db, ym, s, e, full)
        agg = defaultdict(lambda: [0.0, 0.0])
        for (lt, lid), (d, c) in eff.items():
            agg[lt][0] += d
            agg[lt][1] += c
            if lt in L.PARTY_LEDGERS:
                party_tot[(lt, lid)][0] += d
                party_tot[(lt, lid)][1] += c
        fam = Q.family_transactions(db, s, e)
        c_open = cash
        cash = cash + agg["cash"][0] - agg["cash"][1]
        months.append(dict(
            ym=ym, start=s, end=e, partial=not full,
            supplier_maal=agg["supplier"][1], supplier_paid=agg["supplier"][0],
            employee_work=agg["employee"][1], employee_paid=agg["employee"][0],
            purchase_bill=agg["purchase"][1], purchase_paid=agg["purchase"][0],
            expense_bill=agg["expense"][1], expense_paid=agg["expense"][0],
            sale=agg["customer"][0], received=agg["customer"][1],
            family_out=sum(_n(t.amount) for t in fam if _fam_out(t)),
            family_in=sum(_n(t.amount) for t in fam if not _fam_out(t)),
            cash_open=c_open, cash_in=agg["cash"][0], cash_out=agg["cash"][1], cash_close=cash,
        ))
    return months, party_tot, cash


def build_overall_period(db, start, end):
    """Overall report > 1 mahina: har mahine ki ek row + party-wise summary + aakhri mahine ki detail."""
    segs = _segments(start, end)
    cash_open = L.cash_balance_before(db, start)
    months, party_tot, cash = _month_rows(db, segs, cash_open)

    masters = dict(supplier=Q.suppliers(db), customer=Q.customers(db), employee=Q.employees(db))
    parties = {lt: [] for lt in L.PARTY_LEDGERS}
    for lt in L.PARTY_LEDGERS:
        for pid, m in masters[lt].items():
            opening = L.balance_before(db, lt, pid, start)
            d, c = party_tot.get((lt, pid), (0.0, 0.0))
            closing = opening + d - c
            if max(abs(opening), abs(d), abs(c), abs(closing)) < 0.005:
                continue
            parties[lt].append(dict(id=pid, name=m.name, opening=opening, debit=d, credit=c, closing=closing))

    last_ym, ls, le, _ = segs[-1]
    return dict(
        kind="overall_period", start=start, end=end, months=months,
        parties=parties,
        cash=dict(opening=cash_open, closing=cash,
                  total_in=sum(m["cash_in"] for m in months), total_out=sum(m["cash_out"] for m in months)),
        last_month_detail=build_overall(db, ls, le),
        final=build_final_hisab(db, end, cash_closing=cash),
        empty=all(not any(abs(v) > 0.005 for k, v in m.items() if k not in ("ym", "start", "end", "partial",
                                                                          "cash_open", "cash_close"))
                  for m in months),
    )


_PARTY_DETAIL = dict(supplier=build_supplier_ledger, customer=build_customer_ledger, employee=build_employee_ledger)


def build_party_period(db, ledger_type, ledger_id, start, end):
    """Person ledger > 1 mahina: har mahine ki ek row (opening, debit, credit, closing) + aakhri mahine ki detail."""
    segs = _segments(start, end)
    bal = L.balance_before(db, ledger_type, ledger_id, start)
    opening = bal
    months = []
    for ym, s, e, full in segs:
        d, c = _segment_effects(db, ym, s, e, full).get((ledger_type, ledger_id), (0.0, 0.0))
        months.append(dict(ym=ym, start=s, end=e, partial=not full, opening=bal, debit=d, credit=c,
                           closing=bal + d - c))
        bal = bal + d - c
    _, ls, le, _ = segs[-1]
    detail = _PARTY_DETAIL[ledger_type](db, ledger_id, ls, le)
    return dict(kind=f"{ledger_type}_period", start=start, end=end, party=detail["party"],
                opening=opening, closing=bal, months=months, last_month_detail=detail,
                total_debit=sum(m["debit"] for m in months), total_credit=sum(m["credit"] for m in months),
                has_history=detail["has_history"],
                empty=all(abs(m["debit"]) < 0.005 and abs(m["credit"]) < 0.005 for m in months))


# =====================================================================
#                 EK HI ENTRY POINT — report_subgraph yahi bulayega
# =====================================================================
REGISTER_BUILDERS = dict(
    purchase=build_purchase_register, expense=build_expense_register, cash_flow=build_cash_book,
    work_log=build_work_log, material_movement=build_material_movement,
)


def build_report(db, report_type, start, end, ledger_id=None):
    """
    report_type: overall | supplier | customer | employee | family | purchase | expense
                 | cash_flow | work_log | material_movement
    1 mahina (≤31 din) → poori detail.  Usse lamba → mahine-wise summary + aakhri mahina detail
    (sirf overall aur person ledgers ke liye; registers hamesha detail — unme balance nahi hota).
    """
    from reports import closing as C
    C.ensure_closed_until(db)
    long = (end - start).days + 1 > DETAIL_MAX_DAYS
    if report_type == "overall":
        return build_overall_period(db, start, end) if long else build_overall(db, start, end)
    if report_type == "family":
        r = build_family_report(db, start, end, member_id=ledger_id or None)
        r["long"] = long          # family ki entries kam hoti hain — poori detail + mahine-wise total
        return r
    if report_type in _PARTY_DETAIL:
        if long:
            return build_party_period(db, report_type, ledger_id, start, end)
        return _PARTY_DETAIL[report_type](db, ledger_id, start, end)
    if report_type in REGISTER_BUILDERS:
        if long:
            # lambi duration: mahine-wise totals + sirf aakhri mahine ki detail
            ls = max(start, end.replace(day=1))
            r = REGISTER_BUILDERS[report_type](db, ls, end)
            months, _, _ = _month_rows(db, _segments(start, end), L.cash_balance_before(db, start))
            r["kind"] = f"{report_type}_period"
            r["start"] = start                      # header pe poora period
            r["requested_start"] = start
            r["months"] = months
            r["last_month_detail_from"] = ls
            r["empty"] = report_is_empty(REGISTER_BUILDERS[report_type](db, start, end))
            return r
        return REGISTER_BUILDERS[report_type](db, start, end)
    raise ValueError(f"unknown report_type {report_type}")
