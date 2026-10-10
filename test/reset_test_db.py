# test/reset_test_db.py — TEST database ko saaf karke Seed Data daalta hai.
#
#   python test/reset_test_db.py          → poochega, phir reset karega
#   python test/reset_test_db.py --yes    → bina pooche (runner isi tarah bulata hai)
#
# SURAKSHA: ye sirf us database pe chalta hai jiske naam mein "test" ho.
# Address .env ki TEST_DATABASE_URL line se aata hai — asli DATABASE_URL ko kabhi nahi chhoota.
import os
import sys
from datetime import date, timedelta
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent


def use_test_database():
    """
    TEST_DATABASE_URL ko DATABASE_URL bana do — project ka koi bhi module import hone se PEHLE.
    (db.py ka load_dotenv() pehle se set env ko overwrite nahi karta.)
    """
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        sys.exit("❌ .env mein TEST_DATABASE_URL nahi hai. Example:\n"
                 "   TEST_DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/hisab_test")
    db_name = url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name.lower():
        sys.exit(f"❌ RUKO: database '{db_name}' ke naam mein 'test' nahi hai. "
                 f"Asli data mitne ke darr se reset nahi kiya.")
    if os.environ.get("DATABASE_URL") == url and os.environ.get("HK_TEST_DB_ACTIVE") != "1":
        sys.exit("❌ TEST_DATABASE_URL aur DATABASE_URL ek hi hain — asli DB ke darr se ruk gaye. "
                 "Test ke liye alag database (jaise hisab_test) banao.")
    os.environ["DATABASE_URL"] = url
    os.environ["HK_TEST_DB_ACTIVE"] = "1"
    if str(PROJECT_DIR) not in sys.path:
        sys.path.insert(0, str(PROJECT_DIR))
    if str(TEST_DIR) not in sys.path:
        sys.path.insert(0, str(TEST_DIR))
    return db_name


# Ye tables reset ke baad bhi rehte hain (business data nahi hai)
KEEP_TABLES = {"translation_cache"}


def _wipe(engine, Base):
    from sqlalchemy import text
    tables = [t.name for t in Base.metadata.sorted_tables if t.name not in KEEP_TABLES]
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("TRUNCATE TABLE " + ", ".join(f'"{t}"' for t in tables)
                              + " RESTART IDENTITY CASCADE"))
        else:                                   # sqlite (sirf sandbox testing ke liye)
            for t in reversed(tables):
                conn.execute(text(f'DELETE FROM "{t}"'))


def _seed(SessionLocal, today, lang="hinglish"):
    import seed_data as S
    from helpers import (get_or_create_employee, get_or_create_customer, get_or_create_supplier,
                         get_or_create_family_member, sync_movement_entity)
    from models import OpeningBalance, MovementEntityType

    db = SessionLocal()
    try:
        ids = {}
        n = lambda x: S.name_for(x, lang)
        for name, role in S.EMPLOYEES:
            e = get_or_create_employee(n(name), db)
            e.role = role
            ids[("employee", name)] = e.id
        for name in S.CUSTOMERS:
            ids[("customer", name)] = get_or_create_customer(n(name), db).id
        for name, typ in S.SUPPLIERS:
            s = get_or_create_supplier(n(name), db)
            s.supplier_type = typ
            ids[("supplier", name)] = s.id
        for name, rel in S.FAMILY:
            ids[("family", name)] = get_or_create_family_member(n(name), db, relation=rel).id
        locs = list(S.STORAGE_LOCATIONS) + (list(S.HINDI_STORAGE_LOCATIONS) if lang == "hindi" else [])
        for loc in locs:
            sync_movement_entity(db, name=loc, entity_type=MovementEntityType.STORAGE, confirmed_by="seed")
        as_of = today - timedelta(days=S.OPENING_DAYS_BEFORE)
        for ltype, name, amount, direction in S.OPENING_BALANCES:
            lid = 0 if ltype == "cash" else ids[(ltype, name)]
            db.add(OpeningBalance(ledger_type=ltype, ledger_id=lid, amount=amount,
                                  direction=direction, as_of_date=as_of, note="seed"))
        db.commit()
    finally:
        db.close()


def reset(today=None, quiet=False, lang="hinglish"):
    """Test DB: tables bana do (agar nahi hain), sab data mitao, Seed daalo (naam test ki bhasha mein)."""
    from db import engine, SessionLocal
    from models import Base
    Base.metadata.create_all(engine)
    _wipe(engine, Base)
    _seed(SessionLocal, today or date.today(), lang)
    if not quiet:
        print("✅ Test DB reset + seed ho gaya.")


if __name__ == "__main__":
    name = use_test_database()
    if "--yes" not in sys.argv:
        ans = input(f"Database '{name}' ka SAARA data delete hoga aur seed data daala jayega. Aage badhein? (yes/no): ")
        if ans.strip().lower() != "yes":
            sys.exit("Reset nahi kiya.")
    reset()
