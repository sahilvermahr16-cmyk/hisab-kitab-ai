from datetime import date
from enum import Enum
from pydantic import BaseModel, Field
from schemas import ToolName
from tool_argument_common import ArgumentField

# Global Enums
class PaymentMethod(str, Enum):
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CARD = "card"
    NET_BANKING = "net_banking"

class PaymentProvider(str, Enum):
    GOOGLE_PAY = "google_pay"
    PHONEPE = "phonepe"
    PAYTM = "paytm"
    BHIM = "bhim"
    SBI = "sbi"
    HDFC = "hdfc"
    ICICI = "icici"
    PNB = "pnb"
    AXIS = "axis"
    VISA = "visa"
    MASTERCARD = "mastercard"
    RUPAY = "rupay"

class InventoryUnit(str, Enum):
    PIECE = "piece"
    KG = "kg"
    TON = "ton"
    BAG = "bag"
    TROLLEY = "trolley"
    TRIP = "trip"
    LITRE = "litre"
    TIN = "tin"
    SQFT = "sqft"


# Employee Bundle
class EmployeeTransactionType(str, Enum):
    WORK = "work"
    PAYMENT = "payment"

class AttendanceStatus(str, Enum):
    PRESENT = "P"
    HALF = "half"
    ABSENT = "absent"

class RecordEmployeeTransactionArgs(BaseModel):
    employee_name: str | None = Field(default=None, description="Employee name.")
    transaction_type: EmployeeTransactionType | None = Field(default=None, description="Employee transaction type. Allowed values: work (employee completed work), payment (money paid to employee).")
    amount: float | None = Field(default=None, ge=0, description="Transaction amount in rupees.")
    transaction_date: str | None = Field(
        default=None,
        description="Transaction date in YYYY-MM-DD format. Resolve relative dates (today, yesterday, tomorrow, kal, parso) into an actual date string. Leave null if no date is mentioned."
    )
    payment_method: str | None = Field(
        default=None,
        description="Payment method if explicitly mentioned."
    )
    payment_provider: str | None = Field(
        default=None,
        description="Payment provider if explicitly mentioned."
    )
    note: str | None = Field(
        default=None,
        description="Additional information that does not belong to any other field."
    )

