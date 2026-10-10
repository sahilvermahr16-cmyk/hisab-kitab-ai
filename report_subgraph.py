# report_subgraph.py — Reporting Phase: "hisab dikhao" wali har baat yahan aati hai.
#
# Flow (har sawaal tabhi jab statement se pata na chale):
#
#   parse ──► [kind?] ──► person wali report:  [role?] ──► [naam? (list ke saath)] ──► hisab hai?
#                    └──► bina person:  overall / purchase / expense / cash_flow / work_log / material
#         ──► [duration?] ──► is duration mein data hai? ──► [bhasha?] ──► PDF ──► jawab
#
# Kisi bhi step pe "hisab nahi" → seedha message, aage ke sawaal nahi.
# Har sawaal ek hi generic ReportHITLRequest hai (question + numbered options + text allowed?),
# taaki main.py aur aage FastAPI dono ek hi tarah dikha sakein.
#
# report_data (state mein) sirf JSON-safe cheezein rakhta hai — dates ISO string.
from datetime import date, timedelta

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from db import SessionLocal
from llm_setup import llm
from helpers import normalize_name
from models import PersonRoleLookup
from schemas import (
    ReportOption, ReportHITLRequest, ReportHITLResponse, ReportParseResult, ReportRangeResult,
)
from state import ChatState
from reports import builders as B, render as R, queries as Q, closing as C

_parse_llm = llm.with_structured_output(ReportParseResult)
_range_llm = llm.with_structured_output(ReportRangeResult)

# ---------------------------------------------------------------- options
KIND_OPTIONS = [
    ("overall", "Poore business ka hisab"),
    ("person", "Kisi person ka khata (employee / customer / supplier / family)"),
    ("purchase", "Purchase (kharid)"),
    ("expense", "Expense (kharcha)"),
    ("cash_flow", "Cash Flow (cash kab aaya, kab gaya)"),
    ("work_log", "Work Log (kis din kya kaam hua)"),
    ("material_movement", "Material Movement (maal kahan se kahan gaya)"),
]
ROLE_OPTIONS = [
    ("employee", "Employee"),
    ("customer", "Customer"),
    ("supplier", "Supplier"),
    ("family", "Family kharcha"),
]
RANGE_OPTIONS = [
    (2, "Pichle 2 din"), (15, "Pichle 15 din"), (30, "Pichla 1 mahina"),
    (90, "Pichle 3 mahine"), (180, "Pichle 6 mahine"), (270, "Pichle 9 mahine"), (365, "Pichla 1 saal"),
]
LANG_OPTIONS = [("hi", "हिंदी (Hindi)"), ("hg", "Hinglish"), ("en", "English")]

ROLE_LABEL = {"employee": "employee", "customer": "customer", "supplier": "supplier", "family": "family member"}

PARSE_PROMPT = """
You read ONE message from the owner of a brick & timber salvage business who wants to SEE a report
(hisab). Extract what is already stated. Never guess — use null for anything not stated.
Today's date: {today}

kind:
- "overall"  → ONLY when the WHOLE business is clearly meant: "poore business ka", "pura hisab", "sab ka hisab",
               "dukaan / business ka hisab", "total hisab", "business report"
- "person"   → a specific person or party is named, or "kisi employee/customer/supplier ka hisab"
- "purchase" → kharid / purchase / property deal ka hisab
- "expense"  → BUSINESS ka kharcha / expense / kharche ka hisab (diesel, bijli, servicing...)
               BUT "family kharcha", "ghar ka kharcha", "ghar ka hisab", "parivar ka kharcha" → kind="person",
               person_role="family" (NOT expense)
- "cash_flow" → cash / galla / cash flow / paisa kab aaya kab gaya
- "work_log" → kaam ka register / kis din kya kaam hua / labour
- "material_movement" → maal kahan se kahan gaya / material movement / maal ki aawajahi
- null → not clear. A bare "hisab dikhao" / "report do" / "hisab bata" with nothing else is NOT overall → null.

person_name: the person/party name if one is named (e.g. "Ram", "Suresh Traders", "SBI bhata"), else null.
  RULE: in "<X> ka hisab", "<X> ka khata", "<X> ki report", "<X> se kitna lena", "<X> ko kitna dena",
  "<X> ka kitna baaki" — <X> is ALWAYS a person/party name, even if it is an unusual or unknown word
  (e.g. "kitanu ka hisab dekho" → person_name="kitanu"; "sonu ka hisab" → "sonu"; "bablu ka khata" → "bablu").
  Copy the name exactly as written. Words like "business", "dukaan", "sab", "pura", "kharcha", "cash",
  "purchase", "maal", "kaam", "is mahine", "family", "parivar", "ghar", "ghr" are NOT names.
person_role: "employee" | "customer" | "supplier" | "family" ONLY if the message says the role, else null.

date_from / date_to (YYYY-MM-DD) ONLY if a duration or dates are stated:
- "aaj" → today..today;  "kal" → yesterday..yesterday
- "pichle N din" / "N din ka" → (today − N + 1)..today
- "is mahine" → 1st of this month..today;  "pichla mahina" / "last month" → previous calendar month (1st..last day)
- "pichle N mahine" → today minus N months (+1 day)..today
- "is saal" → 1 Jan..today;  "pichla saal" → previous calendar year
- "september ka" → that month of the current year (previous year if it is in the future)
- explicit dates ("1 se 15 september", "2026-09-01 to 2026-09-30")
otherwise both null.

language: "hi" if the user asks for Hindi, "en" for English, "hg" for Hinglish; else null.
"""

