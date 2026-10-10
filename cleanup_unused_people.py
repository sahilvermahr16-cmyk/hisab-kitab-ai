# cleanup_unused_people.py — testing ka kachra saaf karne wali script.
#
# Galat role chun lene se kabhi-kabhi aisa person ban jaata hai jiska koi
# hisab hi nahi (jaise "Suresh" employee, jabki asli Suresh customer hai).
# Ye script aise employee / customer / supplier / family member dhoondhti hai jinki EK BHI
# sahi (active) entry nahi hai, aur unhe hata deti hai. Saath mein
# person_role_lookup ko bhi theek karti hai (taaki naam sahi role pe point kare).
#
#   python cleanup_unused_people.py          → sirf dikhata hai kya hatega
#   python cleanup_unused_people.py --apply  → asli mein hatata hai
#   (jinka phone/pata/kaam bhara hai unhe nahi hatata — wo jaan-boojh ke bane hain;
#    unhe bhi hatana ho to --all jodo)
import sys

from db import SessionLocal
from helpers import normalize_name, sync_person_role
from models import (
    Employee, Customer, Supplier, EmployeeTransaction, Attendance, SalesTransaction, SalesPayment,
    SupplierTransaction, SupplierPayment, OpeningBalance, PersonRoleLookup, MovementEntityLookup,
    FamilyMember, FamilyTransaction,
)

KINDS = (("employee", Employee), ("customer", Customer), ("supplier", Supplier), ("family", FamilyMember))
LOOKUP_ROLE = {"employee": "employee", "customer": "customer", "supplier": "supplier", "family": "family_member"}

APPLY = "--apply" in sys.argv
ALL = "--all" in sys.argv        # profile wale (phone/pata bhara) bina-entry log bhi


def _active(model):
    return (model.status == "active") & (model.reversal_of_id.is_(None))


def _count(db, model, col, pid):
    return db.query(model).filter(col == pid, _active(model)).count()


def usage(db, kind, pid):
    """Is person ki kitni sahi entries hain (har table mein)."""
    if kind == "family":
        return _count(db, FamilyTransaction, FamilyTransaction.member_id, pid)
    ob = db.query(OpeningBalance).filter(OpeningBalance.ledger_type == kind, OpeningBalance.ledger_id == pid,
                                         _active(OpeningBalance)).count()
    if kind == "employee":
        return (_count(db, EmployeeTransaction, EmployeeTransaction.employee_id, pid)
                + _count(db, Attendance, Attendance.employee_id, pid) + ob)
    if kind == "customer":
        return (_count(db, SalesTransaction, SalesTransaction.customer_id, pid)
                + _count(db, SalesPayment, SalesPayment.customer_id, pid)
                + _count(db, SupplierTransaction, SupplierTransaction.customer_id, pid) + ob)
    return (_count(db, SupplierTransaction, SupplierTransaction.supplier_id, pid)
            + _count(db, SupplierPayment, SupplierPayment.supplier_id, pid)
            + _count(db, SalesTransaction, SalesTransaction.supplier_id, pid) + ob)


def has_fk_rows(db, kind, pid):
    """Koi bhi row (corrected/reversal bhi) jo is person ko foreign key se point karti ho — delete nahi ho sakta."""
    if kind == "family":
        pairs = [(FamilyTransaction, FamilyTransaction.member_id)]
    elif kind == "employee":
        pairs = [(EmployeeTransaction, EmployeeTransaction.employee_id), (Attendance, Attendance.employee_id)]
    elif kind == "customer":
        pairs = [(SalesTransaction, SalesTransaction.customer_id), (SalesPayment, SalesPayment.customer_id),
                 (SupplierTransaction, SupplierTransaction.customer_id)]
    else:
        pairs = [(SupplierTransaction, SupplierTransaction.supplier_id), (SupplierPayment, SupplierPayment.supplier_id),
                 (SalesTransaction, SalesTransaction.supplier_id)]
    return any(db.query(m).filter(c == pid).count() for m, c in pairs)


def main():
    db = SessionLocal()
    try:
        removed = []
        for kind, model in KINDS:
            for p in db.query(model).all():
                if usage(db, kind, p.id) == 0:
                    profile = [getattr(p, f, None) for f in ("phone", "address", "role", "supplier_type")]
                    if any(profile) and not ALL:
                        print(f"  (chhoda) {kind} #{p.id} {p.name}: entry nahi, lekin profile (phone/pata/kaam) "
                              f"bhara hai — jaan-boojh ke banaya lagta hai. Hatana ho to --all ke saath chalao.")
                        continue
                    if has_fk_rows(db, kind, p.id):
                        print(f"  (chhoda) {kind} #{p.id} {p.name}: sirf purani/corrected entries hain, "
                              f"unhe chhedna safe nahi")
                        continue
                    removed.append((kind, model, p))

        if not removed:
            print("✅ Koi bina-hisab wala person nahi mila — kuch saaf karne ko nahi.")
            return

        print("Ye log hatenge (inki ek bhi sahi entry nahi hai):")
        for kind, _, p in removed:
            print(f"  - {kind:<9} #{p.id}  {p.name}")

        if not APPLY:
            print("\n(dry run) Asli mein hatane ke liye:  python cleanup_unused_people.py --apply")
            return

        names = set()
        for kind, model, p in removed:
            names.add(normalize_name(p.name))
            (db.query(PersonRoleLookup)
               .filter(PersonRoleLookup.role == LOOKUP_ROLE[kind], PersonRoleLookup.linked_id == p.id)
               .delete(synchronize_session=False))
            if kind in ("customer", "supplier"):
                (db.query(MovementEntityLookup)
                   .filter(MovementEntityLookup.entity_type == kind, MovementEntityLookup.linked_id == p.id)
                   .delete(synchronize_session=False))
            db.delete(p)
        db.flush()

        # Jo naam bache hain (dusre role mein), unka lookup dobara sahi role pe
        for kind, model in KINDS:
            for p in db.query(model).all():
                if normalize_name(p.name) in names:
                    row = db.query(PersonRoleLookup).filter(
                        PersonRoleLookup.normalized_name == normalize_name(p.name)).first()
                    if row is None:
                        sync_person_role(db, name=p.name, role=LOOKUP_ROLE[kind], linked_id=p.id, confirmed_by="cleanup")
                        print(f"  🔗 '{p.name}' ab {kind} ke roop mein pehchana jayega")
        db.commit()
        print(f"\n✅ {len(removed)} person hata diye.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
