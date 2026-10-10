# date_helpers.py — vaar (weekday) aur "kis cheez ka paisa" wali dates, code se pakki.
#
# LLM ko "pichla Somvaar kab tha" ka hisab nahi lagana chahiye — gpt-4o-mini ye
# bharose se nahi kar paata. Isliye:
#   1. calendar_block(): prompt mein aaj ka vaar + pichle 7 din ki table
#   2. fix_dates(): date resolution ke baad pakki jaanch
#        - statement mein EK hi vaar ka naam, koi aur date shabd nahi → sab actions us din
#        - doosre date shabd bhi hain → sirf us action ki date jiske text mein vaar likha hai
#        - date ke naam pe sirf maksad ("agle hafte KI mazdoori", "next week's wages")
#          aur koi date shabd nahi → aaj
import re
from datetime import date, timedelta

# Monday=0 … Sunday=6  (akele "mangal", "budh", "shani", "guru" nahi — ye naam bhi hote hain)
WEEKDAYS = [
    ("Somvaar", "Monday", "सोमवार", ["somvar", "somvaar", "somwar", "sombar", "sombaar", "monday", "सोमवार"]),
    ("Mangalvaar", "Tuesday", "मंगलवार", ["mangalvar", "mangalvaar", "mangalwar", "tuesday", "मंगलवार"]),
    ("Budhvaar", "Wednesday", "बुधवार", ["budhvar", "budhvaar", "budhwar", "wednesday", "बुधवार"]),
    ("Guruvaar", "Thursday", "गुरुवार", ["guruvar", "guruvaar", "guruwar", "veervar", "veervaar", "virvar",
                                         "brihaspativar", "thursday", "गुरुवार", "वीरवार", "बृहस्पतिवार"]),
    ("Shukravaar", "Friday", "शुक्रवार", ["shukravar", "shukravaar", "shukrawar", "friday", "शुक्रवार"]),
    ("Shanivaar", "Saturday", "शनिवार", ["shanivar", "shanivaar", "shaniwar", "saturday", "शनिवार"]),
    ("Raviwaar", "Sunday", "रविवार", ["ravivar", "ravivaar", "raviwar", "raviwaar", "itvar", "itwar",
                                       "itvaar", "etvaar", "sunday", "रविवार", "इतवार"]),
]


def _word_re(words):
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
                      + r")(?!\w)", re.IGNORECASE)


_WEEKDAY_RES = [_word_re(v[3]) for v in WEEKDAYS]

# "is cheez ka paisa" — date nahi, maksad
_PURPOSE = re.compile(
    r"(?<!\w)(agle|agli|pichle|pichhle|pichli|is|iss|next|last|this)\s+(hafte|hafta|hapte|mahine|mahina|week|month|saal)"
    r"(?:'s)?\s+(ki|ka|ke)(?!\w)"
    r"|(?<!\w)(next|last|this)\s+(week|month|year)'s(?!\w)"
    r"|(अगले|पिछले|इस)\s+(हफ्ते|हफ़्ते|महीने|साल)\s+(की|का|के)"
    # "kal ki mazdoori" = kal ke kaam ka paisa (diya aaj) — sirf paise wale shabd ke saath
    r"|(?<!\w)(kal|parso|aaj)\s+(ki|ka|ke)\s+(mazdoori|majdoori|dihadi|diahdi|salary|tankhwah|hisab|hisaab|paise|payment)(?!\w)"
    r"|(?<!\w)(yesterday|today)'s\s+(wages|wage|pay|salary|payment)(?!\w)"
    r"|(कल|परसों|आज)\s+(की|का|के)\s+(मज़दूरी|मजदूरी|दिहाड़ी|हिसाब|पैसे|सैलरी|तनख्वाह)",
    re.IGNORECASE)

_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
           "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep",
           "sept", "oct", "nov", "dec", "janvari", "farvari", "agast", "sitambar", "aktubar", "navambar",
           "disambar", "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर",
           "अक्टूबर", "नवंबर", "दिसंबर"]
