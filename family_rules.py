# family_rules.py — Ghar / Family ke shabd (grouping + tool decision ke safety nets).
#
#   • galla / galle / dukaan — paisa rakhne ki JAGAH hai, party nahi ("paise galle se diye")
#   • rishte ke shabd — Mummy, Bhai, Beti, Chhote… — naam ki tarah ("Beti ki school van ke 1200")
#   • ghar ke kharche ke shabd — ration, sabzi, dawai, shagun, fees… — kabhi party nahi
#   • "ghar ka nahi, gudam ka kiraya" — ghar ka kharcha NAHI
import re

# paisa rakhne ki jagah (party kabhi nahi)
TILL = re.compile(
    r"^\s*(galla|galle|gale|gala|gullak|gulak|galla\s+box|cash\s+box|dukaan|dukkaan|dukan|shop|gudam|godam|"
    r"business|counter|गल्ला|गल्ले|गुल्लक|दुकान|गोदाम)\s*$", re.IGNORECASE)
TILL_WORD = re.compile(
    r"\b(galla|galle|gullak|gulak)\b|गल्ला|गल्ले|गुल्लक|\b(dukaan|dukan|shop)\s+se\b|दुकान\s+से", re.IGNORECASE)

# rishte ke shabd → naam ki tarah
_REL = {
    "mummy": "Mummy", "mummi": "Mummy", "mumy": "Mummy", "mammi": "Mummy", "mumma": "Mummy", "mom": "Mummy",
    "maa": "Maa", "mata ji": "Mata ji", "papa": "Papa", "pita ji": "Pita ji", "dad": "Papa",
    "bhai": "Bhai", "bhaiya": "Bhaiya", "brother": "Bhai", "chhote": "Chhote", "chhota": "Chhote", "chote": "Chhote",
    "behen": "Behen", "bahen": "Behen", "didi": "Didi", "sister": "Behen",
    "beta": "Beta", "bete": "Beta", "son": "Beta", "beti": "Beti", "daughter": "Beti",
    "bhabhi": "Bhabhi", "biwi": "Biwi", "wife": "Biwi", "patni": "Biwi", "bahu": "Bahu",
    "chacha": "Chacha", "chachi": "Chachi", "tau": "Tau", "tai": "Tai", "dada": "Dada", "dadi": "Dadi",
    "nana": "Nana", "nani": "Nani", "mama": "Mama", "mami": "Mami", "jija": "Jija",
    "मम्मी": "मम्मी", "माँ": "माँ", "मां": "माँ", "पापा": "पापा", "भाई": "भाई", "छोटे": "छोटे", "बहन": "बहन",
    "दीदी": "दीदी", "बेटा": "बेटा", "बेटी": "बेटी", "भाभी": "भाभी", "पत्नी": "पत्नी", "बीवी": "बीवी",
    "चाचा": "चाचा", "चाची": "चाची", "दादा": "दादा", "दादी": "दादी",
}
_REL_RE = re.compile(
    r"(?<![\wऀ-ॿ])(" + "|".join(sorted((re.escape(k) for k in _REL), key=len, reverse=True))
    + r")(?![\wऀ-ॿ])", re.IGNORECASE)


def relation_person(text: str):
    """Text mein rishte ka shabd (naam ki jagah) → us rishte ka naam. 'Ramesh bhai' / 'Chhote bhai Rohit' → None
    (wahan asli naam hai, wahi rahega)."""
    for m in _REL_RE.finditer(text or ""):
        before = (text[:m.start()].split() or [""])[-1]
        rest = [w for w in text[m.end():].split()]
        while rest and rest[0].strip(",.").lower() in _REL:
            rest = rest[1:]                # "Chhote bhai Rohit" — rishte ke shabd laangh ke asli naam dekho
        after = rest[0] if rest else ""
        if before[:1].isupper() and before.lower() not in _REL and before.lower() not in ("ghar", "ki", "ke", "ka"):
            continue                       # "Ramesh bhai" — naam Ramesh
        if after[:1].isupper() and after.lower() not in _REL and not re.match(r"^(SBI|Ko|Ne|Ki|Ke)$", after):
            continue                       # "bhai Rohit" — naam Rohit
        return _REL.get(m.group(1).lower()) or _REL.get(m.group(1)) or m.group(1)
    return None


# ghar ke kharche ke shabd (cheez / kaam) — party nahi, dukaan ka kharcha bhi nahi
HOME_SPEND = re.compile(
    r"\b(ration|raashan|rashan|sabzi|sabji|subzi|dawai|dawa|dawaai|medicine|shagun|shaadi|tuition|coaching|"
    r"school|fees?|gas\s+cylinder|cylinder|mandir|daan|grocer(y|ies))\b"
    r"|राशन|सब्ज़ी|सब्जी|दवाई|दवा|शगुन|शादी|ट्यूशन|कोचिंग|स्कूल|फीस|सिलेंडर|मंदिर|दान", re.IGNORECASE)

# "ghar ka nahi" / "ghar ki nahi" — ghar ka kharcha NAHI
GHAR_NOT = re.compile(r"\b(ghar|ghr)\s+(ka|ki|ke)\s+(nahi|nahin|na)\b|घर\s+(का|की|के)\s+नहीं", re.IGNORECASE)

# "ghar → UNKNOWN" movement ki ghar wali side (kisi ka ghar nahi, apna ghar)
OWN_HOME = re.compile(r"^\s*(ghar|ghr|ghar\s+ke\s+liye|ghar\s+ka|home|house|घर|घर\s+के\s+लिए)\s*$", re.IGNORECASE)