RANGE_PROMPT = """
Convert the user's answer into a date range. Today's date: {today}
Same rules: "pichle N din", "is mahine", "pichla mahina", "september", "1 se 15 september",
"2026-09-01 se 2026-09-30", "pichle 2 mahine". Return date_from and date_to as YYYY-MM-DD, or null if unclear.
"""


import re
_FAMILY_WORDS = re.compile(r"\b(family|famili|parivar|gh(a)?r (ka |ke )?kharch|gh(a)?r ka hisab)")
# "family ka hisab", "ghr kharch ka hisab" — LLM inhe naam samajh leta hai; ye naam nahi hain
_FAMILY_GENERIC = {"family", "famili", "parivar", "ghar", "ghr", "ka", "ke", "ki", "kharch", "kharcha", "kharche",
                   "hisab", "aaj", "is", "mahine"}

# Role tabhi maano jab message mein role ka shabd ho — "papa ka hisab" mein role nahi likha
# (LLM "papa" dekh ke khud family maan leta hai), to confirm wala sawaal aana chahiye.
_ROLE_WORDS = {
    "employee": re.compile(r"\b(employee|emp|karmchari|karamchari|mazdoor|majdoor|worker|labour|driver)\b"),
    "customer": re.compile(r"\b(customer|grahak|graahak|party)\b"),
    "supplier": re.compile(r"\b(supplier|suppliar|bhatta|bhatte|bhate)\b"),
    "family": re.compile(r"\b(family|famili|parivar)\b"),
}
_LANG_WORDS = re.compile(r"\b(hindi|hinglish|english|angrezi|angreji|इंग्लिश|हिंदी)")
_TODAY_WORD = re.compile(r"\b(aaj|aj|today)\b")
_YESTERDAY_WORD = re.compile(r"\b(kal|yesterday)\b")
_RANGE_WORDS = re.compile(r"\btak\b|\bpichle|\bpichhle|\blast\b|\bmahine|\bhafte|\bsaal\b|\bdin\b|\bdino|\babhi\s+tak|"
                          r"\bweek|\bmonth|\byear|\bse\s+(aaj|kal)\b")

# ---------------------------------------------------------------- helpers
def _today():
    return date.today()


def _valid_range(f, t):
    try:
        a, b = date.fromisoformat(f), date.fromisoformat(t)
    except (TypeError, ValueError):
        return None
    if a > b:
        a, b = b, a
    if a > _today():
        return None
    return a.isoformat(), min(b, _today()).isoformat()


def _ask(step, question, options=(), allow_text=False, retry=False, hint=None):
    req = ReportHITLRequest(
        step=step, question=question, hint=hint, retry=retry, allow_text=allow_text,
        options=[ReportOption(option_id=i, label=lbl) for i, lbl in enumerate(options, 1)],
    )
    resp = interrupt(req)
    if isinstance(resp, dict):          # FastAPI / plain dict resume bhi chalega
        resp = ReportHITLResponse(**resp)
    return resp


