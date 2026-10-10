# test/testcases/cor_testcases.py — Correction bundle (25), test set v1 (LOCKED 2026-10-08).
#
# Correction ka flow: model sirf (1) pehchanta hai ki ye correction hai, (2) naam aur (3) tareekh nikalta hai.
# Uske baad sab menu se chalta hai (category, entry ki list, delete / naya statement) — wo Python hai, yahan NAHI jaancha.
# Runner pehle correction-sawaal pe rukta hai; us waqt tak jo samjha gaya (correction_data) wahi jaancha jaata hai:
#   route  — correction pehchana (A/B/C) ya nahi pehchana (D — wahan entry banni chahiye)
#   naam   — correction_data.name (None = statement mein naam nahi)
#   tareekh— correction_data.date (None = statement mein pakki tareekh nahi → system poochhe)
#   C      — saath wali nayi entry bhi final confirmation tak pahunchi (correction ke baad save hoti, isliye DB nahi)
# Date codes: T = test ka din; T-N; "MM-DD" = isi saal ki tareekh.
# Statements user (Sahil) ke saath tay kiye; prompt / purane tests se milaaye (difflib ≤ 0.69).

BUNDLE = "Correction"
PREFIX = "COR"

E, C, S, F = "Employee", "Customer", "Supplier", "Family"
ROLES = {"ram": E, "kitanu": E, "sohan": E, "sharma ji": C, "suresh traders": S, "sbi bhatta": S, "papa": F}


def CR(name=None, date=None):
    return dict(route="correction", name=name, date=date)


def NOT_CORR():
    return dict(route="accounting")


def T(tool, name=None, amount=None, **extra):
    return dict(tool=tool, name=name, amount=amount, **extra)


EMP_TXN, ATT, SALE_PAY = "record_employee_transaction", "record_attendance", "record_sale_payment"
SUP_TXN, EXP, OPEN = "record_supplier_transaction", "record_expense", "record_opening_balance"


def tc(id_, hg, en, corr, expected=(), why=""):
    cat = id_.split("-")[1]
    return dict(id=id_, category=cat, hinglish=hg, english=en,
                outcome="CORRECTION" if corr["route"] == "correction" else "ENTRY",
                roles=dict(ROLES), correction=corr, expected=list(expected), why=why)


