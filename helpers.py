from db import SessionLocal
from datetime import date
from sqlalchemy.orm import Session
from models import (Employee, Supplier, Customer, CashLedger, Inventory, Adjustment,MovementEntityLookup, MovementEntityType, PersonRoleLookup,)
from models import (
    EmployeeTransaction, Attendance, SalesTransaction, SalesPayment,
    SupplierTransaction, SupplierPayment, Purchase, PurchasePayment,
    Expense, ExpensePayment, WorkLog, MaterialMovement,
)
from schemas import ToolArgumentResult, ToolName
from models import AuditLog, MonthClose, OpeningBalance, FamilyMember, FamilyTransaction
import json

# audit_log.target_table (jo tools.py har successful tool-call ke baad
# return karta hai) → uska apna SQLAlchemy model. Sirf wahi tables isme
# hain jin par Correction-tracking columns (status/superseded_by_id/
# reversal_of_id) exist karte hain — master tables (employees, customers,
# suppliers) jaan-boojhkar bahar hain, kyunki unke manage_* tools Correction
# search mein already exclude hain (tool_name.startswith("manage_")).
TARGET_TABLE_MODEL_MAP = {
    "employee_transactions": EmployeeTransaction,
    "attendance": Attendance,
    "sales_transactions": SalesTransaction,
    "sales_payments": SalesPayment,
    "supplier_transactions": SupplierTransaction,
    "supplier_payments": SupplierPayment,
    "purchases": Purchase,
    "purchase_payments": PurchasePayment,
    "expenses": Expense,
    "expense_payments": ExpensePayment,
    "work_logs": WorkLog,
    "material_movements": MaterialMovement,
    "stock_adjustments": Adjustment,
    "opening_balances": OpeningBalance,
    "family_transactions": FamilyTransaction,
}


def mark_business_tables_corrected(db: Session, target_table: str, old_row_id: int, new_row_id: int) -> None:
    """
    Correction-reversal ke time audit_log ke saath-saath ASLI business-table
    row par bhi status/link-columns update karta hai — Reporting Phase
    business tables se hi padhega, audit_log se nahi.

    - OLD row (jo galat thi): status='corrected', superseded_by_id=new_row_id
    - NEW row (reversal wali): reversal_of_id=old_row_id

    Commit nahi karta — caller commit karega.
    """
    model = TARGET_TABLE_MODEL_MAP.get(target_table)
    if model is None:
        print(f"⚠️ TARGET_TABLE_MODEL_MAP mein '{target_table}' registered nahi hai — "
              f"business-table status update skip ho raha hai.")
        return

    old_row = db.query(model).filter(model.id == old_row_id).first()
    if old_row is not None:
        old_row.status = "corrected"
        old_row.superseded_by_id = new_row_id

    new_row = db.query(model).filter(model.id == new_row_id).first()
    if new_row is not None:
        new_row.reversal_of_id = old_row_id

    # Purani row ne jo cash_ledger entry banayi thi, wo bhi ab galat hai.
    # (Reversal minus amount se chalta hai aur add_cash_ledger_entry()
    # 0/minus pe kuch nahi likhta — isliye purani cash row khud mark karni padti hai.)
    for cash in (db.query(CashLedger)
                 .filter(CashLedger.source_table == target_table,
                         CashLedger.source_id == old_row_id,
                         CashLedger.status == "active")
                 .all()):
        cash.status = "corrected"


# Correction-reversal ke liye: in tools ka "ulta" tool dobara chala ke nahi,
# seedha purani row ki copy (minus amount ke saath) bana ke hota hai.
#   - payment / expense / purchase tools minus amount pe error dete hain
#   - work_log / attendance mein minus karne layak koi number hi nahi
#   - in sab ka koi inventory side-effect nahi; cash wala side-effect
#     mark_business_tables_corrected() sambhal leta hai
# Jin tools ka inventory pe asar hota hai (sale, supplier maal, movement,
# adjustment) wo pehle jaise tool se hi reverse hote hain.
CLONE_REVERSAL_TOOLS = {
    "record_employee_transaction", "record_attendance",
    "record_sale_payment", "record_supplier_payment",
    "record_purchase", "record_purchase_payment",
    "record_expense", "record_expense_payment",
    "record_work_log", "record_opening_balance",
    "record_family_transaction",
}

