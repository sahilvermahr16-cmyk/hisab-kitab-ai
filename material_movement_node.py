# material_movement_node.py
from langgraph.types import interrupt
from db import SessionLocal
from schemas import (
    MaterialMovementHITLRequest, MaterialMovementHITLResponse,
    MaterialMovementHITLReason, LocationTypeOption,
    TransactionType, TransactionClassifierResult,
)
from helpers import lookup_movement_entity, sync_movement_entity
from models import MovementEntityType, MovementEntityLookup
from item_mapper import normalize_location

# Grouping "maal kahan se aaya" na pata ho to "UNKNOWN" likhta hai — ye jagah ka NAAM nahi hai.
_UNKNOWN_WORDS = {"unknown", "unkown", "none", "null", "na", "n/a", "-", "?", "pata nahi", "pta nhi",
                  "nahi pata", "not known", "अज्ञात", "पता नहीं"}
# Inke canonical naam (item_mapper.LOCATION_ALIASES) hamesha apni jagah hain
_STORAGE_CANON = {"गोदाम", "दुकान", "पलाट"}
_SITE_CANON = {"साइट"}


def _clean_location(name):
    """'UNKNOWN' / khaali → None (missing), warna naam."""
    if name is None:
        return None
    n = " ".join(str(name).strip().lower().split())
    return None if not n or n in _UNKNOWN_WORDS else str(name).strip()


_ENDINGS = ("ों", "ो", "े", "ा", "on", "e", "a", "o")


def _stem_word(w):
    """Hindi mein naam ka aakhri hissa badalta hai: bhatta/bhatte, Sharma/Sharme, Gudam/Gudamon."""
    for end in _ENDINGS:
        if w.endswith(end) and len(w) - len(end) >= 3:
            w = w[: -len(end)]
            break
    out = []
    for ch in w:                      # bhatt / bhat — dohra akshar ek
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


def _name_key(name):
    return " ".join(_stem_word(w) for w in str(name).strip().lower().split())


def _match_known_name(db, name):
    """
    Naam DB mein hu-ba-hu nahi mila to aakhri a/e/o ka fark chhod ke dhoondo
    ("SBI bhatte" → "SBI Bhatta"). Sirf EK naam mile tabhi badlo — do mile to
    jaisa tha waisa rehne do (tab user se poochenge, galat entry nahi banegi).
    """
    if not name:
        return name
    exact = lookup_movement_entity(db, name)
    if exact:
        return exact.name                       # DB wali spelling ("sbi bhatta" → "SBI Bhatta")
    key = _name_key(name)
    rows = [row.name for row in db.query(MovementEntityLookup).all() if row.name]
    hits = {n for n in rows if _name_key(n) == key}
    if len(hits) == 1:
        return hits.pop()
    better = _close_known_name(name, rows)
    if better:
        print(f"🔗 MATERIAL MOVEMENT: '{name}' → jaana-pehchaana '{better}'")
        return better
    return name


_POSSESSIVE = {"ki", "ke", "ka", "की", "के", "का", "'s", "wale", "wala", "wali", "वाले", "वाला"}


def _close_known_name(name, rows):
    """
    Hu-ba-hu nahi mila to (sirf EK naam mile tabhi):
      1. adhoora naam  — "Suresh" → "Suresh Traders"
      2. naam + 'ki site' — "Sharma ji ki site" → "Sharma ji"
      3. galat spelling — "Suresh tradrs" → "Suresh Traders" (90%+ milta-julta)
    """
    import difflib
    raw = str(name).lower().split()
    words = [_stem_word(w) for w in raw]
    if not words or any(ch.isdigit() for ch in str(name)):
        return None
    prefix, owner, fuzzy = set(), set(), set()
    for n in rows:
        kw = [_stem_word(w) for w in n.lower().split()]
        if len(words) < len(kw) and kw[: len(words)] == words:
            prefix.add(n)
        if len(kw) < len(words) and words[: len(kw)] == kw and raw[len(kw)] in _POSSESSIVE:
            owner.add(n)
        if len(words) == len(kw) and len(words) > 1 and \
                difflib.SequenceMatcher(None, " ".join(words), " ".join(kw)).ratio() >= 0.9:
            fuzzy.add(n)
    for found in (prefix, owner, fuzzy):
        if len(found) == 1:
            return next(iter(found))
    return None


