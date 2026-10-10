# report_closing_check.py — Step 3 check: month closing sahi hai ya nahi.
#
#   python report_closing_check.py
#
# 1. Pichle saare mahine close karta hai (monthly_closing table bharti hai)
# 2. Har khaate ka har din ka baaki do tarah se nikaalta hai:
#      tez  (pichle mahine ka closing + is mahine ki entries)
#      raw  (shuru se saari entries jod ke)
#    Dono hamesha barabar hone chahiye.
from datetime import date, timedelta
from db import SessionLocal
from models import MonthClose, MonthlyClosing, Supplier, Customer, Employee
from reports import ledgers as L, closing as C


def main():
    db = SessionLocal()
    try:
        first = C.earliest_data_date(db)
        if first is None:
            print("DB mein koi data nahi.")
            return
        n = C.ensure_closed_until(db)
        print(f"Data shuru: {first}   |   abhi calculate hue mahine: {n}")
        for m in db.query(MonthClose).order_by(MonthClose.year_month):
            rows = db.query(MonthlyClosing).filter(MonthlyClosing.year_month == m.year_month).count()
            print(f"  {m.year_month}  {m.status:<7} {rows} khaate")

        keys = [("cash", 0), ("purchase", 0), ("expense", 0)]
        keys += [("supplier", s.id) for s in db.query(Supplier)]
        keys += [("customer", c.id) for c in db.query(Customer)]
        keys += [("employee", e.id) for e in db.query(Employee)]
        bad = total = 0
        d = first
        while d <= date.today() + timedelta(days=1):
            for lt, lid in keys:
                f = L.balance_before(db, lt, lid, d)
                r = L.raw_balance_before(db, lt, lid, d)
                total += 1
                if abs(f - r) > 0.01:
                    bad += 1
                    if bad <= 10:
                        print(f"  ❌ {lt} #{lid} {d}: tez {f:,.2f} vs raw {r:,.2f}")
            d += timedelta(days=1)
        print(f"\n{total} comparisons — {'✅ sab barabar' if bad == 0 else f'❌ {bad} alag'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
