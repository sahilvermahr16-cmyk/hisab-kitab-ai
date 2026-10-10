# test/testcases/rpt_testcases.py — Report bundle (chhota set, 20), test set v1 (LOCKED 2026-10-08).
#
# Report ka hisaab (PDF, numbers) Python/SQL karta hai — wo yahan NAHI jaancha jaata.
# Yahan sirf LLM wala hissa jaancha jaata hai:
#   1. route   — sawaal report mein gaya (entry nahi bani); D wale statement entry hain, report nahi
#   2. kind    — kaunsi report (person / overall / expense / cash_flow / work_log / material_movement / purchase)
#   3. naam    — kis party ka (jaana-pehchaana naam DB wali spelling mein)
#   4. tareekh — start / end (date ke code: T = test ka din; T-N; M0 = is mahine ki 1 tareekh; PM_S/PM_E = pichla
#                mahina; Y0 = 1 Jan; "MM-DD" = isi saal ki tareekh; None = statement mein tareekh nahi → system poochhe)
#
# Runner pehle report-sawaal pe ruk jaata hai; us waqt tak statement se jo samjha gaya (report_data) wahi jaancha jaata hai.
# Statements user (Sahil) ke saath tay kiye; prompt ke examples se milaaye (difflib ≤ 0.69).

BUNDLE = "Report"
PREFIX = "RPT"


def RP(kind, person=None, role=None, start=None, end=None, lang=None):
    return dict(route="report", kind=kind, person=person, role=role, start=start, end=end, lang=lang)


def NOT_REPORT():
    return dict(route="accounting")


TESTCASES = [
    # =====================================================================  A — person ka khata
    dict(id="RPT-A-01", category="A", hinglish="Zara Sharma ji wala khata kholo, poora lena dena dekhna hai",
         english="Open Sharma ji's account, want to see all dues", outcome="REPORT", roles={},
         report=RP("person", "Sharma ji"), expected=[], why="Customer ledger, no date (system should ask)"),
    dict(id="RPT-A-02", category="A", hinglish="Suresh Traders pe hamara kitna udhaar chadha hua hai abhi",
         english="How much credit is outstanding on Suresh Traders right now", outcome="REPORT", roles={},
         report=RP("person", "Suresh Traders"), expected=[], why="Balance question = report, not entry"),
    dict(id="RPT-A-03", category="A", hinglish="Bhatte wale SBI ki pichle 14 dino ki entries ka report bana do",
         english="Make a report of the last 14 days' entries of SBI kiln", outcome="REPORT", roles={},
         report=RP("person", "SBI Bhatta", "supplier", "T-13", "T"), expected=[], why="Supplier + 14 days"),
    dict(id="RPT-A-04", category="A", hinglish="Is mahine Ram ko kya kya diya aur kitna kaam kiya, report do",
         english="Give a report of what Ram was paid and how much he worked this month", outcome="REPORT", roles={},
         report=RP("person", "Ram", None, "M0", "T"), expected=[], why="'diya / kaam kiya' must not become entries"),
    dict(id="RPT-A-05", category="A", hinglish="Kitanu ka khata dikhao English mein",
         english="Show Kitanu's account in English", outcome="REPORT", roles={},
         report=RP("person", "Kitanu", lang="en"), expected=[], why="Language stated"),
    dict(id="RPT-A-06", category="A", hinglish="1 se 15 september tak Suresh Traders ka hisab",
         english="Suresh Traders' account from 1 to 15 September", outcome="REPORT", roles={},
         report=RP("person", "Suresh Traders", None, "09-01", "09-15"), expected=[], why="Explicit date range"),

    # =====================================================================  B — bina person wali report
    dict(id="RPT-B-01", category="B", hinglish="October mein dukaan ke kharchon ki list nikalo",
         english="List the shop's expenses in October", outcome="REPORT", roles={},
         report=RP("expense", start="10-01", end="10-31|T"), expected=[], why="Month name"),
    dict(id="RPT-B-02", category="B", hinglish="Aaj galle mein kitna cash aaya aur kitna gaya",
         english="How much cash came in and went out of the till today", outcome="REPORT", roles={},
         report=RP("cash_flow", start="T", end="T"), expected=[], why="Cash flow today"),
    dict(id="RPT-B-03", category="B", hinglish="Pichle mahine ka poore business ka hisab chahiye",
         english="Need the whole business account for last month", outcome="REPORT", roles={},
         report=RP("overall", start="PM_S", end="PM_E"), expected=[], why="Overall, previous month"),
    dict(id="RPT-B-04", category="B", hinglish="Kal kis din kya kaam hua site pe, register dikhao",
         english="Show the register of what work happened at the site yesterday", outcome="REPORT", roles={},
         report=RP("work_log", start="T-1", end="T-1"), expected=[], why="Work log yesterday"),
    dict(id="RPT-B-05", category="B", hinglish="Sitambar mahine ki maal aawajahi ki report",
         english="Report of material movement in September", outcome="REPORT", roles={},
         report=RP("material_movement", start="09-01", end="09-30"), expected=[], why="Misspelt month"),
    dict(id="RPT-B-06", category="B", hinglish="Property wale saudon ka hisab dikha do",
         english="Show the account of the property deals", outcome="REPORT", roles={},
         report=RP("purchase"), expected=[], why="Purchase report"),
    dict(id="RPT-B-07", category="B", hinglish="Pichle 7 dino mein galle se kya aaya kya gaya",
         english="What came into and went out of the till in the last 7 days", outcome="REPORT", roles={},
         report=RP("cash_flow", start="T-6", end="T"), expected=[], why="7 days"),
    dict(id="RPT-B-08", category="B", hinglish="Pichle 3 mahine ki kharid ka hisab",
         english="Account of purchases in the last 3 months", outcome="REPORT", roles={},
         report=RP("purchase", start="T-3M", end="T"), expected=[], why="3 months"),

    # =====================================================================  C — edge
    dict(id="RPT-C-01", category="C", hinglish="ek report bana do bhai",
         english="make a report", outcome="REPORT", roles={},
         report=RP(None), expected=[], why="Kind not stated — must ask, not guess 'overall'"),
    dict(id="RPT-C-02", category="C", hinglish="Ghar ka kharcha is saal kitna gaya",
         english="How much household spending went this year", outcome="REPORT", roles={},
         report=RP("person", None, "family", "Y0", "T"), expected=[], why="Family report, not business expense"),
    dict(id="RPT-C-03", category="C", hinglish="Papa ne is mahine kitne paise liye, dikhao",
         english="Show how much money Papa took this month", outcome="REPORT", roles={},
         report=RP("person", "Papa", None, "M0", "T"), expected=[], why="'liye' must not become a family entry"),
    dict(id="RPT-C-04", category="C", hinglish="sohan ki puri entri dkhao bhai",
         english="show all of sohan's entries", outcome="REPORT", roles={},
         report=RP("person", "Sohan"), expected=[], why="Spelling mistakes"),

    # =====================================================================  D — entry hai, report NAHI
    dict(id="RPT-D-01", category="D", hinglish="Sharma ji ka hisab clear ho gaya, 4000 de gaye",
         english="Sharma ji's account is cleared, he paid 4000", outcome="ENTRY", roles={"sharma ji": "Customer"},
         report=NOT_REPORT(), expected=[], why="'hisab' word but money came — accounting"),
    dict(id="RPT-D-02", category="D", hinglish="Ram ka aaj ka 600 banta tha, de diya",
         english="Ram's 600 for today was due, paid it", outcome="ENTRY", roles={"ram": "Employee"},
         report=NOT_REPORT(), expected=[], why="Payment — accounting, not report"),
]

