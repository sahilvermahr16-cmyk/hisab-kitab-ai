# attendance_rules.py — haazri ke pakke niyam (LLM ke andaze ke baad code se jaanch)
#
#   1. "kaam pe tha", "duty pe tha", "subah se shaam tak" = MAUJOODGI → attendance, task nahi
#   2. driving tabhi jab gaadi/trip/chakkar/tractor/dumper ki baat ho
#   3. "poore din trip pe raha" → driving P ; "aadhe din baad chala gaya" → attendance half
import re

DRIVING_WORDS = re.compile(
    r"\b(driving|drivery|driveri|driver|drive|drove|gaadi|gadi|gaddi|tractor|dumper|truck|tempo|"
    r"trip|trips|chakkar|chakar|chakkr|pheri|feri|round)\b"
    r"|ड्राइविंग|ड्राइवरी|गाड़ी|गाडी|ट्रैक्टर|डंपर|ट्रक|ट्रिप|चक्कर|फेरी",
    re.IGNORECASE)

FULL_DAY = re.compile(
    r"\b(poora din|pura din|poore din|pure din|sara din|saara din|all day|whole day|full day|"
    r"subah se shaam|subah se sham|morning (?:to|till) evening)\b"
    r"|पूरा दिन|पूरे दिन|सारा दिन|सुबह से शाम",
    re.IGNORECASE)

HALF_DAY = re.compile(
    r"\b(aadha din|adha din|aadhe din|adhe din|half day|half a day|half the day|"
    r"dopahar ko chala|dopahar me chala|beech mein chala|beech me chala|left early|left after|"
    r"sirf subah|sirf shaam|sirf sham|subah ki shift|shaam ki shift|sham ki shift|aadhi shift|adhi shift|"
    r"morning shift only|only the morning shift|only morning|half shift)\b"
    r"|आधा दिन|आधे दिन|दोपहर को चला|बीच में चला|सिर्फ सुबह|सिर्फ शाम|सुबह की शिफ्ट|शाम की शिफ्ट|आधी शिफ्ट",
    re.IGNORECASE)

# "kaam pe tha" — maujoodgi, koi task nahi
PRESENCE = re.compile(
    r"\b(kaam pe tha|kaam par tha|kaam pe thi|kaam par thi|kaam pe raha|kaam par raha|kaam pe aaya|"
    r"kaam par aaya|duty pe tha|duty par tha|duty pe raha|duty par raha|subah se shaam tak|"
    r"subah se sham tak|was at work|at work all day|on duty|was on duty)\b"
    r"|काम पे था|काम पर था|काम पे रहा|काम पर रहा|ड्यूटी पे था|ड्यूटी पर था|सुबह से शाम तक",
    re.IGNORECASE)

# maujoodgi ke alawa kaam ke shabd (task) — ye ho to net nahi chalega
_TASK = re.compile(
    r"\b(banai|banaya|bhari|bhara|utari|utara|todi|toda|giraayi|safai|ladai|load|unload|chinai|"
    r"plaster|kiya|ki safai|built|loaded|unloaded|painted|cleaned)\b"
    r"|बनाई|बनाया|भरी|उतारी|तोड़ी|सफाई|लोड",
    re.IGNORECASE)


# haazri ke shabd (maujoodgi / gair-maujoodgi)
ATTEND_WORDS = re.compile(
    r"\b(haaziri|haazri|hajri|haziri|hazri|present|absent|aaya|aayi|aa gaya|nahi aaya|chutti|chhutti|"
    r"pura din|poora din|aadha din|came|attendance)\b"
    r"|हाज़िरी|हाजिरी|हाज़री|आया|आई|छुट्टी|पूरा दिन|आधा दिन",
    re.IGNORECASE)
# "poori" haazri saaf likhi hai (haaziri lagao / present / pura din aaya)
FULL_PRESENCE = re.compile(
    r"\b(haaziri|haazri|hajri|haziri|hazri|present|pura din aaya|poora din aaya)\b|हाज़िरी|हाजिरी|हाज़री",
    re.IGNORECASE)


# Ye number paisa nahi hain: ginti ("6 chakkar", "3 trips", "2 ghante") aur phone number
_COUNT = re.compile(
    r"\d+\s*(chakkar|chakar|chakkr|trip|trips|pheri|pheriyan|feri|round|rounds|ghante|ghanta|hours?|hrs?|"
    r"chakkaron|tasle|tasla|boriyan|bori|bags?)\b"
    r"|\d+\s*(चक्कर|ट्रिप|फेरी|फेरे|घंटे|घंटा|तसले|बोरी|बोरियां|बोरियाँ)",
    re.IGNORECASE)