def _find_people(db, name, role=None):
    """
    Naam se party dhoondo: [(role, id, display_name)].
    Pehle exact (normalize), fir 'contains'. role diya ho to sirf us role mein.
    """
    n = normalize_name(name)
    q_tokens = set(n.split())
    tables = [("employee", Q.employees(db)), ("customer", Q.customers(db)), ("supplier", Q.suppliers(db)),
              ("family", Q.family_members(db))]
    exact, partial = [], []
    for r, masters in tables:
        if role and r != role:
            continue
        for pid, m in masters.items():
            mn = normalize_name(m.name)
            if mn == n:
                exact.append((r, pid, m.name))
            elif q_tokens and q_tokens <= set(mn.split()):
                # poore shabd milne chahiye: "suresh" → "Suresh Traders" haan, "ram" → "Ramesh" nahi
                partial.append((r, pid, m.name))
    if exact or partial:
        return exact or partial
    # "SBI Bhatte" = "SBI Bhatta" — aakhri a/e/o ka fark (Hinglish ka ling / vachan)
    def _st(w):
        return w[:-1] if len(w) >= 4 and w[-1] in "aeo" else w
    q_st = {_st(w) for w in q_tokens}
    for r, masters in tables:
        if role and r != role:
            continue
        for pid, m in masters.items():
            if q_st and q_st <= {_st(w) for w in normalize_name(m.name).split()}:
                partial.append((r, pid, m.name))
    return partial


def _resolve_person(data):
    """person_name (+ role) se ledger_id tay karo. data ko badalta hai."""
    name, role = data.get("person_name"), data.get("role")
    if not name:
        return
    db = SessionLocal()
    try:
        found = _find_people(db, name, role)
        if not found:
            data["stop"] = (f"'{name}' naam ka koi {ROLE_LABEL[role]} nahi mila — iska koi hisab nahi hai."
                            if role else f"'{name}' ka koi hisab nahi hai.")
            return
        if role is None:
            # role statement mein nahi → hamesha poochho; jis role mein naam mila uspe ✓
            data["found_roles"] = sorted({r for r, _, _ in found})
            return
        same = [x for x in found if x[0] == role]
        if len(same) == 1:
            data["ledger_id"], data["person_name"] = same[0][1], same[0][2]
        else:
            data["name_choices"] = [[pid, nm] for _, pid, nm in same]   # ek role, kai milte-julte naam
    finally:
        db.close()


# ---------------------------------------------------------------- code nets (LLM ke baad)
# "Zara Sharma ji wala khata" — LLM ne "Zara Sharma" naam bana diya; shuru ke bharti ke shabd naam nahi
_FILLER = {"zara", "jara", "jra", "zra", "bhai", "are", "arre", "ek", "please", "plz", "mujhe", "hamein", "humein"}
# "pichle 7 din / 2 hafte / 3 mahine" — tareekh ka hisaab Python mein (LLM ek din chook jaata tha)
_LAST_N = re.compile(r"\b(?:pichle|pichhle|picchle|last|pichla|pichli)\s+(\d+)\s*"
                     r"(din|dino|dinon|days?|hafte|hafton|hafta|weeks?|mahine|mahino|mahina|months?)\b")
_CASH_WORDS = re.compile(r"\b(galla|galle|gulak|cash|nakad|cash\s*flow)\b")
_GENERIC_NAME = re.compile(r"^\s*(dukaan|dukan|shop|ghar|ghr|business|site|gudam|godown|sab|sabka|poora|kharcha|"
                           r"kharche|property|maal|galla|galle)\s*$", re.IGNORECASE)


def _strip_filler(name):
    words = (name or "").split()
    while words and words[0].lower() in _FILLER:
        words = words[1:]
    return " ".join(words) or None


def _last_n_range(low):
    m = _LAST_N.search(low)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    end = _today()
    if unit.startswith(("din", "day")):
        start = end - timedelta(days=n - 1)
    elif unit.startswith(("haft", "week")):
        start = end - timedelta(days=7 * n - 1)
    else:
        import calendar
        y, mo = end.year, end.month - n
        while mo <= 0:
            mo += 12
            y -= 1
        start = date(y, mo, min(end.day, calendar.monthrange(y, mo)[1])) + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _stem_rx(name):
    parts = []
    for w in name.lower().split():
        parts.append(re.escape(w[:-1]) + "[aeo]?" if len(w) >= 4 and w[-1] in "aeo" else re.escape(w))
    return r"(?<!\w)" + r"\s+".join(parts) + r"(?!\w)"


