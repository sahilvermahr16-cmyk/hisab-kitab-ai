# note_rules.py — LLM ke bhare "note" ki code se jaanch (sab tools ke liye).
#
#   1. note se date ("on 2026-10-05") hata do — date ka apna field hai
#   2. note mein naam / amount / payment ke shabd / bekaar tukde ("wahan kaam kiya",
#      "ke saath hisab hua") ke alawa KUCH na bache → note = None
#   Asli jaankari wale note ko badla nahi jaata — sirf bekaar note hataya jaata hai.
import re

_DATE = re.compile(r"\s*\b(on\s+)?\d{4}-\d{2}-\d{2}\b\.?", re.IGNORECASE)

# in shabdon ke alawa kuch na ho to note bekaar hai
_FILLER = {
    # hinglish
    "wahan", "vahan", "waha", "vaha", "yahan", "yaha", "udhar", "idhar", "ka", "ke", "ki", "ko", "ne", "se",
    "mein", "me", "main", "par", "pe", "pr", "kaam", "kam", "kiya", "kia", "kiye", "kar", "karke", "diya",
    "diye", "de", "di", "dena", "hua", "hui", "hue", "huye", "aur", "bhi", "tha", "thi", "the", "hai", "hain",
    "saath", "sath", "rupaye", "rupay", "rs", "aaj", "aj", "kal", "parso", "hisab", "hisaab", "ho", "gaya",
    "gayi", "le", "liye", "liya", "bheje", "bheja", "uska", "uske", "usko", "use", "ka", "wala", "wali",
    "cash", "nakad", "naqad", "upi", "phonepe", "paytm", "gpay", "google", "pay", "bank", "khaate", "khate",
    "account", "online", "transfer", "payment", "work", "worth", "paid", "gave", "sent", "did", "done",
    # english
    "there", "here", "to", "him", "her", "the", "a", "an", "of", "for", "and", "with", "today", "yesterday",
    "in", "on", "at", "was", "is", "his",
    # hindi
    "वहाँ", "वहां", "यहाँ", "का", "के", "की", "को", "ने", "से", "में", "पर", "काम", "किया", "दिए", "दिया",
    "हुआ", "और", "भी", "था", "थी", "थे", "है", "साथ", "रुपये", "आज", "कल", "हिसाब", "नकद", "कैश", "खाते",
}
_TOKEN = re.compile(r"[\wऀ-ॿ]+")


def _names(args: dict) -> set:
    out = set()
    for k, v in args.items():
        if isinstance(v, str) and k.endswith("_name") and v.strip():
            out |= {w.lower() for w in _TOKEN.findall(v)}
    return out


def clean_note(note, args: dict):
    """Returns (naya note, badlaav ka kaaran ya None)."""
    if not isinstance(note, str) or not note.strip():
        return note, None
    new = _DATE.sub("", note).strip(" ,.;-")
    names = _names(args)
    rest = [w for w in _TOKEN.findall(new.lower())
            if w not in _FILLER and w not in names and not w.isdigit()]
    if not rest:
        return None, f"note '{note}' mein koi asli jaankari nahi — hataya"
    if new != note:
        return new, f"note se date hatayi: '{note}' → '{new}'"
    return note, None
