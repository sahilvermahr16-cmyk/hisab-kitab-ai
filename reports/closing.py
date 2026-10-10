# reports/closing.py
"""
Month closing — har mahine, har khaate ka opening / debit / credit / closing
pehle se calculate karke monthly_closing table mein rakhta hai.

  - Mahina tab calculate hota hai jab koi report maange (ensure_closed_until).
  - Chalu mahina kabhi store nahi hota — hamesha live.
  - Purani date ki entry/correction aate hi helpers.mark_months_dirty()
    us mahine se aage sab 'dirty' kar deta hai → agli report pe dobara.

    closing = opening + debit − credit      (ledgers.py ka sign convention)
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func

from models import (
    MonthClose, MonthlyClosing, OpeningBalance,
    EmployeeTransaction, SalesTransaction, SalesPayment, SupplierTransaction, SupplierPayment,
    Purchase, PurchasePayment, Expense, ExpensePayment, CashLedger,
)
from reports import queries as Q
from reports import ledgers as L


# ------------------------------------------------------------------ month helpers
def month_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    start = date(y, m, 1)
    nxt = date(y + (m == 12), (m % 12) + 1, 1)
    return start, nxt - timedelta(days=1)


def next_ym(ym):
    _, end = month_bounds(ym)
    return L.ym_of(end + timedelta(days=1))


def prev_ym(ym):
    start, _ = month_bounds(ym)
    return L.ym_of(start - timedelta(days=1))


def months_between(start, end):
    """[start, end] ke beech ke saare 'YYYY-MM' (dono shaamil)."""
    out, ym, last = [], L.ym_of(start), L.ym_of(end)
    while ym <= last:
        out.append(ym)
        ym = next_ym(ym)
    return out


def last_closable_ym(today=None):
    today = today or date.today()
    return L.ym_of(today.replace(day=1) - timedelta(days=1))


def earliest_data_date(db):
    cols = [
        (EmployeeTransaction, EmployeeTransaction.transaction_date),
        (SalesTransaction, SalesTransaction.sale_date), (SalesPayment, SalesPayment.payment_date),
        (SupplierTransaction, SupplierTransaction.transaction_date),
        (SupplierPayment, SupplierPayment.payment_date),
        (Purchase, Purchase.purchase_date), (PurchasePayment, PurchasePayment.payment_date),
        (Expense, Expense.expense_date), (ExpensePayment, ExpensePayment.payment_date),
        (CashLedger, CashLedger.entry_date), (OpeningBalance, OpeningBalance.as_of_date),
    ]
    dates = []
    for model, col in cols:
        d = db.query(func.min(col)).filter(Q.active(model)).scalar()
        if d is not None:
            dates.append(d)
    return min(dates) if dates else None


# ------------------------------------------------------------------ compute
def _expense_by_category(db, start, end):
    out = {}
    for e in Q.expenses(db, start, end):
        k = e.category or "-"
        out[k] = out.get(k, 0.0) + (float(e.amount) if e.amount is not None else 0.0)
    return out


def compute_month(db, ym):
    """
    Ek mahine ke saare khaate calculate karke save. Maan ke chalta hai ki
    pichla mahina (agar data hai) already closed hai — ensure_closed_until
    mahine order mein chalata hai, to ye hamesha sach hota hai.
    """
    start, end = month_bounds(ym)
    p = prev_ym(ym)

    prev_close = {}
    pmc = db.query(MonthClose).filter(MonthClose.business_id == Q.BUSINESS_ID, MonthClose.year_month == p).first()
    if pmc is not None and pmc.status == "closed":
        for r in (db.query(MonthlyClosing)
                  .filter(MonthlyClosing.business_id == Q.BUSINESS_ID, MonthlyClosing.year_month == p).all()):
            prev_close[(r.ledger_type, r.ledger_id)] = r.closing
    else:
        # pichla mahina closed nahi (ya data se pehle ka) → shuru se raw
        for (lt, lid), (d, c, _n) in L.all_effects(db, end=start - timedelta(days=1)).items():
            prev_close[(lt, lid)] = d - c

    eff = L.all_effects(db, start, end)
    keys = set(eff) | {k for k, v in prev_close.items() if abs(v) > 0.005}

    db.query(MonthlyClosing).filter(MonthlyClosing.business_id == Q.BUSINESS_ID,
                                    MonthlyClosing.year_month == ym).delete(synchronize_session=False)
    now = datetime.utcnow()
    exp_cat = _expense_by_category(db, start, end)
    for (lt, lid) in sorted(keys, key=lambda k: (k[0], k[1])):
        opening = prev_close.get((lt, lid), 0.0)
        d, c, n = eff.get((lt, lid), (0.0, 0.0, 0))
        if abs(opening) < 0.005 and abs(d) < 0.005 and abs(c) < 0.005:
            continue
        db.add(MonthlyClosing(
            business_id=Q.BUSINESS_ID, year_month=ym, ledger_type=lt, ledger_id=lid,
            opening=opening, debit_total=d, credit_total=c, closing=opening + d - c, txn_count=n,
            extra={"by_category": exp_cat} if lt == "expense" and exp_cat else None,
            computed_at=now,
        ))

    mc = db.query(MonthClose).filter(MonthClose.business_id == Q.BUSINESS_ID, MonthClose.year_month == ym).first()
    if mc is None:
        mc = MonthClose(business_id=Q.BUSINESS_ID, year_month=ym)
        db.add(mc)
    mc.status = "closed"
    mc.computed_at = now
    db.commit()


def ensure_closed_until(db, upto_ym=None):
    """
    Data ke pehle mahine se 'upto_ym' tak (default: pichla poora mahina) jo
    mahina missing ya dirty hai use calculate karo. Ek mahina dobara bana to
    uske baad ke saare bhi dobara banenge (unka opening badal gaya).
    Returns: kitne mahine calculate hue.
    """
    upto_ym = upto_ym or last_closable_ym()
    upto_ym = min(upto_ym, last_closable_ym())        # chalu mahina kabhi close nahi
    first = earliest_data_date(db)
    if first is None:
        return 0
    status = {m.year_month: m.status for m in
              db.query(MonthClose).filter(MonthClose.business_id == Q.BUSINESS_ID).all()}
    done, rebuild_rest = 0, False
    ym = L.ym_of(first)
    while ym <= upto_ym:
        if rebuild_rest or status.get(ym) != "closed":
            compute_month(db, ym)
            done += 1
            rebuild_rest = True
        ym = next_ym(ym)
    return done


def monthly_rows(db, ledger_type, ledger_id, yms):
    """Closed mahinon ki stored rows: {ym: MonthlyClosing or None}."""
    rows = (db.query(MonthlyClosing)
            .filter(MonthlyClosing.business_id == Q.BUSINESS_ID, MonthlyClosing.year_month.in_(yms),
                    MonthlyClosing.ledger_type == ledger_type, MonthlyClosing.ledger_id == ledger_id).all())
    by = {r.year_month: r for r in rows}
    return {ym: by.get(ym) for ym in yms}


def month_figures(db, ledger_type, ledger_id, ym):
    """
    Ek khaate ka ek mahine ka (opening, debit, credit, closing).
    Closed mahina → stored row; chalu / dirty mahina → live.
    """
    if ledger_type in ("cash", "purchase", "expense"):
        ledger_id = 0
    start, end = month_bounds(ym)
    mc = db.query(MonthClose).filter(MonthClose.business_id == Q.BUSINESS_ID, MonthClose.year_month == ym).first()
    if mc is not None and mc.status == "closed":
        r = monthly_rows(db, ledger_type, ledger_id, [ym])[ym]
        if r is None:
            return dict(opening=0.0, debit=0.0, credit=0.0, closing=0.0)
        return dict(opening=r.opening, debit=r.debit_total, credit=r.credit_total, closing=r.closing)
    opening = L.balance_before(db, ledger_type, ledger_id, start)
    end = min(end, date.today()) if start <= date.today() else end
    d, c = L.effects(db, ledger_type, ledger_id, start, end)
    return dict(opening=opening, debit=d, credit=c, closing=opening + d - c)
