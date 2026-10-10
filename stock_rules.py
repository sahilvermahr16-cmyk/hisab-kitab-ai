# stock_rules.py — Stock / Gudam ke shabd (grouping + tool decision + argument ke safety nets).
#   • toota / kharab / ginti mein kam-zyada → record_adjustment (stock badla, maal kahin gaya nahi)
#   • adjustment ki disha: toota/kam → minus, zyada mila → plus
#   • unit na bola ho → bori/ton/kg se, warna piece
import re

STOCK_CHANGE = re.compile(
    r"\b(toot\w*|tooti|tuti|tute|tut\s+gay\w*|phoot\w*|kharab|bekaar|bekar|sad\s+gay\w*|gal\s+gay\w*|jung|damage\w*|"
    r"chori|gum\s+ho\w*|kam\s+(?:nikl\w*|hain|hai|he|h|mil\w*|the|thi|tha)|zyada\s+(?:nikl\w*|mil\w*)|jyada\s+(?:nikl\w*|mil\w*)|"
    r"extra\s+(?:nikl\w*|mil\w*)|broken|short|missing)\b"
    r"|टूट|ख़राब|खराब|बेकार|जंग|कम\s+(?:निकल|हैं|है|मिल)|ज़्यादा\s+(?:निकल|मिल)|ज्यादा\s+(?:निकल|मिल)", re.IGNORECASE)

_MORE = re.compile(r"\b(zyada|jyada|extra|adhik)\b|ज़्यादा|ज्यादा", re.IGNORECASE)


def stock_sign(text: str):
    """+1 (zyada mila) / -1 (toota, kharab, kam) / None"""
    if not STOCK_CHANGE.search(text or ""):
        return None
    return 1 if _MORE.search(text or "") else -1


def unit_from_text(text: str) -> str:
    t = (text or "").lower()
    if re.search(r"\b(bori|boriyan|boriya|bag|bags)\b|बोरी", t):
        return "bag"
    if re.search(r"\b(ton|tonne)\b|टन", t):
        return "ton"
    if re.search(r"\b(kg|kilo|kilogram)\b|किलो", t):
        return "kg"
    if re.search(r"\b(trolley|trali)\b|ट्रॉली", t):
        return "trolley"
    return "piece"


PLACE_WORD = re.compile(r"\b(gudam|godam|godown|gudm|shop|dukaan|dukan)\b|गोदाम|दुकान", re.IGNORECASE)


def place_in(text: str):
    m = PLACE_WORD.search(text or "")
    if not m:
        return None
    w = m.group(0).lower()
    return "Shop" if w in ("shop", "dukaan", "dukan", "दुकान") else "Gudam"