_NEGATE_FIELDS = ("amount", "total_amount", "quantity", "quantity_change")
_SKIP_CLONE_COLUMNS = {"id", "created_at", "status", "superseded_by_id", "reversal_of_id"}


def clone_reversal_row(db: Session, target_table: str, old_row_id: int) -> int:
    """Purani business row ki copy — numbers minus mein, reversal_of_id set. Naya id deta hai."""
    model = TARGET_TABLE_MODEL_MAP.get(target_table)
    if model is None:
        raise ValueError(f"'{target_table}' ke liye reversal clone support nahi hai")
    old = db.query(model).filter(model.id == old_row_id).first()
    if old is None:
        raise ValueError(f"{target_table} #{old_row_id} nahi mila")
    data = {c.name: getattr(old, c.name) for c in model.__table__.columns
            if c.name not in _SKIP_CLONE_COLUMNS}
    for f in _NEGATE_FIELDS:
        if f in data and data[f] not in (None, 0):
            data[f] = -data[f]
    new = model(**data, status="active", reversal_of_id=old_row_id)
    db.add(new)
    db.flush()
    return new.id


def reverse_entry(tool_name: str, target_table: str, target_id: int, negated_args: dict, tools_map: dict):
    """
    Correction ka "ulta" — tool jaisa hi result deta hai:
    success pe {"message", "target_table", "target_id"}, fail pe error string.
    """
    if tool_name in CLONE_REVERSAL_TOOLS and target_table and target_id:
        db = SessionLocal()
        try:
            new_id = clone_reversal_row(db, target_table, target_id)
            db.commit()
            return {"message": f"↩️ {target_table} #{target_id} reverse ho gayi",
                    "target_table": target_table, "target_id": new_id}
        except Exception as e:
            db.rollback()
            return f"Error: {e}"
        finally:
            db.close()
    tool = tools_map.get(tool_name)
    if tool is None:
        return f"Error: tool '{tool_name}' nahi mila"
    return tool.invoke(negated_args)


def mark_months_dirty(db: Session, from_date) -> None:
    """
    Is tareekh ke mahine se aage ke saare closed mahine 'dirty' —
    agli report pe wo dobara calculate honge. Commit caller karega.
    """
    if from_date is None:
        return
    ym = f"{from_date.year:04d}-{from_date.month:02d}"
    (db.query(MonthClose)
       .filter(MonthClose.business_id == 1, MonthClose.year_month >= ym, MonthClose.status != "dirty")
       .update({MonthClose.status: "dirty"}, synchronize_session=False))

CATEGORY_MAP = {
    "record_opening_balance": "opening",
    "record_family_transaction": "family",
    "manage_employee": "employee",
    "record_employee_transaction": "employee",
    "record_attendance": "employee",
    "manage_customer": "customer",
    "record_sale_transaction": "customer",
    "record_sale_payment": "customer",
    "manage_supplier": "supplier",
    "record_supplier_transaction": "supplier",
    "record_supplier_payment": "supplier",
    "record_purchase": "purchase",
    "record_purchase_payment": "purchase",
    "record_expense": "expense",
    "record_expense_payment": "expense",
    "record_work_log": "material_movement",
    "record_material_movement": "material_movement",
    "record_adjustment": "material_movement",
}

# Har tool ke arguments mein person/party ka naam alag key se aata
# hai — isse ek consistent person_name column mein normalize karte
# hain, taaki Correction-search ek hi tarike se sabhi tools ke liye
# kaam kare.
PERSON_NAME_FIELDS = [
    "employee_name", "customer_name", "supplier_name", "seller_name", "party_name",
    "member_name",
]