_OTHER_DATE = re.compile(
    r"(?<!\w)(aaj|aj|kal|parso|parson|today|yesterday|tomorrow|tarikh|tareekh|tarik|"
    r"hafte|hafta|week|mahine|month|" + "|".join(_MONTHS) + r")(?!\w)"
    r"|आज|कल|परसों|परसो|तारीख|हफ्ते|हफ़्ते|महीने"
    r"|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?",
    re.IGNORECASE)


_AGO = re.compile(r"(?<!\w)(din|dino|dinon|days?)\s+(pehle|pahle|phle|baad|ago|before)(?!\w)|(?<!\w)(dino|dinon)(?!\w)"
                  r"|(?<!\w)(abhi\s+tak|agle|pichle|pichhle|last|next)(?!\w)|दिन\s+पहले|दिनों", re.IGNORECASE)
_RELATIVE = re.compile(r"day before yesterday|(?<!\w)(kal|parso|parson|yesterday)(?!\w)|कल|परसों|परसो",
                       re.IGNORECASE)
# "kal se / kal tak / kal de denge" = aane wala kal; "kal ki mazdoori" = maksad, date nahi → is niyam se date mat badlo
_REL_FUTURE = re.compile(
    r"(?<!\w)(kal|parso|parson)\s+(se|tak|ki|ka|ke|wali|wale|wala)(?!\w)|(कल|परसों)\s+(से|तक|की|का|के|वाली|वाले)|(?<!\w)(denge|dega|degi|dunga|dungi|karenge|karega|"
    r"karegi|aayega|aayegi|aayenge|jayega|jayegi|jayenge|lenge|lega|bhejenge|will|tomorrow)(?!\w)"
    r"|देंगे|देगा|करेंगे|करेगा|आएगा|जाएगा", re.IGNORECASE)
_DONE_NOW = re.compile(
    r"\b(bhara|bhar\s+diya|diya|diye|de\s+diya|de\s+diye|lage|lag\s+gaye|karwaya|karwayi|kiya|kiye|liya|li|"
    r"bharwaya|dalwaya|chukaya|chuka\s+diya|paid|gave)\b|भरा|दिया|दिए|लगे|करवाया|लिया", re.IGNORECASE)
_NEXT_PART = re.compile(r"\b(baaki|baki|bacha|bache)\b.*$|बाकी.*$", re.IGNORECASE)
_REL_DAYS = {"kal": 1, "yesterday": 1, "कल": 1, "parso": 2, "parson": 2, "परसों": 2, "परसो": 2,
             "day before yesterday": 2}
_TODAY = re.compile(r"(?<!\w)(aaj|aj|today)(?!\w)|आज", re.IGNORECASE)


def last_weekday(today: date, idx: int) -> date:
    """Aaj se PEHLE wala sabse kareeb `idx` vaar (aaj Somvaar ho to 'Somvaar' = 7 din pehle)."""
    d = today - timedelta(days=1)
    while d.weekday() != idx:
        d -= timedelta(days=1)
    return d


def calendar_block(today: date) -> str:
    h, e, hi, _ = WEEKDAYS[today.weekday()]
    lines = [f"Today: {today.isoformat()} — {h} / {e} / {hi}",
             "A weekday name means the MOST RECENT PAST such day (before today):"]
    for i in range(1, 8):
        d = today - timedelta(days=i)
        h, e, hi, _ = WEEKDAYS[d.weekday()]
        lines.append(f"  {h} / {e} / {hi}  = {d.isoformat()}")
    return "\n".join(lines)


def weekdays_in(text: str) -> set:
    return {i for i, r in enumerate(_WEEKDAY_RES) if r.search(text or "")}


def has_purpose_only(text: str) -> bool:
    return bool(_PURPOSE.search(text or ""))


def _other_date_words(text: str) -> bool:
    """Vaar aur maksad wale hisse hata ke koi aur date shabd bacha?"""
    t = _PURPOSE.sub(" ", text or "")
    for r in _WEEKDAY_RES:
        t = r.sub(" ", t)
    t = re.sub(r"\s+on\s+\d{4}-\d{2}-\d{2}", " ", t)        # extract ka jodha hua "on 2026-10-02"
    return bool(_OTHER_DATE.search(t))


