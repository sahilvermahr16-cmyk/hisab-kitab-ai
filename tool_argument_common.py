from enum import Enum

# Argument Fields
class ArgumentField(str, Enum):

    # Common / Person
    PHONE = "phone"
    ADDRESS = "address"
    ROLE = "role"

    # Transaction
    SALE_DATE = "sale_date"
    PURCHASE_DATE = "purchase_date"
    # Sales / Supplier Transaction
    RATE = "rate"
    BILL_ID = "bill_id"
    SOURCE = "source"
    DESTINATION_LOCATION = "destination_location"

    # Supplier
    SUPPLIER_TYPE = "supplier_type"

    # Common
    NOTE = "note"

    # Person
    EMPLOYEE_NAME = "employee_name"
    SUPPLIER_NAME = "supplier_name"
    CUSTOMER_NAME = "customer_name"
    DRIVER_NAME = "driver_name"
    SELLER_NAME = "seller_name"

    # Transaction
    TRANSACTION_TYPE = "transaction_type"
    TRANSACTION_DATE = "transaction_date"
    PAYMENT_DATE = "payment_date"
    ATTENDANCE_DATE = "attendance_date"
    ACTIVITY_DATE = "activity_date"
    AMOUNT = "amount"
    TOTAL_AMOUNT = "total_amount"
    AMOUNT_PAID = "amount_paid"
    SUPPLIER_AMOUNT = "supplier_amount"
    SALE_AMOUNT = "sale_amount"
    AMOUNT_RECEIVED = "amount_received"

    # Payment
    PAYMENT_METHOD = "payment_method"
    PAYMENT_PROVIDER = "payment_provider"

    # Attendance
    ATTENDANCE = "attendance"
    DRIVING = "driving"

    # Inventory
    ITEM_NAME = "item_name"
    ITEMS = "items"
    QUANTITY = "quantity"
    UNIT = "unit"

    # Purchase
    DESCRIPTION = "description"
    LOCATION = "location"
    SELLER_PHONE = "seller_phone"

    # Expense
    CATEGORY = "category"

    # Sales
    SALE_TYPE = "sale_type"

    # Activity
    LOCATION_TYPE = "location_type"
    LOCATION_NAME = "location_name"
    ACTIVITY_TYPE = "activity_type"
    SOURCE_TYPE = "source_type"
    SOURCE_NAME = "source_name"
    DESTINATION_TYPE = "destination_type"
    DESTINATION_NAME = "destination_name"
    MOVEMENT_TYPE = "movement_type"
    MOVEMENT_REASON = "movement_reason"

    # Opening balance
    PARTY_TYPE = "party_type"
    PARTY_NAME = "party_name"
    DIRECTION = "direction"
    AS_OF_DATE = "as_of_date"

    # Family
    MEMBER_NAME = "member_name"
    PURPOSE = "purpose"
    RELATION = "relation"

    