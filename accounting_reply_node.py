# accounting_reply_node.py
"""
Accounting pipeline ka aakhri node — user ko asli jawab deta hai.

Pehle pipeline ke end mein koi AIMessage nahi banta tha, isliye main.py
"Bot:" ke aage user ka hi statement dikha deta tha. Ab yahan tool ke apne
messages ("✅ Ram ko ₹500 payment record ho gayi...") aur correction ka
nateeja ek saath jawab bante hain.
"""
from langchain_core.messages import AIMessage


def _correction_line(cd: dict) -> str | None:
    if not cd or cd.get("skip"):
        return None
    if cd.get("cancelled"):
        return "Correction cancel kiya — kuch nahi badla."
    if cd.get("report_shown") and not cd.get("action_choice"):
        return "Report dikha di. Correction ke liye sahi entry ke baare mein poora statement bhejo."
    if cd.get("action_choice") == "delete":
        if cd.get("delete_done"):
            return "✅ Correction ho gaya — galat entry hata di (hisab mein ab nahi dikhegi)."
        if cd.get("delete_error"):
            return f"❌ Galat entry hatate waqt error aaya: {cd['delete_error']}"
    if cd.get("action_choice") == "statement":
        if cd.get("statement_dropped"):
            return "Naya statement khud ek correction tha, isliye chhod diya. Purani entry waisi hi hai."
        if cd.get("statement_cancelled"):
            return "Naya statement cancel hua — purani entry waisi hi hai, kuch nahi badla."
        if cd.get("statement_execution_failed"):
            return "❌ Naya statement record nahi ho paya — purani entry waisi hi hai."
        if cd.get("statement_reversal_error"):
            return f"⚠️ Nayi entry record ho gayi, lekin purani hatate waqt error: {cd['statement_reversal_error']}"
        if cd.get("statement_done"):
            return "✅ Correction ho gaya — purani entry hata ke nayi sahi entry daal di."
    if cd.get("category") and not cd.get("matches"):
        return "Correction ke liye koi matching entry nahi mili."
    return None


def _unrecorded_money_lines(state) -> list:
    """Amount wale action jinka koi tool nahi chuna gaya (aur 'nahi hua/plan' bhi nahi) — chupke se mat chhodo."""
    try:
        from tool_decision_node import _money_without_tool
    except Exception:
        return []
    groups = {g.group_id: g for g in (getattr(state.get("grouped_intent"), "groups", None) or [])}
    out = []
    for res in state.get("tool_decision_results") or []:
        group = groups.get(res.group_id)
        if group is None:
            continue
        for i in _money_without_tool(res, group):
            out.append(f"⚠️ Ye samajh nahi aaya, isliye record NAHI hua: \"{group.actions[i].text}\" "
                       f"— thoda saaf likh ke dobara bhejo (kisko/kisse, kitna).")
    return out


async def accounting_reply_node(state):
    lines = [str(r) for r in (state.get("tool_execution_results") or []) if r]
    lines += _unrecorded_money_lines(state)
    corr = _correction_line(state.get("correction_data") or {})
    if corr:
        lines.append(corr)
    if not lines:
        lines = ["Kuch record nahi hua."]
    return {"messages": [AIMessage(content="\n".join(lines))]}