_PHONE = re.compile(r"(?:\+91[\s-]?)?(?<!\d)[6-9]\d{9}(?!\d)")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def strip_non_money(text: str) -> str:
    """Date, phone number aur ginti hata do — jo number bache wahi paisa ho sakta hai."""
    return _COUNT.sub(" ", _PHONE.sub(" ", _ISO_DATE.sub(" ", text or "")))


def _no_amount(text: str) -> bool:
    return not re.search(r"\d", strip_non_money(text))


def attendance_and_driving_pair(a: str, b: str) -> bool:
    """Ek action haazri ka, doosra sirf gaadi/driving ka — dono bina amount/task ke?"""
    if not (_no_amount(a) and _no_amount(b)) or _TASK.search(a) or _TASK.search(b):
        return False
    da, db = bool(DRIVING_WORDS.search(a)), bool(DRIVING_WORDS.search(b))
    return (ATTEND_WORDS.search(a) and db and not da) or (ATTEND_WORDS.search(b) and da and not db)


OVERTIME = re.compile(
    r"\b(extra ruka|extra ruki|der tak ruka|der tak ruki|overtime|stayed late|ghante extra|ghanta extra)\b"
    r"|एक्स्ट्रा रुका|देर तक रुका|ओवरटाइम|घंटे एक्स्ट्रा",
    re.IGNORECASE)


def overtime(text: str) -> bool:
    """'2 ghante extra ruka' — extra kaam hai, haazri nahi."""
    return bool(OVERTIME.search(text or ""))


# "aadha din kaam kiya" — yahan "kaam kiya" sirf maujoodgi hai, koi task nahi
_GENERIC_WORK = re.compile(
    r"\b(kaam|kam|kaam pe|kaam par)\s+(kiya|kia|kari|kara)\b|\bworked\b|\bdid work\b|काम किया",
    re.IGNORECASE)


def no_amount_no_task(text: str) -> bool:
    """Na amount, na koi task — kaam (employee transaction) ki entry ka matlab hi nahi."""
    t = text or ""
    if (HALF_DAY.search(t) or FULL_DAY.search(t)):
        t = _GENERIC_WORK.sub(" ", t)          # din ki lambai + "kaam kiya" = haazri
    return _no_amount(t) and not _TASK.search(t)


def presence_only(text: str) -> bool:
    """Sirf maujoodgi ki baat hai — koi amount ya task nahi?"""
    t = text or ""
    if not PRESENCE.search(t) or not _no_amount(t):
        return False
    return not _TASK.search(PRESENCE.sub(" ", t))


def fix_attendance_args(arguments, text: str) -> list:
    """record_attendance ke arguments ko text ke hisaab se theek karo. Returns: badlaav (log ke liye)."""
    changes = []
    att = str(getattr(getattr(arguments, "attendance", None), "value", getattr(arguments, "attendance", None)))
    drv = str(getattr(getattr(arguments, "driving", None), "value", getattr(arguments, "driving", None)))
    t = text or ""
    if not DRIVING_WORDS.search(t):
        if drv in ("P", "half"):
            if att == "P" and drv == "half":
                _set(arguments, "attendance", "half", changes)
            _set(arguments, "driving", "absent", changes)
    else:
        if drv in ("absent", "None") and att != "absent":
            if HALF_DAY.search(t):
                _set(arguments, "driving", "half", changes)
            elif FULL_DAY.search(t):
                _set(arguments, "driving", "P", changes)
    att = str(getattr(getattr(arguments, "attendance", None), "value", getattr(arguments, "attendance", None)))
    drv = str(getattr(getattr(arguments, "driving", None), "value", getattr(arguments, "driving", None)))
    if att == "P" and HALF_DAY.search(t) and not DRIVING_WORDS.search(t):
        _set(arguments, "attendance", "half", changes)
    # "haaziri lagao, aadha din gaadi chalayi" → poori haazri, aadhi driving
    if att == "half" and drv == "half" and FULL_PRESENCE.search(t) and DRIVING_WORDS.search(t):
        _set(arguments, "attendance", "P", changes)
    return changes


def _set(arguments, field, value, changes):
    from tool_argument_models import AttendanceStatus
    old = getattr(arguments, field, None)
    new = AttendanceStatus(value)
    if old != new:
        changes.append(f"{field}: {getattr(old, 'value', old)} → {value}")
        setattr(arguments, field, new)