class RecordAttendanceArgs(BaseModel):
    employee_name: str | None = Field(default=None, description="Employee name.")
    attendance: AttendanceStatus | None = Field(default=None, description="Attendance status.")
    driving: AttendanceStatus | None = Field(default=None, description="Driving status.")
    attendance_date: date | None = Field(default=None, description="Attendance date. Resolve relative dates (today, yesterday, tomorrow, kal, parso) into an actual date. Leave null if no date is mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

class ManageEmployeeArgs(BaseModel):
    employee_name: str | None = Field(default=None, description="Employee name.")
    role: str | None = Field(default=None, description="Employee role if explicitly mentioned.")
    phone: str | None = Field(default=None, description="Employee phone number if explicitly mentioned.")
    address: str | None = Field(default=None, description="Employee address if explicitly mentioned.")
    note: str | None = Field(default=None, description="Additional employee profile information.")

EMPLOYEE_VALIDATION_RULES = {
    ToolName.RECORD_EMPLOYEE_TRANSACTION: {
        "mandatory_fields": [
            ArgumentField.EMPLOYEE_NAME,
            ArgumentField.TRANSACTION_TYPE,
            ArgumentField.AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.TRANSACTION_DATE,
            ArgumentField.PAYMENT_METHOD,
            ArgumentField.PAYMENT_PROVIDER,
            ArgumentField.NOTE,
        ],
    },
    ToolName.RECORD_ATTENDANCE: {
        "mandatory_fields": [
            ArgumentField.EMPLOYEE_NAME,
        ],
        "optional_fields": [
            ArgumentField.ATTENDANCE,
            ArgumentField.DRIVING,
            ArgumentField.ATTENDANCE_DATE,
            ArgumentField.NOTE,
        ],
    },
    ToolName.MANAGE_EMPLOYEE: {
        "mandatory_fields": [
            ArgumentField.EMPLOYEE_NAME,
        ],
        "optional_fields": [
            ArgumentField.ROLE,
            ArgumentField.PHONE,
            ArgumentField.ADDRESS,
            ArgumentField.NOTE,
        ],
    },
}


# Customer / Sales Bundle

class ManageCustomerArgs(BaseModel):
    customer_name: str | None = Field(
        default=None,
        description="Customer name."
    )
    phone: str | None = Field(
        default=None,
        description="Customer phone number if explicitly mentioned."
    )
    address: str | None = Field(
        default=None,
        description="Customer address if explicitly mentioned."
    )

class RecordSaleTransactionArgs(BaseModel):
    customer_name: str | None = Field(
        default=None,
        description="Customer name."
    )
    sale_date: date | None = Field(
        default=None,
        description="Sale date. Resolve relative dates like today, yesterday, tomorrow, kal, parso into an actual date. Leave null if not mentioned."
    )
    amount: float | None = Field(
        default=None,
        gt=0,
        description="Total sale amount."
    )
    item_name: str | None = Field(
        default=None,
        description="Item or material sold."
    )
    unit: InventoryUnit | None = Field(
        default=None,
        description="Unit of the sold quantity."
    )
    quantity: float | None = Field(
        default=None,
        gt=0,
        description="Quantity sold."
    )
    rate: float | None = Field(
        default=None,
        gt=0,
        description="Selling rate per unit."
    )
    driver_name: str | None = Field(
        default=None,
        description="Driver name if explicitly mentioned."
    )
    source: str | None = Field(
        default=None,
        description="Source from where the material was supplied. Examples: shop, gudam, bhata name."
    )
    destination_name: str | None = Field(
        default=None,
        description="Destination or delivery location if explicitly mentioned."
    )
    supplier_name: str | None = Field(
        default=None,
        description="Supplier or bhata name if explicitly mentioned."
    )
    bill_id: str | None = Field(
        default=None,
        description="Bill or reference number if explicitly mentioned."
    )
    note: str | None = Field(
        default=None,
        description="Additional sale information that does not belong to another field."
    )
    update_inventory: bool | None = Field(default=None, description="Whether this sale should decrease stock — determined upstream by the Transaction Classifier, not extracted from wording.")

class RecordSalePaymentArgs(BaseModel):
    customer_name: str | None = Field(default=None, description="Customer name.")
    amount: float | None = Field(default=None, gt=0, description="Amount actually received from the customer.")
    payment_date: date | None = Field(default=None, description="Payment date. Resolve relative dates like today, yesterday, tomorrow, kal, parso into an actual date. Leave null if not mentioned.")
    bill_id: str | None = Field(default=None, description="Bill or reference number if payment is against a specific bill.")
    note: str | None = Field(default=None, description="Additional payment information that does not belong to another field.")

SALES_VALIDATION_RULES = {
    ToolName.MANAGE_CUSTOMER: {
        "mandatory_fields": [
            ArgumentField.CUSTOMER_NAME,
        ],
        "optional_fields": [
            ArgumentField.PHONE,
            ArgumentField.ADDRESS,
        ],
    },
    ToolName.RECORD_SALE_TRANSACTION: {
        "mandatory_fields": [
            ArgumentField.CUSTOMER_NAME,
        ],
        "optional_fields": [
            ArgumentField.SALE_DATE,
            ArgumentField.AMOUNT,
            ArgumentField.ITEM_NAME,
            ArgumentField.UNIT,
            ArgumentField.QUANTITY,
            ArgumentField.RATE,
            ArgumentField.DRIVER_NAME,
            ArgumentField.SOURCE,
            ArgumentField.DESTINATION_NAME,
            ArgumentField.SUPPLIER_NAME,
            ArgumentField.BILL_ID,
            ArgumentField.NOTE,
        ],
    },
    ToolName.RECORD_SALE_PAYMENT: {
        "mandatory_fields": [
            ArgumentField.CUSTOMER_NAME,
            ArgumentField.AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.PAYMENT_DATE,
            ArgumentField.BILL_ID,
            ArgumentField.NOTE,
        ],
    },
}


# Supplier Bundle

class ManageSupplierArgs(BaseModel):
    supplier_name: str | None = Field(
        default=None,
        description="Supplier or bhata name."
    )
    supplier_type: str | None = Field(
        default=None,
        description="Supplier type if explicitly mentioned. Examples: thekedar, timber, hardware."
    )
    phone: str | None = Field(
        default=None,
        description="Supplier phone number if explicitly mentioned."
    )
    address: str | None = Field(
        default=None,
        description="Supplier address if explicitly mentioned."
    )

class RecordSupplierTransactionArgs(BaseModel):
    supplier_name: str | None = Field(
        default=None,
        description="Supplier or bhata name."
    )
    transaction_date: date | None = Field(
        default=None,
        description="Transaction date. Resolve relative dates like today, yesterday, tomorrow, kal, parso into an actual date. Leave null if not mentioned."
    )
    amount: float | None = Field(
        default=None,
        gt=0,
        description="Total supplier-side transaction amount."
    )
    item_name: str | None = Field(
        default=None,
        description="Material or item received from the supplier."
    )
    quantity: float | None = Field(
        default=None,
        gt=0,
        description="Quantity of material received."
    )
    unit: InventoryUnit | None = Field(
        default=None,
        description="Unit of the received quantity."
    )
    rate: float | None = Field(
        default=None,
        gt=0,
        description="Supplier-side rate per unit."
    )
    driver_name: str | None = Field(
        default=None,
        description="Driver name if explicitly mentioned."
    )
    destination_location: str | None = Field(
        default=None,
        description="Location where the supplier material is received or kept when it is not directly supplied to a customer."
    )
    customer_name: str | None = Field(
        default=None,
        description="Customer name if the material was directly supplied to that customer."
    )
    bill_id: str | None = Field(
        default=None,
        description="Supplier bill or reference number if explicitly mentioned."
    )
    note: str | None = Field(
        default=None,
        description="Additional supplier transaction information."
    )

class RecordSupplierPaymentArgs(BaseModel):
    supplier_name: str | None = Field(
        default=None,
        description="Supplier or bhata name."
    )
    amount: float | None = Field(
        default=None,
        gt=0,
        description="Amount actually paid to the supplier."
    )
    payment_date: date | None = Field(
        default=None,
        description="Payment date. Resolve relative dates like today, yesterday, tomorrow, kal, parso into an actual date. Leave null if not mentioned."
    )
    bill_id: str | None = Field(
        default=None,
        description="Bill or reference number if payment is against a specific bill."
    )
    note: str | None = Field(
        default=None,
        description="Additional supplier payment information."
    )

SUPPLIER_VALIDATION_RULES = {
    ToolName.MANAGE_SUPPLIER: {
        "mandatory_fields": [
            ArgumentField.SUPPLIER_NAME,
        ],
        "optional_fields": [
            ArgumentField.SUPPLIER_TYPE,
            ArgumentField.PHONE,
            ArgumentField.ADDRESS,
        ],
    },
    ToolName.RECORD_SUPPLIER_TRANSACTION: {
        "mandatory_fields": [
            ArgumentField.SUPPLIER_NAME,
        ],
        "optional_fields": [
            ArgumentField.TRANSACTION_DATE,
            ArgumentField.AMOUNT,
            ArgumentField.ITEM_NAME,
            ArgumentField.QUANTITY,
            ArgumentField.UNIT,
            ArgumentField.RATE,
            ArgumentField.DRIVER_NAME,
            ArgumentField.DESTINATION_LOCATION,
            ArgumentField.CUSTOMER_NAME,
            ArgumentField.BILL_ID,
            ArgumentField.NOTE,
        ],
    },
    ToolName.RECORD_SUPPLIER_PAYMENT: {
        "mandatory_fields": [
            ArgumentField.SUPPLIER_NAME,
            ArgumentField.AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.PAYMENT_DATE,
            ArgumentField.BILL_ID,
            ArgumentField.NOTE,
        ],
    },
}


# Purchase Tools
class RecordPurchaseArgs(BaseModel):
    seller_name: str | None = Field(default=None, description="Seller name.")
    total_amount: float | None = Field(default=None, gt=0, description="Total purchase amount.")
    purchase_date: date | None = Field(default=None, description="Purchase date. Resolve relative dates like today, yesterday, kal, parso into an actual date. Leave null if not mentioned.")
    description: str | None = Field(default=None, description="Description of the purchased property or material.")
    location: str | None = Field(default=None, description="Purchase location or property location.")
    seller_phone: str | None = Field(default=None, description="Seller phone number if explicitly mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

PURCHASE_VALIDATION_RULES = {
    ToolName.RECORD_PURCHASE: {
        "mandatory_fields": [
            ArgumentField.SELLER_NAME,
            ArgumentField.TOTAL_AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.PURCHASE_DATE,
            ArgumentField.DESCRIPTION,
            ArgumentField.LOCATION,
            ArgumentField.SELLER_PHONE,
            ArgumentField.NOTE,
        ],
    },
}

class RecordPurchasePaymentArgs(BaseModel):
    seller_name: str | None = Field(default=None, description="Seller name whose pending purchase payment is being made.")
    amount: float | None = Field(default=None, gt=0, description="Payment amount given to the seller.")
    payment_date: date | None = Field(default=None, description="Payment date. Resolve relative dates like today, yesterday, kal, parso into an actual date. Leave null if not mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

PURCHASE_PAYMENT_VALIDATION_RULES = {
    ToolName.RECORD_PURCHASE_PAYMENT: {
        "mandatory_fields": [
            ArgumentField.SELLER_NAME,
            ArgumentField.AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.PAYMENT_DATE,
            ArgumentField.NOTE,
        ],
    },
}



# Expense Tools
class ExpenseCategory(str, Enum):
    FUEL = "fuel"
    REPAIR = "repair"
    RENT = "rent"
    SALARY = "salary"
    MISC = "misc"

class RecordExpenseArgs(BaseModel):
    category: ExpenseCategory | None = Field(default=None, description="Expense category. Allowed values: fuel, repair, rent, salary, misc.")
    description: str | None = Field(default=None, description="Expense description. Examples: tractor diesel, machine repair, office rent.")
    amount: float | None = Field(default=None, gt=0, description="Expense amount.")
    expense_date: date | None = Field(default=None, description="Expense date...")
    payment_method: PaymentMethod | None = Field(default=None, description="Payment method if explicitly mentioned. Allowed values: cash, upi, bank_transfer, cheque, card, net_banking.")
    payment_provider: PaymentProvider | None = Field(default=None, description="Payment provider if explicitly mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

EXPENSE_VALIDATION_RULES = {
    ToolName.RECORD_EXPENSE: {
        "mandatory_fields": [
            ArgumentField.CATEGORY,
            ArgumentField.DESCRIPTION,
            ArgumentField.AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.TRANSACTION_DATE,
            ArgumentField.PAYMENT_METHOD,
            ArgumentField.PAYMENT_PROVIDER,
            ArgumentField.NOTE,
        ],
    },
}

class RecordExpensePaymentArgs(BaseModel):
    description: str | None = Field(default=None, description="Description used to match this payment to the correct expense.")
    amount: float | None = Field(default=None, gt=0, description="Payment amount.")
    payment_date: date | None = Field(default=None, description="Payment date. Resolve relative dates like today, yesterday, kal, parso into an actual date. Leave null if not mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

EXPENSE_PAYMENT_VALIDATION_RULES = {
    ToolName.RECORD_EXPENSE_PAYMENT: {
        "mandatory_fields": [
            ArgumentField.DESCRIPTION,
            ArgumentField.AMOUNT,
        ],
        "optional_fields": [
            ArgumentField.PAYMENT_DATE,
            ArgumentField.NOTE,
        ],
    },
}


# Work Log Tool
class WorkLocationType(str, Enum):
    SITE = "site"
    GUDAM = "gudam"
    SHOP = "shop"

class RecordWorkLogArgs(BaseModel):
    location_type: WorkLocationType | None = Field(default=None, description="Location type. Allowed values: site, gudam, shop.")
    location_name: str | None = Field(default=None, description="Specific location name if mentioned.")
    description: str | None = Field(default=None, description="What work was done.")
    labour_count: int | None = Field(default=None, gt=0, description="Number of workers involved, if mentioned.")
    activity_date: date | None = Field(default=None, description="Activity date. Resolve relative dates like today, yesterday, kal, parso into an actual date. Leave null if not mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

WORK_LOG_VALIDATION_RULES = {
    ToolName.RECORD_WORK_LOG: {
        "mandatory_fields": [
            ArgumentField.LOCATION_TYPE,
            ArgumentField.DESCRIPTION,
        ],
        "optional_fields": [
            ArgumentField.LOCATION_NAME,
            ArgumentField.ACTIVITY_DATE,
            ArgumentField.NOTE,
        ],
    },
}

# Material Movement Tool
class RecordMaterialMovementArgs(BaseModel):
    source_type: str | None = Field(default=None, description="Source location type (site/gudam/shop).")
    source_name: str | None = Field(default=None, description="Source location name.")
    destination_type: str | None = Field(default=None, description="Destination location type (site/gudam/shop).")
    destination_name: str | None = Field(default=None, description="Destination location name.")
    item_name: str | None = Field(default=None, description="Item being moved.")
    quantity: float | None = Field(default=None, gt=0, description="Quantity moved.")
    unit: InventoryUnit | None = Field(default=None, description="Unit of the moved quantity.")
    movement_type: str | None = Field(default=None, description="Kind of movement, e.g. transfer, dump, if the wording suggests one.")
    movement_reason: str | None = Field(default=None, description="Reason for movement, if mentioned.")
    movement_date: date | None = Field(default=None, description="Movement date. Resolve relative dates like today, yesterday, kal, parso into an actual date. Leave null if not mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

MATERIAL_MOVEMENT_VALIDATION_RULES = {
    ToolName.RECORD_MATERIAL_MOVEMENT: {
        "mandatory_fields": [
            ArgumentField.SOURCE_NAME,
            ArgumentField.DESTINATION_NAME,
            ArgumentField.ITEM_NAME,
            ArgumentField.QUANTITY,
        ],
        "optional_fields": [
            ArgumentField.SOURCE_TYPE,
            ArgumentField.DESTINATION_TYPE,
            ArgumentField.UNIT,
            ArgumentField.MOVEMENT_TYPE,
            ArgumentField.MOVEMENT_REASON,
            ArgumentField.NOTE,
        ],
    },
}

# Adjustment Tool
class RecordAdjustmentArgs(BaseModel):
    location: str | None = Field(default=None, description="Location where the stock change happened.")
    item_name: str | None = Field(default=None, description="Item whose stock changed.")
    unit: InventoryUnit | None = Field(default=None, description="Unit of the quantity.")
    quantity_change: float | None = Field(default=None, description="Signed quantity change — positive increases stock, negative decreases it. Must not be zero.")
    reason: str | None = Field(default=None, description="Reason, e.g. damage, wastage, count_correction, opening_stock.")
    adjustment_date: date | None = Field(default=None, description="Adjustment date. Resolve relative dates like today, yesterday, kal, parso into an actual date. Leave null if not mentioned.")
    note: str | None = Field(default=None, description="Additional information that does not belong to any other field.")

ADJUSTMENT_VALIDATION_RULES = {
    ToolName.RECORD_ADJUSTMENT: {
        "mandatory_fields": [
            ArgumentField.LOCATION,
            ArgumentField.ITEM_NAME,
        ],
        "optional_fields": [
            ArgumentField.UNIT,
            ArgumentField.NOTE,
        ],
    },
}

# Registration
TOOL_ARGUMENT_MODELS = {
    # Employee
    ToolName.RECORD_EMPLOYEE_TRANSACTION: RecordEmployeeTransactionArgs,
    ToolName.RECORD_ATTENDANCE: RecordAttendanceArgs,
    ToolName.MANAGE_EMPLOYEE: ManageEmployeeArgs,

    # Customer / Sales
    ToolName.MANAGE_CUSTOMER: ManageCustomerArgs,
    ToolName.RECORD_SALE_TRANSACTION: RecordSaleTransactionArgs,
    ToolName.RECORD_SALE_PAYMENT: RecordSalePaymentArgs,

    # Supplier
    ToolName.MANAGE_SUPPLIER: ManageSupplierArgs,
    ToolName.RECORD_SUPPLIER_TRANSACTION: RecordSupplierTransactionArgs,
    ToolName.RECORD_SUPPLIER_PAYMENT: RecordSupplierPaymentArgs,

    # Purchase
    ToolName.RECORD_PURCHASE: RecordPurchaseArgs,
    ToolName.RECORD_PURCHASE_PAYMENT: RecordPurchasePaymentArgs,

    # Expense
    ToolName.RECORD_EXPENSE: RecordExpenseArgs,
    ToolName.RECORD_EXPENSE_PAYMENT: RecordExpensePaymentArgs,

    # Work Log / Movement / Adjustment
    ToolName.RECORD_WORK_LOG: RecordWorkLogArgs,
    ToolName.RECORD_MATERIAL_MOVEMENT: RecordMaterialMovementArgs,
    ToolName.RECORD_ADJUSTMENT: RecordAdjustmentArgs,
}

TOOL_VALIDATION_RULES = {
    **EMPLOYEE_VALIDATION_RULES,

    # Customer / Sales
    **SALES_VALIDATION_RULES,

    # Supplier
    **SUPPLIER_VALIDATION_RULES,

    # Purchase
    **PURCHASE_VALIDATION_RULES,
    **PURCHASE_PAYMENT_VALIDATION_RULES,

    # Expense
    **EXPENSE_VALIDATION_RULES,
    **EXPENSE_PAYMENT_VALIDATION_RULES,

    # Work Log / Movement / Adjustment
    **WORK_LOG_VALIDATION_RULES,
    **MATERIAL_MOVEMENT_VALIDATION_RULES,
    **ADJUSTMENT_VALIDATION_RULES,
}




