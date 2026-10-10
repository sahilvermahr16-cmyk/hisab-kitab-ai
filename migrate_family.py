# migrate_family.py — Family Kharcha ke naye tables (ek baar chalao).
#   python migrate_family.py
# Sirf naye tables banata hai (family_members, family_transactions) + date index.
# Purane tables / data ko haath nahi lagata. Dobara chalane pe kuch nahi bigadta.
from sqlalchemy import text

from db import engine
from models import Base, FamilyMember, FamilyTransaction

Base.metadata.create_all(engine, tables=[FamilyMember.__table__, FamilyTransaction.__table__])
with engine.begin() as conn:
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_family_transactions_date "
                      "ON family_transactions (business_id, transaction_date)"))
    # purane naam → naye (diya → kharcha, liya → jama). Dobara chalane pe kuch nahi badalta.
    n1 = conn.execute(text("UPDATE family_transactions SET transaction_type='kharcha' WHERE transaction_type='diya'")).rowcount
    n2 = conn.execute(text("UPDATE family_transactions SET transaction_type='jama' WHERE transaction_type='liya'")).rowcount
print("✅ family_members, family_transactions tables tayyar.")
if n1 or n2:
    print(f"   {n1 + n2} purani entries ke naam badle (diya → kharcha, liya → jama).")
