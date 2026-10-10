# sale_rules.py — bikri aur customer ke paise ke pakke niyam (LLM ke baad code se jaanch).
#
#   RECEIVED : "poore paise mil gaye", "GPay se payment aayi", "पैसे मिल गए", "got paid"
#              → bikri ke saath payment bhi hui
#   ALREADY  : "5000 advance pehle hi de chuke the", "already paid", "पहले ही दे चुके"
#              → purana paisa, NAYI payment nahi
#   SERVICE  : "phone theek kiya, 800 liye" → seva bhi bikri hai (+ payment)
import re

RECEIVED = re.compile(
    r"\b(poore|pure|pura|poora|sab|saare|full)?\s*(paise|paisa|payment|rakam|amount|nakad|cash)\s+(bhi\s+)?"
    r"(mil gaye|mil gaya|mil gayi|mile|mila|aa gaye|aa gaya|aaye|aaya|aayi|aa gayi|de diye|de gaye|de diya)\b"
    r"|\b(payment|paise)\s+(aayi|aaya|aaye|aa gayi|mil gayi)\b"
    r"|(पूरे|सारे)?\s*(पैसे|पेमेंट|भुगतान)\s+(भी\s+)?(मिल गए|मिल गया|मिले|मिला|आ गए|आए|आई|आ गई)"
    r"|\b(got paid|paid in full|got the (full )?payment|payment (came|was received|received)|received the (full )?(payment|money))\b",
    re.IGNORECASE)
FULL = re.compile(r"\b(poore|pure|pura|poora|saare|sab|full|in full|whole)\b|पूरे|सारे|पूरा", re.IGNORECASE)

ALREADY = re.compile(
    r"\b(pehle hi|pahle hi|pehle se|already|de chuke|de chuka|de chuki|le chuke|pehle de diye the|"
    r"advance (?:pehle )?(?:diya|de diya|diye) (?:tha|the))\b"
    r"|पहले ही|पहले से|दे चुके|दे चुका|ले चुके",
    re.IGNORECASE)
NOW = re.compile(r"\b(aaj|abhi|ab|today|now)\b|आज|अभी", re.IGNORECASE)

SERVICE = re.compile(
    r"\b(theek kiya|theek ki|thik kiya|thik ki|repair kiya|repair ki|marammat|silai ki|silai kiya|service ki|"
    r"service kiya|banwaya|lagaya|fitting ki|repaired|fixed|stitched|serviced)\b"
    r"|ठीक किया|ठीक की|रिपेयर|मरम्मत|सिलाई",
    re.IGNORECASE)
CHARGED = re.compile(
    r"\b(liye|le liye|liya|mile|mila|charge kiye|charge kiya|charged|took|got)\b|लिए|ले लिए|मिले",
    re.IGNORECASE)


_NUM_CAME = re.compile(
    r"\d[\d,]*\s*(?:rupaye|rs)?\s*(mile|mila|aaye|aaya|aayi|diye|de diye|de gaye|jama|bheje)\b"
    r"|\d[\d,]*\s*(मिले|मिला|आए|आई|दिए|दे दिए|भेजे|जमा)|\b(received|paid|got)\s+(?:₹\s*)?\d",
    re.IGNORECASE)


def received(text):
    return bool(RECEIVED.search(text or ""))


def already_paid(text):
    """Purana diya hua paisa — aur 'aaj/abhi' ki nayi payment ki baat nahi."""
    t = text or ""
    return bool(ALREADY.search(t)) and not (NOW.search(t) and (RECEIVED.search(t) or _NUM_CAME.search(t)))


def service_charge(text):
    t = text or ""
    return bool(SERVICE.search(t) and re.search(r"\d", t) and CHARGED.search(t))


RETURN = re.compile(
    r"\b(wapas|vapas|waapas|lauta|lautaya|lautayi|lauta di|lauta diye|return|returned|returns)\b"
    r"|वापस|लौटा|लौटाई|लौटाए",
    re.IGNORECASE)
# "jo 1000 eent li thi", "parso di thi", "that they took" — pehle ho chuki bikri ka sirf zikr
PAST_SALE = re.compile(
    r"\b(li thi|li thi,|liye the|le gaye the|le gaya tha|le gayi thi|di thi|diye the|bheji thi|bheje the|"
    r"gayi thi|gaye the|bechi thi|beche the|they took|had taken|took earlier|bought earlier)\b"
    r"|ली थी|लिए थे|ले गए थे|दी थी|दिए थे|भेजी थी|बेची थी",
    re.IGNORECASE)
# saamaan diya: ginti + unit / saamaan, aur dene ki kriya
GOODS_GIVEN = re.compile(
    r"\d+\s*(kilo|kg|litre|liter|ltr|bori|bag|bags|piece|pcs|trolley|tin|sqft|ton|darjan|dozen|"
    r"किलो|लीटर|बोरी|ट्रॉली|टिन)(?=[\s,.]|$)",
    re.IGNORECASE)
GIVE_VERB = re.compile(
    r"\b(diye|diya|di|de diye|de di|bechi|becha|beche|bheji|bheja|gave|sold|sent|supplied)\b"
    r"|दिए|दिया|दी|बेची|बेचा|भेजी",
    re.IGNORECASE)


def is_return(text):
    return bool(RETURN.search(text or ""))


