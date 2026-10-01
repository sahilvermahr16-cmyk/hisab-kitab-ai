# checkpointer.py
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

_checkpointer = None  # Singleton — ek baar banana hai

async def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        conn = await aiosqlite.connect("checkpoints.db")
        _checkpointer = AsyncSqliteSaver(conn)
    return _checkpointer