def _known_name_in(text):
    """Text mein DB ka EK jaana-pehchaana naam (employee / customer / supplier / family) — 'SBI bhatte' = 'SBI Bhatta'."""
    db = SessionLocal()
    try:
        from models import Employee, Customer, Supplier, FamilyMember
        names = []
        for model in (Employee, Customer, Supplier, FamilyMember):
            names += [n for (n,) in db.query(model.name).all() if n]
    except Exception:
        return None
    finally:
        db.close()
    low = text.lower()
    # har shabd kahin bhi ("Bhatte wale SBI" = "SBI Bhatta"); chhote shabd (ji) ginti mein nahi
    def _has(n):
        ws = [w for w in n.lower().split() if len(w) > 2]
        return bool(ws) and all(re.search(_stem_rx(w), low) for w in ws)
    found = {n for n in names if _has(n)}
    return found.pop() if len(found) == 1 else None


# ---------------------------------------------------------------- nodes
async def report_parse_node(state):
    text = state["messages"][-1].content
    res = await _parse_llm.ainvoke(f"{PARSE_PROMPT.format(today=_today().isoformat())}\n\nMessage:\n{text}")
    data = {"text": text}
    kind = res.kind
    low = text.lower()
    if res.person_name:
        clean = _strip_filler(res.person_name)
        if clean != res.person_name:
            print(f"🧹 REPORT: naam '{res.person_name}' → '{clean}' (shuru ke bharti ke shabd hataye)")
            res.person_name = clean
    if res.person_name and _GENERIC_NAME.match(res.person_name):
        res.person_name = None                  # "dukaan" / "ghar" / "business" naam nahi
    if kind in (None, "cash_flow", "expense") and not _CASH_WORDS.search(low):
        # naam mila (LLM se ya DB ke jaane-pehchaane naam se) aur galla/cash ka shabd nahi → us ka khata
        known = _known_name_in(text)
        if known or res.person_name:
            name = known or res.person_name
            print(f"👤 REPORT: '{text}' mein naam '{name}' — {kind} nahi, us ka khata")
            res.person_name, kind = name, "person"
    elif kind == "cash_flow":
        # "Papa ne pichle mahine galle se kitna uthaya" — galla sirf jagah hai, sawaal Papa ka hai
        from family_rules import relation_person
        rel = relation_person(text)
        if rel and not re.search(r"(?<!\w)" + re.escape(rel.lower()) + r"\s+(ne|ko|ka|ki|ke)\b", low):
            rel = None                               # "Bhai aaj galle mein kitna aaya" — bhai sirf bulaava hai
        who = _known_name_in(text) or rel
        if who:
            print(f"👤 REPORT: '{text}' mein '{who}' ka sawaal — galla report nahi, us ka khata")
            res.person_name, kind = who, "person"
    rng = _last_n_range(low)
    if rng:
        if (res.date_from, res.date_to) != rng:
            print(f"📅 REPORT: tareekh {res.date_from}..{res.date_to} → {rng[0]}..{rng[1]} (code se)")
        res.date_from, res.date_to = rng
    if res.person_role and not _ROLE_WORDS.get(res.person_role, re.compile(r"^$")).search(low):
        res.person_role = None                  # role likha nahi — andaza nahi, confirm karwayenge
    if not (res.date_from and res.date_to):
        if _TODAY_WORD.search(low):
            res.date_from = res.date_to = _today().isoformat()
        elif _YESTERDAY_WORD.search(low):
            res.date_from = res.date_to = (_today() - timedelta(days=1)).isoformat()
    # "Kal gudam se kahan kahan maal gaya" — ek din ka shabd, range nahi → shuru = aakhri = wahi din
    one = {"aaj": 0, "aj": 0, "today": 0, "kal": 1, "yesterday": 1, "parso": 2, "parson": 2}
    days = {one[m.group(1)] for m in re.finditer(r"\b(aaj|aj|today|kal|yesterday|parso|parson)\b", low)}
    if len(days) == 1 and not rng and not _RANGE_WORDS.search(low):
        d1 = (_today() - timedelta(days=days.pop())).isoformat()
        if (res.date_from, res.date_to) != (d1, d1):
            print(f"📅 REPORT: ek din ka sawaal — tareekh {res.date_from}..{res.date_to} → {d1}..{d1}")
        res.date_from = res.date_to = d1
    if res.person_name and kind in (None, "person"):
        kind = "person"
    if _FAMILY_WORDS.search(text.lower()) and kind in (None, "expense", "person"):
        kind = "person"                         # "family kharcha / ghar ka kharcha" → family ka hisab
        res.person_role = "family"
        if res.person_name and set(normalize_name(res.person_name).split()) <= _FAMILY_GENERIC:
            res.person_name = None              # "family" / "ghr" naam nahi — list dikhao
    data["kind"] = kind
    if kind == "person":
        data["person_name"] = res.person_name
        data["role"] = res.person_role
    if res.date_from and res.date_to:
        vr = _valid_range(res.date_from, res.date_to)
        if vr:
            data["start"], data["end"] = vr
    # bhasha tabhi jab user ne khud boli ho ("hindi mein", "english") — warna hamesha poochho
    if res.language in ("hi", "hg", "en") and _LANG_WORDS.search(low):
        data["lang"] = res.language
    if kind == "person":
        _resolve_person(data)
    return {"report_data": data}