def _known_location_type(db, name):
    """
    Jagah pehle se pehchani hai? → uski kism (warna None, tab user se poochenge).
      1. movement lookup mein naam se
      2. alias se (warehouse / godown / गोदाम → गोदाम; shop / dukaan / दुकान → दुकान; site → साइट)
    """
    record = lookup_movement_entity(db, name)
    if record:
        return MovementEntityType(record.entity_type)
    canon = normalize_location(name)
    if canon and canon != name.strip():
        record = lookup_movement_entity(db, canon)
        if record:
            return MovementEntityType(record.entity_type)
    for row in db.query(MovementEntityLookup).all():
        if canon and normalize_location(row.name) == canon:
            return MovementEntityType(row.entity_type)
    if any(w in str(name).lower() for w in _PROPERTY_WORDS):
        return MovementEntityType.SITE              # haveli / kothi / building — todne wali jagah = site
    if canon in _STORAGE_CANON:
        return MovementEntityType.STORAGE
    if canon in _SITE_CANON:
        return MovementEntityType.SITE
    return None


def _storage_suggestions(db, limit=5):
    """'Maal kahan se?' sawaal ke liye jaani-pehchaani storage jagahen (ek canonical ka ek hi naam)."""
    seen, out = set(), []
    for row in db.query(MovementEntityLookup).filter(MovementEntityLookup.entity_type == "storage").all():
        canon = normalize_location(row.name)
        if canon not in seen:
            seen.add(canon)
            out.append(row.name)
    return out[:limit]


# "purana bazar sharma ji k utari" — destination jagah ka naam nikla par wahan ek insaan bhi hai.
# Ek insaan ke kai address ho sakte hain → destination = insaan (customer), jagah = address.
import re as _re
_PLACE = _re.compile(
    r"\b(bazar|bazaar|baazar|baazaar|market|colony|clony|coloni|nagar|road|rod|chowk|chauk|gali|mohalla|"
    r"sector|basti|vihar|enclave)\b|बाज़ार|बाजार|मार्केट|कॉलोनी|कालोनी|नगर|रोड|चौक|गली|मोहल्ला|सेक्टर|बस्ती",
    _re.IGNORECASE)
_PERSON_AT = _re.compile(
    r"([A-Za-z\u0900-\u097F]+\s+(?:ji|jee|sahab|saab|sahib|जी|साहब))(?:'s|\s+(?:k|ke|ki|ka|ke\s+yahan|ke\s+yaha|"
    r"ke\s+ghar|के|की|का|के\s+यहाँ|के\s+यहां|के\s+घर))(?![\w\u0900-\u097F])"
    r"|([A-Za-z\u0900-\u097F]+(?:\s+[A-Za-z\u0900-\u097F]+)?)\s+(?:ke\s+yahan|ke\s+yaha|ke\s+ghar|के\s+यहाँ|के\s+यहां|के\s+घर)"
    r"(?![\w\u0900-\u097F])"
    r"|([A-Za-z\u0900-\u097F]+(?:\s+[A-Za-z\u0900-\u097F]+)?)\s+(?:k|ke|ki|के|की)\s+"          # "ravi verma k utri"
    r"(?:utri|utari|utra|utre|utaari|gira|giri|gire|gayi|gai|gaya|pahunchi|pahuchi|उतरी|उतारी|उतरा|गिरी|गई|गया|पहुंची)"
    r"(?![\w\u0900-\u097F])",
    _re.IGNORECASE)
_NOT_NAME = {"main", "mein", "me", "se", "pe", "par", "ko", "aur", "tha", "thi", "the", "में", "से", "पे", "पर", "को",
             "और", "था", "थी", "eent", "int", "ईंट", "maal", "माल"}


def _person_at_place(destination, text, source=None):
    """destination jagah hai aur text mein '<naam> ji k/ke/ke yahan' hai → (insaan, address). Warna None."""
    if not destination or not text or not _PLACE.search(destination):
        return None
    for m in _PERSON_AT.finditer(text):
        person = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if not person or _PLACE.search(person) or any(w.lower() in _NOT_NAME for w in person.split()) \
                or any(ch.isdigit() for ch in person):
            continue
        if source and _name_key(person) == _name_key(source):
            continue
        address = " ".join(_re.sub(_re.escape(person), " ", destination, flags=_re.IGNORECASE).split())
        return person, (address or destination)
    return None



