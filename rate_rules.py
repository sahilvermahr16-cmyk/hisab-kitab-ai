# rate_rules.py — bikri / maal ki entry mein rate, ginti aur total ka hisaab (code se, LLM se nahi).
#
#   1. total khaali / 0, rate aur ginti hain      → total = rate × ginti   ("8 rupaye eent ke hisab se, 1000 eent")
#   2. "total" ginti se bhi chhota aur rate khaali → wo asal mein RATE hai ("1000 eent 8 mein" → 8 × 1000)
#      (sirf jab ginti ≥ 20 aur "total" ≤ 100 — 1000 eent ₹8 mein nahi bikti)
#   Wapsi (ginti/total minus mein) ko nahi chhoota.


def _f(x):
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def fix_rate_amount(arguments) -> list:
    changes = []
    amount, rate, qty = _f(getattr(arguments, "amount", None)), _f(getattr(arguments, "rate", None)), \
        _f(getattr(arguments, "quantity", None))
    if qty is None or qty <= 0:
        return changes
    if (amount in (None, 0)) and rate and rate > 0:
        arguments.amount = rate * qty
        changes.append(f"amount khaali tha → rate {rate:g} × ginti {qty:g} = {rate * qty:g}")
    elif amount and 0 < amount <= 100 and qty >= 20 and amount < qty and not rate:
        arguments.rate = amount
        arguments.amount = amount * qty
        changes.append(f"{amount:g} total nahi, rate hai → {amount:g} × {qty:g} = {amount * qty:g}")
    return changes


def fix_return_sign(arguments, text) -> list:
    """Wapsi (wapas / return / वापस) → ginti aur rakam minus. Bina wapsi ke minus → ginti plus,
    rakam khaali (tab system rakam poochega — andaze se minus bikri nahi banegi)."""
    from sale_rules import is_return
    changes = []
    qty, amt = _f(getattr(arguments, "quantity", None)), _f(getattr(arguments, "amount", None))
    if is_return(text):
        if qty and qty > 0:
            arguments.quantity = -qty
            changes.append(f"ginti {qty:g} → {-qty:g}")
        if amt and amt > 0:
            arguments.amount = -amt
            changes.append(f"rakam {amt:g} → {-amt:g}")
    else:
        if qty is not None and qty < 0:
            arguments.quantity = -qty
            changes.append(f"wapsi ka shabd nahi — ginti {qty:g} → {-qty:g}")
        if amt is not None and amt < 0:
            arguments.amount = None
            changes.append(f"wapsi ka shabd nahi — rakam {amt:g} hataayi (poochenge)")
    return changes


import re as _re
_WALE = _re.compile(r"\s+(?:wale|wala|wali|वाले|वाला|वाली)\s*$", _re.IGNORECASE)
_HI_DESC = {"होटल", "दुकान", "ढाबा", "साइट", "गाँव", "गांव", "ठेकेदार", "मिस्त्री", "फैक्ट्री", "शोरूम"}


# Naam se PEHLE wali pehchaan: brand / shehar / purani jagah — supplier ka naam nahi.
_NAMEY_END = {"ji", "jee", "sahab", "saab", "sahib", "bhai", "bhaiya", "mills", "mill", "traders", "trader",
              "store", "stores", "enterprises", "agency", "जी", "साहब", "भाई", "मिल्स", "ट्रेडर्स"}
_NOT_NAME = {"bhatta", "bhatte", "bhate", "bhata", "plot", "site", "shop", "dukaan", "dukan", "gudam", "godown",
             "ghar", "building", "makaan", "mandi", "भट्टा", "भट्टे", "प्लॉट", "साइट", "दुकान", "गोदाम", "घर"}
_PREFIX_DEALER = _re.compile(
    r"^(?P<desc>.+?\s+(?:ke|ki|ka|के|की|का)\s+(?:dealer|agent|distributor|supplier|डीलर|एजेंट))\s+(?P<name>\S.*)$",
    _re.IGNORECASE)
_PREFIX_WALE = _re.compile(r"^(?P<desc>.+?\s+(?:wale|wala|wali|वाले|वाला|वाली))\s+(?P<name>\S.*)$", _re.IGNORECASE)
_PREFIX_PLACE = _re.compile(r"^(?P<desc>[A-Za-z\u0900-\u097F]+)\s+(?:ke|ki|ka|के|की|का)\s+(?P<name>\S.*)$",
                            _re.IGNORECASE)


def _namey(name):
    words = name.split()
    if not words or _WALE.search(name) or any(w.lower() in _NOT_NAME for w in words):
        return False
    return words[-1].lower() in _NAMEY_END or (words[0][:1].isupper() and words[0].isascii())


def split_descriptor(name):
    """
    Naam se pehle ki pehchaan alag: (naam, pehchaan) — pehchaan na ho to (name, None).
      'UltraTech ke dealer Bansal'        → ('Bansal', 'UltraTech ke dealer')
      'Kajaria wale Mittal ji'            → ('Mittal ji', 'Kajaria wale')
      'Saharanpur ke Irfan bhai'          → ('Irfan bhai', 'Saharanpur ke')
      'Ludhiana ki Gill mills'            → ('Gill mills', 'Ludhiana ki')
      'Sharma ji ki site' / 'Shiv wale bhatte' → badlaav nahi
    """
    if not isinstance(name, str):
        return name, None
    n = " ".join(name.split())
    m = _PREFIX_DEALER.match(n)
    if m:
        return m.group("name"), m.group("desc")
    m = _PREFIX_WALE.match(n)
    if m and _namey(m.group("name")):
        return m.group("name"), m.group("desc")
    m = _PREFIX_PLACE.match(n)
    if m and _namey(m.group("name")) and m.group("name").split()[-1].lower() in _NAMEY_END \
            and m.group("desc").lower() not in _NAMEY_END:
        return m.group("name"), n[: len(n) - len(m.group("name"))].strip()
    return name, None


