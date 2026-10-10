# models.py — Complete Updated Version (Advance Phase 1)
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Text, Date, UniqueConstraint
from datetime import datetime
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB
Base = declarative_base()

# --- Employee Part

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    role = Column(String, nullable=True)
    # role: driver/gudam_worker/shop_worker/tod_worker
    business_id = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmployeeTransaction(Base):
    __tablename__ = "employee_transactions"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    transaction_type = Column(String)  # work/payment/advance
    amount = Column(Float)
    transaction_date = Column(Date)
    payment_method = Column(String, nullable=True)
    payment_provider = Column(String, nullable=True)
    note = Column(Text)
    business_id = Column(Integer, default=1, nullable=False)
    # Correction Phase — audit-trail
    status = Column(String, default="active", nullable=False)
    # "active" | "corrected" | "reversal"
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    attendance_date = Column(Date)
    attendance = Column(String, default="absent")
    # "P" / "half" / "absent"
    driving = Column(String, default="absent")
    # "P" / "half" / "absent"
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Family Part (ghar ke log — papa, bhai, mummy...)
# Business ke galle se ghar ke liye paisa gaya ("kharcha") ya ghar se business mein
# paisa aaya ("jama"). Ye lena-dena nahi hai — sirf family kharcha ka hisab.

class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    relation = Column(String, nullable=True)     # papa / bhai / mummy ... (agar bataya)
    business_id = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class FamilyTransaction(Base):
    __tablename__ = "family_transactions"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("family_members.id"))
    transaction_type = Column(String)   # "kharcha" (galle se ghar gaya, cash OUT) / "jama" (galle mein aaya, cash IN)
    amount = Column(Float)
    transaction_date = Column(Date)
    purpose = Column(String, nullable=True)   # kis kaam ke liye (ghar ka saman, fees, ...)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- sales Part

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SalesTransaction(Base):
    __tablename__ = "sales_transactions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    item_name = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    rate = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    driver_name = Column(String, nullable=True)
    source = Column(String, nullable=True)   # "shop" / "gudam" / bhatte ka naam
    destination_name = Column(String, nullable=True)
    bill_id = Column(String, nullable=True)
    sale_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SalesPayment(Base):
    __tablename__ = "sales_payments"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    bill_id = Column(String, nullable=True)
    amount = Column(Float)
    payment_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Supplier part

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    supplier_type = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SupplierTransaction(Base):
    __tablename__ = "supplier_transactions"
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    quantity = Column(Float, nullable=True)
    item_name = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    rate = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    driver_name = Column(String, nullable=True)
    destination_location = Column(String, nullable=True)
    transaction_date = Column(Date)
    bill_id = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SupplierPayment(Base):
    __tablename__ = "supplier_payments"
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    bill_id = Column(String, nullable=True)
    amount = Column(Float)
    payment_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Inventory Part

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    location = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    stock_quantity = Column(Float, default=0)
    unit = Column(String, nullable=False)
    business_id = Column(Integer, default=1, nullable=False)
    # NOTE: Inventory is a derived running-total (one row per
    # location+item+unit), not an append-only transaction log —
    # Correction columns (status/reversal_of_id) don't apply here.
    # Corrections cascade into Inventory automatically when the
    # originating transaction (sale/supplier/movement) is reversed
    # and re-run — this table never needs to be touched directly.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint('location', 'item_name', 'unit', name='uq_location_item_unit'),)

class Adjustment(Base):
    __tablename__ = "stock_adjustments"
    id = Column(Integer, primary_key=True)
    location = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    quantity_change = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    related_party = Column(String, nullable=True)
    source_table = Column(String, nullable=True)
    source_id = Column(Integer, nullable=True)
    adjustment_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Purchase Part

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    seller_name = Column(String, nullable=False)
    seller_phone = Column(String, nullable=True)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    total_amount = Column(Float, nullable=True)
    purchase_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchasePayment(Base):
    __tablename__ = "purchase_payments"
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    amount = Column(Float)
    payment_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Expense Part

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    expense_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExpensePayment(Base):
    __tablename__ = "expense_payments"
    id = Column(Integer, primary_key=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"))
    amount = Column(Float)
    payment_date = Column(Date)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- CashLedger Part

class CashLedger(Base):
    __tablename__ = "cash_ledger"
    id = Column(Integer, primary_key=True)
    entry_date = Column(Date, nullable=False)
    direction = Column(String, nullable=False)   # "in" ya "out"
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    source_table = Column(String, nullable=True)
    source_id = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Activity Log Part

class WorkLog(Base):
    __tablename__ = "work_logs"
    id = Column(Integer, primary_key=True)
    location_type = Column(String, nullable=False)
    location_name = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    labour_count = Column(Integer, nullable=True)
    activity_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MaterialMovement(Base):
    __tablename__ = "material_movements"
    id = Column(Integer, primary_key=True)
    item_name = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    source_type = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    destination_type = Column(String, nullable=True)
    destination_name = Column(String, nullable=True)
    movement_type = Column(String, nullable=True)
    movement_reason = Column(String, nullable=True)
    movement_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Movement Entity Lookup (unified: storage / site / customer / supplier)
# Internal machinery — no business_id, no Correction columns.

class MovementEntityType(str, Enum):
    STORAGE = "storage"
    SITE = "site"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"

class MovementEntityLookup(Base):
    __tablename__ = "movement_entity_lookup"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    linked_id = Column(Integer, nullable=True)
    confirmed_by = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint('normalized_name', name='uq_movement_entity_normalized_name'),)