_REF = re.compile(r"\b(jo|uske|uska|unke|unka|for the|of the|that they)\b|जो|उसके|उनके", re.IGNORECASE)
_PRICE = re.compile(r"\d[\d,]*\s*(mein|me|ki|ka)\b|\d[\d,]*\s*(में|की|का)(?=[\s,.]|$)|\bfor\s+₹?\s*\d", re.IGNORECASE)


def past_sale_reference(text):
    """
    Purani bikri ka sirf ZIKR + aaj ka paisa ("jo 1000 eent li thi uske 4000 aaj de gaye").
    Agar purani bikri ka DAAM bhi likha hai ("kal 600 eent 5400 mein di thi, aaj 3000 bheje")
    to wo nayi entry hai — zikr nahi.
    """
    t = text or ""
    money_now = _NUM_CAME.search(t) or RECEIVED.search(t) or re.search(
        r"\b(de gaye|de gaya|de diye|paid)\b|दे गए|दे दिए", t, re.IGNORECASE)
    return bool(PAST_SALE.search(t) and _REF.search(t) and money_now and not _PRICE.search(t))


_MONEY_IN = re.compile(r"\b(mile|mila|mil gaye|mil gaya|aaye|aaya|aayi|jama|de gaye|bheje|received|got)\b|मिले|मिला|मिल गए|आए|जमा", re.IGNORECASE)


def goods_given(text):
    """Customer ko saamaan diya (ginti + unit + dene ki kriya), paisa aane ki baat nahi."""
    t = text or ""
    return bool(GOODS_GIVEN.search(t) and GIVE_VERB.search(t) and not _MONEY_IN.search(t))


# ---- maal aaj hila? (grouping + tool decision dono yahi use karte hain)
_GOODS_EXTRA = ["eent", "int", "ईंट", "इंट", "brick", "bricks", "malba", "मलबा", "khidki", "khidkiyan", "खिड़की",
                "lakdi", "lakad", "लकड़ी", "timber", "patthar", "पत्थर", "reta", "ret", "रेता", "रेत", "bajri", "बजरी",
                "cement", "सीमेंट", "maal", "माल", "saman", "samaan", "सामान", "goods", "gate", "गेट", "darwaza",
                "darwaze", "दरवाज़ा", "दरवाज़े", "tile", "tiles", "टाइल", "cheeni", "चीनी", "sugar", "doodh", "दूध", "milk",
                "aloo", "आलू", "potato", "potatoes", "kapda", "कपड़ा", "cloth", "loha", "लोहा", "iron", "suit", "सूट",
                "sabzi", "सब्ज़ी", "atta", "आटा", "gehu", "गेहूं", "pipe", "पाइप", "fatte", "फट्टे", "planks", "sand", "gravel",
                "cupboard", "cupboards", "almari", "अलमारी", "paint", "पेंट", "chaukhat", "चौखट"]
_UNIT_QTY = re.compile(
    r"\d[\d,]*\s*(fatte|fatta|trolley|trolleys|bori|boriyan|bag|bags|kilo|kg|litre|liter|ton|tin|tins|sqft|"
    r"piece|pcs|dumper|dumpers|meter|metre|metres|darjan|dozen|sacks?|loads?|"
    r"फट्टे|ट्रॉली|बोरी|किलो|लीटर|टन|टिन|डंपर|मीटर)(?=[\s,.]|$)",
    re.IGNORECASE)
_GOODS_RE = None


def has_goods(text: str) -> bool:
    """Statement mein koi MAAL hai? (saamaan ka naam, 'maal/saman', ya ginti + unit)"""
    global _GOODS_RE
    if _GOODS_RE is None:
        from item_mapper import ITEM_ALIASES
        words = {w for w in list(ITEM_ALIASES) + _GOODS_EXTRA if w and w not in ("misc", "miscellaneous", "अन्य")}
        _GOODS_RE = re.compile(r"(?<![\w\u0900-\u097F])(" + "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True))
                               + r")(?![\w\u0900-\u097F])", re.IGNORECASE)
    # "reta wale", "aara wale", "the sand supplier", "cement ke dealer" — pehchaan hai, maal nahi
    t = _DESC_WORDS.sub(" ", text or "")
    return bool(_GOODS_RE.search(t) or _UNIT_QTY.search(t))


_DESC_WORDS = re.compile(
    r"[\w\u0900-\u097F]+\s+(?:wale|wala|wali|ke dealer|ka dealer|वाले|वाला|वाली|के डीलर)(?![\w\u0900-\u097F])"
    r"|\bthe\s+\w+\s+(?:supplier|dealer|guy|wala|owner)\b",
    re.IGNORECASE)


# "3000 nayi gudam mein aayi" — LLM ne item "nayi" likh diya. Vishesan item nahi hota.
ITEM_ADJECTIVES = {"nayi", "naya", "nai", "naye", "nae", "purani", "purana", "purane", "tooti", "tuti", "tooti hui",
                   "baaki", "baki", "wali", "wala", "wale", "achhi", "kharab", "new", "old", "broken",
                   "नई", "नया", "पुरानी", "पुराना", "टूटी", "बाकी"}


def goods_word(text: str):
    """Text ka pehla saamaan wala shabd (eent, reta, lakdi…) — vishesan chhod ke. Na mile to None."""
    has_goods("")                                   # _GOODS_RE bana do
    for m in _GOODS_RE.finditer(_DESC_WORDS.sub(" ", text or "")):
        if m.group(1).lower() not in ITEM_ADJECTIVES:
            return m.group(1)
    return None