# Har tool ke arguments mein date bhi alag key se aati hai.
DATE_FIELDS = [
    "transaction_date", "attendance_date", "sale_date", "payment_date",
    "purchase_date", "expense_date", "adjustment_date", "movement_date",
    "activity_date", "as_of_date",
]


def _build_summary_text(tool_name: str, arguments: dict) -> str:
    """
    Simple, deterministic summary for Correction-search matching.

    NOTE — Future enrichment planned: right now this is a plain
    template (no LLM call, so it stays fast on every successful
    tool-execution). Later, this can be upgraded to a small LLM
    call that generates a genuinely natural-sounding Hinglish
    sentence (e.g. "Ram ko 500 rupaye ka work payment") — that
    upgrade only needs to happen HERE, nothing else in the
    Correction flow needs to change, since everything downstream
    just reads summary_text as a plain string.
    """
    person = _extract_person_name(arguments)
    amount = arguments.get("amount") or arguments.get("total_amount")

    if person and amount:
        return f"{person} — {tool_name} — ₹{amount}"
    if person:
        return f"{person} — {tool_name}"
    if amount:
        return f"{tool_name} — ₹{amount}"
    return f"{tool_name} entry"

def _extract_person_name(arguments: dict) -> str | None:
    for field in PERSON_NAME_FIELDS:
        value = arguments.get(field)
        if value:
            return value
    return None

def _extract_entry_date(arguments: dict) -> date | None:
    for field in DATE_FIELDS:
        value = arguments.get(field)
        if value:
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value)
                except ValueError:
                    continue
            return value
    return None

def _row_date(db: Session, target_table: str, target_id: int):
    """
    Arguments mein date na ho (jaise opening balance bina date ke) to asli
    business row se uski date lo — taaki audit_log.entry_date kabhi khaali na
    rahe (Correction search aur month-closing dirty marking dono isi pe chalte hain).
    """
    from sqlalchemy import Date as _Date
    model = TARGET_TABLE_MODEL_MAP.get(target_table)
    if model is None or target_id is None:
        return None
    row = db.query(model).filter(model.id == target_id).first()
    if row is None:
        return None
    for col in model.__table__.columns:
        if isinstance(col.type, _Date):
            value = getattr(row, col.name)
            if value is not None:
                return value
    return None


def insert_audit_log(
    db: Session,
    full_statement: str,
    action_statement: str,
    tool_name: str,
    arguments: dict,
    target_table: str,
    target_id: int,
    group_id: str | None = None,
    action_index: int | None = None,
    run_id: str | None = None,
) -> AuditLog:
    """
    Records one successful tool-call for the Correction Phase.

    Called once per successfully-executed tool, right after that
    tool's own row is committed. Does NOT commit itself — caller
    decides when to commit.

    full_statement is the user's entire original message (may span
    multiple unrelated groups). action_statement is the narrower
    extract+grouping-stage text for THIS specific group/action —
    the one Correction-search actually needs, since full_statement
    can be a mix of unrelated things (e.g. "Ram ne 500 ka kaam
    kiya, SBI se eent aayi, kiraya diya" all in one message).
    """
    entry = AuditLog(
        full_statement=full_statement,
        action_statement=action_statement,
        tool_name=tool_name,
        arguments=arguments,
        summary_text=_build_summary_text(tool_name, arguments),
        group_id=group_id,
        action_index=action_index,
        run_id=run_id,
        target_table=target_table,
        target_id=target_id,
        category=CATEGORY_MAP.get(tool_name),
        person_name=_extract_person_name(arguments),
        # opening_balances: tool date ko pehli entry tak khiskaata hai — asli row ki date hi sahi
        entry_date=(_row_date(db, target_table, target_id) if target_table == "opening_balances"
                    else _extract_entry_date(arguments) or _row_date(db, target_table, target_id)),
    )
    db.add(entry)
    db.flush()
    # Reporting: purane mahine ki entry/correction → us mahine se aage sab dobara calculate
    mark_months_dirty(db, entry.entry_date)
    return entry


