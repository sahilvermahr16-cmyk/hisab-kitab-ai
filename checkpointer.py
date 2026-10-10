# checkpointer.py
import importlib
import inspect

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

_checkpointer = None  # Singleton — ek baar banana hai

# Hamare apne Pydantic models / Enums jo graph state mein jaate hain. LangGraph
# checkpoint se inhe wapas padhte waqt sirf ALLOWED types ko wapas banata hai —
# jo list mein nahi, wo BLOCK hoke saadha text ban jaata hai (isi se material
# movement crash hua tha: models.MovementEntityType list mein nahi tha).
# ⚠️ Koi NAYI file bane jisme Enum / Pydantic class ho aur wo state mein jaaye →
#    uska naam yahan jodo, aur `python test/check_serde.py` chala ke check karo.
_STATE_MODULES = (
    "schemas",
    "tool_argument_models",
    "tool_argument_common",
    "models",            # MovementEntityType (material movement)
    "router_schema",
)


def _allowed_msgpack_types():
    allowed = []
    for modname in _STATE_MODULES:
        try:
            mod = importlib.import_module(modname)
        except Exception as e:  # noqa: BLE001 — ek file toot jaye to bhi app chale
            print(f"⚠️ checkpointer: '{modname}' import nahi hua ({e}) — iske types allowlist mein nahi")
            continue
        for name, obj in vars(mod).items():
            if inspect.isclass(obj) and obj.__module__ == modname:
                allowed.append((modname, name))
    return allowed


def make_serde():
    try:
        return JsonPlusSerializer(allowed_msgpack_modules=_allowed_msgpack_types())
    except TypeError:          # purana langgraph — ye option hi nahi tha
        return JsonPlusSerializer()


async def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        conn = await aiosqlite.connect("checkpoints.db")
        _checkpointer = AsyncSqliteSaver(conn, serde=make_serde())
    return _checkpointer
