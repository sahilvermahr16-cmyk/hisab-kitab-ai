# report_debug.py — Reporting Phase Step 2 check (koi PDF nahi, sirf numbers)
#
#   python report_debug.py                      → pichla poora mahina
#   python report_debug.py 2026-09-01 2026-09-30
#
# Overall report + saare ledgers ke totals print karta hai, aur
# reconciliation checks chalata hai (✅ / ❌). Sab ✅ hone chahiye.
import sys
from datetime import date, timedelta
from db import SessionLocal
from reports import builders as B
from reports import queries as Q


def fmt(x):
    return f"{x:,.2f}"


def sign(x):
    if abs(x) < 0.005:
        return "0"
    return f"{fmt(abs(x))} {'LENA' if x > 0 else 'DENA'}"


def check(label, a, b):
    ok = abs(a - b) < 0.01
    print(f"  {'✅' if ok else '❌'} {label}: {fmt(a)} vs {fmt(b)}")
    return ok


def main():
    if len(sys.argv) == 3:
        start, end = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
    else:
        first_this = date.today().replace(day=1)
        end = first_this - timedelta(days=1)
        start = end.replace(day=1)
    db = SessionLocal()
    try:
        o = B.build_overall(db, start, end)
        print(f"\n===== OVERALL {start} → {end}   (empty={o['empty']}) =====")

        print("\n-- A. Supplier summary")
        for r in o["supplier"]["summary"]:
            print(f"  {r['name']:<25} open {sign(r['opening']):>18} | maal {fmt(r['maal']):>12} | paid {fmt(r['paid']):>12} | close {sign(r['closing'])}")
        print("\n-- B. Employee summary")
        for r in o["employee"]["summary"]:
            print(f"  {r['name']:<25} open {sign(r['opening']):>18} | kaam {fmt(r['work']):>12} | liya {fmt(r['paid']):>12} | close {sign(r['closing'])}")
        print("   day rows:")
        for d in o["employee"]["days"]:
            print(f"    {d['date']} {d['employee']:<10} kaam {d['work_breakdown']} liya {d['paid_breakdown']} {d['modes']} {d['providers']}")
        print(f"\n-- C. Purchase  total {fmt(o['purchase']['total'])} paid {fmt(o['purchase']['paid'])} baaki {fmt(o['purchase']['baaki'])}  (purani kharid ki payments: {len(o['purchase']['old_payments'])})")
        print(f"-- D. Expense   total {fmt(o['expense']['total'])} paid {fmt(o['expense']['paid'])} baaki {fmt(o['expense']['baaki'])}  by_cat {[(c['category'], c['amount']) for c in o['expense']['by_category']]}")
        print("\n-- E. Customer summary")
        for r in o["sale"]["summary"]:
            print(f"  {r['name']:<25} open {sign(r['opening']):>18} | sale {fmt(r['sale']):>12} | recd {fmt(r['received']):>12} | close {sign(r['closing'])}")
        c = o["cash"]
        print(f"\n-- F. Cash  opening {fmt(c['opening'])} + in {fmt(c['total_in'])} - out {fmt(c['total_out'])} = closing {fmt(c['closing'])}")

        f = o["final"]
        print(f"\n===== FINAL HISAB (as of {f['as_of']}) =====")
        print("  DENA:")
        for x in f["give"]:
            print(f"    {x['party']:<25} {x['reason']:<20} {fmt(x['amount'])}")
        print(f"    TOTAL DENA {fmt(f['total_give'])}")
        print("  LENA:")
        for x in f["take"]:
            print(f"    {x['party']:<25} {x['reason']:<20} {fmt(x['amount'])}")
        print(f"    TOTAL LENA {fmt(f['total_take'])}")
        print(f"  Cash {fmt(f['cash'])}  →  sab nipataane ke baad {fmt(f['after_settlement'])}")

        print("\n===== CHECKS =====")
        ok = True
        h = o["heads"]
        ok &= check("Cash OUT = supplier+employee+purchase+expense payments",
                    c["total_out"], h["supplier"]["out"] + h["employee"]["out"] + h["purchase"]["out"] + h["expense"]["out"])
        ok &= check("Cash IN = customer payments", c["total_in"], h["sale"]["inn"])
        ok &= check("Cash closing = opening + in - out", c["closing"], c["opening"] + c["total_in"] - c["total_out"])
        ok &= check("Cash book last balance = closing",
                    o["cash_book"]["rows"][-1]["balance"] if o["cash_book"]["rows"] else o["cash_book"]["opening"], c["closing"])

        for r in o["supplier"]["summary"]:
            led = B.build_supplier_ledger(db, r["id"], start, end)
            ok &= check(f"Supplier ledger closing [{r['name']}]", led["closing"], r["closing"])
        for r in o["sale"]["summary"]:
            led = B.build_customer_ledger(db, r["id"], start, end)
            ok &= check(f"Customer ledger closing [{r['name']}]", led["closing"], r["closing"])
        for r in o["employee"]["summary"]:
            led = B.build_employee_ledger(db, r["id"], start, end)
            ok &= check(f"Employee ledger closing [{r['name']}]", led["closing"], r["closing"])

        give_sup = sum(x["amount"] for x in f["give"] if x["ledger"] == "supplier")
        take_sup = sum(x["amount"] for x in f["take"] if x["ledger"] == "supplier")
        ok &= check("Final hisab supplier = supplier summary closing",
                    take_sup - give_sup, sum(r["closing"] for r in o["supplier"]["summary"]))
        print("\n" + ("✅ SAB CHECKS PASS" if ok else "❌ KUCH CHECKS FAIL — upar dekho"))
    finally:
        db.close()


if __name__ == "__main__":
    main()