async def report_ask_kind_node(state):
    data = dict(state["report_data"])
    resp = _ask("kind", "Kiska hisab dekhna hai?", [lbl for _, lbl in KIND_OPTIONS])
    if resp.cancelled:
        data["stop"] = "Theek hai, report cancel."
    elif resp.selected_option and 1 <= resp.selected_option <= len(KIND_OPTIONS):
        data["kind"] = KIND_OPTIONS[resp.selected_option - 1][0]
    return {"report_data": data}


async def report_ask_role_node(state):
    data = dict(state["report_data"])
    found = data.get("found_roles") or []
    if len(found) == 1 and not data.get("role_rejected"):
        # naam sirf ek category mein mila → bas confirm karo
        label = dict(ROLE_OPTIONS)[found[0]]
        resp = _ask("role", f"'{data['person_name']}' humein {label} mein mila — isi ka hisab?",
                    [f"Haan, {label} hi hai", "Nahi, dusri category hai"])
        if resp.cancelled:
            data["stop"] = "Theek hai, report cancel."
        elif resp.selected_option == 1:
            data["role"] = found[0]
            data.pop("found_roles", None)
            _resolve_person(data)
        elif resp.selected_option == 2:
            data["role_rejected"] = True        # agli baar poori list
        return {"report_data": data}
    opts = list(ROLE_OPTIONS)
    labels = [f"{l}  ✓ ('{data['person_name']}' isme mila)" if r in found else l for r, l in opts]
    q = (f"'{data['person_name']}' kaun hai — kis category ka hisab dekhna hai?" if data.get("person_name")
         else "Kis type ke person ka hisab?")
    resp = _ask("role", q, labels)
    if resp.cancelled:
        data["stop"] = "Theek hai, report cancel."
        return {"report_data": data}
    if resp.selected_option and 1 <= resp.selected_option <= len(opts):
        data["role"] = opts[resp.selected_option - 1][0]
        data.pop("found_roles", None)
        if data.get("person_name"):
            _resolve_person(data)
    return {"report_data": data}