def add_cash_ledger_entry(db, entry_date, direction, amount, category, source_table, source_id, note=""):
    """
    Add one cash movement entry to CashLedger.

    direction:
    - "in"  -> business mein paisa aaya
    - "out" -> business se paisa gaya
    """

    if amount is None or amount <= 0:
        return
    cash_entry = CashLedger(
        entry_date=entry_date,
        direction=direction,
        amount=amount,
        category=category,
        source_table=source_table,
        source_id=source_id,
        note=note
    )
    db.add(cash_entry)

def get_or_create_employee(name: str, db=None):
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        employee = (
            db.query(Employee)
            .filter(
                Employee.name.ilike(
                    name.strip()
                )
            )
            .first()
        )
        if employee:
            return employee
        employee = Employee(name=name.strip())
        db.add(employee)
        # id generate
        db.flush()
        # agar helper ne apna session banaya hai

        sync_person_role(db, name=employee.name, role="employee", linked_id=employee.id)

        if own_session:
            db.commit()
            db.refresh(employee)
        return employee
    finally:
        if own_session:
            db.close()

def get_or_create_family_member(name: str, db, relation: str = ""):
    """Ghar ka member (papa / bhai / ...) — naam se dhoondo, na mile to banao."""
    member = db.query(FamilyMember).filter(FamilyMember.name.ilike(name.strip())).first()
    if member:
        if relation and not member.relation:
            member.relation = relation.strip().lower()
        return member
    member = FamilyMember(name=name.strip(), relation=(relation.strip().lower() or None) if relation else None)
    db.add(member)
    db.flush()
    sync_person_role(db, name=member.name, role="family_member", linked_id=member.id)
    return member

def get_or_create_customer(name: str, db):
    customer = db.query(Customer).filter(
        Customer.name.ilike(name.strip())
    ).first()

    if customer:
        return customer

    customer = Customer(name=name.strip())
    db.add(customer)
    db.flush()

    # naya customer bana — movement lookup table mein bhi sync karo
    sync_movement_entity(
        db,
        name=customer.name,
        entity_type=MovementEntityType.CUSTOMER,
        linked_id=customer.id,
    )

    sync_person_role(db, name=customer.name, role="customer", linked_id=customer.id)    

    return customer

def get_or_create_supplier(name: str, db):
    supplier = db.query(Supplier).filter(
        Supplier.name.ilike(name.strip())
    ).first()

    if supplier:
        return supplier

    supplier = Supplier(name=name.strip())
    db.add(supplier)
    db.flush()

    # naya supplier bana — movement lookup table mein bhi sync karo
    sync_movement_entity(
        db,
        name=supplier.name,
        entity_type=MovementEntityType.SUPPLIER,
        linked_id=supplier.id,
    )

    sync_person_role(db, name=supplier.name, role="supplier", linked_id=supplier.id)

    return supplier

def update_stock_history(
    db: Session,
    location: str,
    item_name: str,
    unit: str,
    quantity_change: float,
    reason: str | None = None,
    related_party: str | None = None,
    source_table: str | None = None,
    source_id: int | None = None,
    adjustment_date: date | None = None,
    note: str | None = None,
) -> Adjustment:
    """
    Create a stock history entry in the Adjustment table.

    This helper only records stock history.
    It does NOT update Inventory.
    It does NOT commit the transaction.
    """

    adjustment = Adjustment(
        location=location,
        item_name=item_name,
        unit=unit,
        quantity_change=quantity_change,
        reason=reason,
        related_party=related_party,
        source_table=source_table,
        source_id=source_id,
        adjustment_date=adjustment_date,
        note=note,
    )

    db.add(adjustment)
    db.flush()

    return adjustment

