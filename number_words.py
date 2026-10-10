# number_words.py — shabdon mein likhe number ko ankon mein (LLM ko bhejne se pehle).
#
# gpt-4o-mini "saade teen hazaar" ko kabhi 3300 bana deta hai — hisaab ka kaam code karega.
#   "dedh hazaar"        → 1500        "saade teen hazaar" → 3500
#   "teen sau"           → 300         "dhai sau"          → 250
#   "sava do hazaar"     → 2250        "paune paanch sau"  → 475
#   "do hazaar paanch sau" → 2500      "5k" / "1.5k"       → 5000 / 1500
#   "डेढ़ हज़ार" → 1500 ; "one and a half thousand" → 1500 ; "three hundred" → 300
#
# Suraksha: sirf wahi badalta hai jisme sau/hazaar/lakh (ya dedh/dhai/saade/sava/paune) ho.
# Akela "do" ("de do"), "ek" ("ek din"), "saath" ("ke saath") kabhi nahi chhoota.
import re

_UNITS = {
    # hinglish
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "pach": 5,
    "chhe": 6, "chhah": 6, "che": 6, "chah": 6, "saat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "gyara": 11, "barah": 12, "bara": 12, "terah": 13, "tera": 13, "chaudah": 14, "chauda": 14,
    "pandrah": 15, "pandra": 15, "solah": 16, "sola": 16, "satrah": 17, "satra": 17, "atharah": 18,
    "athara": 18, "unnis": 19, "bees": 20, "bis": 20, "pachees": 25, "pachchis": 25, "tees": 30, "tis": 30,
    "chalis": 40, "chaalees": 40, "chaalis": 40, "pachaas": 50, "pachas": 50, "saath": 60, "sattar": 70,
    "assi": 80, "nabbe": 90,
    # hindi
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "छे": 6, "सात": 7,
    "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "पंद्रह": 15, "बीस": 20, "पच्चीस": 25,
    "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90,
    # english
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty-five": 25, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "a": 1, "an": 1,
}
_MULT = {
    "sau": 100, "so": 100, "सौ": 100, "hundred": 100,
    "hazaar": 1000, "hazar": 1000, "hajaar": 1000, "hajar": 1000, "hazaar,": 1000, "हज़ार": 1000,
    "हजार": 1000, "thousand": 1000,
    "lakh": 100000, "lac": 100000, "laakh": 100000, "लाख": 100000,
}
_HALF_TIMES = {"dedh": 1.5, "derh": 1.5, "डेढ़": 1.5, "डेढ": 1.5, "dhai": 2.5, "dhaai": 2.5, "ढाई": 2.5}
_PLUS = {"saade": 0.5, "sade": 0.5, "saadhe": 0.5, "साढ़े": 0.5, "साढे": 0.5,
         "sava": 0.25, "sawa": 0.25, "सवा": 0.25,
         "paune": -0.25, "pone": -0.25, "पौने": -0.25}
_JOIN = {"aur", "and", "और"}
_ONLY_WITH_DIGITS = {"a", "an", "so"}         # "a thousand", "paanch so" — akele kabhi number nahi

_K = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s?[kK](?!\w)")
_TOKEN = re.compile(r"[^\s,;।]+")


def _num(tok):
    t = tok.lower()
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return float(t)
    return _UNITS.get(t)


def _parse(words, i):
    """words[i:] se number padho. Returns (value, next_index) ya None (koi multiplier/fraction nahi)."""
    total, j, used = 0.0, i, False
    n = len(words)
    while j < n:
        w = words[j].lower()
        nxt = words[j + 1].lower() if j + 1 < n else ""
        if w in _PLUS and j + 2 < n and _num(words[j + 1]) is not None and words[j + 2].lower() in _MULT:
            total += (_num(words[j + 1]) + _PLUS[w]) * _MULT[words[j + 2].lower()]
            j, used = j + 3, True
            continue
        if w in _HALF_TIMES and nxt in _MULT:
            total += _HALF_TIMES[w] * _MULT[nxt]
            j, used = j + 2, True
            continue
        v = _num(words[j])
        if v is not None and nxt in _MULT and not (w in _ONLY_WITH_DIGITS and nxt == "so"):
            if nxt == "so" and w in _UNITS and _UNITS[w] > 9:
                break
            total += v * _MULT[nxt]
            j, used = j + 2, True
            continue
        # "one and a half thousand"
        if v is not None and j + 4 < n and [x.lower() for x in words[j + 1:j + 4]] == ["and", "a", "half"] \
                and words[j + 4].lower() in _MULT:
            total += (v + 0.5) * _MULT[words[j + 4].lower()]
            j, used = j + 5, True
            continue
        if used and w in _JOIN and j + 1 < n and _parse(words, j + 1):
            j += 1
            continue
        if used and v is not None and w not in _ONLY_WITH_DIGITS:      # "ek hazaar pachaas" → +50
            total += v
            j += 1
        break
    return (total, j) if used else None


def _fmt(v):
    return str(int(v)) if float(v).is_integer() else str(v)


def normalize_numbers(text: str) -> str:
    """Statement ke number-shabd → ank. Kuch na mile to text jaisa tha waisa."""
    if not text:
        return text
    out = _K.sub(lambda m: _fmt(float(m.group(1)) * 1000), text)
    spans = [(m.start(), m.end(), m.group(0)) for m in _TOKEN.finditer(out)]
    words = [w.strip(".!?") for _, _, w in spans]
    pieces, last, i = [], 0, 0
    while i < len(words):
        got = _parse(words, i)
        if got:
            value, j = got
            start, end = spans[i][0], spans[j - 1][0] + len(words[j - 1])
            pieces.append(out[last:start] + _fmt(value))
            last, i = end, j
        else:
            i += 1
    pieces.append(out[last:])
    return "".join(pieces)


if __name__ == "__main__":
    for t in ["Sharma ji ko teen sau eent saade teen hazaar mein di", "dedh hazaar eent le gaye 12000 ki",
              "sharma ji ne 5k de diye", "do hazaar paanch sau", "Ram ke saath gaya", "de do sau rupaye"]:
        print(t, "→", normalize_numbers(t))