CATEGORY_LABELS = {"A": "A - Person report", "B": "B - Other reports", "C": "C - Edge", "D": "D - Not a report"}

HINDI = {
    "RPT-A-01": "ज़रा शर्मा जी वाला खाता खोलो, पूरा लेना देना देखना है",
    "RPT-A-02": "सुरेश ट्रेडर्स पे हमारा कितना उधार चढ़ा हुआ है अभी",
    "RPT-A-03": "भट्टे वाले एसबीआई की पिछले 14 दिनों की एंट्री की रिपोर्ट बना दो",
    "RPT-A-04": "इस महीने राम को क्या क्या दिया और कितना काम किया, रिपोर्ट दो",
    "RPT-A-05": "कितनू का खाता दिखाओ इंग्लिश में",
    "RPT-A-06": "1 से 15 सितंबर तक सुरेश ट्रेडर्स का हिसाब",
    "RPT-B-01": "अक्टूबर में दुकान के खर्चों की लिस्ट निकालो",
    "RPT-B-02": "आज गल्ले में कितना कैश आया और कितना गया",
    "RPT-B-03": "पिछले महीने का पूरे बिज़नेस का हिसाब चाहिए",
    "RPT-B-04": "कल किस दिन क्या काम हुआ साइट पे, रजिस्टर दिखाओ",
    "RPT-B-05": "सितंबर महीने की माल आवाजाही की रिपोर्ट",
    "RPT-B-06": "प्रॉपर्टी वाले सौदों का हिसाब दिखा दो",
    "RPT-B-07": "पिछले 7 दिनों में गल्ले से क्या आया क्या गया",
    "RPT-B-08": "पिछले 3 महीने की खरीद का हिसाब",
    "RPT-C-01": "एक रिपोर्ट बना दो भाई",
    "RPT-C-02": "घर का खर्चा इस साल कितना गया",
    "RPT-C-03": "पापा ने इस महीने कितने पैसे लिए, दिखाओ",
    "RPT-C-04": "सोहन की पूरी एंट्री दिखाओ भाई",
    "RPT-D-01": "शर्मा जी का हिसाब क्लियर हो गया, 4000 दे गए",
    "RPT-D-02": "राम का आज का 600 बनता था, दे दिया",
}

ENGLISH_INPUT = {t["id"]: t["english"] for t in TESTCASES}

for _t in TESTCASES:
    _t["hindi"] = HINDI[_t["id"]]
    _t["english_input"] = ENGLISH_INPUT[_t["id"]]
assert set(HINDI) == set(ENGLISH_INPUT) == {t["id"] for t in TESTCASES}
assert len(TESTCASES) == 20
