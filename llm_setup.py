from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()
from tools import (
    manage_employee, record_employee_transaction, record_attendance,
    manage_customer, record_sale_transaction, record_sale_payment,
    manage_supplier, record_supplier_transaction, record_supplier_payment,
    record_adjustment, record_work_log, record_material_movement,
    record_expense, record_expense_payment,
    record_purchase, record_purchase_payment,
    record_opening_balance,
    record_family_transaction,
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

TOOLS_MAP = {
    "manage_employee": manage_employee,
    "record_employee_transaction": record_employee_transaction,
    "record_attendance": record_attendance,

    "manage_customer": manage_customer,
    "record_sale_transaction": record_sale_transaction,
    "record_sale_payment": record_sale_payment,

    "manage_supplier": manage_supplier,
    "record_supplier_transaction": record_supplier_transaction,
    "record_supplier_payment": record_supplier_payment,

    "record_adjustment": record_adjustment,
    "record_work_log": record_work_log,
    "record_material_movement": record_material_movement,

    "record_expense": record_expense,
    "record_expense_payment": record_expense_payment,

    "record_purchase": record_purchase,
    "record_purchase_payment": record_purchase_payment,

    "record_opening_balance": record_opening_balance,

    "record_family_transaction": record_family_transaction,
}

llm_with_tools = llm.bind_tools(list(TOOLS_MAP.values()))