async def report_ask_name_node(state):
    data = dict(state["report_data"])
    role = data["role"]
    db = SessionLocal()
    try:
        if data.get("name_choices"):
            people = [(pid, nm) for pid, nm in data["name_choices"]]
        else:
            masters = {"employee": Q.employees, "customer": Q.customers, "supplier": Q.suppliers,
                       "family": Q.family_members}[role](db)
            people = sorted(((pid, m.name) for pid, m in masters.items()), key=lambda x: x[1].lower())
            if role == "family" and people:
                people = [(0, "Poori family (sab members)")] + people   # 0 = sab
    finally:
        db.close()
    if not people:
        data["stop"] = f"Abhi tak kisi {ROLE_LABEL[role]} ka koi hisab nahi hai."
        return {"report_data": data}

    retry = bool(data.get("name_retry"))
    resp = _ask("name", f"Kis {ROLE_LABEL[role]} ka hisab? Naam likho, ya list mein se number chuno.",
                [nm for _, nm in people], allow_text=True, retry=retry,
                hint="Naam yaad nahi to list se number chuno.")
    data.pop("name_retry", None)
    if resp.cancelled:
        data["stop"] = "Theek hai, report cancel."
        return {"report_data": data}
    if resp.selected_option and 1 <= resp.selected_option <= len(people):
        data["ledger_id"], data["person_name"] = people[resp.selected_option - 1]
        if data["ledger_id"] == 0:
            data["person_name"] = "Poori family"
        data.pop("name_choices", None)
        return {"report_data": data}
    if resp.answer:
        data["person_name"] = resp.answer.strip()
        data.pop("name_choices", None)
        db = SessionLocal()
        try:
            found = _find_people(db, data["person_name"], role)
        finally:
            db.close()
        if len(found) == 1:
            data["ledger_id"], data["person_name"] = found[0][1], found[0][2]
        elif len(found) > 1:
            data["name_choices"] = [[pid, nm] for _, pid, nm in found]
        else:
            data["stop"] = f"'{data['person_name']}' naam ka koi {ROLE_LABEL[role]} nahi mila — iska koi hisab nahi hai."
    return {"report_data": data}


async def report_ask_range_node(state):
    data = dict(state["report_data"])
    retry = bool(data.get("range_retry"))
    resp = _ask("range", "Kitne din ka hisab dekhna hai?",
                [lbl for _, lbl in RANGE_OPTIONS], allow_text=True, retry=retry,
                hint="Ya apni dates likho — jaise 'september ka', '1 se 15 september', 'is mahine'.")
    data.pop("range_retry", None)
    if resp.cancelled:
        data["stop"] = "Theek hai, report cancel."
        return {"report_data": data}
    if resp.selected_option and 1 <= resp.selected_option <= len(RANGE_OPTIONS):
        days = RANGE_OPTIONS[resp.selected_option - 1][0]
        end = _today()
        data["start"], data["end"] = (end - timedelta(days=days - 1)).isoformat(), end.isoformat()
        return {"report_data": data}
    if resp.answer:
        res = await _range_llm.ainvoke(f"{RANGE_PROMPT.format(today=_today().isoformat())}\n\nAnswer:\n{resp.answer}")
        vr = _valid_range(res.date_from, res.date_to) if res.date_from and res.date_to else None
        if vr:
            data["start"], data["end"] = vr
            return {"report_data": data}
    data["range_retry"] = True
    return {"report_data": data}


async def report_check_node(state):
    """Data hai ya nahi — bhasha poochne se PEHLE (khaali report ke liye bhasha kyun poochein)."""
    data = dict(state["report_data"])
    start, end = date.fromisoformat(data["start"]), date.fromisoformat(data["end"])
    db = SessionLocal()
    try:
        rtype = data["role"] if data["kind"] == "person" else data["kind"]
        rep = B.build_report(db, rtype, start, end, ledger_id=data.get("ledger_id"))
        if data["kind"] == "person" and not rep.get("has_history", True):
            data["stop"] = f"{data['person_name']} ka koi hisab nahi hai."
        elif B.report_is_empty(rep):
            msg = f"Is duration ({start.strftime('%d-%b-%Y')} se {end.strftime('%d-%b-%Y')}) mein koi hisab nahi hai"
            if data["kind"] == "person":
                last = B.last_entry_date(db, data["role"], data["ledger_id"] or None)
                msg = (f"{data['person_name']} ka is duration ({start.strftime('%d-%b-%Y')} se "
                       f"{end.strftime('%d-%b-%Y')}) mein koi hisab nahi hai")
                if last:
                    msg += f". Aakhri entry {last.strftime('%d-%b-%Y')} ki hai — lambi duration chuno"
            data["stop"] = msg + "."
        data["checked"] = True
    finally:
        db.close()
    return {"report_data": data}


