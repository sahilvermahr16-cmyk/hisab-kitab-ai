# reports/ledgers.py
"""
Kisi bhi khaate ka "is tareekh se PEHLE tak ka baaki" (signed).

    balance > 0  → humein LENA hai      balance < 0  → humein DENA hai
    cash ledger  → haath mein kitna cash

Har khaate pe har entry ya to DEBIT hai ya CREDIT:
    balance = opening + debit − credit          (sab khaaton ke liye ek hi formula)

    supplier : debit = humne paisa diya        credit = maal aaya
    customer : debit = maal becha              credit = paisa aaya
    employee : debit = mazdoori/advance diya   credit = kaam kiya
    cash     : debit = paisa aaya              credit = paisa gaya
    purchase : debit = payment di              credit = kharid ka bill   (ledger_id 0)
    expense  : debit = payment di              credit = kharcha          (ledger_id 0)
    opening_balances: lena → debit, dena → credit, cash → debit

Tez raasta (month closing): agar pichla mahina 'closed' hai to
    baaki = pichle mahine ka closing + is mahine ki entries (before se pehle tak)
warna shuru se saari entries jod ke (raw). Dono ka jawab hamesha same hota hai.
"""
from collections import defaultdict
from datetime import timedelta

from reports import queries as Q

LEDGER_TYPES = ("supplier", "customer", "employee", "cash", "purchase", "expense")
PARTY_LEDGERS = ("supplier", "customer", "employee")


def _n(x):
    return float(x) if x is not None else 0.0


def ym_of(d):
    return f"{d.year:04d}-{d.month:02d}"


# =====================================================================
#            ALL effects in a date range — grouped by (type, id)
# =====================================================================
def all_effects(db, start=None, end=None):
    """
    {(ledger_type, ledger_id): [debit, credit, txn_count]} — is date-range ki saari entries.
    Month closing isi ko use karta hai; per-party raw function bhi isi ke upar hai,
    taaki dono ka hisab kabhi alag na ho.
    """
    eff = defaultdict(lambda: [0.0, 0.0, 0])

    def add(key, debit=0.0, credit=0.0):
        e = eff[key]
        e[0] += debit
        e[1] += credit
        e[2] += 1

    for o in Q.opening_balances(db, start=start, end=end):
        s = Q.opening_signed(o)
        add((o.ledger_type, o.ledger_id if o.ledger_type != "cash" else 0),
            debit=max(s, 0.0), credit=max(-s, 0.0))

    for t in Q.supplier_transactions(db, start, end):
        add(("supplier", t.supplier_id), credit=_n(t.amount))
    for p in Q.supplier_payments(db, start, end):
        add(("supplier", p.supplier_id), debit=_n(p.amount))

    for t in Q.sales_transactions(db, start, end):
        add(("customer", t.customer_id), debit=_n(t.amount))
    for p in Q.sales_payments(db, start, end):
        add(("customer", p.customer_id), credit=_n(p.amount))

    for t in Q.employee_transactions(db, start, end):
        if t.transaction_type == "work":
            add(("employee", t.employee_id), credit=_n(t.amount))
        elif t.transaction_type in ("payment", "advance"):
            add(("employee", t.employee_id), debit=_n(t.amount))

    for row, _src in Q.cash_entries(db, start, end):
        if row.direction == "in":
            add(("cash", 0), debit=_n(row.amount))
        else:
            add(("cash", 0), credit=_n(row.amount))

    for p in Q.purchases(db, start, end):
        add(("purchase", 0), credit=_n(p.total_amount))
    for p in Q.purchase_payments(db, start, end):
        add(("purchase", 0), debit=_n(p.amount))

    for e in Q.expenses(db, start, end):
        add(("expense", 0), credit=_n(e.amount))
    for p in Q.expense_payments(db, start, end):
        add(("expense", 0), debit=_n(p.amount))

    return eff


def effects(db, ledger_type, ledger_id, start=None, end=None):
    """Ek khaate ka (debit, credit) is range mein."""
    ledger_id = 0 if ledger_type in ("cash", "purchase", "expense") else ledger_id
    if ledger_type in PARTY_LEDGERS:
        # sirf is party ki rows — poore business ki query se bachne ke liye
        d = c = 0.0
        for o in Q.opening_balances(db, ledger_type, ledger_id, start, end):
            s = Q.opening_signed(o)
            d += max(s, 0.0); c += max(-s, 0.0)
        if ledger_type == "supplier":
            c += sum(_n(t.amount) for t in Q.supplier_transactions(db, start, end, ledger_id))
            d += sum(_n(p.amount) for p in Q.supplier_payments(db, start, end, ledger_id))
        elif ledger_type == "customer":
            d += sum(_n(t.amount) for t in Q.sales_transactions(db, start, end, ledger_id))
            c += sum(_n(p.amount) for p in Q.sales_payments(db, start, end, ledger_id))
        else:
            for t in Q.employee_transactions(db, start, end, ledger_id):
                if t.transaction_type == "work":
                    c += _n(t.amount)
                elif t.transaction_type in ("payment", "advance"):
                    d += _n(t.amount)
        return d, c
    e = all_effects(db, start, end).get((ledger_type, 0))
    return (e[0], e[1]) if e else (0.0, 0.0)


# =====================================================================
#                       balance_before (fast + raw)
# =====================================================================
def raw_balance_before(db, ledger_type, ledger_id, before):
    d, c = effects(db, ledger_type, ledger_id, end=before - timedelta(days=1))
    return d - c


def _closed_month_closing(db, ledger_type, ledger_id, ym):
    """Mahina closed hai to us khaate ka closing (row nahi = 0), warna None."""
    from models import MonthClose, MonthlyClosing
    mc = (db.query(MonthClose)
          .filter(MonthClose.business_id == Q.BUSINESS_ID, MonthClose.year_month == ym).first())
    if mc is None or mc.status != "closed":
        return None
    row = (db.query(MonthlyClosing)
           .filter(MonthlyClosing.business_id == Q.BUSINESS_ID, MonthlyClosing.year_month == ym,
                   MonthlyClosing.ledger_type == ledger_type, MonthlyClosing.ledger_id == ledger_id).first())
    return row.closing if row else 0.0


def balance_before(db, ledger_type, ledger_id, before):
    if ledger_type in ("cash", "purchase", "expense"):
        ledger_id = 0
    month_start = before.replace(day=1)
    prev_ym = ym_of(month_start - timedelta(days=1))
    base = _closed_month_closing(db, ledger_type, ledger_id, prev_ym)
    if base is None:
        return raw_balance_before(db, ledger_type, ledger_id, before)
    if before == month_start:
        return base
    d, c = effects(db, ledger_type, ledger_id, start=month_start, end=before - timedelta(days=1))
    return base + d - c


# purane naam — builders inhe use karte hain
def supplier_balance_before(db, supplier_id, before):
    return balance_before(db, "supplier", supplier_id, before)


def customer_balance_before(db, customer_id, before):
    return balance_before(db, "customer", customer_id, before)


def employee_balance_before(db, employee_id, before):
    return balance_before(db, "employee", employee_id, before)


def cash_balance_before(db, before):
    return balance_before(db, "cash", 0, before)