def update_inventory_stock(
    db: Session,
    location: str,
    item_name: str,
    unit: str,
    quantity_change: float,
) -> Inventory:
    """
    Update the current inventory stock.

    If the inventory row exists, increase/decrease its stock quantity.
    If it does not exist, create a new inventory row.

    This helper only updates Inventory.
    It does NOT create stock history.
    It does NOT commit the transaction.
    """

    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.location == location,
            Inventory.item_name == item_name,
            Inventory.unit == unit,
        )
        .first()
    )

    if inventory:
        inventory.stock_quantity += quantity_change
    else:
        inventory = Inventory(
            location=location,
            item_name=item_name,
            unit=unit,
            stock_quantity=quantity_change,
        )
        db.add(inventory)

    db.flush()

    return inventory

# -- Movement Entity Lookup helpers (Storage / Site / Customer / Supplier)

def normalize_name(name: str) -> str:
    """
    Normalizes a name for consistent matching.
    Lowercase + strip extra whitespace.
    Used for both Location and MovementEntityLookup matching.
    """
    return " ".join(name.strip().lower().split())


def lookup_movement_entity(db: Session, name: str) -> MovementEntityLookup | None:
    """
    Looks up a name in the unified movement-entity lookup table.
    Returns the record if found (could be storage, site, customer,
    or supplier), else None.

    This should be checked BEFORE assuming a name is an unknown
    location — a name might already be a known customer/supplier.
    """
    normalized = normalize_name(name)
    return db.query(MovementEntityLookup).filter_by(normalized_name=normalized).first()

def sync_movement_entity(
    db: Session,
    name: str,
    entity_type: MovementEntityType,
    linked_id: int | None = None,
    confirmed_by: str = "auto_sync",
) -> MovementEntityLookup:
    """
    Ensures a name exists in the unified movement-entity lookup table.

    Called whenever a NEW Customer or Supplier record is created
    (whether via get_or_create_customer/get_or_create_supplier during
    a transaction, or via the manage_customer/manage_supplier tools),
    so that Material Movement resolution can recognize this name
    without triggering an unnecessary "storage or site?" HITL prompt.

    Does NOT commit — caller is responsible for committing alongside
    whatever else is happening in that transaction.
    """
    normalized = normalize_name(name)

    existing = db.query(MovementEntityLookup).filter_by(normalized_name=normalized).first()
    if existing:
        return existing  # already synced, avoid duplicate

    entry = MovementEntityLookup(
        name=name,
        normalized_name=normalized,
        entity_type=entity_type.value,
        linked_id=linked_id,
        confirmed_by=confirmed_by,
    )
    db.add(entry)
    db.flush()
    return entry


# --- Person Entity Lookup helpers (for Employee / Person classification)

def sync_person_role(
    db,
    name: str,
    role: str,
    linked_id: int | None = None,
    confirmed_by: str = "auto_sync",
) -> PersonRoleLookup:
    """
    Ensures a name exists in the person-role lookup table, with its
    confirmed business role. Called whenever a new Employee, Customer,
    Supplier, or Purchase-seller record is created, so that Person-Role-
    Classification can (in future) short-circuit re-classification for
    an already-known entity.
    """
    normalized = normalize_name(name)

    existing = db.query(PersonRoleLookup).filter_by(normalized_name=normalized).first()
    if existing:
        return existing  # already synced, avoid duplicate

    entry = PersonRoleLookup(
        name=name,
        normalized_name=normalized,
        role=role,
        linked_id=linked_id,
        confirmed_by=confirmed_by,
    )
    db.add(entry)
    db.flush()
    return entry

def _link_direct_sale_tools(results: list[ToolArgumentResult], group_id: str) -> None:
    """
    Direct Sale produces TWO tool calls (record_supplier_transaction +
    record_sale_transaction) for the SAME real-world event. They must
    agree on customer_name — copy it from the sale-side call (where
    it usually ends up, often via a later Tool-Argument HITL answer)
    into the supplier-side call, so the material isn't left sitting
    in storage under no customer.
    """
    supplier_result = None
    sale_result = None

    for r in results:
        if r.group_id != group_id:
            continue
        if r.tool_name == ToolName.RECORD_SUPPLIER_TRANSACTION:
            supplier_result = r
        elif r.tool_name == ToolName.RECORD_SALE_TRANSACTION:
            sale_result = r

    if supplier_result is None or sale_result is None:
        return

    sale_args = sale_result.arguments
    customer_name = (
        sale_args.get("customer_name")
        if isinstance(sale_args, dict)
        else getattr(sale_args, "customer_name", None)
    )
    if customer_name:
        if isinstance(supplier_result.arguments, dict):
            supplier_result.arguments["customer_name"] = customer_name
        else:
            supplier_result.arguments.customer_name = customer_name