# "UltraTech ke dealer Bansal" → naam "Bansal" (brand/shehar note mein) — warna DB mein lamba naya naam banta.
# "Mandi mein Sethi ji se aloo li" → maal Sethi ji SE aaya; "Mandi" sirf jagah hai jahan khareeda.
_SOURCE_PERSON = _re.compile(
    r"([A-Za-z\u0900-\u097F]+\s+(?:ji|jee|sahab|saab|bhai|जी|साहब|भाई))\s+(?:se|से)(?![\w\u0900-\u097F])",
    _re.IGNORECASE)


# "3000 eent gudam mein aayi" — destination ka shabd text mein hai par grouping ne UNKNOWN likha
_ARRIVED_AT = _re.compile(
    r"(?<![\w\u0900-\u097F])(gudam|godown|godam|shop|dukaan|dukan|गोदाम|दुकान)\s+(?:mein|me|main|pe|par|में|पे|पर)\s+"
    r"(?:\S+\s+){0,3}(?:aayi|aaya|aaye|aai|utri|utra|utre|pahunchi|pahuncha|rakhi|rakha|आई|आया|उतरी|पहुंची)(?![\w\u0900-\u097F])",
    _re.IGNORECASE)
_PARTY_SFX = {"bhatte", "bhatta", "bhate", "bhata", "bhatha", "traders", "trader", "भट्टे", "भट्टा", "ट्रेडर्स"}
_PARTY_MARK = {"ki", "ke", "ka", "wali", "wale", "wala", "se", "की", "के", "का", "वाली", "वाले", "से"}
_PARTY_STOP = {"pe", "par", "mein", "me", "main", "se", "ko", "ne", "aur", "ki", "ke", "ka", "tak", "aaj", "kal",
               "gudam", "godown", "shop", "dukaan", "site", "plot", "पे", "पर", "में", "से", "को", "ने", "और",
               "की", "के", "का", "गोदाम", "दुकान", "साइट"}


def _source_party(text, destination=None):
    """'Gudam pe SBI bhatte ki 2000 eent utri' → 'SBI bhatte'. Sirf EK aisa naam mile tabhi."""
    toks = _re.findall(r"[A-Za-z\u0900-\u097F]+", text)
    found, marked = {}, False
    for i, t in enumerate(toks):
        if t.lower() not in _PARTY_SFX:
            continue
        marked = marked or (i + 1 < len(toks) and toks[i + 1].lower() in _PARTY_MARK)
        name, j = [], i - 1
        while j >= 0 and len(name) < 2 and toks[j].lower() not in _PARTY_STOP and toks[j].lower() not in _PARTY_SFX:
            name.insert(0, toks[j])
            j -= 1
        while name and name[0].lower() in {"wale", "wali", "wala", "वाले", "वाली"}:
            name.pop(0)
        if not name:
            continue
        full = " ".join(name + [t])
        if destination and _name_key(full) == _name_key(destination):
            continue
        found.setdefault(_name_key(" ".join(name)), full)
    return next(iter(found.values())) if len(found) == 1 and marked else None


def _fix_descriptor_and_source(group_progress, text, statement=""):
    from rate_rules import split_descriptor
    notes = list(group_progress.get("descriptor_notes") or [])
    for side in ("source", "destination"):
        name = group_progress.get(side)
        new, desc = split_descriptor(name) if name else (name, None)
        if desc:
            print(f"🔗 MATERIAL MOVEMENT: {side} '{name}' → '{new}' (pehchaan '{desc}' note mein)")
            group_progress[side] = new
            notes.append(desc)
    src, dst = group_progress.get("source"), group_progress.get("destination")
    if not src:
        party = _source_party(text or "", dst)
        if party:
            group_progress["source"] = src = party
            print(f"🔗 MATERIAL MOVEMENT: source khaali tha — text mein '{party} ki/se' → source '{party}'")
    if not src:
        m = _SOURCE_PERSON.search(text or "")
        if m:
            group_progress["source"] = m.group(1)
            print(f"🔗 MATERIAL MOVEMENT: source khaali tha — text mein '{m.group(1)} se' → source '{m.group(1)}'")
            if dst and _re.search(rf"{_re.escape(dst)}\s+(?:mein|me|main|में)\s+.*{_re.escape(m.group(1))}",
                                  text, _re.IGNORECASE):
                print(f"🔗 MATERIAL MOVEMENT: '{dst} mein' sirf khareedne ki jagah hai — destination nahi")
                group_progress["destination"] = None
                notes.append(f"{dst} mein")
    if not group_progress.get("destination"):
        m = _ARRIVED_AT.search(text or "")
        if m:
            group_progress["destination"] = m.group(1)
            print(f"🔗 MATERIAL MOVEMENT: destination khaali tha — text mein '{m.group(0)}' → destination '{m.group(1)}'")
    _fix_places(group_progress, text, statement)
    if notes:
        group_progress["descriptor_notes"] = notes


