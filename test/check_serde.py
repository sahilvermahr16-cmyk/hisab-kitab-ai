# test/check_serde.py — kya graph ki memory (checkpoint) hamare saare types sahi wapas laati hai?
#
#   python test/check_serde.py
#
# Har project file ke har Enum ko checkpoint ke serializer se save karke wapas padhta hai.
# Agar koi type wapas aate waqt saadha text ban gaya (allowlist mein nahi hai) → ❌ aur file ka naam.
# Kab chalayein: checkpointer.py ya kisi schema/model file mein naya Enum jodne ke baad.
import enum
import importlib
import inspect
import logging
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

# Jin files mein state ke types hote hain (checkpointer ki list se alag bhi check karte hain,
# taaki koi nayi file chhoot jaye to pakda jaye)
CANDIDATES = ["schemas", "tool_argument_models", "tool_argument_common", "models",
              "router_schema"]


def main():
    logging.disable(logging.WARNING)
    from checkpointer import make_serde, _STATE_MODULES
    serde = make_serde()
    bad, total = [], 0
    for modname in CANDIDATES:
        mod = importlib.import_module(modname)
        for name, obj in vars(mod).items():
            if inspect.isclass(obj) and issubclass(obj, enum.Enum) and obj is not enum.Enum \
                    and obj.__module__ == modname and len(obj):
                member = next(iter(obj))
                back = serde.loads_typed(serde.dumps_typed({"x": member}))["x"]
                total += 1
                if type(back) is not obj:
                    bad.append(f"{modname}.{name} → wapas aaya {type(back).__name__} ({back!r})")
    missing = [m for m in CANDIDATES if m not in _STATE_MODULES]
    print(f"Checked {total} Enum types.")
    if missing:
        print(f"⚠️  checkpointer._STATE_MODULES mein nahi: {missing}")
    if bad:
        print("❌ Ye types checkpoint se sahi wapas nahi aaye (checkpointer.py ki list mein jodo):")
        for b in bad:
            print("   -", b)
        sys.exit(1)
    print("✅ Saare types checkpoint se sahi wapas aate hain.")


if __name__ == "__main__":
    main()
