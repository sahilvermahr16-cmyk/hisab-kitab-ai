# report_e2e_check.py — Reporting Phase ka poora end-to-end check (Step 7).
#
#   python report_e2e_check.py            → PDF bhi banata hai (thoda time lagega)
#   python report_e2e_check.py --no-pdf   → sirf numbers ke checks
#
# Kya check hota hai (har jagah ✅ / ❌):
#   A. Month closing  — har khaate ka har din ka baaki: tez raasta == shuru se jod ke
#   B. Is mahine ki report — cash book, overall, final hisab, har party ka khata: sab aapas mein milte hain
#   C. Pichle 3 mahine (lambi duration) — mahine-wise summary ki kadi (closing == agle mahine ka opening),
#      party-wise summary == party ledger, final hisab == 1-mahine wala final hisab
#   D. Registers (purchase, expense, cash flow, work log, material, family) — ban jaate hain, totals sahi
#   E. PDF — har report type, overall teeno bhasha mein; koi error nahi
import sys
import traceback
from datetime import date, timedelta

from db import SessionLocal
from reports import builders as B, closing as C, ledgers as L, queries as Q

PDF = "--no-pdf" not in sys.argv
RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append(ok)
    print(f"  {'✅' if ok else '❌'} {label}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def eq(a, b):
    return abs((a or 0) - (b or 0)) < 0.01


def run(label, fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        check(f"{label} — ERROR: {e}", False)
        return None


def section_a(db):
    print("\n=== A. Month closing ===")
    first = C.earliest_data_date(db)
    if first is None:
        check("DB mein data hai", False, "koi entry nahi")
        return
    n = C.ensure_closed_until(db)
    print(f"  data shuru: {first}, abhi calculate hue mahine: {n}")
    keys = [("cash", 0), ("purchase", 0), ("expense", 0)]
    keys += [("supplier", i) for i in Q.suppliers(db)]
    keys += [("customer", i) for i in Q.customers(db)]
    keys += [("employee", i) for i in Q.employees(db)]
    bad, d = 0, first
    while d <= date.today() + timedelta(days=1):
        for lt, lid in keys:
            if not eq(L.balance_before(db, lt, lid, d), L.raw_balance_before(db, lt, lid, d)):
                bad += 1
        d += timedelta(days=1)
    check(f"tez baaki == raw baaki ({len(keys)} khaate, har din)", bad == 0, f"{bad} alag")


def section_b(db, start, end):
    print(f"\n=== B. Is mahine ki report ({start} → {end}) ===")
    o = B.build_report(db, "overall", start, end)
    cb, f, h = o["cash_book"], o["final"], o["heads"]
    check("cash book closing == overall cash closing", eq(cb["closing"], o["cash"]["closing"]))
    check("final hisab cash == cash book closing", eq(f["cash"], cb["closing"]))
    check("cash OUT == supplier + employee + purchase + expense payments + family (ghar gaya)",
          eq(cb["total_out"], h["supplier"]["out"] + h["employee"]["out"] + h["purchase"]["out"] + h["expense"]["out"]
             + h["family"]["out"]))
    check("cash IN == customer payments + family (galle mein aaya)", eq(cb["total_in"], h["sale"]["inn"] + h["family"]["inn"]))
    for lt, key, builder in (("supplier", "supplier", B.build_supplier_ledger),
                             ("customer", "sale", B.build_customer_ledger),
                             ("employee", "employee", B.build_employee_ledger)):
        rows = o[key]["summary"]
        ok = all(eq(builder(db, r["id"], start, end)["closing"], r["closing"]) for r in rows)
        check(f"{lt}: har khaate ka closing == summary ({len(rows)} khaate)", ok)
        give = sum(x["amount"] for x in f["give"] if x["ledger"] == lt)
        take = sum(x["amount"] for x in f["take"] if x["ledger"] == lt)
        all_close = sum(L.balance_before(db, lt, i, end + timedelta(days=1))
                        for i in {"supplier": Q.suppliers, "customer": Q.customers, "employee": Q.employees}[lt](db))
        check(f"{lt}: final hisab (lena − dena) == saare khaaton ka baaki", eq(take - give, all_close))
    check("after_settlement == cash + lena − dena", eq(f["after_settlement"], f["cash"] + f["total_take"] - f["total_give"]))
    return o


def section_c(db, start, end, month_report):
    print(f"\n=== C. Lambi duration ({start} → {end}) ===")
    p = B.build_report(db, "overall", start, end)
    check("kind == overall_period", p["kind"] == "overall_period")
    ms = p["months"]
    check("mahine ki kadi: closing cash == agle mahine ka opening",
          all(eq(ms[i]["cash_close"], ms[i + 1]["cash_open"]) for i in range(len(ms) - 1)))
    check("cash: period opening + in − out == closing",
          eq(p["cash"]["opening"] + p["cash"]["total_in"] - p["cash"]["total_out"], p["cash"]["closing"]))
    check("final hisab == 1-mahine wali report ka final hisab (same end date)",
          eq(p["final"]["total_give"], month_report["final"]["total_give"])
          and eq(p["final"]["total_take"], month_report["final"]["total_take"])
          and eq(p["final"]["cash"], month_report["final"]["cash"]))
    for lt in ("supplier", "customer", "employee"):
        rows = p["parties"][lt]
        ok = True
        for r in rows:
            pp = B.build_report(db, lt, start, end, ledger_id=r["id"])
            ms2 = pp["months"]
            chain = all(eq(ms2[i]["closing"], ms2[i + 1]["opening"]) for i in range(len(ms2) - 1))
            ok &= eq(pp["closing"], r["closing"]) and chain and eq(pp["last_month_detail"]["closing"], pp["closing"])
        check(f"{lt}: lambi duration ka khata == party summary, mahine ki kadi sahi ({len(rows)} khaate)", ok)
    return p


def section_d(db, start, end):
    print(f"\n=== D. Registers ({start} → {end}) ===")
    out = {}
    for k in ("purchase", "expense", "cash_flow", "work_log", "material_movement", "family"):
        r = run(k, lambda k=k: B.build_report(db, k, start, end))
        if r is None:
            continue
        out[k] = r
        if k in ("purchase", "expense"):
            check(f"{k}: kul − diya == baaki", eq(r["total"] - r["paid"], r["baaki"]))
        elif k == "family":
            check("family: diya − liya == net, member-wise jod == total",
                  eq(r["total_diya"] - r["total_liya"], r["net"])
                  and eq(sum(x["diya"] for x in r["summary"]), r["total_diya"]))
        elif k == "cash_flow":
            check("cash flow: opening + in − out == closing", eq(r["opening"] + r["total_in"] - r["total_out"], r["closing"]))
        else:
            check(f"{k}: ban gaya ({len(r['rows'])} rows)", True)
    return out


def section_e(db, reports):
    print("\n=== E. PDF ===")
    from llm_setup import llm
    from reports import render as R
    made = []
    for name, rep, langs in reports:
        for lang in langs:
            path = run(f"PDF {name} [{lang}]", lambda rep=rep, lang=lang: R.make_pdf(db, rep, lang, llm=llm))
            if path:
                made.append(path)
                check(f"PDF {name} [{lang}]", True)
    print("\n  Bani PDF:")
    for m in made:
        print("   ", m)


def main():
    db = SessionLocal()
    try:
        today = date.today()
        m_start = today.replace(day=1)
        long_start = (m_start - timedelta(days=62)).replace(day=1)

        run("A", lambda: section_a(db))
        month = run("B", lambda: section_b(db, m_start, today))
        long_rep = run("C", lambda: section_c(db, long_start, today, month)) if month else None
        regs = run("D", lambda: section_d(db, m_start, today)) or {}

        if PDF:
            reports = []
            if month:
                reports.append(("overall (is mahina)", month, ("hi", "hg", "en")))
            if long_rep:
                reports.append(("overall (3 mahine)", long_rep, ("hg",)))
            for lt, masters in (("employee", Q.employees(db)), ("customer", Q.customers(db)), ("supplier", Q.suppliers(db))):
                for pid in masters:
                    rep = B.build_report(db, lt, long_start, today, ledger_id=pid)
                    if not B.report_is_empty(rep):
                        reports.append((f"{lt} {masters[pid].name} (3 mahine)", rep, ("hg",)))
                        break   # har type ka ek sample kaafi
            for k, r in regs.items():
                if not B.report_is_empty(r):
                    reports.append((k, r, ("hg",)))
            run("E", lambda: section_e(db, reports))

        passed, total = sum(RESULTS), len(RESULTS)
        print("\n" + "=" * 60)
        print(f"{'✅ SAB CHECKS PASS' if passed == total else '❌ KUCH CHECKS FAIL'} — {passed}/{total}")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