# ───────────────────────────────────────────────────────────────
# Jagah ke naam (Stock bundle):
#   • "gudm" / "godm" / "dukn" — galat spelling → Gudam / Shop
#   • "6 khidkiyan dukaan pe rakhwayi, gudam wali" — "<jagah> wali" = source
#   • source khaali + statement mein doosri hamari jagah ("Sohan aaj gudam pe tha, … dukaan pahunchayi") → wahi source
#   • "Sharma ji ki site pe gudam wali 200 eent gayi" — ulta (source "… ki site", "pe" ke saath) → palto
# ───────────────────────────────────────────────────────────────
_OUR_PLACES = {"gudam": "Gudam", "godam": "Gudam", "godown": "Gudam", "shop": "Shop", "dukaan": "Shop", "dukan": "Shop",
               "गोदाम": "Gudam", "दुकान": "Shop"}
_PLACE_WALI = _re.compile(r"\b(gudam|godam|godown|shop|dukaan|dukan)\s+(?:wali|wala|wale|waali|waala|waale)\b"
                          r"|(गोदाम|दुकान)\s+(?:वाली|वाला|वाले)", _re.IGNORECASE)
_PLACE_ANY = _re.compile(r"\b(gudam|godam|godown|shop|dukaan|dukan)\b|गोदाम|दुकान", _re.IGNORECASE)


def _our_place(name):
    """Hamari jagah (gudam/shop) — galat spelling bhi ("gudm") → canonical, warna None."""
    import difflib
    n = " ".join(str(name or "").strip().lower().split())
    if not n:
        return None
    if n in _OUR_PLACES:
        return _OUR_PLACES[n]
    if " " not in n and len(n) >= 4:
        best = max(_OUR_PLACES, key=lambda k: difflib.SequenceMatcher(None, n, k).ratio())
        if difflib.SequenceMatcher(None, n, best).ratio() >= 0.8:
            return _OUR_PLACES[best]
    return None


_PROPERTY_WORDS = ("haveli", "kothi", "building", "dharamshala", "makaan", "makan", "हवेली", "कोठी", "बिल्डिंग", "धर्मशाला", "मकान")
_OWNER_PLACE = _re.compile(
    r"\b(?P<n>[A-Z][a-z]+\s+(?:ji|sahab|saab|seth))\s+(?:ki|ke|ka)\s+(?:purani\s+)?"
    r"(?P<p>haveli|kothi|building|dharamshala|makaan|makan|dukaan|dukan|godown|gudam)\b"
    r"(?:\s+(?P<m>wali|wala|wale|se|ka|ki))?")


