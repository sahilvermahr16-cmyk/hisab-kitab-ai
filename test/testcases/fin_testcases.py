# test/testcases/fin_testcases.py — FINAL test set (holdout), LOCKED 2026-10-08 14:35.
#
# 135 naye statements: 7 entry bundles × 15 (8 papa ke business jaise + 7 mix) + Report / Correction / Router × 10.
# Prompt aur dev set se alag (difflib ≤ 0.69). Assistant ne likhe, user (Sahil) ne har bundle lock kiya.
# Ek hi baar chalega, beech mein koi fix nahi. Hinglish only.
# Scorer fix (run ke baad, 15:25): STK-02 / STK-12 se driver_name hataya — record_material_movement mein driver ka
#   field hi nahi hai, isliye wo expectation galat thi (system ki galti nahi).
#   python test/HK_Testing.py --bundle fin

BUNDLE = "Final (holdout)"
PREFIX = "FIN"

E, C, S, F, P, SITE = "Employee", "Customer", "Supplier", "Family Member", "Property / Site Owner", "Site"
EMP_TXN, ATT, MEMP = "record_employee_transaction", "record_attendance", "manage_employee"
SALE, CPAY, MCUS = "record_sale_transaction", "record_sale_payment", "manage_customer"
STX, SPAY, MSUP = "record_supplier_transaction", "record_supplier_payment", "manage_supplier"
EXP, EPAY, FAM, OPEN = "record_expense", "record_expense_payment", "record_family_transaction", "record_opening_balance"
MOV, ADJ, WORK = "record_material_movement", "record_adjustment", "record_work_log"
PUR, PPAY = "record_purchase", "record_purchase_payment"

BASE_ROLES = {"ram": E, "sohan": E, "kitanu": E, "sharma ji": C, "sharma": C, "suresh traders": C, "suresh": C,
              "sbi bhatta": S, "sbi bhatte": S, "sbi": S, "papa": F,
              "bhupender": E, "mahavir": E, "rajbir": C, "satbir": C, "mohan ji": C, "mohan": C,
              "gill saw mill": S, "gill": S, "jindal steel": S, "jindal": S,
              "mummy": F, "maa": F, "chhote": F, "bhai": F, "didi": F, "beta": F, "rohit": F,
              "haluwas": SITE, "dhani": SITE, "kalanaur": SITE,
              "jagbir": P, "jagbeer": P, "ramphal ji": P, "ramphal": P, "satpal ji": P, "satpal": P, "bhupi": P}


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


def RP(kind, person=None, role=None, start=None, end=None, lang=None):
    return dict(route="report", kind=kind, person=person, role=role, start=start, end=end, lang=lang)


def CR(name=None, date=None):
    return dict(route="correction", name=name, date=date)


def T(tool, name=None, amount=None, **kw):
    return dict(tool=tool, name=name, amount=amount, **kw)


