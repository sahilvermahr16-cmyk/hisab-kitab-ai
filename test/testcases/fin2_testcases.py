# test/testcases/fin2_testcases.py — HOLDOUT v2 (after the 7 fixes found on holdout v1), LOCKED 2026-10-08 16:49.
#
# 135 naye statements, v1 jaisa hi mix: 7 entry bundles × 15 (8 papa ke business jaise, 2 rozana, 2 mushkil,
# 1 adhoora, 1 kai kaam ek saath, 1 entry nahi) + Report / Correction / Router × 10.
# Prompt, dev set aur holdout v1 se alag (difflib ≤ 0.69). Assistant ne likhe, user (Sahil) ne lock kiye.
# Run se pehle user ne 5 statements aasan karwaye (EMP-04, EMP-07, EMP-08, SUP-07, PUR-01) — methodology mein likha hai.
# Ek hi baar chalega, beech mein koi fix nahi. Hinglish only.
#   python test/HK_Testing.py --bundle fin2

BUNDLE = "Holdout v2"
PREFIX = "F2"

E, C, S, F, P, SITE = "Employee", "Customer", "Supplier", "Family Member", "Property / Site Owner", "Site"
EMP_TXN, ATT, MEMP = "record_employee_transaction", "record_attendance", "manage_employee"
SALE, CPAY = "record_sale_transaction", "record_sale_payment"
STX, SPAY = "record_supplier_transaction", "record_supplier_payment"
EXP, EPAY, FAM, OPEN = "record_expense", "record_expense_payment", "record_family_transaction", "record_opening_balance"
MOV, ADJ, WORK = "record_material_movement", "record_adjustment", "record_work_log"
PUR, PPAY = "record_purchase", "record_purchase_payment"

BASE_ROLES = {"ram": E, "sohan": E, "kitanu": E, "naresh": E, "pappu": E,
              "sharma ji": C, "sharma": C, "suresh traders": C, "suresh": C, "dalbir": C, "kuldeep ji": C, "kuldeep": C,
              "satbir": C,
              "sbi bhatta": S, "sbi bhatte": S, "sbi": S, "hanuman bhatta": S, "hanuman bhatte": S, "hanuman": S,
              "garg timber": S, "garg": S,
              "papa": F, "mummy": F, "bhai": F, "beti": F, "chhote": F,
              "dhani": SITE, "kalanaur": SITE,
              "om prakash ji": P, "om prakash": P, "om": P, "billu": P, "mange ram": P, "mange ram ji": P, "mange": P}


def ev(role, tool, **args):
    return dict(role=role, tool=tool, args=args)


def tc(id_, hg, outcome, expected=(), ask=None, why="", **extra):
    d = dict(id=id_, category=id_.split("-")[1], hinglish=hg, english="", outcome=outcome, roles=dict(BASE_ROLES),
             expected=list(expected), ask=ask, why=why)
    d.update(extra)
    return d


def X(category, amount, date="T", paid=True):
    out = [ev(None, EXP, category=category, amount=amount, date=date)]
    return out + ([ev(None, EPAY, amount=amount, date=date)] if paid else [])


def EP(name, amount, date="T", kind="payment"):
    return ev(E, EMP_TXN, employee_name=name, transaction_type=kind, amount=amount, date=date)


def K(member, amount, kind="kharcha", date="T"):
    args = dict(transaction_type=kind, amount=amount, date=date)
    if member:
        args["member_name"] = member
    return ev(F if member else None, FAM, **args)


def RP(kind, person=None, role=None, start=None, end=None, lang=None):
    return dict(route="report", kind=kind, person=person, role=role, start=start, end=end, lang=lang)


def CR(name=None, date=None):
    return dict(route="correction", name=name, date=date)


def T(tool, name=None, amount=None, **kw):
    return dict(tool=tool, name=name, amount=amount, **kw)