def _fix_places(group_progress, text, statement=""):
    # "Malik sahab ki dukaan" / "Yadav ji ki haveli wali" — kisi aur ki jagah: us aadmi ka naam (site), hamari Shop nahi
    owned = list(_OWNER_PLACE.finditer(text or ""))
    if not group_progress.get("source"):
        owned += [m for m in _OWNER_PLACE.finditer(statement or "") if m.group(0) not in (text or "")]
    for m in owned:
        for side in ("source", "destination"):
            name = str(group_progress.get(side) or "").strip().lower()
            pw = m.group("p").lower()
            once = len(_re.findall(rf"\b{pw}\b", (text or "").lower())) == 1
            if name and ((name == pw and once) or name.startswith(m.group("n").lower())):
                if group_progress.get(side) != m.group("n"):
                    print(f"🏚️ MATERIAL MOVEMENT: {side} '{group_progress.get(side)}' → '{m.group('n')}' "
                          f"('{m.group(0)}' kisi aur ki jagah hai)")
                    group_progress[side] = m.group("n")
        in_action = m.group(0) in (text or "")
        if not group_progress.get("source") and ((m.group("m") or "").lower() in ("wali", "wala", "wale", "se")
                                                  or not in_action):
            group_progress["source"] = m.group("n")
            print(f"🏚️ MATERIAL MOVEMENT: source khaali — '{m.group(0)}' → source '{m.group('n')}'")
    for side in ("source", "destination"):
        name = group_progress.get(side)
        canon = _our_place(name)
        if name and canon and canon.lower() != str(name).strip().lower() and str(name).strip().lower() not in _OUR_PLACES:
            print(f"🔗 MATERIAL MOVEMENT: {side} '{name}' → '{canon}' (galat spelling)")
            group_progress[side] = canon
    src, dst = group_progress.get("source"), group_progress.get("destination")
    # ulta: source "<X> ki site" ke baad "pe/par/tak", aur doosri side "<jagah> wali/se"
    if src and dst and not _our_place(src) and _our_place(dst):
        if _re.search(rf"{_re.escape(src)}\s+(?:pe|par|tak|पे|पर|तक)\b", text or "", _re.IGNORECASE) and \
                _re.search(rf"{_re.escape(dst)}\s+(?:wali|wala|wale|se|से|वाली)\b", text or "", _re.IGNORECASE):
            print(f"🔁 MATERIAL MOVEMENT: '{src} pe' destination hai, '{dst} wali' source — palta")
            group_progress["source"], group_progress["destination"] = dst, src
            src, dst = dst, src
    if not src:
        m = _PLACE_WALI.search(text or "") or _PLACE_WALI.search(statement or "")
        if m and _OUR_PLACES.get((m.group(1) or m.group(2)).lower()) != _our_place(dst):
            group_progress["source"] = src = _OUR_PLACES[(m.group(1) or m.group(2)).lower()]
            print(f"🔗 MATERIAL MOVEMENT: source khaali — text mein '{m.group(0)}' → source '{src}'")
    if not src and _our_place(dst):
        st = _OWNER_PLACE.sub(" ", statement or "")          # "Malik sahab ki dukaan" hamari Shop nahi
        others = {_OUR_PLACES[w.lower()] for w in _PLACE_ANY.findall(st) if w} - {_our_place(dst)}
        if len(others) == 1:
            group_progress["source"] = src = others.pop()
            print(f"🔗 MATERIAL MOVEMENT: source khaali — statement mein doosri jagah '{src}' hi hai → source")

def _parse_identity_key(identity_key: str) -> tuple[str | None, str | None]:
    if "→" not in identity_key:
        return (_clean_location(identity_key), None)
    source, destination = identity_key.split("→", 1)
    return (_clean_location(source), _clean_location(destination))

_CLASSIFICATION_TABLE = {
    (MovementEntityType.SUPPLIER, MovementEntityType.STORAGE): TransactionType.IN,
    (MovementEntityType.SUPPLIER, MovementEntityType.SITE): TransactionType.IN,
    (MovementEntityType.STORAGE, MovementEntityType.CUSTOMER): TransactionType.OUT,
    (MovementEntityType.STORAGE, MovementEntityType.STORAGE): TransactionType.INTERNAL_MOVEMENT,
    (MovementEntityType.SITE, MovementEntityType.STORAGE): TransactionType.INTERNAL_MOVEMENT,
    (MovementEntityType.SITE, MovementEntityType.SITE): TransactionType.INTERNAL_MOVEMENT,
    (MovementEntityType.SUPPLIER, MovementEntityType.CUSTOMER): TransactionType.DIRECT_SALE,
    (MovementEntityType.SITE, MovementEntityType.CUSTOMER): TransactionType.DIRECT_SALE,
}

def _classify_transaction(
    group_id: str,
    source: str | None,
    source_type: MovementEntityType | None,
    destination: str | None,
    destination_type: MovementEntityType | None,
    existing_note: str | None,
) -> TransactionClassifierResult:
    # Aadhi jaankari: customer ko gaya par kahan se pata nahi → phir bhi SALE (stock nahi ghatega);
    # supplier se aaya par kahan gaya pata nahi → phir bhi MAAL AAYA (stock nahi badhega).
    if source_type is None and destination_type == MovementEntityType.CUSTOMER:
        return TransactionClassifierResult(
            group_id=group_id, transaction_type=TransactionType.OUT, source=None, destination=destination,
            note="Maal kahan se gaya pata nahi — sale record hogi, stock nahi ghatega.")
    if source_type == MovementEntityType.SUPPLIER and destination_type is None:
        return TransactionClassifierResult(
            group_id=group_id, transaction_type=TransactionType.IN, source=source, destination=None,
            note="Maal kahan utra pata nahi — supplier entry hogi, stock nahi badhega.")
    if source_type is None or destination_type is None:
        return TransactionClassifierResult(
            group_id=group_id,
            transaction_type=TransactionType.UNRESOLVED,
            source=source,
            destination=destination,
            note="Source or destination type unknown — user skipped confirmation.",
        )

    transaction_type = _CLASSIFICATION_TABLE.get(
        (source_type, destination_type),
        TransactionType.UNRESOLVED,
    )
    note = existing_note
    if transaction_type == TransactionType.UNRESOLVED and note is None:
        note = f"Unexpected combination: {getattr(source_type, 'value', source_type)} → {getattr(destination_type, 'value', destination_type)}"

    return TransactionClassifierResult(
        group_id=group_id,
        transaction_type=transaction_type,
        source=source,
        destination=destination,
        note=note,
    )

