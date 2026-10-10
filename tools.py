# tools.py — Full Updated Version
from datetime import datetime, date
from langchain_core.tools import tool
from sqlalchemy import desc
from db import SessionLocal
import db
from models import (
    Attendance, Employee, EmployeeTransaction, 
    Customer, SalesTransaction, SalesPayment,
    Supplier,  SupplierTransaction, SupplierPayment, 
    WorkLog, MaterialMovement, Expense, ExpensePayment, 
    Purchase, PurchasePayment, 
)
import traceback
from helpers import (get_or_create_employee, get_or_create_customer, get_or_create_supplier, add_cash_ledger_entry, 
    update_stock_history, update_inventory_stock, sync_movement_entity, sync_person_role,)
from models import MovementEntityType, OpeningBalance, CashLedger, FamilyTransaction
from item_mapper import normalize_item

# -- Employee Tools

@tool
def manage_employee(employee_name: str, phone: str = "", address: str = "", role: str = ""):
    """
    Manage employee profile information.

    ═══════════════════════════════
    DO NOT USE THIS TOOL FOR
    ═══════════════════════════════

    - Employee ne aaj kya kaam kiya → record_employee_transaction
    - Employee ko payment di → record_employee_transaction
    - Employee ko advance diya → record_employee_transaction
    - Employee aaj aaya / nahi aaya → record_attendance
    - Employee ki driving attendance → record_attendance

    This tool is ONLY for creating a new employee
    or updating an existing employee's profile.

    ═══════════════════════════════
    TOOL PURPOSE
    ═══════════════════════════════

    Use this tool when the user provides employee
    profile information such as:

    - employee name
    - phone number
    - address
    - role / type of work

    If the employee does not exist, create a new employee.

    If the employee already exists, update ONLY the
    profile fields explicitly provided by the user.

    Never overwrite an existing field with an empty value.

    ═══════════════════════════════
    EXAMPLES
    ═══════════════════════════════

    "राम हमारे यहाँ कर्मचारी है, वह ड्राइवर है,
    उसका फोन नंबर 9876543210 है और पता रामनगर है।"

    → नया कर्मचारी होने पर नया Employee record बनाएं.

    name = राम
    role = driver
    phone = 9876543210
    address = रामनगर


    "राम अब गोदाम पर काम करेगा और उसका नया फोन नंबर
    9876543211 है।"

    → राम पहले से मौजूद है तो उसी Employee की profile update करें.

    role = gudam_worker
    phone = 9876543211

    address जैसी दूसरी existing information को न बदलें.


    "राम का पता बदलकर शास्त्री नगर कर दो।"

    → केवल address update करें.

    address = शास्त्री नगर


    "राम अब ड्राइवर है।"

    → केवल role update करें.

    role = driver


    "राम ने आज गोदाम पर काम किया।"

    → इस tool का उपयोग न करें.
    → record_employee_transaction का उपयोग करें.

    ═══════════════════════════════
    PROFILE UPDATE RULE
    ═══════════════════════════════

    Existing employee मिलने पर:

    - phone दिया गया है → केवल phone update करें
    - address दिया गया है → केवल address update करें
    - role दिया गया है → केवल role update करें
    - field नहीं दी गई है → उस field को unchanged रखें

    New employee होने पर:

    - उपलब्ध profile information के साथ employee create करें.
    - जो information नहीं दी गई है उसे NULL रखें.
    """
    db = SessionLocal()

    try:
        employee_name = employee_name.strip()

        if not employee_name:
            return "Error: employee name is required."
        employee = db.query(Employee).filter(
            Employee.name.ilike(employee_name)
        ).first()

        if not employee:
            employee = Employee(
                name=employee_name,
                phone=phone.strip() if phone else None,
                address=address.strip() if address else None,
                role=role.strip().lower() if role else None
            )
            db.add(employee)
            db.flush()
            sync_person_role(db, name=employee.name, role="employee", linked_id=employee.id)
            db.commit()
            db.refresh(employee)
            return {
                "message": f"✅ New employee registered: {employee.name}",
                "target_table": "employees",
                "target_id": employee.id,
            }
        updated_fields = []

        # Only update explicitly provided values
        if phone and phone.strip():
            employee.phone = phone.strip()
            updated_fields.append("phone")

        if address and address.strip():
            employee.address = address.strip()
            updated_fields.append("address")

        if role and role.strip():
            employee.role = role.strip().lower()
            updated_fields.append("role")

        # Nothing to update
        if not updated_fields:
            return (
                f"ℹ️ Employee '{employee.name}' already exists. "
                f"No profile changes were provided."
            )

        db.commit()

        return {
            "message": (
                f"✅ Employee profile updated: {employee.name}\n"
                f"Updated fields: {', '.join(updated_fields)}"
            ),
            "target_table": "employees",
            "target_id": employee.id,
        }

    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {str(e)}"

    finally:
        db.close()