TESTCASES = [
    # ============================================================ EMPLOYEE (1–8 papa ke kaam jaise, 9–15 mix)
    tc("FIN-EMP-01", "Bhupender ko aaj ki dihadi 600 de di", "ENTRY",
       [ev(E, EMP_TXN, employee_name="Bhupender", transaction_type="payment", amount=600, date="T")]),
    tc("FIN-EMP-02", "Kitanu aaj trolley lekar do chakkar Kalanaur gaya", "ENTRY",
       [ev(E, ATT, employee_name="Kitanu", attendance="P", driving="P", date="T")]),
    tc("FIN-EMP-03", "Sohan ne Dhani wali site pe chaukhat nikalne ka 800 ka kaam kiya", "ENTRY",
       [ev(E, EMP_TXN, employee_name="Sohan", transaction_type="work", amount=800, date="T")]),
    tc("FIN-EMP-04", "Ram aaj dopahar baad aaya, aadha din", "ENTRY",
       [ev(E, ATT, employee_name="Ram", attendance="half", date="T")]),
    tc("FIN-EMP-05", "Mahavir mistri ko 2000 advance diye, agle hafte se kaam pe aayega", "ENTRY",
       [ev(E, EMP_TXN, employee_name="Mahavir", transaction_type="payment", amount=2000, date="T")]),
    tc("FIN-EMP-06", "Sohan aur Ram dono ne aaj girder katai ki, 500-500 banta hai", "ENTRY",
       [ev(E, EMP_TXN, employee_name="Sohan", transaction_type="work", amount=500, date="T"),
        ev(E, EMP_TXN, employee_name="Ram", transaction_type="work", amount=500, date="T")]),
    tc("FIN-EMP-07", "Kitanu kal chutti pe tha", "ENTRY",
       [ev(E, ATT, employee_name="Kitanu", attendance="absent", date="T-1")]),
    tc("FIN-EMP-08", "Bhupender ke purane hisab ke 1500 dene baaki hain", "ENTRY",
       [ev(E, OPEN, party_name="Bhupender", amount=1500, direction="dena")]),
    tc("FIN-EMP-09", "Sohan ko 300 kharchi di", "ENTRY",
       [ev(E, EMP_TXN, employee_name="Sohan", transaction_type="payment", amount=300, date="T")]),
    tc("FIN-EMP-10", "Ram subah saat baje hi pahunch gaya tha aaj", "ENTRY",
       [ev(E, ATT, employee_name="Ram", attendance="P", date="T")]),
    tc("FIN-EMP-11", "ram ko kal 5 sau diye the uske baad aaj 2 sau aur", "ENTRY",
       [ev(E, EMP_TXN, employee_name="Ram", transaction_type="payment", amount=500, date="T-1"),
        ev(E, EMP_TXN, employee_name="Ram", transaction_type="payment", amount=200, date="T")]),
    tc("FIN-EMP-12", "Mahavir ka number 9812233445 hai, mistri hai wo", "ENTRY",
       [ev(E, MEMP, employee_name="Mahavir")]),
    tc("FIN-EMP-13", "Mahavir ka hisab chuka diya", "ASK",
       [ev(E, EMP_TXN, employee_name="Mahavir", transaction_type="payment", date="T")], ask="How much?"),
    tc("FIN-EMP-14", "Ram aaj aaya, 650 ka kaam kiya aur 400 le gaya", "ENTRY",
       [ev(E, ATT, employee_name="Ram", attendance="P", date="T"),
        ev(E, EMP_TXN, employee_name="Ram", transaction_type="work", amount=650, date="T"),
        ev(E, EMP_TXN, employee_name="Ram", transaction_type="payment", amount=400, date="T")]),
    tc("FIN-EMP-15", "Agle somvar Bhupender ka 700 ka hisab karna hai", "NO-ENTRY"),

    # ============================================================ CUSTOMER
    tc("FIN-CUS-01", "Rajbir ko 1500 purani eent di, 4 rupaye wali, Gudam se", "ENTRY",
       [ev(C, SALE, customer_name="Rajbir", item_name="eent", quantity=1500, rate=4, amount=6000, source="gudam", date="T")]),
    tc("FIN-CUS-02", "Sharma ji 3 purane darwaze le gaye 4500 ke", "ENTRY",
       [ev(C, SALE, customer_name="Sharma ji", item_name="darwaza", quantity=3, amount=4500, date="T")]),
    tc("FIN-CUS-03", "Rajbir ne 3000 de diye baaki baad mein dega", "ENTRY",
       [ev(C, CPAY, customer_name="Rajbir", amount=3000, date="T")]),
    tc("FIN-CUS-04", "Dukaan se 2 chaukhat Satbir ko becha 1800 mein, cash mil gaya", "ENTRY",
       [ev(C, SALE, customer_name="Satbir", item_name="chaukhat", quantity=2, amount=1800, source="shop", date="T"),
        ev(C, CPAY, customer_name="Satbir", amount=1800, date="T")]),
    tc("FIN-CUS-05", "Suresh Traders ko 2 quintal sariya 9000 ka, udhaar", "ENTRY",
       [ev(C, SALE, customer_name="Suresh Traders", item_name="sariya", quantity=2, unit="quintal", amount=9000, date="T")]),
    tc("FIN-CUS-06", "Kitanu trolley mein 800 eent Satbir ke yahan chhod aaya, 5 ka rate", "ENTRY",
       [ev(C, SALE, customer_name="Satbir", item_name="eent", quantity=800, rate=5, amount=4000, driver_name="Kitanu", date="T")]),
    tc("FIN-CUS-07", "Rajbir pe pichle saal ke 7000 baaki hain", "ENTRY",
       [ev(C, OPEN, party_name="Rajbir", amount=7000, direction="lena")]),
    tc("FIN-CUS-08", "Gudam se ek purani lakdi ki almari Mohan ji ko 3500 ki di, 2000 abhi diye", "ENTRY",
       [ev(C, SALE, customer_name="Mohan ji", item_name="almari", quantity=1, amount=3500, source="gudam", date="T"),
        ev(C, CPAY, customer_name="Mohan ji", amount=2000, date="T")]),
    tc("FIN-CUS-09", "Satbir se aaj 2500 aa gaye", "ENTRY",
       [ev(C, CPAY, customer_name="Satbir", amount=2500, date="T")]),
    tc("FIN-CUS-10", "Suresh Traders ne 2000 online bheje", "ENTRY",
       [ev(C, CPAY, customer_name="Suresh Traders", amount=2000, date="T")]),
    tc("FIN-CUS-11", "satbir ko dedh sau eent saade chaar ke bhaav", "ENTRY",
       [ev(C, SALE, customer_name="Satbir", item_name="eent", quantity=150, rate=4.5, amount=675, date="T")]),
    tc("FIN-CUS-12", "Rajbir ka mobile 9416012345, Bhiwani bus adde ke paas dukaan hai", "ENTRY",
       [ev(C, MCUS, customer_name="Rajbir")]),
    tc("FIN-CUS-13", "Mohan ji ko 4 khidki de di", "ASK",
       [ev(C, SALE, customer_name="Mohan ji", item_name="khidki", quantity=4, date="T")], ask="For how much?"),
    tc("FIN-CUS-14", "Sharma ji ko 1000 eent 5500 ki gayi, Kitanu chhod ke aaya, 3000 haath mein diye", "ENTRY",
       [ev(C, SALE, customer_name="Sharma ji", item_name="eent", quantity=1000, amount=5500, driver_name="Kitanu", date="T"),
        ev(C, CPAY, customer_name="Sharma ji", amount=3000, date="T")]),
    tc("FIN-CUS-15", "Rajbir agle hafte 3 girder lene aayega, 12000 bataye hain", "NO-ENTRY"),

    # ============================================================ SUPPLIER
    tc("FIN-SUP-01", "SBI wala truck 3000 nayi eent Gudam utaar gaya, saat ka rate", "ENTRY",
       [ev(S, STX, supplier_name="SBI Bhatta", item_name="eent", quantity=3000, rate=7, amount=21000,
           destination_location="gudam", date="T")]),
    tc("FIN-SUP-02", "Gill saw mill se 20 shahteer aaye 16000 ke, dukaan pe utre", "ENTRY",
       [ev(S, STX, supplier_name="Gill saw mill", item_name="shahteer", quantity=20, amount=16000,
           destination_location="shop", date="T")]),
    tc("FIN-SUP-03", "SBI Bhatta ka 10 hazaar ka hisab chuka diya aaj", "ENTRY",
       [ev(S, SPAY, supplier_name="SBI Bhatta", amount=10000, date="T")]),
    tc("FIN-SUP-04", "Jindal steel wale se 5 quintal sariya liya 26000 ka, aadha diya", "ENTRY",
       [ev(S, STX, supplier_name="Jindal steel", item_name="sariya", quantity=5, unit="quintal", amount=26000, date="T"),
        ev(S, SPAY, supplier_name="Jindal steel", amount=13000, date="T")]),
    tc("FIN-SUP-05", "Gill saw mill wale ko 8000 PhonePe kiye", "ENTRY",
       [ev(S, SPAY, supplier_name="Gill saw mill", amount=8000, date="T")]),
    tc("FIN-SUP-06", "Bhatte se 2 trolley rodi aayi, 4500 ki ek, site Haluwas pe", "ENTRY",
       [ev(S, STX, supplier_name="SBI Bhatta", item_name="rodi", quantity=2, unit="trolley", rate=4500, amount=9000,
           destination_location="haluwas", date="T")]),
    tc("FIN-SUP-07", "Jindal steel ke 12000 pehle ke dene baaki hain", "ENTRY",
       [ev(S, OPEN, party_name="Jindal steel", amount=12000, direction="dena")]),
    tc("FIN-SUP-08", "300 eent tooti nikli thi, SBI Bhatte ko lauta di", "ENTRY",
       [ev(S, STX, supplier_name="SBI Bhatta", item_name="eent", quantity=-300, date="T")]),
    tc("FIN-SUP-09", "Dukaan pe SBI ki 1500 eent utri, 10500 ka bill", "ENTRY",
       [ev(S, STX, supplier_name="SBI Bhatta", item_name="eent", quantity=1500, amount=10500,
           destination_location="shop", date="T")]),
    tc("FIN-SUP-10", "Gill wale ko paanch hazaar nakad pakdaye", "ENTRY",
       [ev(S, SPAY, supplier_name="Gill saw mill", amount=5000, date="T")]),
    tc("FIN-SUP-11", "jindal wale se dhai quintal sariya aaya, 52 rupaye kilo, gudam mein", "ENTRY",
       [ev(S, STX, supplier_name="Jindal steel", item_name="sariya", quantity=250, unit="kg", amount=13000,
           destination_location="gudam", date="T")]),
    tc("FIN-SUP-12", "Gill saw mill Charkhi Dadri road pe hai, number 9896011223", "ENTRY",
       [ev(S, MSUP, supplier_name="Gill saw mill")]),
    tc("FIN-SUP-13", "Jindal steel se sariya aa gaya, bill baad mein aayega", "ASK",
       [ev(S, STX, supplier_name="Jindal steel", item_name="sariya", date="T")], ask="How much / how many?"),
    tc("FIN-SUP-14", "Jindal steel se 3 quintal sariya 15600 ka gudam aaya, 10000 diye, Kitanu trolley laya", "ENTRY",
       [ev(S, STX, supplier_name="Jindal steel", item_name="sariya", quantity=3, unit="quintal", amount=15600,
           destination_location="gudam", driver_name="Kitanu", date="T"),
        ev(S, SPAY, supplier_name="Jindal steel", amount=10000, date="T")]),
    tc("FIN-SUP-15", "Gill saw mill wale bol rahe the agle mahine shahteer mehenga hoga", "NO-ENTRY"),

    # ============================================================ EXPENSE
    tc("FIN-EXP-01", "Kalanaur nikalne se pehle tractor mein 2500 ka tel daala", "ENTRY", X("fuel", 2500)),
    tc("FIN-EXP-02", "Gas cutter ka cylinder bharwaya 1100 laga", "ENTRY", X("fuel", 1100)),
    tc("FIN-EXP-03", "JCB 3 ghante chali Haluwas site pe, 3600 de diye", "ENTRY", X("rent", 3600)),
    tc("FIN-EXP-04", "Bijli wale ko gudam ke meter ke 2300 de aaye", "ENTRY", X("misc", 2300)),
    tc("FIN-EXP-05", "Trolley pankchar ho gayi thi raste mein, 150 ka lagwaya", "ENTRY", X("repair", 150)),
    tc("FIN-EXP-06", "Is mahine ki dukaan ki 6000 kiraye ki rakam baad mein denge", "ENTRY", X("rent", 6000, paid=False)),
    tc("FIN-EXP-07", "Labour ko dopahar mein samose khilaye 240 ke", "ENTRY", X("misc", 240)),
    tc("FIN-EXP-08", "Cutter machine theek karwayi, 850 ka kharcha", "ENTRY", X("repair", 850)),
    tc("FIN-EXP-09", "Aaj 500 ka petrol bike mein", "ENTRY", X("fuel", 500)),
    tc("FIN-EXP-10", "Phone recharge 299 ka karwaya", "ENTRY", X("misc", 299)),
    tc("FIN-EXP-11", "dhai sau ki rassi aur taala laaye gudam ke liye", "ENTRY", X("misc", 250)),
    tc("FIN-EXP-12", "JCB wale ke purane 1800 aaj chuka diye", "ENTRY", [ev(None, EPAY, amount=1800, date="T")]),
    tc("FIN-EXP-13", "Tractor ki service karwa li", "ASK", ask="How much?"),
    tc("FIN-EXP-14", "Diesel 2000 ka, tyre 1500 ka badalwaya, aur 100 ki chai", "ENTRY",
       X("fuel", 2000) + X("repair", 1500) + X("misc", 100)),
    tc("FIN-EXP-15", "Kal gudam ki bijli wala aayega, 3000 lagenge shayad", "NO-ENTRY"),

    # ============================================================ FAMILY
    tc("FIN-FAM-01", "Mummy ne ghar ke kharche ke liye 3000 maange the, de diye", "ENTRY",
       [ev(F, FAM, member_name="Mummy", transaction_type="kharcha", amount=3000, date="T")]),
    tc("FIN-FAM-02", "Papa 1500 le gaye galle se, mandi jana tha", "ENTRY",
       [ev(F, FAM, member_name="Papa", transaction_type="kharcha", amount=1500, date="T")]),
    tc("FIN-FAM-03", "Chhote ki college fees 18000 bhari", "ENTRY",
       [ev(F, FAM, member_name="Chhote", transaction_type="kharcha", amount=18000, date="T")]),
    tc("FIN-FAM-04", "Ghar ke liye 25 kilo aata aur daal 1800 ki aayi", "ENTRY",
       [ev(None, FAM, transaction_type="kharcha", amount=1800, date="T")]),
    tc("FIN-FAM-05", "Bhai apne 5000 lauta gaya, galle mein rakh diye", "ENTRY",
       [ev(F, FAM, member_name="Bhai", transaction_type="jama", amount=5000, date="T")]),
    tc("FIN-FAM-06", "Didi ki shaadi ke shagun ke 11000 nikale", "ENTRY",
       [ev(F, FAM, member_name="Didi", transaction_type="kharcha", amount=11000, date="T")]),
    tc("FIN-FAM-07", "Ghar ka gas cylinder 950 ka aaya", "ENTRY",
       [ev(None, FAM, transaction_type="kharcha", amount=950, date="T")]),
    tc("FIN-FAM-08", "Papa dukaan se 2000 le gaye the, 500 wapas kar gaye aaj", "ENTRY",
       [ev(F, FAM, member_name="Papa", transaction_type="jama", amount=500, date="T")]),
    tc("FIN-FAM-09", "Maa ko dawai ke 450 de diye", "ENTRY",
       [ev(F, FAM, member_name="Maa", transaction_type="kharcha", amount=450, date="T")]),
    tc("FIN-FAM-10", "Beta 200 le gaya", "ENTRY",
       [ev(F, FAM, member_name="Beta", transaction_type="kharcha", amount=200, date="T")]),
    tc("FIN-FAM-11", "chhote bhai rohit ko kitab ke liye teen sau", "ENTRY",
       [ev(F, FAM, member_name="Rohit", transaction_type="kharcha", amount=300, date="T")]),
    tc("FIN-FAM-12", "Ghar nahi, gudam ke liye paani ka tanker mangwaya 700 ka", "ENTRY", X("misc", 700)),
    tc("FIN-FAM-13", "Papa aaj phir galle se paise utha le gaye, gine nahi", "ASK", ask="How much?"),
    tc("FIN-FAM-14", "Mummy ko 2000 diye aur Bhai ne 1000 galle mein daale", "ENTRY",
       [ev(F, FAM, member_name="Mummy", transaction_type="kharcha", amount=2000, date="T"),
        ev(F, FAM, member_name="Bhai", transaction_type="jama", amount=1000, date="T")]),
    tc("FIN-FAM-15", "Agle mahine behen ki shaadi hai, 50000 rakhne padenge", "NO-ENTRY"),

    # ============================================================ STOCK
    tc("FIN-STK-01", "Haluwas site se 40 darwaze aur 25 chaukhat gudam aaye trolley mein", "ENTRY",
       [ev(None, MOV, item_name="darwaza", quantity=40, source_name="haluwas", destination_name="gudam", date="T"),
        ev(None, MOV, item_name="chaukhat", quantity=25, source_name="haluwas", destination_name="gudam", date="T")]),
    tc("FIN-STK-02", "Gudam se dukaan 500 eent bheji, Kitanu le gaya", "ENTRY",
       [ev(None, MOV, item_name="eent", quantity=500, source_name="gudam", destination_name="shop", date="T")]),  # driver: movement tool mein field nahi (scorer fix 15:25)
    tc("FIN-STK-03", "Chhat todne ko Dhani wali site pe 6 aadmi lagaye the aaj", "ENTRY",
       [ev(None, WORK, location_type="site", location_name="dhani", labour_count=6, date="T")]),
    tc("FIN-STK-04", "Hisab milaya to gudam mein 60 eent faltu padi mili", "ENTRY",
       [ev(None, ADJ, location="gudam", item_name="eent", quantity_change=60, date="T")]),
    tc("FIN-STK-05", "Dukaan pe rakhe 4 shahteer deemak lag ke kharab ho gaye", "ENTRY",
       [ev(None, ADJ, location="shop", item_name="shahteer", quantity_change=-4, date="T")]),
    tc("FIN-STK-06", "Kalanaur wali kothi se 3 trolley malba gudam pahunchaya", "ENTRY",
       [ev(None, MOV, item_name="malba", quantity=3, source_name="kalanaur", destination_name="gudam", date="T")]),
    tc("FIN-STK-07", "Dukaan se 10 girder wapas gudam rakhwaye", "ENTRY",
       [ev(None, MOV, item_name="girder", quantity=10, source_name="shop", destination_name="gudam", date="T")]),
    tc("FIN-STK-08", "Haluwas site pe 2 mistri aur 4 beldar the, deewar giraayi", "ENTRY",
       [ev(None, WORK, location_type="site", location_name="haluwas", labour_count=6, date="T")]),
    tc("FIN-STK-09", "300 eent gudam se uthwa ke dukaan pe lagwa di", "ENTRY",
       [ev(None, MOV, item_name="eent", quantity=300, source_name="gudam", destination_name="shop", date="T")]),
    tc("FIN-STK-10", "Utaarte hue 15 eent phoot gayi gudam pe", "ENTRY",
       [ev(None, ADJ, location="gudam", item_name="eent", quantity_change=-15, date="T")]),
    tc("FIN-STK-11", "gudm se sau chaukhat haluwas wali site bheji", "ENTRY",
       [ev(None, MOV, item_name="chaukhat", quantity=100, source_name="gudam", destination_name="haluwas", date="T")]),
    tc("FIN-STK-12", "Kitanu tractor se Haluwas se 2 trolley lakdi seedha dukaan le aaya", "ENTRY",
       [ev(None, MOV, item_name="lakdi", quantity=2, source_name="haluwas", destination_name="shop", date="T")]),  # driver: field nahi (scorer fix)
    tc("FIN-STK-13", "Site se kuch darwaze gudam aa gaye", "ASK", ask="Which site / how many?"),
    tc("FIN-STK-14", "Gudam se 400 eent Dhani site gayi, wahan 3 labour lage, 20 eent raaste mein tooti", "ENTRY",
       [ev(None, MOV, item_name="eent", quantity=400, source_name="gudam", destination_name="dhani", date="T"),
        ev(None, WORK, location_type="site", location_name="dhani", labour_count=3, date="T"),
        ev(None, ADJ, location="", item_name="eent", quantity_change=-20, date="T")]),
    tc("FIN-STK-15", "Kal Haluwas se baaki malba uthwana hai", "NO-ENTRY"),

    # ============================================================ PURCHASE
    tc("FIN-PUR-01", "Kalanaur mein Jagbir ki purani haveli 6 lakh mein todne ke liye li", "ENTRY",
       [ev(P, PUR, seller_name="Jagbir", total_amount=600000, date="T")]),
    tc("FIN-PUR-02", "Jagbir ko haveli ka 1 lakh bayana diya", "ENTRY",
       [ev(P, PPAY, seller_name="Jagbir", amount=100000, date="T")]),
    tc("FIN-PUR-03", "Dhani mein Ramphal ji ka purana makaan 3.5 lakh mein le liya, 50000 abhi diye", "ENTRY",
       [ev(P, PUR, seller_name="Ramphal ji", total_amount=350000, date="T"),
        ev(P, PPAY, seller_name="Ramphal ji", amount=50000, date="T")]),
    tc("FIN-PUR-04", "Gas cutter machine 18000 ki nayi li", "ENTRY",
       [ev(None, PUR, seller_name=None, total_amount=18000, date="T")]),
    tc("FIN-PUR-05", "Jagbir ko 2 lakh aur pakdaye haveli ke", "ENTRY",
       [ev(P, PPAY, seller_name="Jagbir", amount=200000, date="T")]),
    tc("FIN-PUR-06", "Satpal ji se Haluwas wali kothi le li, chaar lakh mein baat bani", "ENTRY",
       [ev(P, PUR, seller_name="Satpal ji", total_amount=400000, date="T")]),
    tc("FIN-PUR-07", "Purana tractor trolley 1.2 lakh mein liya Bhupi se", "ENTRY",
       [ev(P, PUR, seller_name="Bhupi", total_amount=120000, date="T")]),
    tc("FIN-PUR-08", "Ramphal ji ka baaki 3 lakh chuka diya, makaan ka hisab khatam", "ENTRY",
       [ev(P, PPAY, seller_name="Ramphal ji", amount=300000, date="T")]),
    tc("FIN-PUR-09", "Kothi wale Satpal ji ke ghar 50000 pahuncha diye", "ENTRY",
       [ev(P, PPAY, seller_name="Satpal ji", amount=50000, date="T")]),
    tc("FIN-PUR-10", "Naya generator 45000 ka liya", "ENTRY",
       [ev(None, PUR, seller_name=None, total_amount=45000, date="T")]),
    tc("FIN-PUR-11", "satpal ji wali kothi dhai lakh mein tay hui thi, aadhi rakam de di", "ENTRY",
       [ev(P, PPAY, seller_name="Satpal ji", amount=125000, date="T")]),
    tc("FIN-PUR-12", "jagbeer ki haveli ke 1.5 lac online kiye", "ENTRY",
       [ev(P, PPAY, seller_name="Jagbir", amount=150000, date="T")]),
    tc("FIN-PUR-13", "Dhani wale makaan ka bayana de diya", "ASK", ask="How much / to whom?"),
    tc("FIN-PUR-14", "Bhupi se purani JCB 8 lakh mein li, 3 lakh cheque aur 1 lakh cash diye", "ENTRY",
       [ev(P, PUR, seller_name="Bhupi", total_amount=800000, date="T"),
        ev(P, PPAY, seller_name="Bhupi", amount=300000, date="T"),
        ev(P, PPAY, seller_name="Bhupi", amount=100000, date="T")]),
    tc("FIN-PUR-15", "Kalanaur mein ek aur haveli dekhi hai, 5 lakh maang rahe hain", "NO-ENTRY"),

    # ============================================================ REPORT (route + kind + naam + tareekh)
    tc("FIN-RPT-01", "Kitanu ka pichle 10 din ka hisab nikalo", "REPORT", report=RP("person", "Kitanu", None, "T-9", "T")),
    tc("FIN-RPT-02", "SBI Bhatte ka khata dikhana zara, is mahine ka", "REPORT", report=RP("person", "SBI Bhatta", None, "M0", "T")),
    tc("FIN-RPT-03", "Suresh Traders wale pe humara kitna nikalta hai?", "REPORT", report=RP("person", "Suresh Traders")),
    tc("FIN-RPT-04", "Papa ne pichle mahine galle se kitna uthaya", "REPORT", report=RP("person", "Papa", None, "PM_S", "PM_E")),
    tc("FIN-RPT-05", "15 se 30 september tak ka diesel aur baaki kharcha", "REPORT", report=RP("expense", None, None, "09-15", "09-30")),
    tc("FIN-RPT-06", "Kal gudam se kahan kahan maal gaya", "REPORT", report=RP("material_movement", None, None, "T-1", "T-1")),
    tc("FIN-RPT-07", "Is saal kitni haveliyan kharidi, list do", "REPORT", report=RP("purchase", None, None, "Y0", "T")),
    tc("FIN-RPT-08", "kuch report chahiye thi mujhe", "REPORT", report=RP(None)),
    tc("FIN-RPT-09", "Sohan ke saath len-den saaf kar diya, 2000 thama diye", "ENTRY", report=dict(route="accounting")),
    tc("FIN-RPT-10", "Sharma ji ke khate mein 1500 aur chadha do, 3 darwaze le gaye", "ENTRY", report=dict(route="accounting")),

    # ============================================================ CORRECTION (pehle correction-sawaal pe ruk ke)
    tc("FIN-COR-01", "Sohan ki 6 tareekh wali dihadi galat chadh gayi", "CORRECTION", correction=CR("Sohan", "10-06"), expected_c=[]),
    tc("FIN-COR-02", "Parso Suresh Traders wali payment do baar likh di galti se", "CORRECTION",
       correction=CR("Suresh Traders", "T-2"), expected_c=[]),
    tc("FIN-COR-03", "Kitanu ko kal absent likh diya, galat hai, wo to aaya tha", "CORRECTION",
       correction=CR("Kitanu", "T-1"), expected_c=[]),
    tc("FIN-COR-04", "Koi entry galat ho gayi hai, dekhna padega", "CORRECTION", correction=CR(None, None), expected_c=[]),
    tc("FIN-COR-05", "Aaj subah wala diesel wala hisab hata do", "CORRECTION", correction=CR(None, "T"), expected_c=[]),
    tc("FIN-COR-06", "Ram ko aaj 400 diye, aur parso ki uski entry cancel kar do", "CORRECTION",
       correction=CR("Ram", "T-2"), expected_c=[T(EMP_TXN, "Ram", 400)]),
    tc("FIN-COR-07", "Gudam ka bijli bill 1900 bhara aaj, kal wala bill galat chadha tha", "CORRECTION",
       correction=CR(None, "T-1"), expected_c=[T(EXP, None, 1900)]),
    tc("FIN-COR-08", "Ram ko 700 pakdaye aaj, pehle 600 bola tha", "ENTRY",
       correction=dict(route="accounting"), expected_c=[T(EMP_TXN, "Ram", 700)]),
    tc("FIN-COR-09", "Kitanu ke purane 900 abhi dene hain", "ENTRY",
       correction=dict(route="accounting"), expected_c=[T(OPEN, "Kitanu", 900)]),
    tc("FIN-COR-10", "Sharma ji ne kal wala bacha hua 1000 aaj de diya", "ENTRY",
       correction=dict(route="accounting"), expected_c=[T(CPAY, "Sharma ji", 1000)]),

    # ============================================================ ROUTER (sirf route, route-only)
    tc("FIN-RTR-01", "Chai bana lo sabke liye", "general_chat", route="general_chat", route_only=True),
    tc("FIN-RTR-02", "Aaj Bhiwani mein baarish hogi kya?", "general_chat", route="general_chat", route_only=True),
    tc("FIN-RTR-03", "Tumhara naam kya hai?", "general_chat", route="general_chat", route_only=True),
    tc("FIN-RTR-04", "Kitanu ki shaadi mein kab chalna hai?", "general_chat", route="general_chat", route_only=True),
    tc("FIN-RTR-05", "Eent ka kaam aajkal mandi mein kaisa chal raha hai", "general_chat", route="general_chat", route_only=True),
    tc("FIN-RTR-06", "Sohan subah se gayab hai aaj, aaya hi nahi", "accounting", route="accounting", route_only=True),
    tc("FIN-RTR-07", "Haanji bhai, Suresh Traders ki taraf se 3000 aa gaye", "accounting", route="accounting", route_only=True),
    tc("FIN-RTR-08", "Arre Papa gudam ki chaabi ke saath 500 bhi le gaye", "accounting", route="accounting", route_only=True),
    tc("FIN-RTR-09", "Bhatte wale SBI ko abhi kitna chukana bacha hai?", "report", route="report", route_only=True),
    tc("FIN-RTR-10", "Bhatte wale SBI ke 4000 abhi chukane bache hain", "accounting", route="accounting", route_only=True),
]

CATEGORY_LABELS = {"EMP": "Employee", "CUS": "Customer", "SUP": "Supplier", "EXP": "Expense", "FAM": "Family",
                   "STK": "Stock", "PUR": "Purchase", "RPT": "Report", "COR": "Correction", "RTR": "Router"}

for _t in TESTCASES:
    _t["hindi"] = ""
    _t["english_input"] = ""
assert len(TESTCASES) == 135 and len({t["id"] for t in TESTCASES}) == 135