# ───────────────────────────────────────────────────────────────
# Naam ko DB ke asli record se milana
#   "SBI bhata" / "SBI bhatte"   → "SBI Bhatta"
#   "Beldar Sohan" / "Sohan the cook" / "सोहन कुक" → "Sohan" / "सोहन"
# Kram: seedha match → kaam ka naam hata ke → Hindi ka aakhri hissa
# (a/e/o, ा/े/ो) chhod ke. Sirf EK record mile tabhi badlo, warna naam
# jaisa tha waisa (naya aadmi tabhi banega jab sach mein naya ho).
# ───────────────────────────────────────────────────────────────
_TITLE_WORDS = {
    "beldar", "cook", "driver", "mistri", "munshi", "the", "wala", "wale", "waala", "waale",
    "ladka", "ladke", "helper", "mazdoor", "majdoor", "labour", "labourer", "worker", "karigar",
    "chowkidar", "chaukidar", "dumper", "dukaan", "dukan", "shop", "boy",
    "बेलदार", "कुक", "ड्राइवर", "मिस्त्री", "मुंशी", "वाला", "वाले", "लड़का", "लड़के", "हेल्पर",
    "मज़दूर", "मजदूर", "कारीगर", "चौकीदार", "डंपर", "दुकान",
}
_NAME_ENDINGS = ("ों", "ो", "े", "ा", "on", "e", "a", "o")


def _stem_name_word(w: str) -> str:
    for end in _NAME_ENDINGS:
        if w.endswith(end) and len(w) - len(end) >= 4:     # "Raja" ≠ "Raj" — chhote naam nahi chhedte
            w = w[: -len(end)]
            break
    out = []
    for ch in w:                                  # bhatt / bhat — dohra akshar ek
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


def _strip_titles(name: str) -> str:
    words = [w for w in normalize_name(name).replace("'s", "").split() if w not in _TITLE_WORDS]
    return " ".join(words)


def _name_stem_key(name: str) -> str:
    return " ".join(_stem_name_word(w) for w in _strip_titles(name).split())


def match_known_name(db: Session, name: str, model) -> str | None:
    """`model` (Employee/Customer/Supplier/FamilyMember) mein ye naam hai? → DB wala naam, warna None."""
    if not name or not name.strip():
        return None
    names = [n for (n,) in db.query(model.name).all() if n]
    target = normalize_name(name)
    for n in names:                                           # 1. seedha
        if normalize_name(n) == target:
            return n
    stripped = _strip_titles(name)
    if stripped and stripped != target:                       # 2. kaam ka naam hata ke
        hits = {n for n in names if normalize_name(n) == stripped}
        if len(hits) == 1:
            return hits.pop()
    key = _name_stem_key(name)                                # 3. aakhri hissa chhod ke
    if key:
        hits = {n for n in names if _name_stem_key(n) == key}
        if len(hits) == 1:
            return hits.pop()
    return None


NAME_FIELD_MODELS = {
    "employee_name": Employee,
    "customer_name": Customer,
    "supplier_name": Supplier,
    "member_name": FamilyMember,
}


def resolve_person_name(name: str, field: str) -> str:
    """Tool argument ka naam (employee_name/…) → DB ka asli naam agar ek hi mila, warna wahi."""
    model = NAME_FIELD_MODELS.get(field)
    if model is None or not name:
        return name
    db = SessionLocal()
    try:
        return match_known_name(db, name, model) or name
    finally:
        db.close()
