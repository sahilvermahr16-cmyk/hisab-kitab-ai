# report_pdf_test.py — Step 4 check: asli DB se PDF banao (graph ke bina).
#
#   python report_pdf_test.py 2026-09-01 2026-09-30
#
# reports_output/ folder mein ye banenge:
#   - Poore business ki report — Hindi, Hinglish, English (teeno)
#   - Har employee / customer / supplier ka khata (Hinglish)
#   - Purchase, Expense, Cash Book, Work Log, Material Movement (Hinglish)
# Hindi/English ke liye item/note/naam ka translation LLM se hota hai
# (ek baar — fir translation_cache table se).
import sys
from datetime import date
from db import SessionLocal
from llm_setup import llm
from reports import builders as B, render as R, queries as Q


def main():
    start, end = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])
    db = SessionLocal()
    try:
        made = []
        o = B.build_report(db, "overall", start, end)
        for lang in ("hi", "hg", "en"):
            made.append(R.make_pdf(db, o, lang, llm=llm))
        for lt, masters in (("employee", Q.employees(db)), ("customer", Q.customers(db)), ("supplier", Q.suppliers(db))):
            for pid in masters:
                rep = B.build_report(db, lt, start, end, ledger_id=pid)
                if not B.report_is_empty(rep):
                    made.append(R.make_pdf(db, rep, "hg", llm=llm))
        for k in ("purchase", "expense", "cash_flow", "work_log", "material_movement"):
            rep = B.build_report(db, k, start, end)
            if not B.report_is_empty(rep):
                made.append(R.make_pdf(db, rep, "hg", llm=llm))
        print("✅ PDF bane:")
        for m in made:
            print("  ", m)
    finally:
        db.close()


if __name__ == "__main__":
    main()