async def material_movement_node(state):
    """
    Resolves source and destination for ONE MATERIAL_MOVEMENT group,
    AND — once fully resolved — classifies it (IN/OUT/Internal/
    Direct Sale) in the same final pass. Classification used to live
    in a separate transaction_classifier_node, but that intermediate
    node created a race condition with LangGraph's fan-in: because
    this node loops back on itself (via route_after_material_movement)
    across multiple super-steps for its HITL resolution, LangGraph's
    fan-in at TOOL_DECISION was firing as soon as the FASTER parallel
    branches (e.g. a single-confirmation Person-Role branch) arrived,
    without waiting for this branch's separate classifier node to run.

    Merging classification into this node's own final return
    eliminates that extra edge/node entirely — TOOL_DECISION now only
    fires once this node's SINGLE outgoing edge resolves, which
    LangGraph can track correctly.

    Still invoked once per MATERIAL_MOVEMENT group, via Send. This
    node calls interrupt() AT MOST ONCE per invocation, per the
    original multi-pass design — see git history for full rationale.
    """
    db = SessionLocal()
    group = state["single_group"]

    results = state.get("material_movement_results", {})
    progress = state.get("material_movement_progress", {})
    classifier_results = state.get("transaction_classifier_results", {})

    try:
        if group.group_id in results:
            return {
                "material_movement_results": results,
                "transaction_classifier_results": classifier_results,
                "single_group": group,
            }

        group_progress = progress.get(group.group_id, {})

        if "source" not in group_progress or "destination" not in group_progress:
            source, destination = _parse_identity_key(group.identity_key)
            group_progress.setdefault("source", source)
            group_progress.setdefault("destination", destination)
            text = " ".join(a.text for a in group.actions)
            _fix_descriptor_and_source(group_progress, text, state.get("original_user_statement") or text)
            split = _person_at_place(group_progress.get("destination"), text, group_progress.get("source"))
            if split:
                print(f"📍 MATERIAL MOVEMENT: '{group_progress['destination']}' jagah hai — destination "
                      f"'{split[0]}', address '{split[1]}'")
                group_progress["destination"], group_progress["address"] = split
            progress[group.group_id] = group_progress

        source = group_progress.get("source")
        destination = group_progress.get("destination")

        if not source and "source" not in group_progress.get("resolved_missing", []):
            request = MaterialMovementHITLRequest(
                group_id=group.group_id,
                reason=MaterialMovementHITLReason.MISSING_FIELD,
                missing_field="source",
                suggestions=_storage_suggestions(db),
            )
            response: MaterialMovementHITLResponse = interrupt(request)
            group_progress["source"] = _clean_location(response.provided_value)
            group_progress.setdefault("resolved_missing", []).append("source")
            progress[group.group_id] = group_progress
            db.commit()
            db.close()
            return {"material_movement_progress": progress, "single_group": group}

        if not destination and "destination" not in group_progress.get("resolved_missing", []):
            request = MaterialMovementHITLRequest(
                group_id=group.group_id,
                reason=MaterialMovementHITLReason.MISSING_FIELD,
                missing_field="destination",
                suggestions=_storage_suggestions(db),
            )
            response: MaterialMovementHITLResponse = interrupt(request)
            group_progress["destination"] = _clean_location(response.provided_value)
            group_progress.setdefault("resolved_missing", []).append("destination")
            progress[group.group_id] = group_progress
            db.commit()
            db.close()
            return {"material_movement_progress": progress, "single_group": group}

        source = group_progress.get("source")
        destination = group_progress.get("destination")

        if source and "source_type" not in group_progress:
            source = _match_known_name(db, source)          # "SBI bhatte" → "SBI Bhatta"
            group_progress["source"] = source
            known = _known_location_type(db, source)
            if known:
                group_progress["source_type"] = known
                progress[group.group_id] = group_progress
            else:
                request = MaterialMovementHITLRequest(
                    group_id=group.group_id,
                    reason=MaterialMovementHITLReason.LOCATION_TYPE_CONFIRMATION,
                    location_name=source,
                    options=[
                        LocationTypeOption(option_id=1, location_type=MovementEntityType.STORAGE),
                        LocationTypeOption(option_id=2, location_type=MovementEntityType.SITE),
                        LocationTypeOption(option_id=3, location_type=MovementEntityType.CUSTOMER),
                        LocationTypeOption(option_id=4, location_type=MovementEntityType.SUPPLIER),
                    ],
                )
                response: MaterialMovementHITLResponse = interrupt(request)
                if response.selected_option is None:
                    group_progress["source_type"] = None
                else:
                    chosen = {1: MovementEntityType.STORAGE, 2: MovementEntityType.SITE,
                              3: MovementEntityType.CUSTOMER, 4: MovementEntityType.SUPPLIER}[response.selected_option]
                    sync_movement_entity(db, name=source, entity_type=chosen, confirmed_by="hitl")
                    group_progress["source_type"] = chosen
                progress[group.group_id] = group_progress
                db.commit()
                db.close()
                return {"material_movement_progress": progress, "single_group": group}

        elif not source:
            group_progress["source_type"] = None
            progress[group.group_id] = group_progress

        if destination and "destination_type" not in group_progress:
            destination = _match_known_name(db, destination)
            group_progress["destination"] = destination
            known = _known_location_type(db, destination)
            if known:
                group_progress["destination_type"] = known
                progress[group.group_id] = group_progress
            else:
                request = MaterialMovementHITLRequest(
                    group_id=group.group_id,
                    reason=MaterialMovementHITLReason.LOCATION_TYPE_CONFIRMATION,
                    location_name=destination,
                    options=[
                        LocationTypeOption(option_id=1, location_type=MovementEntityType.STORAGE),
                        LocationTypeOption(option_id=2, location_type=MovementEntityType.SITE),
                        LocationTypeOption(option_id=3, location_type=MovementEntityType.CUSTOMER),
                        LocationTypeOption(option_id=4, location_type=MovementEntityType.SUPPLIER),
                    ],
                )
                response: MaterialMovementHITLResponse = interrupt(request)
                if response.selected_option is None:
                    group_progress["destination_type"] = None
                else:
                    chosen = {1: MovementEntityType.STORAGE, 2: MovementEntityType.SITE,
                              3: MovementEntityType.CUSTOMER, 4: MovementEntityType.SUPPLIER}[response.selected_option]
                    sync_movement_entity(db, name=destination, entity_type=chosen, confirmed_by="hitl")
                    group_progress["destination_type"] = chosen
                progress[group.group_id] = group_progress
                db.commit()
                db.close()
                return {"material_movement_progress": progress, "single_group": group}

        elif not destination:
            group_progress["destination_type"] = None
            progress[group.group_id] = group_progress

        # Both fully resolved — finalize this group AND classify it,
        # all in this same final pass, so no extra node/edge is needed.
        note = None
        if source and destination and source.strip().lower() == destination.strip().lower():
            note = "WARNING: source and destination resolved to the same location."

        results[group.group_id] = {
            "source": source,
            "source_type": group_progress.get("source_type"),
            "destination": destination,
            "destination_type": group_progress.get("destination_type"),
            "address": group_progress.get("address"),
            "descriptor": ", ".join(group_progress.get("descriptor_notes") or []) or None,
            "note": note,
        }
        progress.pop(group.group_id, None)

        classification = _classify_transaction(
            group_id=group.group_id,
            source=source,
            source_type=group_progress.get("source_type"),
            destination=destination,
            destination_type=group_progress.get("destination_type"),
            existing_note=note,
        )
        classifier_results[group.group_id] = classification

    finally:
        db.commit()
        db.close()

    print("\n=== MATERIAL MOVEMENT NODE RESULT ===")
    print(results)
    print("=== TRANSACTION CLASSIFIER RESULT ===")
    print(classifier_results)
    print("======================================")

    return {
        "material_movement_results": results,
        "material_movement_progress": progress,
        "transaction_classifier_results": classifier_results,
        "single_group": group,
    }