def strip_descriptor(name: str) -> str:
    """
    'Raju hotel wale' → 'Raju' ; 'Suresh Traders wale' → 'Suresh Traders' (bade akshar = naam ka hissa)
    'राजू होटल वाले' → 'राजू' ; 'UltraTech ke dealer Bansal' → 'Bansal' (split_descriptor)
    """
    if isinstance(name, str):
        name = split_descriptor(name)[0]
    if not isinstance(name, str) or not _WALE.search(name):
        return name
    words = _WALE.sub("", name).split()
    if len(words) > 1:
        last = words[-1]
        if (last.isascii() and last[:1].islower()) or last in _HI_DESC:
            words = words[:-1]
    return " ".join(words) or name


# "6500 ka hazaar rate" — bhatte ka bhav HAZAAR eent ka hota hai: 6500 / 1000 = 6.5 ek eent.
_PER_BULK = _re.compile(
    r"(?P<n>\d+(?:\.\d+)?)\s*(?:rupaye\s+|rs\.?\s+|₹\s*|रुपये\s+)?(?:ka|ke|ki|per|prati|/|का|के|की|प्रति)\s*"
    r"(?P<unit>hazaar|hazar|hajaar|hajar|thousand|हज़ार|हजार|sau|hundred|सौ)(?![\w\u0900-\u097F])",
    _re.IGNORECASE)


def fix_per_bulk_rate(arguments, text) -> list:
    """'1500 eent, 6500 ka hazaar' → rate 6.5, total 9750 (rate/total jo LLM ne 6500 likha tha, theek)."""
    changes = []
    m = _PER_BULK.search(text or "")
    qty = _f(getattr(arguments, "quantity", None))
    if not m or not qty or qty <= 0 or not hasattr(arguments, "rate"):
        return changes
    n = float(m.group("n"))
    div = 100 if m.group("unit").lower() in ("sau", "hundred", "सौ") else 1000
    if qty < div / 10:                       # 5 trolley "6500 ka hazaar" — ye bhav eent ka nahi, mat chhedo
        return changes
    rate = n / div
    old_rate, old_amt = _f(getattr(arguments, "rate", None)), _f(getattr(arguments, "amount", None))
    if old_rate == rate and old_amt is not None and abs(old_amt - rate * qty) < 0.01:
        return changes
    arguments.rate = rate
    arguments.amount = round(rate * qty, 2)
    changes.append(f"'{m.group(0)}' = {n:g} har {div} ka → rate {rate:g}, total {rate:g} × {qty:g} = {rate * qty:g}"
                   f" (pehle rate {old_rate}, total {old_amt})")
    return changes


# "2 dumper bajri, 9000 ka dumper" / "360 ki bori" / "1600 ka tin" — har EK ka bhav. LLM kabhi total = 9000 likh deta.
_PER_UNIT = _re.compile(
    r"(?P<n>\d+(?:\.\d+)?)\s*(?:rupaye\s+|rs\.?\s+|₹\s*|रुपये\s+)?(?:ka|ki|ke|per|prati|/|का|की|के)\s*"
    r"(?P<u>dumper|dampar|trolley|trali|bori|bora|bag|tin|tanker|truck|tempo|gaadi|fatta|fatte|piece|peti|katta|"
    r"डंपर|ट्रॉली|बोरी|टिन|ट्रक)(?![\w\u0900-\u097F])", _re.IGNORECASE)


def fix_per_unit_rate(arguments, text) -> list:
    """'<N> ka dumper' → rate N, total N × ginti (sirf jab LLM ne total N likha ya khaali chhoda)."""
    changes = []
    m = _PER_UNIT.search(text or "")
    qty = _f(getattr(arguments, "quantity", None))
    if not m or not qty or qty <= 1 or qty > 500 or not hasattr(arguments, "rate"):
        return changes
    n = float(m.group("n"))
    amt = _f(getattr(arguments, "amount", None))
    if amt is not None and abs(amt - n) > 0.01 and amt != 0:
        return changes                       # total kuch aur likha hai — andaza nahi
    arguments.rate = n
    arguments.amount = n * qty
    changes.append(f"'{m.group(0)}' = har ek ka bhav → rate {n:g}, total {n:g} × {qty:g} = {n * qty:g} (pehle total {amt})")
    return changes


_TON_IN_TEXT = _re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*(?:ton|tan|टन)(?![\w\u0900-\u097F])", _re.IGNORECASE)


def fix_ton_kg(arguments, text) -> list:
    """'2 ton … 32 rupaye kilo' → LLM ne ginti 2000 (kg) par unit 'ton' rakha. Unit kg karo (rate kilo ka hai)."""
    m = _TON_IN_TEXT.search(text or "")
    qty = _f(getattr(arguments, "quantity", None))
    unit = getattr(getattr(arguments, "unit", None), "value", getattr(arguments, "unit", None))
    if m and qty and str(unit).lower() == "ton" and abs(qty - float(m.group("n")) * 1000) < 0.01:
        return ["kg"]
    return []
