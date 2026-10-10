# expense_rules.py — kharche (expense) ke code niyam: payment kab, purana kharcha, aadha.
#
#   Model: record_expense = kharcha / bill; record_expense_payment = paisa diya (galla / CashLedger ghatta hai).
#   Isliye "diesel dalwaya / 1400 diye / 250 lage" = DONO. Sirf bill aaya (abhi nahi diya / udhaar) = sirf expense.
#   "Pichle hafte wali servicing ke 3000 baaki the, aaj de diye" = purana kharcha → sirf payment.
import re

EXPENSE_WORD = re.compile(
    r"\b(diesel|deezal|dijal|petrol|cng|fuel|tel|gas\s+cylinder|cylinder|bijli|bijlee|electricity|bill|kiraya|kiraaya|"
    r"rent|repair|marammat|theek|thik|servicing|service|puncture|tyre|tayar|engine|oil|recharge|bhaada|bhada|freight|"
    r"chai|nashta|kharcha|kharche|safai|wifi|tanker|board|taala|tala|meter|freezer|ac|jcb|crane|hydra|rassi|"
    r"pankchar|panchar|puncher)\b"
    r"|डीज़ल|डीजल|पेट्रोल|सीएनजी|सिलेंडर|बिजली|बिल|किराया|मरम्मत|ठीक|सर्विस|पंक्चर|टायर|रिचार्ज|भाड़ा|चाय|खर्चा|खर्चे|सफाई",
    re.IGNORECASE)

# paisa abhi NAHI gaya
UNPAID = re.compile(
    r"\b(abhi\s+)?(diya|diye|di|bhara|bhare|chukaya|chukaye)\s+nahi\b|\bnahi\s+(diya|diye|bhara|chukaya)\b"
    r"|\bbaad\s+(mein|me|main)\s+(denge|dena|de\s+denge|dunga|chukayenge)\b|\budhaar\b|\budhar\b|\bnot\s+paid\b"
    r"|अभी\s+दिया\s+नहीं|नहीं\s+दिया|बाद\s+में\s+देंगे|उधार", re.IGNORECASE)

# paisa diya / kharch hua (inme se koi ho to "bill aaya" bhi paid maana jayega)
PAID_VERB = re.compile(
    r"\b(diya|diye|di|de\s+diya|de\s+diye|bhara|bhar\s+diya|bhare|chukaya|chuka\s+diya|lage|lag\s+gaye|kiye|kiya|"
    r"karwaya|karwayi|karaya|karayi|bharwaya|bharwayi|dalwaya|dalwayi|daala|dala|badalwaya|banwaya|mangwaya|li|liya|"
    r"laaye|laya|gaya|gayi|kat\s+gaya|kata|paid|gave|spent)\b"
    r"|दिया|दिए|भरा|भरवाया|डलवाया|करवाया|करवाई|लगे|लिया|ली|गया|कट\s+गया", re.IGNORECASE)

_BILL_ONLY = re.compile(r"\bbill\s+(aaya|aayi|aa\s+gaya)(\s+hai)?\b|बिल\s+आया", re.IGNORECASE)

OLD_DUE = re.compile(
    r"\b(baaki|baki|bakaya)\s+(the|tha|thi|hai|hain)\b.*\b(diye|diya|de\s+diye|de\s+diya|chuka\w*|bhar\s+diya|bhara)\b"
    r"|(?:\b(?:ke|ka|ki)\s+purane\b|\bpurane\s+(?:\d|hisab|hisaab|bill|paise)).*\b(chuka\w*|de\s+diye|de\s+diya|diye|diya)\b"
    r"|बाकी\s+थे.*(दिए|दिया|चुका)", re.IGNORECASE)

HALF = re.compile(r"\b(aadha|adha|aadhe|adhe|aadhi|adhi|half)\b|आधा|आधे|आधी", re.IGNORECASE)


def expense_paid(text: str) -> bool:
    """Is kharche ka paisa diya gaya? (warna sirf expense, payment nahi)"""
    t = text or ""
    if UNPAID.search(t):
        return False
    if _BILL_ONLY.search(t):
        rest = _BILL_ONLY.sub(" ", t)
        return bool(PAID_VERB.search(rest))
    return True


def old_expense_due(text: str) -> bool:
    """'X ke 3000 baaki the, aaj de diye' — purane kharche ka paisa, naya kharcha nahi."""
    return bool(OLD_DUE.search(text or "")) and bool(EXPENSE_WORD.search(text or ""))


# Category ke pakke shabd — LLM 'misc' likh de tab bhi saaf shabd par code sahi category lagata hai.
_REPAIR = re.compile(
    r"\b(theek|thik|marammat|repair|servicing|service|puncture|pankchar|panchar|puncher|tyre|tayar|tire|engine\s+oil|clutch|hydraulic|"
    r"kharab|badalwaya|badalwayi|generator)\b|\bac\s+(mein|me|main|ki|ka)\s+gas\b"
    r"|ठीक|मरम्मत|सर्विस|पंक्चर|टायर|खराब|बदलवाया", re.IGNORECASE)
_FUEL = re.compile(
    r"\b(diesel|deezal|dijal|petrol|cng|lpg|fuel|gas\s+cylinder|cylinder)\b|डीज़ल|डीजल|पेट्रोल|सीएनजी|सिलेंडर", re.IGNORECASE)
_RENT = re.compile(r"\b(kiraya|kiraaya|kiraye|rent|jcb|crane|hydra)\b|किराया|जेसीबी", re.IGNORECASE)


def category_from_text(text: str):
    """'repair' / 'fuel' / 'rent' — sirf jab shabd saaf ho; warna None (LLM ka jawaab rahega)."""
    t = text or ""
    fuel = _FUEL.search(t)
    # "Diesel 2000 ka badalwaya" — fuel ke saath sirf "badalwaya" repair nahi (tyre / parts ho tab repair)
    if _REPAIR.search(t) and not (fuel and not re.search(r"\b(theek|thik|marammat|repair|servic\w*|puncture|pankchar|"
                                                         r"panchar|tyre|tayar|engine\s+oil|clutch|hydraulic|kharab)\b"
                                                         r"|\bac\s+(mein|me|main)\s+gas\b", t, re.IGNORECASE)):
        return "repair"
    if fuel:
        return "fuel"
    if _RENT.search(t):
        return "rent"
    return None


if __name__ == "__main__":
    for t in ["Tractor ki tanki full karwayi, 3200 ka diesel", "Bijli ka bill aaya 1850 ka, PhonePe se bhar diya",
              "Generator ka 2400 ka bill aaya hai, abhi diya nahi", "Bijli ka bill 2100 aaya, aadha abhi bhara baaki agle mahine",
              "Mazdooron ke liye chai-nashta 180 ka aaya", "Diesel 3000", "Mistri ne generator dekh liya, paise baad mein denge",
              "Pichle hafte wali servicing ke 3000 baaki the, aaj de diye", "Dukaan ka kiraya is baar abhi nahi diya"]:
        print(f"{t[:60]:62} paid={expense_paid(t)} old_due={old_expense_due(t)} half={bool(HALF.search(t))}")
