# backfill_reversal_links.py — ek baar chalane wali safai script.
#
# Correction Phase ke shuruaati tests mein reversal to bana, lekin business
# table pe link nahi laga (mark_business_tables_corrected tab tha hi nahi).
# Isliye report mein  kaam [500, -500]  jaisi rows dikhti hain.
# Ye script audit_log ke "[REVERSAL]" rows se purani-nayi entry dhoondh ke
# link laga deti hai (purani → corrected, nayi → reversal_of_id, cash row → corrected).
#
#   python backfill_reversal_links.py          → sirf dikhata hai kya badlega
#   python backfill_reversal_links.py --apply  → asli mein badalta hai
import sys
from db import SessionLocal
from models import AuditLog, CashLedger, MonthClose
from helpers import TARGET_TABLE_MODEL_MAP, mark_business_tables_corrected

APPLY = "--apply" in sys.argv


def main():
    db = SessionLocal()
    fixed = skipped = 0
    try:
        reversals = (db.query(AuditLog)
                     .filter(AuditLog.action_statement.like("[REVERSAL]%"))
                     .order_by(AuditLog.id).all())
        print(f"[REVERSAL] audit rows: {len(reversals)}")
        for rev in reversals:
            model = TARGET_TABLE_MODEL_MAP.get(rev.target_table)
            if model is None:
                continue
            orig = (db.query(AuditLog)
                    .filter(AuditLog.id < rev.id,
                            AuditLog.status == "corrected",
                            AuditLog.tool_name == rev.tool_name,
                            AuditLog.target_table == rev.target_table,
                            AuditLog.run_id.is_(None) if rev.run_id is None else AuditLog.run_id == rev.run_id,
                            AuditLog.group_id.is_(None) if rev.group_id is None else AuditLog.group_id == rev.group_id,
                            AuditLog.action_index.is_(None) if rev.action_index is None else AuditLog.action_index == rev.action_index,
                            ~AuditLog.action_statement.like("[REVERSAL]%"))
                    .order_by(AuditLog.id.desc()).first())
            if orig is None:
                print(f"  ⚠️ audit #{rev.id}: original entry nahi mili — chhod diya")
                skipped += 1
                continue
            if orig.target_id == rev.target_id:
                print(f"  ⚠️ audit #{rev.id}: original aur reversal same row ({rev.target_table} #{rev.target_id}) — "
                      f"attendance jaisa overwrite case, chhod diya")
                skipped += 1
                continue
            old_row = db.query(model).filter(model.id == orig.target_id).first()
            new_row = db.query(model).filter(model.id == rev.target_id).first()
            cash_active = (db.query(CashLedger).filter(CashLedger.source_table == rev.target_table,
                                                       CashLedger.source_id == orig.target_id,
                                                       CashLedger.status == "active").count())
            need = ((old_row is not None and old_row.status != "corrected")
                    or (new_row is not None and new_row.reversal_of_id is None)
                    or cash_active)
            if not need:
                continue
            print(f"  🔗 {rev.target_table}: #{orig.target_id} (galat) ↔ #{rev.target_id} (reversal)"
                  f"{'  + cash row' if cash_active else ''}")
            mark_business_tables_corrected(db, rev.target_table, orig.target_id, rev.target_id)
            fixed += 1

        if fixed:
            # report ke liye: saare closed mahine dobara calculate honge
            db.query(MonthClose).update({MonthClose.status: "dirty"}, synchronize_session=False)
        if APPLY:
            db.commit()
            print(f"\n✅ {fixed} entries link ho gayi, {skipped} chhodi.")
        else:
            db.rollback()
            print(f"\n(dry run) {fixed} entries link hongi, {skipped} chhodi jayengi. "
                  f"Asli mein karne ke liye:  python backfill_reversal_links.py --apply")
    finally:
        db.close()


if __name__ == "__main__":
    main()
