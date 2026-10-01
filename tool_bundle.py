from enum import Enum

from schemas import PersonRole, ToolName


class ToolBundle(str, Enum):
    EMPLOYEE = "employee"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    PURCHASE = "purchase"
    EXPENSE = "expense"
    ACTIVITY = "activity"


TOOL_BUNDLES = {
    ToolBundle.EMPLOYEE: [
        ToolName.MANAGE_EMPLOYEE,
        ToolName.RECORD_EMPLOYEE_TRANSACTION,
        ToolName.RECORD_ATTENDANCE,
    ],
    ToolBundle.SUPPLIER: [
        ToolName.RECORD_SUPPLIER_TRANSACTION,
    ],
    ToolBundle.CUSTOMER: [
        ToolName.RECORD_DELIVERY,
        ToolName.RECORD_STOCK_IN,
        ToolName.RECORD_GUDAM_SALE,
        ToolName.RECORD_SHOP_SALE,
        ToolName.RECORD_SALE_PAYMENT,
    ],
    ToolBundle.PURCHASE: [
        ToolName.RECORD_PURCHASE,
        ToolName.RECORD_PURCHASE_PAYMENT,
    ],
    ToolBundle.EXPENSE: [
        ToolName.RECORD_EXPENSE,
    ],
    ToolBundle.ACTIVITY: [
        ToolName.RECORD_ACTIVITY,
    ],
}


ROLE_TO_BUNDLE = {
    PersonRole.EMPLOYEE: ToolBundle.EMPLOYEE,
    PersonRole.SUPPLIER: ToolBundle.SUPPLIER,
    PersonRole.CUSTOMER: ToolBundle.CUSTOMER,
    PersonRole.SELLER: ToolBundle.PURCHASE,
}