TESTCASES = [
    # ============================================================ EMPLOYEE
    tc("F2-EMP-01", "Naresh beldar ki aaj ki 550 mazdoori chuka di", "ENTRY", [EP("Naresh", 550)]),
    tc("F2-EMP-02", "Sohan aaj site pe nahi aaya, beemar hai", "ENTRY",
       [ev(E, ATT, employee_name="Sohan", attendance="absent", date="T")]),
    tc("F2-EMP-03", "Ram ne gudam mein darwaze chhaante, 700 bante hain", "ENTRY", [EP("Ram", 700, kind="work")]),
    tc("F2-EMP-04", "Kitanu aaj kaam pe aaya, tractor bhi usi ne chalaya", "ENTRY",
       [ev(E, ATT, employee_name="Kitanu", attendance="P", driving="P", date="T")]),
    tc("F2-EMP-05", "Pappu ko kal 300 aur aaj 400 diye", "ENTRY", [EP("Pappu", 300, "T-1"), EP("Pappu", 400)]),
    tc("F2-EMP-06", "sohan ko saade teen sau thama diye dopahar mein", "ENTRY", [EP("Sohan", 350)]),
    tc("F2-EMP-07", "Naresh aaj aaya aur 600 le gaya", "ENTRY",
       [ev(E, ATT, employee_name="Naresh", attendance="P", date="T"), EP("Naresh", 600)]),
    tc("F2-EMP-08", "Pappu ko agle hafte 500 denge", "NO-ENTRY"),
    tc("F2-EMP-09", "Naresh ne aaj gudam pe chaukhat saaf ki, 500 banta hai", "ENTRY", [EP("Naresh", 500, kind="work")]),
    tc("F2-EMP-10", "Ram lunch ke baad nikal gaya aaj, aadha din hi raha", "ENTRY",
       [ev(E, ATT, employee_name="Ram", attendance="half", date="T")]),
    tc("F2-EMP-11", "Pappu ko 1000 advance de diye shaadi ke liye", "ENTRY", [EP("Pappu", 1000)]),
    tc("F2-EMP-12", "Kitanu ko aaj 250 kharche ke diye", "ENTRY", [EP("Kitanu", 250)]),
    tc("F2-EMP-13", "Naresh ki aaj chhutti rahi", "ENTRY",
       [ev(E, ATT, employee_name="Naresh", attendance="absent", date="T")]),
    tc("F2-EMP-14", "pappu kal aadha din aaya tha, aaj poora", "ENTRY",
       [ev(E, ATT, employee_name="Pappu", attendance="half", date="T-1"),
        ev(E, ATT, employee_name="Pappu", attendance="P", date="T")]),
    tc("F2-EMP-15", "Naresh ko kuch paise de diye", "ASK",
       [ev(E, EMP_TXN, employee_name="Naresh", transaction_type="payment", date="T")], ask="How much?"),

    # ============================================================ CUSTOMER
    tc("F2-CUS-01", "Dalbir ko 12 purani khidkiyan 6000 mein bechi", "ENTRY",
       [ev(C, SALE, customer_name="Dalbir", item_name="khidki", quantity=12, amount=6000, date="T")]),
    tc("F2-CUS-02", "Kuldeep ji ne 4500 bheje PhonePe se", "ENTRY", [ev(C, CPAY, customer_name="Kuldeep ji", amount=4500, date="T")]),
    tc("F2-CUS-03", "Gudam se 2000 eent Sharma ji ke plot pe gayi, 6 ka rate", "ENTRY",
       [ev(C, SALE, customer_name="Sharma ji", item_name="eent", quantity=2000, rate=6, amount=12000, source="gudam", date="T")]),
    tc("F2-CUS-04", "Dalbir pe pehle ka 3500 nikalta hai", "ENTRY",
       [ev(C, OPEN, party_name="Dalbir", amount=3500, direction="lena")]),
    tc("F2-CUS-05", "Suresh Traders 5 shahteer le gaye 10000 ke, 4000 de gaye", "ENTRY",
       [ev(C, SALE, customer_name="Suresh Traders", item_name="shahteer", quantity=5, amount=10000, date="T"),
        ev(C, CPAY, customer_name="Suresh Traders", amount=4000, date="T")]),
    tc("F2-CUS-06", "kuldeep ji ko dhai hazaar ki ek purani almari di", "ENTRY",
       [ev(C, SALE, customer_name="Kuldeep ji", item_name="almari", quantity=1, amount=2500, date="T")]),
    tc("F2-CUS-07", "Dalbir 300 eent le gaya", "ASK",
       [ev(C, SALE, customer_name="Dalbir", item_name="eent", quantity=300, date="T")], ask="For how much?"),
    tc("F2-CUS-08", "Sharma ji ne bola hai parso tak 5000 pahuncha denge", "NO-ENTRY"),
    tc("F2-CUS-09", "Kuldeep ji ko 20 balli 6000 mein di, gudam se", "ENTRY",
       [ev(C, SALE, customer_name="Kuldeep ji", item_name="balli", quantity=20, amount=6000, source="gudam", date="T")]),
    tc("F2-CUS-10", "Dalbir ne purane 1500 de diye", "ENTRY", [ev(C, CPAY, customer_name="Dalbir", amount=1500, date="T")]),
    tc("F2-CUS-11", "Sharma ji ko 4 girder 16000 ke diye, 10000 aaye", "ENTRY",
       [ev(C, SALE, customer_name="Sharma ji", item_name="girder", quantity=4, amount=16000, date="T"),
        ev(C, CPAY, customer_name="Sharma ji", amount=10000, date="T")]),
    tc("F2-CUS-12", "Kuldeep ji ka 2000 aaya", "ENTRY", [ev(C, CPAY, customer_name="Kuldeep ji", amount=2000, date="T")]),
    tc("F2-CUS-13", "Satbir paanch sau eent le gaya teen hazaar ki", "ENTRY",
       [ev(C, SALE, customer_name="Satbir", item_name="eent", quantity=500, amount=3000, date="T")]),
    tc("F2-CUS-14", "dalbir ko sava sau eent saade paanch ke rate se", "ENTRY",
       [ev(C, SALE, customer_name="Dalbir", item_name="eent", quantity=125, rate=5.5, amount=687.5, date="T")]),
    tc("F2-CUS-15", "Dalbir se 1000 aaye, aur Sharma ji 300 eent 1800 mein le gaye", "ENTRY",
       [ev(C, CPAY, customer_name="Dalbir", amount=1000, date="T"),
        ev(C, SALE, customer_name="Sharma ji", item_name="eent", quantity=300, amount=1800, date="T")]),

    # ============================================================ SUPPLIER
    tc("F2-SUP-01", "Hanuman bhatte se 4000 eent gudam aayi, 6.5 ka rate", "ENTRY",
       [ev(S, STX, supplier_name="Hanuman", item_name="eent", quantity=4000, rate=6.5, amount=26000,
           destination_location="gudam", date="T")]),
    tc("F2-SUP-02", "Garg timber wale ko 12000 cheque diya", "ENTRY", [ev(S, SPAY, supplier_name="Garg timber", amount=12000, date="T")]),
    tc("F2-SUP-03", "SBI se 2500 eent dukaan pe utri 17500 ki, Kitanu laya", "ENTRY",
       [ev(S, STX, supplier_name="SBI Bhatta", item_name="eent", quantity=2500, amount=17500, destination_location="shop",
           driver_name="Kitanu", date="T")]),
    tc("F2-SUP-04", "Garg timber se 40 balli aayi 8000 ki, gudam mein", "ENTRY",
       [ev(S, STX, supplier_name="Garg timber", item_name="balli", quantity=40, amount=8000, destination_location="gudam", date="T")]),
    tc("F2-SUP-05", "Hanuman bhatte ke 20000 purane dene hain", "ENTRY",
       [ev(S, OPEN, party_name="Hanuman", amount=20000, direction="dena")]),
    tc("F2-SUP-06", "hanuman wale ko aath hazaar online kar diye", "ENTRY", [ev(S, SPAY, supplier_name="Hanuman", amount=8000, date="T")]),
    tc("F2-SUP-07", "Garg timber se 25 phatte aaye 5000 ke, poore de diye", "ENTRY",
       [ev(S, STX, supplier_name="Garg timber", item_name="phatta", quantity=25, amount=5000, date="T"),
        ev(S, SPAY, supplier_name="Garg timber", amount=5000, date="T")]),
    tc("F2-SUP-08", "SBI wale bol rahe the rate badhega agle hafte", "NO-ENTRY"),
    tc("F2-SUP-09", "SBI se 3000 eent shop pe aayi 21000 ki", "ENTRY",
       [ev(S, STX, supplier_name="SBI Bhatta", item_name="eent", quantity=3000, amount=21000, destination_location="shop", date="T")]),
    tc("F2-SUP-10", "Garg timber ka 6000 ka hisab chuka diya", "ENTRY", [ev(S, SPAY, supplier_name="Garg timber", amount=6000, date="T")]),
    tc("F2-SUP-11", "Hanuman bhatte se 2 trolley rodi gudam aayi 9000 ki", "ENTRY",
       [ev(S, STX, supplier_name="Hanuman", item_name="rodi", quantity=2, unit="trolley", amount=9000,
           destination_location="gudam", date="T")]),
    tc("F2-SUP-12", "Hanuman bhatte wale ka 5000 online kar diya", "ENTRY", [ev(S, SPAY, supplier_name="Hanuman", amount=5000, date="T")]),
    tc("F2-SUP-13", "SBI wale ko 15000 ka cheque diya", "ENTRY", [ev(S, SPAY, supplier_name="SBI Bhatta", amount=15000, date="T")]),
    tc("F2-SUP-14", "garg wale se dedh sau phatte aaye, sau rupaye ka ek, dukaan pe", "ENTRY",
       [ev(S, STX, supplier_name="Garg timber", item_name="phatta", quantity=150, rate=100, amount=15000,
           destination_location="shop", date="T")]),
    tc("F2-SUP-15", "Hanuman wale ki gaadi aayi thi eent lekar", "ASK",
       [ev(S, STX, supplier_name="Hanuman", item_name="eent", date="T")], ask="How many / how much?"),

    # ============================================================ EXPENSE
    tc("F2-EXP-01", "Dumper chalane ko 3000 ka tel daalwa diya pump pe", "ENTRY", X("fuel", 3000)),
    tc("F2-EXP-02", "Gudam ki tubelight aur wire 450 ki aayi", "ENTRY", X("misc", 450)),
    tc("F2-EXP-03", "Hydra 2 ghante lagi Dhani wali site pe, 2400 diye", "ENTRY", X("rent", 2400)),
    tc("F2-EXP-04", "Gudam ka kiraya 7000 de diya is mahine ka", "ENTRY", X("rent", 7000)),
    tc("F2-EXP-05", "Trolley ki welding karwayi 600 mein", "ENTRY", X("repair", 600)),
    tc("F2-EXP-06", "chai paani mein aaj dedh sau gaye", "ENTRY", X("misc", 150)),
    tc("F2-EXP-07", "Generator theek karwaya", "ASK", ask="How much?"),
    tc("F2-EXP-08", "Agle hafte malba uthwane ko hydra mangwani padegi", "NO-ENTRY"),
    tc("F2-EXP-09", "Tractor ka filter badalwaya 800 ka", "ENTRY", X("repair", 800)),
    tc("F2-EXP-10", "Bijli daftar mein dukaan ka 1900 bhara", "ENTRY", X("misc", 1900)),
    tc("F2-EXP-11", "JCB ka 3 ghante ka 2700 diya Kalanaur site pe", "ENTRY", X("rent", 2700)),
    tc("F2-EXP-12", "Petrol 300 ka", "ENTRY", X("fuel", 300)),
    tc("F2-EXP-13", "Chai 120 ki", "ENTRY", X("misc", 120)),
    tc("F2-EXP-14", "gudam ke taale ki chaabi banwayi, pachaas lage", "ENTRY", X("misc", 50)),
    tc("F2-EXP-15", "Diesel 1500 ka aur tyre puncture 200 ka", "ENTRY", X("fuel", 1500) + X("repair", 200)),

    # ============================================================ FAMILY
    tc("F2-FAM-01", "Mummy ko doodh wale ke 900 diye", "ENTRY", [K("Mummy", 900)]),
    tc("F2-FAM-02", "Bhai galle se 2500 le gaya bike ki kisht ke liye", "ENTRY", [K("Bhai", 2500)]),
    tc("F2-FAM-03", "Galle mein Papa 10 hazaar rakh gaye", "ENTRY", [K("Papa", 10000, "jama")]),
    tc("F2-FAM-04", "Beti ki school fees 6500 bhar di", "ENTRY", [K("Beti", 6500)]),
    tc("F2-FAM-05", "Ghar ki gas khatam thi, nayi tanki 1050 mein bharwayi", "ENTRY", [K(None, 1050)]),
    tc("F2-FAM-06", "chhote ko kitabon ke liye paanch sau pakda diye", "ENTRY", [K("Chhote", 500)]),
    tc("F2-FAM-07", "Papa 2000 le gaye aur Mummy ne 500 wapas rakhe", "ENTRY", [K("Papa", 2000), K("Mummy", 500, "jama")]),
    tc("F2-FAM-08", "Diwali pe ghar ki safai karwani hai, 3000 lagenge", "NO-ENTRY"),
    tc("F2-FAM-09", "Mummy 1000 le gayi galle se", "ENTRY", [K("Mummy", 1000)]),
    tc("F2-FAM-10", "Papa ko 5000 diye mandi ke liye", "ENTRY", [K("Papa", 5000)]),
    tc("F2-FAM-11", "Bhai apni jeb se 2000 laya, galle mein daal gaya", "ENTRY", [K("Bhai", 2000, "jama")]),
    tc("F2-FAM-12", "Beti ko jeb kharch ke 200 diye", "ENTRY", [K("Beti", 200)]),
    tc("F2-FAM-13", "Mahine bhar ka ghar ka saman 2500 mein aaya", "ENTRY", [K(None, 2500)]),
    tc("F2-FAM-14", "mummy ne galle se teen hazaar nikale dawai ke", "ENTRY", [K("Mummy", 3000)]),
    tc("F2-FAM-15", "Bhai ne galle se pata nahi kitne nikale", "ASK", ask="How much?"),

    # ============================================================ STOCK
    tc("F2-STK-01", "Dhani site se 60 balli gudam aayi", "ENTRY",
       [ev(None, MOV, item_name="balli", quantity=60, source_name="dhani", destination_name="gudam", date="T")]),
    tc("F2-STK-02", "Gudam se dukaan 30 chaukhat bheji", "ENTRY",
       [ev(None, MOV, item_name="chaukhat", quantity=30, source_name="gudam", destination_name="shop", date="T")]),
    tc("F2-STK-03", "Kalanaur site pe 5 labour lage, chhat utaari", "ENTRY",
       [ev(None, WORK, location_type="site", location_name="kalanaur", labour_count=5, date="T")]),
    tc("F2-STK-04", "Dukaan pe 8 khidkiyan toot gayi", "ENTRY",
       [ev(None, ADJ, location="shop", item_name="khidki", quantity_change=-8, date="T")]),
    tc("F2-STK-05", "Ginti karwayi to dukaan pe 12 darwaze kam pade", "ENTRY",
       [ev(None, ADJ, location="shop", item_name="darwaza", quantity_change=-12, date="T")]),
    tc("F2-STK-06", "dhani wali site se dedh sau eent gudm aayi", "ENTRY",
       [ev(None, MOV, item_name="eent", quantity=150, source_name="dhani", destination_name="gudam", date="T")]),
    tc("F2-STK-07", "Gudam se 200 eent Kalanaur site gayi aur wahan 4 labour lage", "ENTRY",
       [ev(None, MOV, item_name="eent", quantity=200, source_name="gudam", destination_name="kalanaur", date="T"),
        ev(None, WORK, location_type="site", location_name="kalanaur", labour_count=4, date="T")]),
    tc("F2-STK-08", "Parso tak dukaan ke liye kuch maal nikalna padega", "NO-ENTRY"),
    tc("F2-STK-09", "Malba 4 trolley Kalanaur site se gudam pe utra", "ENTRY",
       [ev(None, MOV, item_name="malba", quantity=4, source_name="kalanaur", destination_name="gudam", date="T")]),
    tc("F2-STK-10", "Dukaan se 50 khidkiyan gudam bheji", "ENTRY",
       [ev(None, MOV, item_name="khidki", quantity=50, source_name="shop", destination_name="gudam", date="T")]),
    tc("F2-STK-11", "Dhani wali site pe teen aadmi lagaye, chhat ka lintel toda", "ENTRY",
       [ev(None, WORK, location_type="site", location_name="dhani", labour_count=3, date="T")]),
    tc("F2-STK-12", "Dukaan ke liye gudam se 100 eent nikaali", "ENTRY",
       [ev(None, MOV, item_name="eent", quantity=100, source_name="gudam", destination_name="shop", date="T")]),
    tc("F2-STK-13", "Gudam pe 6 chaukhat bekaar nikli", "ENTRY",
       [ev(None, ADJ, location="gudam", item_name="chaukhat", quantity_change=-6, date="T")]),
    tc("F2-STK-14", "dukan ka stock dekha, das darwaze faltu mile", "ENTRY",
       [ev(None, ADJ, location="shop", item_name="darwaza", quantity_change=10, date="T")]),
    tc("F2-STK-15", "Site se balli aa gayi gudam", "ASK", ask="Which site / how many?"),

    # ============================================================ PURCHASE
    tc("F2-PUR-01", "Om Prakash ji se purani haveli 5 lakh mein khareedi", "ENTRY",
       [ev(P, PUR, seller_name="Om Prakash ji", total_amount=500000, date="T")]),
    tc("F2-PUR-02", "Om Prakash ji ko 1 lakh bayana de diya", "ENTRY",
       [ev(P, PPAY, seller_name="Om Prakash ji", amount=100000, date="T")]),
    tc("F2-PUR-03", "Nayi welding machine 22000 ki li", "ENTRY", [ev(None, PUR, seller_name=None, total_amount=22000, date="T")]),
    tc("F2-PUR-04", "Billu se purana dumper 3 lakh mein liya", "ENTRY",
       [ev(P, PUR, seller_name="Billu", total_amount=300000, date="T")]),
    tc("F2-PUR-05", "Om Prakash ji ko haveli ke 2 lakh aur diye", "ENTRY",
       [ev(P, PPAY, seller_name="Om Prakash ji", amount=200000, date="T")]),
    tc("F2-PUR-06", "billu ko dumper ke dedh lakh pakda diye", "ENTRY",
       [ev(P, PPAY, seller_name="Billu", amount=150000, date="T")]),
    tc("F2-PUR-07", "Ek kothi ka sauda pakka ho gaya", "ASK", ask="How much / with whom?"),
    tc("F2-PUR-08", "Om Prakash ji wali haveli ke baare mein soch rahe hain", "NO-ENTRY"),
    tc("F2-PUR-09", "Om Prakash ji ka bacha hua 2 lakh de ke haveli ka hisab khatam", "ENTRY",
       [ev(P, PPAY, seller_name="Om Prakash ji", amount=200000, date="T")]),
    tc("F2-PUR-10", "Mange Ram se Dhani wala makaan todne ko dhai lakh mein le liya", "ENTRY",
       [ev(P, PUR, seller_name="Mange Ram", total_amount=250000, date="T")]),
    tc("F2-PUR-11", "Mange Ram ko makaan ke 50000 diye", "ENTRY", [ev(P, PPAY, seller_name="Mange Ram", amount=50000, date="T")]),
    tc("F2-PUR-12", "Naya tractor 6 lakh ka liya", "ENTRY", [ev(None, PUR, seller_name=None, total_amount=600000, date="T")]),
    tc("F2-PUR-13", "Mange Ram ji ko makaan ke 20000 aur bheje", "ENTRY",
       [ev(P, PPAY, seller_name="Mange Ram", amount=20000, date="T")]),
    tc("F2-PUR-14", "mange ram ji wale makaan ke dhai lakh mein se aadhe de diye", "ENTRY",
       [ev(P, PPAY, seller_name="Mange Ram", amount=125000, date="T")]),
    tc("F2-PUR-15", "Om Prakash ji ko 1 lakh diye aur Billu ko 50000", "ENTRY",
       [ev(P, PPAY, seller_name="Om Prakash ji", amount=100000, date="T"),
        ev(P, PPAY, seller_name="Billu", amount=50000, date="T")]),

    # ============================================================ REPORT
    tc("F2-RPT-01", "Sohan ki is mahine ki dihadi aur payment ki report bhejo", "REPORT", report=RP("person", "Sohan", None, "M0", "T")),
    tc("F2-RPT-02", "Sharma ji ke khate mein abhi kitna udhaar bacha hai", "REPORT", report=RP("person", "Sharma ji")),
    tc("F2-RPT-03", "Pichle paanch dino mein kharche kahan kahan hue, report do", "REPORT",
       report=RP("expense", None, None, "T-4", "T")),
    tc("F2-RPT-04", "Papa ne aaj galle se kitne nikale, dikhao", "REPORT", report=RP("person", "Papa", None, "T", "T")),
    tc("F2-RPT-05", "SBI wala hisab poora kar diya, 8000 bhej ke", "ENTRY", report=dict(route="accounting")),
    tc("F2-RPT-06", "Parso gudam se kya kya gaya, dikhao", "REPORT", report=RP("material_movement", None, None, "T-2", "T-2")),
    tc("F2-RPT-07", "Kitanu ka 1 tareekh se aaj tak ka hisab", "REPORT", report=RP("person", "Kitanu", None, "10-01", "T")),
    tc("F2-RPT-08", "Suresh Traders ki saari entry nikal do", "REPORT", report=RP("person", "Suresh Traders")),
    tc("F2-RPT-09", "Is mahine poore dhande ka hisab kitab batao", "REPORT", report=RP("overall", None, None, "M0", "T")),
    tc("F2-RPT-10", "Kitanu ka aaj tak ka len-den barabar kar diya, 500 de ke", "ENTRY", report=dict(route="accounting")),

    # ============================================================ CORRECTION
    tc("F2-COR-01", "Kal Sohan ki mazdoori do baar chadh gayi", "CORRECTION", correction=CR("Sohan", "T-1"), expected_c=[]),
    tc("F2-COR-02", "Suresh Traders ki 4 tareekh wali bikri galat likhi", "CORRECTION",
       correction=CR("Suresh Traders", "10-04"), expected_c=[]),
    tc("F2-COR-03", "Koi kharche ki entry do baar ho gayi hai", "CORRECTION", correction=CR(None, None), expected_c=[]),
    tc("F2-COR-04", "Kitanu ko aaj 300 pakdaye, aur kal ki uski absent wali entry hata do", "CORRECTION",
       correction=CR("Kitanu", "T-1"), expected_c=[T(EMP_TXN, "Kitanu", 300)]),
    tc("F2-COR-05", "Satbir ne atke hue 2000 bhi aaj chuka diye", "ENTRY",
       correction=dict(route="accounting"), expected_c=[T(CPAY, "Satbir", 2000)]),
    tc("F2-COR-06", "Kitanu ka purana 1200 udhaar aaj utaar diya", "ENTRY",
       correction=dict(route="accounting"), expected_c=[T(EMP_TXN, "Kitanu", 1200)]),
    tc("F2-COR-07", "Parso ka diesel wala kharcha galat chadh gaya", "CORRECTION", correction=CR(None, "T-2"), expected_c=[]),
    tc("F2-COR-08", "Sharma ji ki kal wali payment galti se chadh gayi", "CORRECTION", correction=CR("Sharma ji", "T-1"), expected_c=[]),
    tc("F2-COR-09", "Sohan ko aaj 500 diye, 3 tareekh wala uska kaam galat hai", "CORRECTION",
       correction=CR("Sohan", "10-03"), expected_c=[T(EMP_TXN, "Sohan", 500)]),
    tc("F2-COR-10", "Ram ne aaj gudam mein 600 ki dihadi lagayi", "ENTRY",
       correction=dict(route="accounting"), expected_c=[T(EMP_TXN, "Ram", 600)]),

    # ============================================================ ROUTER (route-only)
    tc("F2-RTR-01", "Aaj bahut thand hai yaar", "general_chat", route="general_chat", route_only=True),
    tc("F2-RTR-02", "Tum mera hisab kitab rakhoge na?", "general_chat", route="general_chat", route_only=True),
    tc("F2-RTR-03", "Sohan ki maa ab theek hain kya?", "general_chat", route="general_chat", route_only=True),
    tc("F2-RTR-04", "Kitanu aaj der se aaya, 10 baje", "accounting", route="accounting", route_only=True),
    tc("F2-RTR-05", "SBI waalon ka kitna lena-dena baaki chal raha hai, batao", "report", route="report", route_only=True),
    tc("F2-RTR-06", "Sharma ji ka beta 1500 de kar gaya abhi", "accounting", route="accounting", route_only=True),
    tc("F2-RTR-07", "Bhiwani se Rohtak kitni door hai?", "general_chat", route="general_chat", route_only=True),
    tc("F2-RTR-08", "Sharma ji ke ghar shaadi hai agle hafte", "general_chat", route="general_chat", route_only=True),
    tc("F2-RTR-09", "Naresh aaj time se pahle aa gaya", "accounting", route="accounting", route_only=True),
    tc("F2-RTR-10", "Garg timber ka hisab dikhao", "report", route="report", route_only=True),
]

CATEGORY_LABELS = {"EMP": "Employee", "CUS": "Customer", "SUP": "Supplier", "EXP": "Expense", "FAM": "Family",
                   "STK": "Stock", "PUR": "Purchase", "RPT": "Report", "COR": "Correction", "RTR": "Router"}

for _t in TESTCASES:
    _t["hindi"] = ""
    _t["english_input"] = ""
assert len(TESTCASES) == 135 and len({t["id"] for t in TESTCASES}) == 135