TESTCASES = [
    # =====================================================================  A — naam + tareekh
    tc("COR-A-01", "Ram ki kal wali haazri galat chadh gayi, wo aaya hi nahi tha",
       "Ram's attendance for yesterday was recorded wrongly, he didn't even come", CR("Ram", "T-1"),
       why="'aaya hi nahi' — attendance net se nayi entry nahi"),
    tc("COR-A-02", "Sharma ji se 3 tareekh ko jo 5000 aaye the, wo entry galat hai",
       "The 5000 received from Sharma ji on the 3rd is a wrong entry", CR("Sharma ji", "10-03")),
    tc("COR-A-03", "Suresh Traders ka parso wala bill galti se do baar likh diya",
       "Suresh Traders' bill from day before yesterday was written twice by mistake", CR("Suresh Traders", "T-2")),
    tc("COR-A-04", "Kitanu ko 2 din pehle 800 diye the, wo 600 the, theek kar do",
       "Kitanu was given 800 two days ago, it was 600, fix it", CR("Kitanu", "T-2"),
       why="'800 diye' se nayi payment nahi"),
    tc("COR-A-05", "5 october ko Sohan ke naam pe jo kaam chadhaya wo cancel karo",
       "Cancel the work entered in Sohan's name on 5 October", CR("Sohan", "10-05")),
    tc("COR-A-06", "Papa ne kal galle se 2000 liye the wali entry hata do",
       "Remove the entry of Papa taking 2000 from the till yesterday", CR("Papa", "T-1"),
       why="'liye the' se family entry nahi"),
    tc("COR-A-07", "SBI Bhatte ki 1 tareekh wali eent ki entry mein rate galat lag gaya",
       "The rate in the 1st's brick entry of SBI kiln is wrong", CR("SBI Bhatta", "10-01")),

    # =====================================================================  B — bina naam ya bina tareekh
    tc("COR-B-01", "Kal wali diesel ki entry mein galti ho gayi hai",
       "There is a mistake in yesterday's diesel entry", CR(None, "T-1")),
    tc("COR-B-02", "Pichli wali entry mein rakam galat chadh gayi",
       "The amount in the previous entry was entered wrong", CR(None, None),
       why="'pichli wali' tareekh nahi — poochhna chahiye"),
    tc("COR-B-03", "Ram ka jo payment likha tha usme gadbad hai, sahi karna hai",
       "Something is wrong in Ram's payment that was written, need to fix it", CR("Ram", None)),
    tc("COR-B-04", "Aaj subah jo bijli ka bill chadhaya wo hata do",
       "Remove the electricity bill entered this morning", CR(None, "T")),
    tc("COR-B-05", "Galti se 4000 ki jagah 40000 likh diya, theek karo",
       "Wrote 40000 instead of 4000 by mistake, fix it", CR(None, None)),
    tc("COR-B-06", "Suresh Traders ke khate mein se wo ek entry hatwani hai",
       "Need to get that one entry removed from Suresh Traders' account", CR("Suresh Traders", None),
       why="'hatwani' — regex ka shabd nahi"),

    # =====================================================================  C — nayi entry + correction
    tc("COR-C-01", "Ram ko aaj 500 diye, aur kal ki uski haazri galat lagi thi",
       "Gave Ram 500 today, and his attendance yesterday was marked wrong", CR("Ram", "T-1"),
       [T(EMP_TXN, "Ram", 500)]),
    tc("COR-C-02", "Sharma ji ne 3000 aur bheje, parso wali unki entry mein galti hai",
       "Sharma ji sent 3000 more, there's a mistake in his entry from day before yesterday", CR("Sharma ji", "T-2"),
       [T(SALE_PAY, "Sharma ji", 3000)]),
    tc("COR-C-03", "Aaj chai ke 120 lage, kal wala kiraya galat likha gaya tha",
       "Spent 120 on tea today, yesterday's rent was written wrong", CR(None, "T-1"),
       [T(EXP, None, 120)]),
    tc("COR-C-04", "Kitanu ne aaj 700 ka kaam kiya, 4 tareekh wali uski entry cancel karo",
       "Kitanu did 700 worth of work today, cancel his entry from the 4th", CR("Kitanu", "10-04"),
       [T(EMP_TXN, "Kitanu", 700)]),
    tc("COR-C-05", "Suresh Traders se 2000 eent aayi, pichle hafte ka unka bill galti se dobara chadh gaya tha",
       "2000 bricks came from Suresh Traders, their bill from last week got entered twice by mistake",
       CR("Suresh Traders", None), [T(SUP_TXN, "Suresh Traders", None, quantity=2000)],
       why="'pichle hafte' range hai, pakki tareekh nahi"),

    # =====================================================================  D — correction nahi, entry banni chahiye
    tc("COR-D-01", "Sohan ki pichhle mahine ki 1800 dihadi abhi deni hai",
       "Sohan's 1800 wages from last month are still to be paid", NOT_CORR(), [T(OPEN, "Sohan", 1800)]),
    tc("COR-D-02", "Aaj phir Sharma ji 2000 jama karwa gaye",
       "Sharma ji again deposited 2000 today", NOT_CORR(), [T(SALE_PAY, "Sharma ji", 2000)]),
    tc("COR-D-03", "Kitanu kal ka bacha hua plaster aaj nipta gaya, 400 banta hai",
       "Kitanu finished yesterday's leftover plaster today, 400 is due", NOT_CORR(), [T(EMP_TXN, "Kitanu", 400)]),
    tc("COR-D-04", "Purane hisab ke 15000 abhi Suresh Traders ko chukane hain",
       "15000 from the old account still has to be paid to Suresh Traders", NOT_CORR(),
       [T(OPEN, "Suresh Traders", 15000)]),
    tc("COR-D-05", "Ram ko aaj 600 pakdaye, 500 nahi",
       "Handed Ram 600 today, not 500", NOT_CORR(), [T(EMP_TXN, "Ram", 600)]),
    tc("COR-D-06", "Pichle hafte eent laane wale tempo ka 1500 kiraya aaj chukaya",
       "Paid today the 1500 fare of the tempo that brought bricks last week", NOT_CORR(), [T(EXP, None, 1500)]),
    tc("COR-D-07", "Sohan aaj bilkul sahi waqt pe pahuncha aur shaam tak laga raha",
       "Sohan arrived right on time today and stayed till evening", NOT_CORR(), [T(ATT, "Sohan", None)]),
]

