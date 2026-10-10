# migrate_reporting.py — Reporting Phase ke liye nayi tables + date indexes.
# Ek baar chalao:  python migrate_reporting.py
# Dobara chalane se kuch nahi bigadta (sab IF NOT EXISTS hai).
from sqlalchemy import text
from models import Base, OpeningBalance, MonthClose, MonthlyClosing, TranslationCache
from db import engine

NEW_TABLES = [OpeningBalance.__table__, MonthClose.__table__,
              MonthlyClosing.__table__, TranslationCache.__table__]

# Report hamesha date-range pe query karegi — in columns pe index.
DATE_INDEXES = [
    ("employee_transactions", "transaction_date"),
    ("attendance", "attendance_date"),
    ("sales_transactions", "sale_date"),
    ("sales_payments", "payment_date"),
    ("supplier_transactions", "transaction_date"),
    ("supplier_payments", "payment_date"),
    ("purchases", "purchase_date"),
    ("purchase_payments", "payment_date"),
    ("expenses", "expense_date"),
    ("expense_payments", "payment_date"),
    ("cash_ledger", "entry_date"),
    ("work_logs", "activity_date"),
    ("material_movements", "movement_date"),
    ("stock_adjustments", "adjustment_date"),
]

if __name__ == "__main__":
    Base.metadata.create_all(engine, tables=NEW_TABLES)
    print("✅ Nayi tables: opening_balances, month_close, monthly_closing, translation_cache")
    with engine.begin() as conn:
        for table, col in DATE_INDEXES:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_{col} ON {table} ({col})"))
            print(f"   index: {table}.{col}")
    print("✅ Migration complete")