@tool
def record_employee_transaction(employee_name: str, transaction_type: str, amount: float, transaction_date: str, payment_method: str = "", payment_provider: str = "", note: str = ""):
    """
    Record employee work or payment entries.

    transaction_type:
    - work     → employee ne kaam kiya
    - payment  → employee ko paisa diya

    Examples:
    "Ram ne 500 ka kaam kiya" => transaction_type="work", amount=500
    "Ram ne driveri ki" => transaction_type="work", amount=0, note="driveri"
    "Ram ko 500 diye" => transaction_type="payment", amount=500

    Rules:
    1. Work descriptions → note field mein daalo
    2. Amount nahi hai toh amount=0 rakho
    3. Date nahi hai toh aaj ki date (YYYY-MM-DD)
    4. Payment hone par CashLedger mein cash OUT entry create karo.
    """
    db = SessionLocal()
    try:
        transaction_type = transaction_type.strip().lower()
        payment_method = (
            payment_method.strip().lower()
            if payment_method
            else None
        )
        payment_provider = (
            payment_provider.strip().lower()
            if payment_provider
            else None
        )
        employee = get_or_create_employee(employee_name, db)
        print("Employee ID:", employee.id)
        print("Employee Name:", employee.name)
        date_obj = datetime.strptime(
            transaction_date,
            "%Y-%m-%d"
        ).date()
        tx = EmployeeTransaction(
            employee_id=employee.id,
            transaction_type=transaction_type,
            amount=amount,
            transaction_date=date_obj,
            payment_method=payment_method,
            payment_provider=payment_provider,
            note=note
        )
        db.add(tx)
        print("Before flush")
        # Generate transaction ID
        db.flush()
        print("TX ID:", tx.id)
        if transaction_type == "payment" and amount > 0:
            add_cash_ledger_entry(
                db=db,
                entry_date=tx.transaction_date,
                direction="out",
                amount=amount,
                category="salary",
                source_table="employee_transactions",
                source_id=tx.id,
                note=note
            )
            print(
                f"CashLedger updated: OUT ₹{amount}, "
                f"source_id={tx.id}"
            )
        db.commit()
        print("Committed")
        if transaction_type == "payment":
            msg = (
                f"✅ {employee_name} ko ₹{amount} payment record ho gayi.\n"
                f"💰 CashLedger mein ₹{amount} cash OUT bhi record ho gaya."
            )
        else:
            msg = f"✅ {employee_name} ki work entry record ho gayi."

        return {
            "message": msg,
            "target_table": "employee_transactions",
            "target_id": tx.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"

    finally:
        db.close()

@tool
def record_attendance(employee_name: str, attendance_date: str, attendance: str = "absent", driving: str = "absent", note: str = ""):
    """
    Record employee attendance — general kaam aur
    driving dono track hote hain.

    attendance / driving values: "P" (present/poora din),
    "half" (aadha din), "absent" (nahi aaya)

    IMPORTANT RULE: Agar sirf driving bola gaya hai
    (attendance explicitly nahi bola), toh attendance
    automatically driving ke SAME value le lega.

    Examples:

    "Ram aaj aaya"
    => attendance="P", driving="absent"

    "Ram aaj nahi aaya"
    => attendance="absent", driving="absent"

    "Satpal aaj driving ki" (poora din)
    => attendance="P", driving="P"

    "Satpal aadha din driving ki"
    => attendance="half", driving="half"

    "Mohan poora din kaam kiya aur thodi driving bhi ki"
    => attendance="P", driving="half"
    """
    db = SessionLocal()
    try:
        employee = get_or_create_employee(employee_name)
        date_obj = datetime.strptime(attendance_date, "%Y-%m-%d").date()

        # Ek din ki attendance dobara aaye to purani row ko BADLO mat — nayi row
        # banao aur purani ko "corrected" (superseded) karo. Overwrite karne se
        # Correction ka "naya statement" flow toot jaata tha: nayi entry purani
        # row ko hi badal deti thi, aur fir purani ko reverse karte hi nayi bhi
        # chali jaati thi. Ab har attendance ki apni row hai, history bhi bachi rehti hai.
        previous = db.query(Attendance).filter(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date == date_obj,
            Attendance.status == "active",
            Attendance.reversal_of_id.is_(None),
        ).order_by(Attendance.id).all()

        row = Attendance(
            employee_id=employee.id,
            attendance_date=date_obj,
            attendance=attendance,
            driving=driving,
            note=note or (previous[-1].note if previous else None),
        )
        db.add(row)
        db.flush()
        for old_row in previous:
            old_row.status = "corrected"
            old_row.superseded_by_id = row.id

        db.commit()
        return {
            "message": (
                f"✅ {employee_name} ki {attendance_date} ki attendance record hui — "
                f"Attendance: {attendance}, Driving: {driving}"
            ),
            "target_table": "attendance",
            "target_id": row.id,
        }
    except Exception as e:
        db.rollback()
        return f"Error: {str(e)}"
    finally:
        db.close()

# --- Sales Tools

@tool
def manage_customer(customer_name: str, phone: str = "", address: str = "", note: str = ""):
    """
    Create a new customer or update an existing customer's profile.

    Use this tool ONLY for customer profile information.

    Examples:
    "Sharma ji customer hain"
    => customer_name="Sharma ji"

    "Sharma ji ka phone number 9876543210 hai"
    => customer_name="Sharma ji", phone="9876543210"

    "Sharma ji ka address Bhiwani hai"
    => customer_name="Sharma ji", address="Bhiwani"

    "Sharma ji ka phone number badal kar 9999999999 kar do"
    => customer_name="Sharma ji", phone="9999999999"

    Rules:
    1. Customer exist nahi karta → new customer create karo.
    2. Customer exist karta hai → sirf explicitly provided fields update karo.
    3. Jo fields provide nahi hui hain unhe change mat karo.
    4. Customer ka naam required hai.
    5. Sales ya payment record karne ke liye is tool ka use mat karo.
    """
    db = SessionLocal()
    try:
        name = customer_name.strip()
        if not name:
            return "Error: Customer name required hai."
        customer = db.query(Customer).filter(
            Customer.name.ilike(name)
        ).first()
        if customer:
            updated_fields = []
            if phone:
                customer.phone = phone.strip()
                updated_fields.append("phone")
            if address:
                customer.address = address.strip()
                updated_fields.append("address")
            if note:
                # Customer model mein note field nahi hai,
                # isliye note ko abhi save nahi kar rahe.
                pass
            if updated_fields:
                db.commit()
                return {
                    "message": (
                        f"✅ {customer.name} ka customer profile update ho gaya. "
                        f"Updated: {', '.join(updated_fields)}"
                    ),
                    "target_table": "customers",
                    "target_id": customer.id,
                }
            return f"✅ {customer.name} ka customer record already exist karta hai."
        customer = Customer(name=name, phone=phone.strip() if phone else None, address=address.strip() if address else None)
        db.add(customer)
        db.flush()
        sync_movement_entity(db, name=customer.name, entity_type=MovementEntityType.CUSTOMER, linked_id=customer.id,)
        sync_person_role(db, name=customer.name, role="customer", linked_id=customer.id)
        db.commit()
        return {
            "message": f"✅ New customer '{customer.name}' create ho gaya.",
            "target_table": "customers",
            "target_id": customer.id,
        }
    except Exception as e:
        db.rollback()
        return f"Error: {str(e)}"
    finally:
        db.close()

@tool
def record_sale_transaction(
    customer_name: str, sale_date: str, amount: float = 0, item_name: str = "",
    unit: str = "", quantity: float = 0, rate: float = 0, driver_name: str = "",
    source: str = "", destination_name: str = "", supplier_name: str = "",
    bill_id: str = "", note: str = "",
    update_inventory: bool = True,
):
    """
    Record a sale transaction for a customer.

    Use this tool when:
    - customer ko maal/samaan becha gaya
    - customer ke naam par sale record karni ho
    - customer ko material deliver/supply kiya gaya as a sale

    This tool records the sale transaction only.
    It does NOT record customer payment and does NOT update CashLedger.

    Fields:
    - customer_name: customer name
    - sale_date: sale date in YYYY-MM-DD format
    - amount: total sale amount (can be negative for a return)
    - item_name: item/material sold
    - unit: unit of measurement
    - quantity: quantity sold (can be negative for a return)
    - rate: selling rate per unit
    - driver_name: driver name if mentioned
    - source: where the material came from, e.g. shop, gudam, bhata
    - destination_name: where delivery was made
    - supplier_name: supplier associated with the material, if explicitly mentioned
    - bill_id: bill/reference number if mentioned
    - note: additional sale details
    - update_inventory: True for a normal OUT sale (material was in
      storage before this sale — decreases stock). False for a
      Direct Sale (material went straight from supplier/site to
      customer, never entered storage — stock must NOT be touched).
      This is determined upstream by the Transaction Classifier,
      not guessed here.
    """
    db = SessionLocal()
    try:
        customer_name = customer_name.strip()
        supplier_name = supplier_name.strip() if supplier_name else ""
        item_name = item_name.strip() if item_name else ""
        unit = unit.strip() if unit else ""
        driver_name = driver_name.strip() if driver_name else ""
        source = source.strip() if source else ""
        destination_name = destination_name.strip() if destination_name else ""
        bill_id = bill_id.strip() if bill_id else ""
        note = note.strip() if note else ""

        # Customer identity
        customer = get_or_create_customer(customer_name, db)

        # Supplier is optional
        supplier = None
        if supplier_name:
            supplier = get_or_create_supplier(supplier_name, db)

        sale = SalesTransaction(
            customer_id=customer.id,
            supplier_id=supplier.id if supplier else None,
            item_name=item_name or None,
            unit=unit or None,
            quantity=quantity if quantity != 0 else None,
            rate=rate if rate > 0 else None,
            amount=amount if amount != 0 else None,
            driver_name=driver_name or None,
            source=source or None,
            destination_name=destination_name or None,
            bill_id=bill_id or None,
            sale_date=datetime.strptime(sale_date, "%Y-%m-%d").date(),
            note=note or None
        )
        db.add(sale)
        db.flush()

        # Sirf tab Inventory touch karo jab upstream ne explicitly
        # bola ho ki maal storage se nikla hai (normal OUT sale).
        # Direct Sale ke liye ye False aayega, inventory bilkul
        # touch nahi hogi. quantity != 0 taaki return (negative
        # quantity) bhi Inventory ko sahi se update kare.
        if update_inventory and source and quantity != 0:
            update_stock_history(
                db=db,
                location=source,
                item_name=item_name,
                unit=unit,
                quantity_change=-quantity,
                reason="sale" if quantity > 0 else "customer_return",
                related_party=customer_name,
                source_table="sales_transactions",
                source_id=sale.id,
                adjustment_date=sale.sale_date,
                note=note,
            )
            update_inventory_stock(
                db=db,
                location=source,
                item_name=item_name,
                unit=unit,
                quantity_change=-quantity,
            )

        db.commit()
        return {
            "message": (
                f"✅ Sale transaction record ho gayi.\n"
                f"👤 Customer: {customer_name}\n"
                f"📦 Item: {item_name or '-'}\n"
                f"🔢 Quantity: {quantity if quantity != 0 else '-'}\n"
                f"💰 Amount: ₹{amount if amount != 0 else '-'}"
            ),
            "target_table": "sales_transactions",
            "target_id": sale.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

@tool
def record_sale_payment(customer_name: str, amount: float, payment_date: str, bill_id: str = "", note: str = ""):
    """
    Record payment received from a customer.

    Use this tool when:
    - customer ne payment ki
    - customer se paisa receive hua
    - sale ke against payment received hui

    This tool:
    1. Creates a SalesPayment entry.
    2. Creates a CashLedger entry with direction="in".

    bill_id is optional and should be used when payment is against
    a specific bill.
    """
    db = SessionLocal()
    try:
        customer_name = customer_name.strip()
        bill_id = bill_id.strip() if bill_id else ""
        note = note.strip() if note else ""
        if amount is None or amount <= 0:
            return "Error: payment amount must be greater than 0."
        # Customer identity
        customer = get_or_create_customer(
            customer_name,
            db
        )
        payment_date_obj = datetime.strptime(
            payment_date,
            "%Y-%m-%d"
        ).date()
        # Sales payment
        payment = SalesPayment(
            customer_id=customer.id,
            bill_id=bill_id or None,
            amount=amount,
            payment_date=payment_date_obj,
            note=note or None
        )
        db.add(payment)
        db.flush()
        # Actual cash received
        add_cash_ledger_entry(
            db=db,
            entry_date=payment_date_obj,
            direction="in",
            amount=amount,
            category="sales_payment",
            source_table="sales_payments",
            source_id=payment.id,
            note=note
        )
        db.commit()
        return {
            "message": (
                f"✅ Sale payment record ho gayi.\n"
                f"👤 Customer: {customer_name}\n"
                f"💰 Received: ₹{amount}"
            ),
            "target_table": "sales_payments",
            "target_id": payment.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

# --- Supplier Tools

@tool
def manage_supplier(supplier_name: str, supplier_type: str = "", phone: str = "", address: str = "", note: str = ""):
    """
    Create a new supplier or update an existing supplier's profile.

    Use this tool ONLY for supplier profile information.

    Examples:
    "SBI bhata supplier hai"
    => supplier_name="SBI bhata", supplier_type="bhata"

    "SBI bhate ka phone number 9876543210 hai"
    => supplier_name="SBI bhata", phone="9876543210"

    "SBI bhate ka address Bhiwani hai"
    => supplier_name="SBI bhata", address="Bhiwani"

    "SBI bhata ka type bhata se thekedaar kar do"
    => supplier_name="SBI bhata", supplier_type="thekedaar"

    Rules:
    1. Supplier exist nahi karta → new supplier create karo.
    2. Supplier exist karta hai → sirf explicitly provided fields update karo.
    3. Jo fields provide nahi hui hain unhe change mat karo.
    4. Supplier ka naam required hai.
    5. Purchase ya payment record karne ke liye is tool ka use mat karo.
    """
    db = SessionLocal()
    try:
        name = supplier_name.strip()
        if not name:
            return "Error: Supplier name required hai."
        supplier = db.query(Supplier).filter(
            Supplier.name.ilike(name)
        ).first()
        if supplier:
            updated_fields = []
            if supplier_type:
                supplier.supplier_type = supplier_type.strip()
                updated_fields.append("supplier_type")
            if phone:
                supplier.phone = phone.strip()
                updated_fields.append("phone")
            if address:
                supplier.address = address.strip()
                updated_fields.append("address")
            if note:
                # Supplier model mein note field nahi hai,
                # isliye note ko abhi save nahi kar rahe.
                pass
            if updated_fields:
                db.commit()
                return {
                    "message": (
                        f"✅ {supplier.name} ka supplier profile update ho gaya. "
                        f"Updated: {', '.join(updated_fields)}"
                    ),
                    "target_table": "suppliers",
                    "target_id": supplier.id,
                }
            return f"✅ {supplier.name} ka supplier record already exist karta hai."
        supplier = Supplier(
            name=name,
            supplier_type=supplier_type.strip() if supplier_type else None,
            phone=phone.strip() if phone else None,
            address=address.strip() if address else None
        )
        db.add(supplier)
        db.flush()
        sync_movement_entity(db, name=supplier.name, entity_type=MovementEntityType.SUPPLIER, linked_id=supplier.id,)
        sync_person_role(db, name=supplier.name, role="supplier", linked_id=supplier.id)   
        db.commit()
        return {
            "message": f"✅ New supplier '{supplier.name}' create ho gaya.",
            "target_table": "suppliers",
            "target_id": supplier.id,
        }
    except Exception as e:
        db.rollback()
        return f"Error: {str(e)}"
    finally:
        db.close()

@tool
def record_supplier_transaction(supplier_name: str, transaction_date: str, amount: float = 0, item_name: str = "", quantity: float = 0, unit: str = "", rate: float = 0, driver_name: str = "", customer_name: str = "", destination_location: str = "", bill_id: str = "", note: str = ""):
    """
    Record a transaction/material received from a supplier.

    Use this tool when:
    - supplier se material aaya
    - supplier ne maal diya
    - supplier-side purchase/receipt record karna ho
    - supplier se directly customer ko material supply hua

    This tool records the transaction only.
    It does NOT record supplier payment and does NOT update CashLedger.

    Fields:
    - supplier_name: supplier/business name
    - transaction_date: YYYY-MM-DD
    - amount: total supplier-side transaction amount
    - item_name: material/item name
    - quantity: quantity received
    - unit: unit of measurement
    - rate: supplier rate per unit
    - driver_name: driver name if mentioned
    - customer_name: customer if material was directly supplied to a customer
    - bill_id: supplier bill/reference if mentioned
    - note: additional transaction details
    """
    db = SessionLocal()
    try:
        supplier_name = supplier_name.strip()
        customer_name = customer_name.strip() if customer_name else ""
        item_name = item_name.strip() if item_name else ""
        unit = unit.strip() if unit else ""
        driver_name = driver_name.strip() if driver_name else ""
        bill_id = bill_id.strip() if bill_id else ""
        note = note.strip() if note else ""
        # Supplier identity
        supplier = get_or_create_supplier(
            supplier_name,
            db
        )
        # Customer is optional
        customer = None
        if customer_name:
            customer = get_or_create_customer(
                customer_name,
                db
            )
        destination_location = (
            destination_location.strip()
            if destination_location
            else ""
        )
        tx = SupplierTransaction(
            supplier_id=supplier.id,
            customer_id=customer.id if customer else None,
            destination_location=destination_location or None,
            # != 0 (na ki > 0): Correction-reversal minus quantity/amount ke
            # saath isi tool ko chalata hai — tab bhi row aur inventory sahi bane.
            quantity=quantity if quantity != 0 else None,
            item_name=item_name or None,
            unit=unit or None,
            rate=rate if rate > 0 else None,
            amount=amount if amount != 0 else None,
            driver_name=driver_name or None,
            transaction_date=datetime.strptime(
                transaction_date,
                "%Y-%m-%d"
            ).date(),
            bill_id=bill_id or None,
            note=note or None
        )
        db.add(tx)
        db.flush()

        # Supplier ka maal inventory mein aaya hai
        if not customer_name and destination_location and quantity != 0:
            update_stock_history(
                db=db,
                location=destination_location,
                item_name=item_name,
                unit=unit,
                quantity_change=quantity,
                reason="supplier_in" if quantity > 0 else "supplier_return",
                related_party=supplier_name,
                source_table="supplier_transactions",
                source_id=tx.id,
                adjustment_date=tx.transaction_date,
                note=note,
            )

            update_inventory_stock(
                db=db,
                location=destination_location,
                item_name=item_name,
                unit=unit,
                quantity_change=quantity,
            )

        db.commit()
        return {
            "message": (
                f"✅ Supplier transaction record ho gayi.\n"
                f"🏢 Supplier: {supplier_name}\n"
                f"📦 Item: {item_name or '-'}\n"
                f"🔢 Quantity: {quantity if quantity > 0 else '-'}\n"
                f"💰 Amount: ₹{amount if amount > 0 else '-'}"
            ),
            "target_table": "supplier_transactions",
            "target_id": tx.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

@tool
def record_supplier_payment(supplier_name: str, amount: float, payment_date: str, bill_id: str = "", note: str = ""):
    """
    Record payment made to a supplier.

    Use this tool when:
    - supplier ko payment ki gayi
    - supplier ko paisa diya
    - supplier ke bill ke against payment ki gayi

    This tool:
    1. Creates a SupplierPayment entry.
    2. Creates a CashLedger entry with direction="out".

    bill_id is optional and should be used when payment is against
    a specific supplier bill.
    """

    db = SessionLocal()

    try:
        supplier_name = supplier_name.strip()
        bill_id = bill_id.strip() if bill_id else ""
        note = note.strip() if note else ""

        if amount is None or amount <= 0:
            return "Error: payment amount must be greater than 0."

        # Supplier identity
        supplier = get_or_create_supplier(
            supplier_name,
            db
        )

        payment_date_obj = datetime.strptime(
            payment_date,
            "%Y-%m-%d"
        ).date()

        # Supplier payment
        payment = SupplierPayment(
            supplier_id=supplier.id,
            bill_id=bill_id or None,
            amount=amount,
            payment_date=payment_date_obj,
            note=note or None
        )

        db.add(payment)
        db.flush()

        # Actual cash paid to supplier
        add_cash_ledger_entry(
            db=db,
            entry_date=payment_date_obj,
            direction="out",
            amount=amount,
            category="supplier_payment",
            source_table="supplier_payments",
            source_id=payment.id,
            note=note
        )

        db.commit()

        return {
            "message": (
                f"✅ Supplier payment record ho gayi.\n"
                f"🏢 Supplier: {supplier_name}\n"
                f"💸 Paid: ₹{amount}"
            ),
            "target_table": "supplier_payments",
            "target_id": payment.id,
        }

    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"

    finally:
        db.close()

# --- Inventory Tools

@tool
def record_adjustment(
    location: str,
    item_name: str,
    unit: str,
    quantity_change: float,
    reason: str = "",
    adjustment_date: str = "",
    note: str = "",
):
    """
    Record a manual stock adjustment.

    Use this tool for stock changes that are not caused by
    a supplier transaction, sale transaction, or material movement.

    Examples:
    - stock damaged
    - stock wasted
    - stock count correction
    - opening stock

    Positive quantity_change increases stock.
    Negative quantity_change decreases stock.

    This tool:
    1. Creates an Adjustment history entry.
    2. Updates current Inventory.
    3. Commits both changes together.
    """

    db = SessionLocal()

    try:
        location = location.strip()
        item_name = normalize_item(item_name)
        unit = unit.strip().lower()

        reason = reason.strip().lower() if reason else ""
        note = note.strip() if note else ""

        if not location:
            return "Error: location is required."

        if not item_name:
            return "Error: item name is required."

        if not unit:
            return "Error: unit is required."

        if quantity_change == 0:
            return "Error: quantity_change must not be zero."

        adjustment_date_obj = (
            datetime.strptime(
                adjustment_date,
                "%Y-%m-%d"
            ).date()
            if adjustment_date
            else date.today()
        )

        # 1. Create stock history
        adjustment = update_stock_history(
            db=db,
            location=location,
            item_name=item_name,
            unit=unit,
            quantity_change=quantity_change,
            reason=reason or None,
            related_party=None,
            source_table=None,
            source_id=None,
            adjustment_date=adjustment_date_obj,
            note=note or None,
        )

        # 2. Update current inventory
        update_inventory_stock(
            db=db,
            location=location,
            item_name=item_name,
            unit=unit,
            quantity_change=quantity_change,
        )

        # 3. Commit both changes together
        db.commit()

        return {
            "message": (
                f"✅ Stock adjustment record ho gaya.\n"
                f"📍 Location: {location}\n"
                f"📦 Item: {item_name}\n"
                f"🔢 Change: {quantity_change} {unit}\n"
                f"📝 Reason: {reason or '-'}"
            ),
            "target_table": "stock_adjustments",
            "target_id": adjustment.id,
        }

    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"

    finally:
        db.close()

# --- Expense Tools

@tool
def record_expense(category: str, amount: float, expense_date: str, description: str = "", note: str = ""):
    """
    Record a business expense.

    Use this tool when:
    - business ka kharcha hua (transport, bijli, tel, servicing, misc)
    - koi operational cost record karni ho jo kisi employee/supplier/
      customer se juda na ho

    Do NOT use this tool for:
    - salary/employee payment → record_employee_transaction
    - supplier payment → record_supplier_payment
    - property/deal purchase → record_purchase

    This tool:
    1. Creates an Expense entry.
    2. Does NOT record payment and does NOT update CashLedger —
       use record_expense_payment for that.

    Examples:
    "Diesel par 2000 rupaye kharch hue" 
    => category="transport", amount=2000, description="diesel"

    "Office ka bijli bill 1500 diya"
    => category="utility", amount=1500, description="bijli bill"

    "Generator ki servicing karayi, 600 ka"
    => category="maintenance", amount=600, description="generator servicing"
    """
    db = SessionLocal()
    try:
        category = category.strip().lower() if category else ""
        description = description.strip() if description else ""
        note = note.strip() if note else ""

        if amount is None or amount <= 0:
            return "Error: expense amount must be greater than 0."

        expense_date_obj = datetime.strptime(expense_date, "%Y-%m-%d").date()

        expense = Expense(
            category=category or None,
            description=description or None,
            amount=amount,
            expense_date=expense_date_obj,
            note=note or None,
        )
        db.add(expense)
        db.flush()
        db.commit()

        return {
            "message": (
                f"✅ Expense record ho gaya.\n"
                f"📂 Category: {category or '-'}\n"
                f"📝 Description: {description or '-'}\n"
                f"💰 Amount: ₹{amount}"
            ),
            "target_table": "expenses",
            "target_id": expense.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

@tool
def record_expense_payment(description: str, amount: float, payment_date: str, note: str = ""):
    """
    Record payment made against a business expense.

    Use this tool when:
    - expense ka paisa diya gaya (chahe turant ho ya baad mein/udhaar)

    This tool looks up the most recent matching Expense (by
    description) to link the payment. If no matching expense is
    found, the payment is still recorded standalone.

    This tool:
    1. Creates an ExpensePayment entry.
    2. Creates a CashLedger entry with direction="out".
    """
    db = SessionLocal()
    try:
        description = description.strip() if description else ""
        note = note.strip() if note else ""

        if amount is None or amount <= 0:
            return "Error: payment amount must be greater than 0."

        payment_date_obj = datetime.strptime(payment_date, "%Y-%m-%d").date()

        expense = None
        if description:
            expense = (
                db.query(Expense)
                .filter(Expense.description.ilike(f"%{description}%"))
                .order_by(desc(Expense.expense_date))
                .first()
            )

        payment = ExpensePayment(
            expense_id=expense.id if expense else None,
            amount=amount,
            payment_date=payment_date_obj,
            note=note or None,
        )
        db.add(payment)
        db.flush()

        add_cash_ledger_entry(
            db=db,
            entry_date=payment_date_obj,
            direction="out",
            amount=amount,
            category="expense_payment",
            source_table="expense_payments",
            source_id=payment.id,
            note=note,
        )

        db.commit()

        return {
            "message": (
                f"✅ Expense payment record ho gayi.\n"
                f"💸 Paid: ₹{amount}\n"
                f"🔗 Linked expense: {expense.description if expense else 'none found'}"
            ),
            "target_table": "expense_payments",
            "target_id": payment.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


# --- Purchase Tools (property/ghar khareedna, salvage ke liye)

@tool
def record_purchase(seller_name: str, purchase_date: str, total_amount: float = 0, description: str = "", location: str = "", seller_phone: str = "", note: str = ""):
    """
    Record a property/house purchase deal for salvage.

    Use this tool when:
    - poori property/ghar/plot todne ke liye khareeda gaya
    - koi negotiated deal/agreement finalize hui property ke liye

    Do NOT use this tool for:
    - regular material supply from a bhatta/supplier → record_supplier_transaction
    - a customer sale → record_sale_transaction

    This tool:
    1. Creates a Purchase entry.
    2. Does NOT record payment and does NOT update CashLedger —
       use record_purchase_payment for that.

    Examples:
    "Shyam se purana makan todne ki deal hui, 5 lakh mein"
    => seller_name="Shyam", total_amount=500000, description="purana makan todne ki deal"

    "Lela Ram se ghar todne ki deal hui, 3 lakh mein, ghar bus stand ke paas"
    => seller_name="Lela Ram", total_amount=300000, 
       description="ghar todne ki deal", location="bus stand ke paas"
    """
    db = SessionLocal()
    try:
        seller_name = seller_name.strip()
        description = description.strip() if description else ""
        location = location.strip() if location else ""
        seller_phone = seller_phone.strip() if seller_phone else ""
        note = note.strip() if note else ""

        if not seller_name:
            return "Error: seller name is required."

        purchase_date_obj = datetime.strptime(purchase_date, "%Y-%m-%d").date()

        purchase = Purchase(
            seller_name=seller_name,
            seller_phone=seller_phone or None,
            description=description or None,
            location=location or None,
            total_amount=total_amount if total_amount > 0 else None,
            purchase_date=purchase_date_obj,
            note=note or None,
        )
        db.add(purchase)
        db.flush()
        if purchase.seller_name:
            sync_person_role(db, name=purchase.seller_name, role="property_owner", linked_id=purchase.id)

        db.commit()

        return {
            "message": (
                f"✅ Purchase deal record ho gayi.\n"
                f"👤 Seller: {seller_name}\n"
                f"📝 Description: {description or '-'}\n"
                f"💰 Total: ₹{total_amount if total_amount > 0 else '-'}"
            ),
            "target_table": "purchases",
            "target_id": purchase.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

@tool
def record_purchase_payment(seller_name: str, amount: float, payment_date: str, note: str = ""):
    """
    Record a payment (advance or installment) made against a
    property purchase deal.

    Use this tool when:
    - purchase deal ke against advance/installment payment ki gayi

    This tool looks up the most recent matching Purchase (by
    seller_name) to link the payment. If no matching purchase is
    found, the payment is still recorded standalone.

    This tool:
    1. Creates a PurchasePayment entry.
    2. Creates a CashLedger entry with direction="out".

    Examples:
    "Shyam ko 1 lakh advance diya"
    => seller_name="Shyam", amount=100000
    """
    db = SessionLocal()
    try:
        seller_name = seller_name.strip()
        note = note.strip() if note else ""

        if amount is None or amount <= 0:
            return "Error: payment amount must be greater than 0."

        payment_date_obj = datetime.strptime(payment_date, "%Y-%m-%d").date()

        purchase = None
        if seller_name:
            purchase = (
                db.query(Purchase)
                .filter(Purchase.seller_name.ilike(f"%{seller_name}%"))
                .order_by(desc(Purchase.purchase_date))
                .first()
            )

        payment = PurchasePayment(
            purchase_id=purchase.id if purchase else None,
            amount=amount,
            payment_date=payment_date_obj,
            note=note or None,
        )
        db.add(payment)
        db.flush()

        add_cash_ledger_entry(
            db=db,
            entry_date=payment_date_obj,
            direction="out",
            amount=amount,
            category="purchase_payment",
            source_table="purchase_payments",
            source_id=payment.id,
            note=note,
        )

        db.commit()

        return {
            "message": (
                f"✅ Purchase payment record ho gayi.\n"
                f"👤 Seller: {seller_name}\n"
                f"💸 Paid: ₹{amount}\n"
                f"🔗 Linked purchase: {purchase.description if purchase else 'none found'}"
            ),
            "target_table": "purchase_payments",
            "target_id": payment.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


 # --- Activity Log Tools

# --- Activity Log Tools

@tool
def record_work_log(location_type: str, description: str, activity_date: str, location_name: str = "", labour_count: int = 0, note: str = ""):
    """
    Record work/activity performed at a location — labour, general
    work done — NOT a movement of goods and NOT tied to a specific
    named employee's payment.

    Use this tool when:
    - kisi site/gudam/shop pe kaam hua (todne ka kaam, malva nikala, etc.)
    - generic labour count mention hua (koi specific naam nahi)

    Do NOT use this tool for:
    - named employee's work/payment → record_employee_transaction
    - material moving between locations → record_material_movement

    Examples:
    "Haasi Gate pe aaj 5 labour the, todne ka kaam hua"
    => location_type="site", location_name="Haasi Gate", 
       description="todne ka kaam", labour_count=5

    "Ghar pr chhat utari aur 5 labour lagi thi"
    => location_type="site", description="chhat utari", labour_count=5
    """
    db = SessionLocal()
    try:
        location_type = location_type.strip().lower()
        location_name = location_name.strip() if location_name else ""
        description = description.strip()
        note = note.strip() if note else ""

        if not location_type:
            return "Error: location_type is required."
        if not description:
            return "Error: description is required."

        activity_date_obj = datetime.strptime(activity_date, "%Y-%m-%d").date()

        log = WorkLog(
            location_type=location_type,
            location_name=location_name or None,
            description=description,
            labour_count=labour_count if labour_count > 0 else None,
            activity_date=activity_date_obj,
            note=note or None,
        )
        db.add(log)
        db.flush()
        db.commit()

        return {
            "message": (
                f"✅ Work log record ho gaya.\n"
                f"📍 Location: {location_name or location_type}\n"
                f"📝 Work: {description}\n"
                f"👷 Labour: {labour_count if labour_count > 0 else '-'}"
            ),
            "target_table": "work_logs",
            "target_id": log.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

@tool
def record_material_movement(
    source_type: str, source_name: str, destination_type: str, destination_name: str,
    item_name: str, quantity: float, movement_date: str,
    unit: str = "", movement_type: str = "", movement_reason: str = "", note: str = "",
):
    """
    Record material moving between two internal locations
    (site/gudam/shop) — NO external supplier, NO customer involved.

    Use this tool when:
    - item ek internal location se doosri internal location gaya
      (jaise site se gudam, ya gudam se shop)
    - Transaction Classifier ne is movement ko INTERNAL_MOVEMENT
      declare kiya ho

    Do NOT use this tool for:
    - supplier se maal aaya → record_supplier_transaction
    - customer ko maal gaya → record_sale_transaction
    - direct sale (supplier/site → customer, storage touch nahi hua)
      → record_supplier_transaction + record_sale_transaction dono

    This tool:
    1. Creates a MaterialMovement history entry.
    2. Updates Inventory at BOTH ends — decreases at source,
       increases at destination (both sides are tracked storage).

    Examples:
    "Gudam se site pe 5 bore cement bheja"
    => source_type="gudam", source_name="gudam", 
       destination_type="site", destination_name="site",
       item_name="cement", quantity=5, unit="bore"

    "Site A se 200 eent gudam gai"
    => source_type="site", source_name="Site A",
       destination_type="gudam", destination_name="gudam",
       item_name="eent", quantity=200
    """
    db = SessionLocal()
    try:
        source_type = source_type.strip().lower()
        source_name = source_name.strip()
        destination_type = destination_type.strip().lower()
        destination_name = destination_name.strip()
        item_name = normalize_item(item_name)
        unit = unit.strip().lower() if unit else ""
        movement_type = movement_type.strip().lower() if movement_type else ""
        movement_reason = movement_reason.strip().lower() if movement_reason else ""
        note = note.strip() if note else ""

        if not source_name or not destination_name:
            return "Error: both source_name and destination_name are required."
        if not item_name:
            return "Error: item_name is required."
        if quantity is None or quantity == 0:
            return "Error: quantity must not be zero."

        movement_date_obj = datetime.strptime(movement_date, "%Y-%m-%d").date()

        movement = MaterialMovement(
            item_name=item_name,
            quantity=quantity,
            unit=unit or None,
            source_type=source_type or None,
            source_name=source_name,
            destination_type=destination_type or None,
            destination_name=destination_name,
            movement_type=movement_type or None,
            movement_reason=movement_reason or None,
            movement_date=movement_date_obj,
            note=note or None,
        )
        db.add(movement)
        db.flush()

        # Source se ghatao
        update_stock_history(
            db=db,
            location=source_name,
            item_name=item_name,
            unit=unit,
            quantity_change=-quantity,
            reason="internal_movement_out",
            related_party=None,
            source_table="material_movements",
            source_id=movement.id,
            adjustment_date=movement_date_obj,
            note=note,
        )
        update_inventory_stock(
            db=db, location=source_name, item_name=item_name,
            unit=unit, quantity_change=-quantity,
        )

        # Destination mein badhao
        update_stock_history(
            db=db,
            location=destination_name,
            item_name=item_name,
            unit=unit,
            quantity_change=quantity,
            reason="internal_movement_in",
            related_party=None,
            source_table="material_movements",
            source_id=movement.id,
            adjustment_date=movement_date_obj,
            note=note,
        )
        update_inventory_stock(
            db=db, location=destination_name, item_name=item_name,
            unit=unit, quantity_change=quantity,
        )

        db.commit()
        return {
            "message": (
                f"✅ Material movement record ho gaya.\n"
                f"📦 Item: {item_name}, Qty: {quantity} {unit or ''}\n"
                f"➡️ {source_name} → {destination_name}"
            ),
            "target_table": "material_movements",
            "target_id": movement.id,
        }
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


# --- Opening Balance Tool (Reporting Phase)

def _earliest_entry_date(db, party_type, party_id):
    """Is khaate ki sabse pehli (active) entry ki date — opening hamesha usse pehle/usi din ka."""
    from reports import queries as Q
    dates = []
    if party_type == "employee":
        dates += [t.transaction_date for t in Q.employee_transactions(db, employee_id=party_id)]
    elif party_type == "customer":
        dates += [t.sale_date for t in Q.sales_transactions(db, customer_id=party_id)]
        dates += [p.payment_date for p in Q.sales_payments(db, customer_id=party_id)]
    elif party_type == "supplier":
        dates += [t.transaction_date for t in Q.supplier_transactions(db, supplier_id=party_id)]
        dates += [p.payment_date for p in Q.supplier_payments(db, supplier_id=party_id)]
    elif party_type == "cash":
        dates += [row.entry_date for row, _ in Q.cash_entries(db)]
    dates = [d for d in dates if d is not None]
    return min(dates) if dates else None


@tool
def record_opening_balance(party_type: str, amount: float, direction: str = "", party_name: str = "",
                           as_of_date: str = "", note: str = ""):
    """
    Record an OLD balance from BEFORE Hisab-Kitab started — a one-time
    starting figure for a party, or the starting cash in hand.

    party_type: employee | customer | supplier | cash
    direction : lena  → humein us party se lena hai
                dena  → humein us party ko dena hai
                (cash ke liye direction ki zaroorat nahi)

    Examples:
    "Suresh Traders pe pehle ka 6000 udhaar hai"
        => party_type="customer", party_name="Suresh Traders", amount=6000, direction="lena"
    "Jai Bhatte ko pichla 5000 dena baaki hai"
        => party_type="supplier", party_name="Jai Bhatta", amount=5000, direction="dena"
    "Ram ne pehle 2000 advance le rakha hai"
        => party_type="employee", party_name="Ram", amount=2000, direction="lena"
    "Shuru mein galle mein 40000 cash tha"
        => party_type="cash", amount=40000

    Rules:
    1. Ek khaate ka ek hi opening balance. Pehle se hai to naya nahi banta —
       badalna ho to Correction se ("Suresh ka opening balance galat hai").
    2. Opening hamesha us khaate ki pehli entry se pehle (ya usi din) ka hota hai.
       Date na di ho, ya pehli entry ke baad ki ho, to pehli entry ki date le li jaati hai.
    3. Ye CashLedger mein entry NAHI banata — ye purana baaki hai, aaj ka len-den nahi.
    """
    from helpers import mark_months_dirty
    db = SessionLocal()
    try:
        pt = (party_type or "").strip().lower()
        if pt not in ("employee", "customer", "supplier", "cash"):
            return "Error: party_type employee, customer, supplier ya cash hona chahiye."
        if amount is None or amount <= 0:
            return "Error: amount 0 se zyada hona chahiye."
        direction = (direction or "").strip().lower()
        if pt == "cash":
            direction = "cash"
        elif direction not in ("lena", "dena"):
            return "Error: direction 'lena' ya 'dena' hona chahiye."

        party_id, shown = 0, "Cash (galla)"
        if pt != "cash":
            name = (party_name or "").strip()
            if not name:
                return "Error: party ka naam chahiye."
            if pt == "employee":
                party = get_or_create_employee(name, db)
            elif pt == "customer":
                party = get_or_create_customer(name, db)
            else:
                party = get_or_create_supplier(name, db)
            db.flush()
            party_id, shown = party.id, party.name

        existing = (db.query(OpeningBalance)
                    .filter(OpeningBalance.ledger_type == pt, OpeningBalance.ledger_id == party_id,
                            OpeningBalance.status == "active", OpeningBalance.reversal_of_id.is_(None))
                    .first())
        if existing is not None:
            db.rollback()
            return (f"ℹ️ {shown} ka purana baaki pehle se ₹{existing.amount:,.0f} "
                    f"({existing.direction}, {existing.as_of_date}) likha hai — dobara nahi likha. "
                    f"Badalna ho to correction karo, jaise: '{shown} ka opening balance galat hai'.")

        today = date.today()
        try:
            as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date() if as_of_date else today
        except ValueError:
            as_of = today
        earliest = _earliest_entry_date(db, pt, party_id)
        if earliest is not None and earliest < as_of:
            as_of = earliest

        row = OpeningBalance(ledger_type=pt, ledger_id=party_id, amount=amount, direction=direction,
                             as_of_date=as_of, note=(note or "").strip() or None)
        db.add(row)
        db.flush()
        mark_months_dirty(db, as_of)          # is mahine se aage ki closing dobara banegi
        db.commit()

        if pt == "cash":
            msg = f"✅ Shuru ka cash ₹{amount:,.0f} ({as_of}) record ho gaya."
        else:
            word = "lena" if direction == "lena" else "dena"
            msg = f"✅ {shown} ka purana baaki ₹{amount:,.0f} {word} ({as_of}) record ho gaya."
        return {"message": msg, "target_table": "opening_balances", "target_id": row.id}
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


# -- Family Tools

@tool
def record_family_transaction(member_name: str, transaction_type: str, amount: float, transaction_date: str = "",
                              purpose: str = "", relation: str = "", note: str = ""):
    """
    Record money between the BUSINESS galla and a FAMILY member (ghar ke log).
    Ye lena-dena / udhaar nahi hai — sirf family kharcha ka hisab.

    transaction_type:
    - kharcha → business ke galle se paisa GHAR gaya (family member ne liya / ghar ke liye nikala) — cash OUT
    - jama    → family member ne business ke galle mein paisa DAALA / wapas kiya — cash IN

    Examples:
    "Papa ne ghar ke liye 5000 liye"        => member_name="Papa", transaction_type="kharcha", amount=5000, purpose="ghar"
    "Bhai ki fees ke 12000 diye"            => member_name="Bhai", transaction_type="kharcha", amount=12000, purpose="fees"
    "Mummy ne galle mein 3000 daale"        => member_name="Mummy", transaction_type="jama", amount=3000
    "Rohit (bhai) ko 2000 diye"             => member_name="Rohit", relation="bhai", transaction_type="kharcha", amount=2000

    Rules:
    1. Galle ke hisaab se: galle se gaya = kharcha, galle mein aaya = jama.
       "X ne liye" = X ne galle se liye = kharcha.
    2. Date nahi hai to aaj ki date (YYYY-MM-DD).
    3. CashLedger mein entry banti hai (kharcha → OUT, jama → IN).
    """
    db = SessionLocal()
    try:
        from helpers import get_or_create_family_member
        tt = (transaction_type or "").strip().lower()
        tt = {"diya": "kharcha", "liya": "jama"}.get(tt, tt)     # purane naam bhi chalein
        if tt not in ("kharcha", "jama"):
            return "Error: transaction_type 'kharcha' ya 'jama' hona chahiye."
        if amount is None or amount <= 0:
            return "Error: amount 0 se zyada hona chahiye."
        name = (member_name or "").strip()
        if not name:
            return "Error: family member ka naam chahiye."
        date_obj = datetime.strptime(transaction_date, "%Y-%m-%d").date() if transaction_date else date.today()

        member = get_or_create_family_member(name, db, relation=relation or "")
        tx = FamilyTransaction(member_id=member.id, transaction_type=tt, amount=amount,
                               transaction_date=date_obj, purpose=(purpose or "").strip() or None,
                               note=(note or "").strip() or None)
        db.add(tx)
        db.flush()
        add_cash_ledger_entry(db=db, entry_date=date_obj, direction="out" if tt == "kharcha" else "in",
                              amount=amount, category="family", source_table="family_transactions",
                              source_id=tx.id, note=purpose or note or "")
        db.commit()
        if tt == "kharcha":
            msg = (f"✅ {member.name} ko ₹{amount:,.0f} family kharcha record ho gaya"
                   + (f" ({purpose})" if purpose else "") + ".\n💰 Galle se ₹{:,.0f} cash OUT.".format(amount))
        else:
            msg = f"✅ {member.name} se ₹{amount:,.0f} galle mein aaye — record ho gaya.\n💰 Cash IN ₹{amount:,.0f}."
        return {"message": msg, "target_table": "family_transactions", "target_id": tx.id}
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()