# ───────────────────────────────────────────────────────────────
# Family len-den ki DISHA (galle ke nazariye se) — LLM "wapas"/"aaya" pe jama bana deta tha.
#   kharcha: "le gaya/gayi/gaye", "X ko … diye / wapas kar diye", "<cheez> N ka aaya", "galle se … gaye/nikale"
#   jama   : "galle mein daale/rakhe", "X ne … wapas kiye / lautaye", "wapas aa gaye (galle mein)"
# Pakka na ho → None (LLM ka jawaab rehta hai).
# ───────────────────────────────────────────────────────────────
_TOOK = re.compile(r"\ble\s+(gaya|gayi|gayee|gaye|gai|liye|liya|li)\b(?!\s+(tha|the|thi)\b)"
                   r"|\bnikal\w*|ले\s+(गया|गई|गए|लिए)(?!\s+(था|थे|थी))|निकाल", re.IGNORECASE)
_PUT_IN = re.compile(r"\b(daale|dale|daala|dala|daal\s+di\w*|rakhe|rakha|rakhi|rakh\s+di\w*|jama\s+kar\w*|jama\s+ki\w*)\b"
                     r"|\bwapas\s+aa\s+ga\w*|डाले|डाल\s+दिए|रखे|रख\s+दिए|जमा\s+कर|वापस\s+आ\s+गए", re.IGNORECASE)
_RETURNED_BY = re.compile(r"\bne\b[^,]*?\b(wapas|waapas|lauta\w*)\s*(kiye|kiya|ki|kar\s+di\w*|de\s+di\w*|diye|diya)?\b"
                          r"|ने[^,]*?(वापस|लौटा)", re.IGNORECASE)
_GAVE_TO = re.compile(r"\b(ko|unko|usko)\b[^,]*?\b(diye|diya|di|de\s+di\w*|pakdaye|pakda\w*|thama\w*|bhej\w*|"
                      r"wapas\s+kar\s+di\w*|lauta\s+di\w*)\b|को[^,]*?(दिए|दिया|दी|पकड़ाए|वापस\s+कर)", re.IGNORECASE)
_BOUGHT = re.compile(r"\d[\d,]*\s*(ka|ki|ke)\s+(aaya|aayi|aaye|aai|liya|li)\b|\b(aaya|aayi|aaye|aai)\b[^?]*?\d"
                     r"|\b(bhar\s+di\w*|bhari|bhara|lagwa\w*|kharid\w*)\b|का\s+आया|की\s+आई", re.IGNORECASE)
_FROM_TILL = re.compile(r"\b(galle|galla|dukaan|dukan)\s+se\b|गल्ले\s+से|दुकान\s+से", re.IGNORECASE)


def family_direction(text: str):
    t = text or ""
    if _TOOK.search(t) or (re.search(r"\b(ne)\b[^,]*?\d[^,]*?\b(liye|liya|li)\b", t, re.IGNORECASE)
                           and not re.search(r"\b(the|thi|tha)\b", t)):
        return "kharcha"
    if _PUT_IN.search(t) and not _FROM_TILL.search(t):
        return "jama"
    if _RETURNED_BY.search(t) and not _GAVE_TO.search(t):
        return "jama"
    if _GAVE_TO.search(t) or _FROM_TILL.search(t):
        return "kharcha"
    if _BOUGHT.search(t) and not re.search(r"\bwapas\b|वापस", t, re.IGNORECASE):
        return "kharcha"
    return None


# "do-dhai hazaar", "2-3 hazaar", "teen chaar sau" — andaaza hai, pakki rakam nahi → amount poochho
_NUM_W = r"(?:ek|do|teen|char|chaar|paanch|panch|chhe|che|saat|aath|nau|das|dedh|dhai|adhai|ढाई|दो|तीन|चार|पांच|डेढ़)"
AMOUNT_RANGE = re.compile(
    rf"\b{_NUM_W}[\s-]+{_NUM_W}\s+(hazaar|hazar|sau|lakh)\b"
    r"|\b(\d+)\s*-\s*(?!\2\b)(\d+)\s*(hazaar|hazar|sau|lakh|k)\b"
    r"|(?:दो|तीन|चार|डेढ़)[\s-]+(?:ढाई|तीन|चार|पांच)\s+(हज़ार|हजार|सौ)", re.IGNORECASE)


# Router: chat samjha par paise ka len-den hai ("Papa galle se 1100 nikal ke le gaye", "kuch paise le gaye")
_QUESTION = re.compile(r"\?|^\s*(kya|kitna|kitne|kaun|kaise|kab|kahan|kyun)\b|\b(batao|bata\s+do|bataiye|hisab\s+do)\b",
                       re.IGNORECASE)
_MONEY_MOVE = re.compile(r"\b(galle|galla|gullak)\b|गल्ले|गल्ला"
                         r"|\b(paise|paisa|rupaye|rupay)\b[^?]*?\b(le\s+ga\w*|liye|liya|diye|diya|nikal\w*|daale|rakhe|mile|aaye)\b"
                         r"|पैसे[^?]*?(ले\s+गए|लिए|दिए|निकाले|डाले)", re.IGNORECASE)
_AMOUNT_VERB = re.compile(r"\d[\d,]*[^?]*?\b(le\s+ga\w*|liye|liya|diye|diya|di|nikal\w*|daale|bhar\w*|mile|aaye|pakda\w*)\b",
                          re.IGNORECASE)


def money_safety_net(text: str) -> bool:
    if not text or _QUESTION.search(text):
        return False
    return bool(_MONEY_MOVE.search(text) or _AMOUNT_VERB.search(text))