CATEGORY_LABELS = {"A": "A - Naam + tareekh", "B": "B - Bina naam / tareekh", "C": "C - Nayi entry + correction",
                   "D": "D - Correction nahi"}

HINDI = {
    "COR-A-01": "राम की कल वाली हाज़री गलत चढ़ गई, वो आया ही नहीं था",
    "COR-A-02": "शर्मा जी से 3 तारीख को जो 5000 आए थे, वो एंट्री गलत है",
    "COR-A-03": "सुरेश ट्रेडर्स का परसों वाला बिल गलती से दो बार लिख दिया",
    "COR-A-04": "कितनू को 2 दिन पहले 800 दिए थे, वो 600 थे, ठीक कर दो",
    "COR-A-05": "5 अक्टूबर को सोहन के नाम पे जो काम चढ़ाया वो कैंसल करो",
    "COR-A-06": "पापा ने कल गल्ले से 2000 लिए थे वाली एंट्री हटा दो",
    "COR-A-07": "एसबीआई भट्टे की 1 तारीख वाली ईंट की एंट्री में रेट गलत लग गया",
    "COR-B-01": "कल वाली डीज़ल की एंट्री में गलती हो गई है",
    "COR-B-02": "पिछली वाली एंट्री में रकम गलत चढ़ गई",
    "COR-B-03": "राम का जो पेमेंट लिखा था उसमें गड़बड़ है, सही करना है",
    "COR-B-04": "आज सुबह जो बिजली का बिल चढ़ाया वो हटा दो",
    "COR-B-05": "गलती से 4000 की जगह 40000 लिख दिया, ठीक करो",
    "COR-B-06": "सुरेश ट्रेडर्स के खाते में से वो एक एंट्री हटवानी है",
    "COR-C-01": "राम को आज 500 दिए, और कल की उसकी हाज़री गलत लगी थी",
    "COR-C-02": "शर्मा जी ने 3000 और भेजे, परसों वाली उनकी एंट्री में गलती है",
    "COR-C-03": "आज चाय के 120 लगे, कल वाला किराया गलत लिखा गया था",
    "COR-C-04": "कितनू ने आज 700 का काम किया, 4 तारीख वाली उसकी एंट्री कैंसल करो",
    "COR-C-05": "सुरेश ट्रेडर्स से 2000 ईंट आई, पिछले हफ्ते का उनका बिल गलती से दोबारा चढ़ गया था",
    "COR-D-01": "सोहन की पिछले महीने की 1800 दिहाड़ी अभी देनी है",
    "COR-D-02": "आज फिर शर्मा जी 2000 जमा करवा गए",
    "COR-D-03": "कितनू कल का बचा हुआ प्लास्टर आज निपटा गया, 400 बनता है",
    "COR-D-04": "पुराने हिसाब के 15000 अभी सुरेश ट्रेडर्स को चुकाने हैं",
    "COR-D-05": "राम को आज 600 पकड़ाए, 500 नहीं",
    "COR-D-06": "पिछले हफ्ते ईंट लाने वाले टेम्पो का 1500 किराया आज चुकाया",
    "COR-D-07": "सोहन आज बिल्कुल सही वक्त पे पहुँचा और शाम तक लगा रहा",
}

ENGLISH_INPUT = {t["id"]: t["english"] for t in TESTCASES}

for _t in TESTCASES:
    _t["hindi"] = HINDI[_t["id"]]
    _t["english_input"] = ENGLISH_INPUT[_t["id"]]
assert set(HINDI) == set(ENGLISH_INPUT) == {t["id"] for t in TESTCASES}
assert len(TESTCASES) == 25
