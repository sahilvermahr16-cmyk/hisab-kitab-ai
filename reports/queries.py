# reports/queries.py
"""
Report ke liye saari DB queries — ek hi jagah.

ACTIVE RULE: sirf wahi rows jo abhi "sach" hain.
  - status == "corrected"            → galat thi, hata di gayi   → BAHAR
  - reversal_of_id IS NOT NULL       → kisi galat row ka ulta     → BAHAR
  Dono ek-doosre ko cancel karte hain, isliye dono ko chhodna = sahi net hisab.

Sign convention (poore reports package mein):
    balance > 0  → humein LENA hai
    balance < 0  → humein DENA hai
"""
from collections import defaultdict
from sqlalchemy import and_

from models import (
    Employee, EmployeeTransaction, Customer, SalesTransaction, SalesPayment,
    Supplier, SupplierTransaction, SupplierPayment, Purchase, PurchasePayment,
    Expense, ExpensePayment, CashLedger, WorkLog, MaterialMovement, OpeningBalance,
    FamilyMember, FamilyTransaction,
)

BUSINESS_ID = 1

# cash_ledger.source_table → (model, date column)
SOURCE_MODELS = {
    "employee_transactions": EmployeeTransaction,
    "sales_payments": SalesPayment,
    "supplier_payments": SupplierPayment,
    "purchase_payments": PurchasePayment,
    "expense_payments": ExpensePayment,
    "family_transactions": FamilyTransaction,
}


def active(model):
    return and_(
        model.status == "active",
        model.reversal_of_id.is_(None),
        model.business_id == BUSINESS_ID,
    )


def _between(col, start, end):
    conds = []
    if start is not None:
        conds.append(col >= start)
    if end is not None:
        conds.append(col <= end)
    return conds


def _num(x):
    return float(x) if x is not None else 0.0


# ------------------------------------------------------------------ masters
def suppliers(db):
    return {s.id: s for s in db.query(Supplier).filter(Supplier.business_id == BUSINESS_ID).all()}


def customers(db):
    return {c.id: c for c in db.query(Customer).filter(Customer.business_id == BUSINESS_ID).all()}


def employees(db):
    return {e.id: e for e in db.query(Employee).filter(Employee.business_id == BUSINESS_ID).all()}


def family_members(db):
    return {m.id: m for m in db.query(FamilyMember).filter(FamilyMember.business_id == BUSINESS_ID).all()}


# ------------------------------------------------------------------ family
def family_transactions(db, start=None, end=None, member_id=None):
    q = db.query(FamilyTransaction).filter(active(FamilyTransaction),
                                           *_between(FamilyTransaction.transaction_date, start, end))
    if member_id is not None:
        q = q.filter(FamilyTransaction.member_id == member_id)
    return q.order_by(FamilyTransaction.transaction_date, FamilyTransaction.id).all()


# ------------------------------------------------------------------ supplier
def supplier_transactions(db, start=None, end=None, supplier_id=None):
    q = db.query(SupplierTransaction).filter(active(SupplierTransaction),
                                             *_between(SupplierTransaction.transaction_date, start, end))
    if supplier_id is not None:
        q = q.filter(SupplierTransaction.supplier_id == supplier_id)
    return q.order_by(SupplierTransaction.transaction_date, SupplierTransaction.id).all()


def supplier_payments(db, start=None, end=None, supplier_id=None):
    q = db.query(SupplierPayment).filter(active(SupplierPayment),
                                         *_between(SupplierPayment.payment_date, start, end))
    if supplier_id is not None:
        q = q.filter(SupplierPayment.supplier_id == supplier_id)
    return q.order_by(SupplierPayment.payment_date, SupplierPayment.id).all()


# ------------------------------------------------------------------ customer
def sales_transactions(db, start=None, end=None, customer_id=None):
    q = db.query(SalesTransaction).filter(active(SalesTransaction),
                                          *_between(SalesTransaction.sale_date, start, end))
    if customer_id is not None:
        q = q.filter(SalesTransaction.customer_id == customer_id)
    return q.order_by(SalesTransaction.sale_date, SalesTransaction.id).all()


def sales_payments(db, start=None, end=None, customer_id=None):
    q = db.query(SalesPayment).filter(active(SalesPayment),
                                      *_between(SalesPayment.payment_date, start, end))
    if customer_id is not None:
        q = q.filter(SalesPayment.customer_id == customer_id)
    return q.order_by(SalesPayment.payment_date, SalesPayment.id).all()