async def report_ask_lang_node(state):
    data = dict(state["report_data"])
    resp = _ask("language", "Report kis bhasha mein chahiye?", [lbl for _, lbl in LANG_OPTIONS])
    if resp.cancelled:
        data["stop"] = "Theek hai, report cancel."
    elif resp.selected_option and 1 <= resp.selected_option <= len(LANG_OPTIONS):
        data["lang"] = LANG_OPTIONS[resp.selected_option - 1][0]
    return {"report_data": data}


def _summary_lines(rep):
    k = rep["kind"]
    rs = R.rs
    if k in ("overall", "overall_period"):
        f = rep["final"]
        return [f"Kul dena: {rs(f['total_give'])}", f"Kul lena: {rs(f['total_take'])}",
                f"Haath mein cash: {rs(f['cash'])}"]
    if k.endswith("_ledger") or k in ("supplier_period", "customer_period", "employee_period"):
        c = rep["closing"]
        word = "lena" if c > 0 else "dena"
        return [f"Aakhri baaki: {R.inr(abs(c))} {word}" if abs(c) > 0.005 else "Aakhri baaki: kuch nahi"]
    if k == "family_report":
        return [f"Ghar gaya: {rs(rep['total_diya'])}, galle mein wapas aaya: {rs(rep['total_liya'])}",
                f"Net ghar gaya: {rs(rep['net'])}"]
    if k in ("cash_book", "cash_flow_period"):
        return [f"Cash: {rs(rep['opening'])} → {rs(rep['closing'])}"]
    if k.startswith("purchase") or k.startswith("expense"):
        return [f"Kul: {rs(rep['total'])}, diya: {rs(rep['paid'])}, baaki: {rs(rep['baaki'])}"]
    return []


async def report_render_node(state):
    data = dict(state["report_data"])
    start, end = date.fromisoformat(data["start"]), date.fromisoformat(data["end"])
    db = SessionLocal()
    try:
        rtype = data["role"] if data["kind"] == "person" else data["kind"]
        rep = B.build_report(db, rtype, start, end, ledger_id=data.get("ledger_id"))
        path = await R.make_pdf_async(db, rep, data["lang"], llm=llm)
        lines = _summary_lines(rep)
    finally:
        db.close()
    long_note = ("\n(Lambi duration: har mahine ka summary + sirf aakhri mahine ki poori detail.)"
                 if (end - start).days + 1 > B.DETAIL_MAX_DAYS else "")
    msg = "✅ Report taiyaar hai.\n" + "\n".join(lines) + f"\n📄 {path}" + long_note
    data["done"] = True
    data["pdf_path"] = path
    return {"report_data": data, "messages": [AIMessage(content=msg)]}


async def report_stop_node(state):
    data = state["report_data"] or {}
    msg = data.get("stop") or "Report nahi ban payi."
    return {"messages": [AIMessage(content=msg)]}


# ---------------------------------------------------------------- routing
def _next(state):
    d = state["report_data"] or {}
    if d.get("stop"):
        return "stop"
    if not d.get("kind"):
        return "ask_kind"
    if d["kind"] == "person":
        if not d.get("role"):
            return "ask_role"
        if d.get("ledger_id") is None:          # family mein 0 = poori family
            return "ask_name"
    if not (d.get("start") and d.get("end")):
        return "ask_range"
    if not d.get("checked"):
        return "check"
    if not d.get("lang"):
        return "ask_lang"
    return "render"


_ROUTES = {k: k for k in ("stop", "ask_kind", "ask_role", "ask_name", "ask_range", "check",
                          "ask_lang", "render")}

builder = StateGraph(ChatState)
builder.add_node("parse", report_parse_node)
builder.add_node("ask_kind", report_ask_kind_node)
builder.add_node("ask_role", report_ask_role_node)
builder.add_node("ask_name", report_ask_name_node)
builder.add_node("ask_range", report_ask_range_node)
builder.add_node("check", report_check_node)
builder.add_node("ask_lang", report_ask_lang_node)
builder.add_node("render", report_render_node)
builder.add_node("stop", report_stop_node)

builder.add_edge(START, "parse")
for node in ("parse", "ask_kind", "ask_role", "ask_name", "ask_range", "check", "ask_lang"):
    builder.add_conditional_edges(node, _next, _ROUTES)
builder.add_edge("render", END)
builder.add_edge("stop", END)

report_subgraph = builder  # graph.py compile karega (parent ka checkpointer use hoga)