def fix_dates(statement: str, groups, today: date | None = None) -> list:
    """fix_dates_core + ek aakhri jaanch: purani bikri ka zikr ("parso jo li thi") ke saath
    aaj ka paisa ("uske 4000 aaj de gaye") → us action ki date AAJ."""
    from sale_rules import past_sale_reference
    today = today or date.today()
    changes = _fix_dates_core(statement, groups, today)
    # "aadha abhi bhara, baaki agle mahine" — kaam ho chuka (bhara/diya/lage) par date aage ki aa gayi → aaj
    for g in groups:
        for a in g.actions:
            if a.date and a.date > today.isoformat() and _DONE_NOW.search(a.text or "") \
                    and not _REL_FUTURE.search(_NEXT_PART.sub(" ", a.text or "")):
                changes.append(f"'{a.text}': {a.date} → {today.isoformat()} (kaam ho chuka, aage ki date sirf baaki ke liye)")
                a.date = today.isoformat()
    for g in groups:
        for a in g.actions:
            if past_sale_reference(a.text) and _TODAY.search(a.text) and a.date != today.isoformat():
                changes.append(f"'{a.text}': {a.date} → {today.isoformat()} (purana zikr, paisa aaj)")
                a.date = today.isoformat()
    return changes


def _fix_dates_core(statement: str, groups, today: date | None = None) -> list:
    """
    Date resolution ke baad pakki jaanch. `groups` ke actions ki date jagah pe badalti hai.
    Returns: badlaav ki list (log ke liye).
    """
    today = today or date.today()
    changes = []

    def _set(action, new, why):
        if action.date != new:
            changes.append(f"'{action.text}': {action.date} → {new} ({why})")
            action.date = new

    found = weekdays_in(statement)
    other = _other_date_words(statement)
    if len(found) == 1 and not other:
        idx = next(iter(found))
        d = last_weekday(today, idx).isoformat()
        for g in groups:
            for a in g.actions:
                _set(a, d, WEEKDAYS[idx][0])
        return changes
    if found:
        for g in groups:
            for a in g.actions:
                own = weekdays_in(a.text)
                if len(own) == 1:
                    idx = next(iter(own))
                    _set(a, last_weekday(today, idx).isoformat(), WEEKDAYS[idx][0])
        return changes
    # Statement mein tareekh ka KOI shabd nahi ("Kalanaur wali kothi se malba aaya") — LLM ne naam ke "Kal" ko kal
    # samajh liya ho ya tareekh khaali chhodi ho → har action AAJ.
    if not other and not _RELATIVE.search(statement or "") and not _AGO.search(statement or ""):
        for g in groups:
            for a in g.actions:
                _set(a, today.isoformat(), "statement mein tareekh ka koi shabd nahi → aaj")
        return changes
    # Poore statement mein SIRF "kal" (ya sirf "parso") — aur koi date shabd nahi → har action usi din ka.
    # (vaar ke naam wala niyam jaisa; "kal aayi, aaj diye" mein do shabd hain → yahan nahi aata)
    rel = {_REL_DAYS[m.group(0).lower()] for m in _RELATIVE.finditer(statement or "")}
    if len(rel) == 1 and not _OTHER_DATE.search(_RELATIVE.sub(" ", statement or "")) \
            and not _REL_FUTURE.search(statement or ""):
        d = (today - timedelta(days=rel.pop())).isoformat()
        for g in groups:
            for a in g.actions:
                _set(a, d, "statement mein sirf kal/parso")
        return changes
    only_today = other and not _OTHER_DATE.search(
        _TODAY.sub(" ", _PURPOSE.sub(" ", statement or "")))
    if has_purpose_only(statement) and (not other or only_today):
        for g in groups:
            for a in g.actions:
                _set(a, today.isoformat(), "maksad hai, date nahi → aaj")
    return changes
