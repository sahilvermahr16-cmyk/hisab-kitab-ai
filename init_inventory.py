# init_inventory.py
# Pehli baar inventory items register karne ke liye

from db import SessionLocal
from models import GudamInventory, ShopInventory

GUDAM_ITEMS = [
    # Iron/Loha
    ("sariya",      "kg"),
    ("jangla",      "piece"),
    ("chokhat",     "piece"),
    ("jodi",        "piece"),
    ("palaa",       "piece"),
    ("roshan_dan",  "piece"),
    ("loha_gate",   "kg"),
    ("loha_jaal",   "kg"),
    # Lakdi
    ("balita",      "trolley"),
    ("kadi",        "piece"),
    ("fate",        "piece"),
    ("furniture",   "piece"),
    # Eent
    ("eent",        "piece"),
    ("eent",        "trolley"),
    ("eent",        "chakr"),
    ("malba",       "trolley"),
    # Paint
    ("primer",      "litre"),
    ("primer",      "tin"),
    ("puti",        "kg"),
    ("puti",        "bag"),
    ("paint",       "litre"),
    ("paint",       "tin"),
    # Misc
    ("misc",        "piece"),
]

SHOP_ITEMS = [
    ("jangla",      "piece"),
    ("chokhat",     "piece"),
    ("jodi",        "piece"),
    ("palaa",       "piece"),
    ("roshan_dan",  "piece"),
    ("loha_gate",   "piece"),
    ("loha_jaal",   "piece"),
    ("misc",        "piece"),
]

def init():
    db = SessionLocal()
    try:
        # GudamInventory
        for item_name, unit in GUDAM_ITEMS:
            existing = db.query(GudamInventory).filter(
                GudamInventory.item_name == item_name,
                GudamInventory.unit == unit
            ).first()
            if not existing:
                db.add(GudamInventory(
                    item_name=item_name,
                    unit=unit,
                    stock_quantity=0
                ))

        # ShopInventory
        for item_name, unit in SHOP_ITEMS:
            existing = db.query(ShopInventory).filter(
                ShopInventory.item_name == item_name,
                ShopInventory.unit == unit
            ).first()
            if not existing:
                db.add(ShopInventory(
                    item_name=item_name,
                    unit=unit,
                    stock_quantity=0
                ))

        db.commit()
        print("✅ Inventory items registered!")

        # Show all items
        gudam = db.query(GudamInventory).all()
        print(f"\nGudam Inventory ({len(gudam)} items):")
        for g in gudam:
            print(f"  {g.item_name} ({g.unit}): {g.stock_quantity}")

        shop = db.query(ShopInventory).all()
        print(f"\nShop Inventory ({len(shop)} items):")
        for s in shop:
            print(f"  {s.item_name} ({s.unit}): {s.stock_quantity}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init()