# --- Person Role Lookup (employee / customer / supplier / property_owner / family_member)
# Internal machinery — no business_id, no Correction columns.

class PersonRoleLookup(Base):
    __tablename__ = "person_role_lookup"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    linked_id = Column(Integer, nullable=True)
    confirmed_by = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint('normalized_name', name='uq_person_role_normalized_name'),)


# --- Audit Log Part (Correction Phase foundation)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)

    # Poora user-message jaisa-ka-taisa (context ke liye)
    full_statement = Column(Text, nullable=False)

    # Extract+Grouping ke baad wala SPECIFIC action-text jisse
    # YE particular tool-call bana — poori mixed-statement nahi,
    # sirf is group/action ka apna text
    action_statement = Column(Text, nullable=False)

    tool_name = Column(String, nullable=False)
    arguments = Column(JSONB, nullable=False)
    summary_text = Column(Text, nullable=False)

    group_id = Column(String, nullable=True)
    action_index = Column(Integer, nullable=True)

    target_table = Column(String, nullable=False)
    target_id = Column(Integer, nullable=False)

    category = Column(String, nullable=True)
    person_name = Column(String, nullable=True)
    entry_date = Column(Date, nullable=True)
    status = Column(String, default="active", nullable=False)
    run_id = Column(String, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# =====================================================================
# --- Reporting Phase
# =====================================================================

# Hisab-Kitab shuru hone se PEHLE ka purana lena-dena / cash — ek baar
# record_opening_balance tool se aata hai. Ek ledger ka ek hi active row.
#   ledger_type: "supplier" | "customer" | "employee" | "cash"
#   ledger_id  : us party ka id (cash ke liye 0)
#   direction  : "lena" (humein milna hai) | "dena" (humein dena hai)
#                cash ke liye "cash" (haath mein itna tha)
class OpeningBalance(Base):
    __tablename__ = "opening_balances"
    id = Column(Integer, primary_key=True)
    ledger_type = Column(String, nullable=False)
    ledger_id = Column(Integer, nullable=False, default=0)
    amount = Column(Float, nullable=False)
    direction = Column(String, nullable=False)
    as_of_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    business_id = Column(Integer, default=1, nullable=False)
    status = Column(String, default="active", nullable=False)
    superseded_by_id = Column(Integer, nullable=True)
    reversal_of_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Har mahine ka "closing" status — ek row per mahina.
#   status: "closed" (calculate ho chuka, sahi hai)
#           "dirty"  (purani date ki entry/correction aayi — dobara calculate karo)
class MonthClose(Base):
    __tablename__ = "month_close"
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, default=1, nullable=False)
    year_month = Column(String, nullable=False)        # "2026-09"
    status = Column(String, default="dirty", nullable=False)
    computed_at = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint('business_id', 'year_month', name='uq_month_close'),)


# Har mahine, har khaate ki opening / debit / credit / closing.
#   ledger_type: supplier | customer | employee | cash | purchase | expense
#                | work_log | material
#   ledger_id  : party id (category khaaton ke liye 0)
#   Sign convention (sab ledgers ke liye ek jaisa):
#       balance > 0  → humein LENA hai
#       balance < 0  → humein DENA hai
#       cash ke liye balance = haath mein cash
#   extra: category-wise breakup (expense mad-wise, maal item-wise qty, ...)
class MonthlyClosing(Base):
    __tablename__ = "monthly_closing"
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, default=1, nullable=False)
    year_month = Column(String, nullable=False)
    ledger_type = Column(String, nullable=False)
    ledger_id = Column(Integer, nullable=False, default=0)
    opening = Column(Float, nullable=False, default=0)
    debit_total = Column(Float, nullable=False, default=0)
    credit_total = Column(Float, nullable=False, default=0)
    closing = Column(Float, nullable=False, default=0)
    txn_count = Column(Integer, nullable=False, default=0)
    extra = Column(JSONB, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('business_id', 'year_month', 'ledger_type', 'ledger_id',
                                       name='uq_monthly_closing'),)


# Report ke free-text values (item, note, naam) ka Hindi/English
# translation — ek baar LLM se, fir yahin se.
class TranslationCache(Base):
    __tablename__ = "translation_cache"
    id = Column(Integer, primary_key=True)
    source_text = Column(Text, nullable=False)
    lang = Column(String, nullable=False)              # "hi" | "en"
    translated_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('source_text', 'lang', name='uq_translation'),)