# ------------------------------------------------------------------ employee
def employee_transactions(db, start=None, end=None, employee_id=None):
    q = db.query(EmployeeTransaction).filter(active(EmployeeTransaction),
                                             *_between(EmployeeTransaction.transaction_date, start, end))
    if employee_id is not None:
        q = q.filter(EmployeeTransaction.employee_id == employee_id)
    return q.order_by(EmployeeTransaction.transaction_date, EmployeeTransaction.id).all()


# ------------------------------------------------------------------ purchase / expense
def purchases(db, start=None, end=None):
    return (db.query(Purchase).filter(active(Purchase), *_between(Purchase.purchase_date, start, end))
            .order_by(Purchase.purchase_date, Purchase.id).all())


def purchase_payments(db, start=None, end=None, purchase_ids=None):
    q = db.query(PurchasePayment).filter(active(PurchasePayment),
                                         *_between(PurchasePayment.payment_date, start, end))
    if purchase_ids is not None:
        q = q.filter(PurchasePayment.purchase_id.in_(list(purchase_ids) or [-1]))
    return q.order_by(PurchasePayment.payment_date, PurchasePayment.id).all()


def expenses(db, start=None, end=None):
    return (db.query(Expense).filter(active(Expense), *_between(Expense.expense_date, start, end))
            .order_by(Expense.expense_date, Expense.id).all())


def expense_payments(db, start=None, end=None, expense_ids=None):
    q = db.query(ExpensePayment).filter(active(ExpensePayment),
                                        *_between(ExpensePayment.payment_date, start, end))
    if expense_ids is not None:
        q = q.filter(ExpensePayment.expense_id.in_(list(expense_ids) or [-1]))
    return q.order_by(ExpensePayment.payment_date, ExpensePayment.id).all()


# ------------------------------------------------------------------ registers
def work_logs(db, start=None, end=None):
    return (db.query(WorkLog).filter(active(WorkLog), *_between(WorkLog.activity_date, start, end))
            .order_by(WorkLog.activity_date, WorkLog.id).all())


def material_movements(db, start=None, end=None):
    return (db.query(MaterialMovement).filter(active(MaterialMovement),
                                              *_between(MaterialMovement.movement_date, start, end))
            .order_by(MaterialMovement.movement_date, MaterialMovement.id).all())


# ------------------------------------------------------------------ opening balances
def opening_balances(db, ledger_type=None, ledger_id=None, start=None, end=None):
    q = db.query(OpeningBalance).filter(active(OpeningBalance),
                                        *_between(OpeningBalance.as_of_date, start, end))
    if ledger_type is not None:
        q = q.filter(OpeningBalance.ledger_type == ledger_type)
    if ledger_id is not None:
        q = q.filter(OpeningBalance.ledger_id == ledger_id)
    return q.order_by(OpeningBalance.as_of_date, OpeningBalance.id).all()


def opening_signed(ob):
    """OpeningBalance row → signed amount (lena +, dena −, cash +)."""
    amt = _num(ob.amount)
    return -amt if ob.direction == "dena" else amt


# ------------------------------------------------------------------ cash
def cash_entries(db, start=None, end=None):
    """
    cash_ledger ki rows — LEKIN sirf wahi jinki source row abhi active hai.

    Kyun: correction ke time reversal negative amount ke saath chalta hai,
    aur add_cash_ledger_entry() amount <= 0 pe kuch nahi likhta. Purani
    cash_ledger row 'active' hi reh jaati hai. Isliye cash_ledger ka apna
    status bharosemand nahi — source row se check karna padta hai.
    """
    rows = (db.query(CashLedger).filter(CashLedger.status == "active",
                                        CashLedger.reversal_of_id.is_(None),
                                        CashLedger.business_id == BUSINESS_ID,
                                        *_between(CashLedger.entry_date, start, end))
            .order_by(CashLedger.entry_date, CashLedger.id).all())

    by_table = defaultdict(set)
    for r in rows:
        if r.source_table in SOURCE_MODELS and r.source_id is not None:
            by_table[r.source_table].add(r.source_id)

    alive = {}
    for table, ids in by_table.items():
        model = SOURCE_MODELS[table]
        alive[table] = {
            x.id: x for x in db.query(model).filter(model.id.in_(ids), active(model)).all()
        }

    out = []
    for r in rows:
        if r.source_table in SOURCE_MODELS:
            src = alive.get(r.source_table, {}).get(r.source_id)
            if src is None:
                continue          # source row corrected/reversed → ye cash entry bhi bahar
            out.append((r, src))
        else:
            out.append((r, None))
    return out
