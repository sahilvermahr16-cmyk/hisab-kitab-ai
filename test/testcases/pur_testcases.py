# test/testcases/pur_testcases.py — Purchase (property) bundle, test set v1 (LOCKED 2026-10-08).
#
# Har test case:
#   id        : PUR-<category>-<no>
#   category  : A Daily | B Tricky | C Edge | D Other business | E Mixed
#   hinglish  : statement jo system ko diya jayega
#   english   : professors ke liye anuvaad
#   outcome   : ENTRY | ASK | NO-ENTRY   (kya hona CHAHIYE)
#   roles     : beech mein role / jagah ki kism ka sawaal aaye to runner kya jawaab de {naam: role}
#               ("Property / Site Owner" → role ka jawaab; jagah ki kism poochi to "site")
#   expected  : har expected entry — role, tool, key arguments
#               date: "T" = test ka din, "T-1" = ek din pehle
#   ask       : (ASK ke liye) kya poochna chahiye tha
#   why       : ye test kyun hai
#
# Purchase ka model: record_purchase = purana makaan / dukaan / building todne ke liye khareeda (sauda, total);
# record_purchase_payment = seller ko paisa diya (bayana, advance, kist, baaki).
# User (Sahil) ka faisla: statement mein seller saaf ho to entry banegi — DB mein purana sauda na ho tab bhi
# (advance pehle diya jaata hai, sauda baad mein judta hai).
#
# Statements user ke saath tay kiye; har statement prompt ke saare examples aur pichhle bundles ke test
# statements se milaaya gaya (difflib ≤ 0.69).
#
# Seed (test/seed_data.py): koi seller nahi. Yadav ji, Malik sahab, Choudhary ji, Saini ji, Rana ji, Pawan naye.
#
# Is file ke statements aur expected jawaab LOCKED hain (v1). Badlaav = naya version.

BUNDLE = "Purchase"
PREFIX = "PUR"

S, C, E, F, P = "Supplier", "Customer", "Employee", "Family Member", "Property / Site Owner"
PUR = "record_purchase"
PPAY = "record_purchase_payment"
MOV = "record_material_movement"
WORK = "record_work_log"
SALE = "record_sale_transaction"
CPAY = "record_sale_payment"
SPAY = "record_supplier_payment"
EXP = "record_expense"
EPAY = "record_expense_payment"
FAM = "record_family_transaction"
EMP_TXN = "record_employee_transaction"
ATT = "record_attendance"


def R(**kw):
    return {k.replace("_", " "): v for k, v in kw.items()}


def B(seller, total, date="T", **extra):
    """sauda (purchase)"""
    return [dict(role=P, tool=PUR, args=dict(seller_name=seller, total_amount=total, date=date, **extra))]


def PP(seller, amount, date="T", **extra):
    """seller ko paisa (purchase payment)"""
    return [dict(role=P, tool=PPAY, args=dict(seller_name=seller, amount=amount, date=date, **extra))]


def X(category, amount, desc, date="T"):
    return [dict(role=None, tool=EXP, args=dict(category=category, amount=amount, description=desc, date=date)),
            dict(role=None, tool=EPAY, args=dict(amount=amount, date=date))]


YADAV = R(yadav_ji=P, यादव=P)
MALIK = R(malik_sahab=P, मलिक=P)
CHOU = R(choudhary_ji=P, चौधरी=P)
SAINI = R(saini_ji=P, सैनी=P)
RANA = R(rana_ji=P, राणा=P)
PAWAN = R(pawan=P, पवन=P)

TESTCASES = [
    # =====================================================================  A — DAILY
    dict(id="PUR-A-01", category="A", hinglish="Rohtak road wali haveli 4 lakh mein khareedi Yadav ji se",
         english="Bought the haveli on Rohtak road from Yadav ji for 4 lakh", outcome="ENTRY", roles=YADAV,
         expected=B("Yadav ji", 400000), why="Simple purchase, seller at the end"),
    dict(id="PUR-A-02", category="A", hinglish="Yadav ji ko haveli ke 50000 diye",
         english="Paid Yadav ji 50000 for the haveli", outcome="ENTRY", roles=YADAV,
         expected=PP("Yadav ji", 50000), why="Payment to seller (no old deal in DB — entry still made)"),
    dict(id="PUR-A-03", category="A", hinglish="Malik sahab ki purani dukaan 1.5 lakh mein tay hui todne ko",
         english="Malik sahab's old shop was settled at 1.5 lakh for demolition", outcome="ENTRY", roles=MALIK,
         expected=B("Malik sahab", 150000), why="'tay hui' = deal done"),
    dict(id="PUR-A-04", category="A", hinglish="Malik sahab ko 1 lakh pakda diye dukaan ke",
         english="Handed Malik sahab 1 lakh for the shop", outcome="ENTRY", roles=MALIK,
         expected=PP("Malik sahab", 100000), why="Payment"),
    dict(id="PUR-A-05", category="A", hinglish="Choudhary ji se school ki purani building 8 lakh mein li",
         english="Bought the old school building from Choudhary ji for 8 lakh", outcome="ENTRY", roles=CHOU,
         expected=B("Choudhary ji", 800000), why="Purchase"),
    dict(id="PUR-A-06", category="A", hinglish="Choudhary ji ko 2 lakh advance diye building ka",
         english="Gave Choudhary ji 2 lakh advance for the building", outcome="ENTRY", roles=CHOU,
         expected=PP("Choudhary ji", 200000), why="'advance' must not become employee advance"),
    dict(id="PUR-A-07", category="A", hinglish="Kal Saini ji ka godown 2.5 lakh mein liya, tod ke maal nikalna hai",
         english="Yesterday bought Saini ji's godown for 2.5 lakh, have to break it and take out the material",
         outcome="ENTRY", roles=SAINI,
         expected=B("Saini ji", 250000, date="T-1"), why="Purchase yesterday; future salvage = no movement"),
    dict(id="PUR-A-08", category="A", hinglish="Saini ji ko aaj 50 hazaar aur bheje",
         english="Sent Saini ji 50 thousand more today", outcome="ENTRY", roles=SAINI,
         expected=PP("Saini ji", 50000), why="'50 hazaar'"),
    dict(id="PUR-A-09", category="A", hinglish="Rana ji ki kothi ka sauda 6 lakh mein pakka hua",
         english="The deal for Rana ji's bungalow was fixed at 6 lakh", outcome="ENTRY", roles=RANA,
         expected=B("Rana ji", 600000), why="'sauda pakka'"),
    dict(id="PUR-A-10", category="A", hinglish="Rana ji ka baaki 4 lakh chuka diya",
         english="Cleared Rana ji's remaining 4 lakh", outcome="ENTRY", roles=RANA,
         expected=PP("Rana ji", 400000), why="Remaining payment"),

    # =====================================================================  B — TRICKY
    dict(id="PUR-B-01", category="B", hinglish="Haveli todne ka sauda Yadav ji se 4 lakh mein, 1 lakh abhi de diya",
         english="Deal with Yadav ji to break the haveli for 4 lakh, paid 1 lakh now", outcome="ENTRY", roles=YADAV,
         expected=B("Yadav ji", 400000) + PP("Yadav ji", 100000), why="Deal + payment in one line"),
    dict(id="PUR-B-02", category="B", hinglish="Malik sahab ki dukaan ka pura malba 1.5 lakh mein utha liya",
         english="Took all the debris of Malik sahab's shop for 1.5 lakh", outcome="ENTRY", roles=MALIK,
         expected=B("Malik sahab", 150000), why="'malba' looks like goods — it is a property purchase"),
    dict(id="PUR-B-03", category="B", hinglish="Choudhary ji wali building ke 2 lakh aur de aaye",
         english="Gave 2 lakh more for Choudhary ji's building", outcome="ENTRY", roles=CHOU,
         expected=PP("Choudhary ji", 200000), why="'wali building' is a descriptor"),
    dict(id="PUR-B-04", category="B", hinglish="Saini ji ka godown liya tha 2.5 lakh ka, aaj aadha de diya",
         english="Had bought Saini ji's godown for 2.5 lakh, paid half today", outcome="ENTRY", roles=SAINI,
         expected=PP("Saini ji", 125000), why="Old deal is background — only today's half payment"),
    dict(id="PUR-B-05", category="B", hinglish="Rana ji ne apni kothi 6 lakh mein de di, paise agle hafte denge",
         english="Rana ji gave us his bungalow for 6 lakh, will pay next week", outcome="ENTRY", roles=RANA,
         expected=B("Rana ji", 600000), why="'Rana ji ne … de di' = we bought; no payment yet"),
    dict(id="PUR-B-06", category="B", hinglish="Purani dharamshala ka thekedar Pawan hai, usse 3 lakh mein deal hui",
         english="Pawan is the contractor of the old dharamshala, the deal with him is 3 lakh", outcome="ENTRY",
         roles=PAWAN, expected=B("Pawan", 300000), why="Seller named in the middle"),
    dict(id="PUR-B-07", category="B", hinglish="Haveli pakki karne ko Yadav ji ke haath 21000 bayana rakh aaye",
         english="Left 21000 token money with Yadav ji to confirm the haveli", outcome="ENTRY", roles=YADAV,
         expected=PP("Yadav ji", 21000), why="'bayana' = token payment"),
    dict(id="PUR-B-08", category="B", hinglish="Malik sahab se dukaan 1.5 lakh mein li, 50000 cash diye aur 1 lakh PhonePe kiye",
         english="Bought the shop from Malik sahab for 1.5 lakh, paid 50000 cash and 1 lakh by PhonePe", outcome="ENTRY",
         roles=MALIK, expected=B("Malik sahab", 150000) + PP("Malik sahab", 50000) + PP("Malik sahab", 100000),
         why="Two payment methods"),
    dict(id="PUR-B-09", category="B", hinglish="Choudhary ji ki building ka sauda 8 se ghat ke 7.5 lakh pe hua",
         english="The deal for Choudhary ji's building came down from 8 to 7.5 lakh", outcome="ENTRY", roles=CHOU,
         expected=B("Choudhary ji", 750000), why="Two numbers — final is 7.5 lakh"),
    dict(id="PUR-B-10", category="B", hinglish="Kal Rana ji ko kothi ke 2 lakh diye the, aaj 1 lakh aur",
         english="Gave Rana ji 2 lakh for the bungalow yesterday, 1 lakh more today", outcome="ENTRY", roles=RANA,
         expected=PP("Rana ji", 200000, date="T-1") + PP("Rana ji", 100000), why="Two payments, two dates"),

    # =====================================================================  C — EDGE
    dict(id="PUR-C-01", category="C", hinglish="Haveli todne ko le li Yadav ji wali, rakam abhi likhi nahi",
         english="Took Yadav ji's haveli for demolition, amount not written yet", outcome="ASK", roles=YADAV,
         expected=[], ask="For how much?", why="No amount"),
    dict(id="PUR-C-02", category="C", hinglish="Ek purana makaan 2 lakh mein le liya aaj",
         english="Bought an old house for 2 lakh today", outcome="ASK", roles={},
         expected=[], ask="From whom?", why="No seller"),
    dict(id="PUR-C-03", category="C", hinglish="Agle mahine Malik sahab ki dukaan lene ki soch rahe hain",
         english="Thinking of buying Malik sahab's shop next month", outcome="NO-ENTRY", roles=MALIK,
         expected=[], why="Plan only"),
    dict(id="PUR-C-04", category="C", hinglish="Rana ji se kothi 5 lakh, nahi nahi 5.5 lakh mein li",
         english="Bought the bungalow from Rana ji for 5 lakh, no no, 5.5 lakh", outcome="ENTRY", roles=RANA,
         expected=B("Rana ji", 550000), why="Self-correction"),
    dict(id="PUR-C-05", category="C", hinglish="Saini ji ka godown dhai lakh mein le liya",
         english="Bought Saini ji's godown for two and a half lakh", outcome="ENTRY", roles=SAINI,
         expected=B("Saini ji", 250000), why="Amount in words"),
    dict(id="PUR-C-06", category="C", hinglish="Choudhary ji ke building wale kitne dene baaki hain?",
         english="How much is still to be paid to Choudhary ji for the building?", outcome="NO-ENTRY", roles=CHOU,
         expected=[], why="Question — report"),
    dict(id="PUR-C-07", category="C", hinglish="yadv ji ki haveli 4 lac me le li",
         english="bought yadav ji's haveli for 4 lac", outcome="ENTRY", roles=R(yadv_ji=P, yadav_ji=P, यादव=P),
         expected=B("Yadav ji", 400000), why="Spelling (yadv, lac)"),
    dict(id="PUR-C-08", category="C", hinglish="Pawan wala sauda toot gaya, dharamshala nahi li",
         english="The deal with Pawan broke, didn't buy the dharamshala", outcome="NO-ENTRY", roles=PAWAN,
         expected=[], why="Deal did not happen"),
    dict(id="PUR-C-09", category="C", hinglish="Malik sahab ko 50k de diye",
         english="Gave Malik sahab 50k", outcome="ENTRY", roles=MALIK,
         expected=PP("Malik sahab", 50000), why="'50k'"),
    dict(id="PUR-C-10", category="C", hinglish="Kothi ke liye Rana ji 6-7 lakh bol rahe hain, abhi pakka nahi",
         english="Rana ji is asking 6-7 lakh for the bungalow, not final yet", outcome="NO-ENTRY", roles=RANA,
         expected=[], why="Range + not final"),

    # =====================================================================  D — OTHER BUSINESS
    dict(id="PUR-D-01", category="D", hinglish="Tractor teen chakkar laga ke Yadav ji ki haveli wali 3000 eent gudam le aaya",
         english="The tractor made three trips and brought 3000 bricks from Yadav ji's haveli to the warehouse",
         outcome="ENTRY", roles=YADAV,
         expected=[dict(role=None, tool=MOV, args=dict(item_name="eent", quantity=3000, source_name="Yadav ji",
                                                       destination_name="gudam", date="T"))],
         why="Site → gudam movement, not a purchase"),
    dict(id="PUR-D-02", category="D", hinglish="Malik sahab ki dukaan todne mein aaj 6 labour lage",
         english="6 labourers worked today breaking Malik sahab's shop", outcome="ENTRY", roles=MALIK,
         expected=[dict(role=None, tool=WORK, args=dict(location_type="site", description="dukaan todna", labour_count=6, date="T"))],
         why="Work log at site"),
    dict(id="PUR-D-03", category="D", hinglish="Choudhary ji wali building ka malba Sharma ji ko 5000 mein becha",
         english="Sold the debris from Choudhary ji's building to Sharma ji for 5000", outcome="ENTRY",
         roles=R(sharma_ji=C, choudhary_ji=P),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Sharma ji", item_name="malba", amount=5000, date="T"))],
         why="Sale of debris"),
    dict(id="PUR-D-04", category="D", hinglish="Ram ko haveli pe kaam ke 600 diye",
         english="Paid Ram 600 for work at the haveli", outcome="ENTRY", roles=R(ram=E),
         expected=[dict(role=E, tool=EMP_TXN, args=dict(employee_name="Ram", transaction_type="payment", amount=600, date="T"))],
         why="Employee payment"),
    dict(id="PUR-D-05", category="D", hinglish="Haveli todne ke liye JCB ka kiraya 8000 diya",
         english="Paid 8000 JCB rent for breaking the haveli", outcome="ENTRY", roles={},
         expected=X("rent", 8000, "JCB kiraya"), why="Expense"),
    dict(id="PUR-D-06", category="D", hinglish="Rana ji ki kothi ke kaam pe Sohan ki hazri laga do",
         english="Mark Sohan's attendance for the work at Rana ji's bungalow", outcome="ENTRY", roles=R(sohan=E, rana_ji=P),
         expected=[dict(role=E, tool=ATT, args=dict(employee_name="Sohan", attendance="P", date="T"))],
         why="Attendance"),
    dict(id="PUR-D-07", category="D", hinglish="Saini ji ke godown ki 40 kadiyan Suresh Traders ko 6000 mein di",
         english="Gave 40 beams from Saini ji's godown to Suresh Traders for 6000", outcome="ENTRY",
         roles=R(suresh_traders=C, saini_ji=P),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Suresh Traders", item_name="kadi", quantity=40, amount=6000, date="T"))],
         why="Sale; 'Saini ji ke godown' is only the source"),
    dict(id="PUR-D-08", category="D", hinglish="Kothi wale kaam se lautte hue tractor mein 1500 ka diesel dalwaya",
         english="On the way back from the bungalow job, put 1500 of diesel in the tractor", outcome="ENTRY", roles={},
         expected=X("fuel", 1500, "tractor diesel"), why="Expense"),
    dict(id="PUR-D-09", category="D", hinglish="Malik sahab ki dukaan ka kaam khatam, 15 trolley malba gudam pahuncha",
         english="Work at Malik sahab's shop is over, 15 trolleys of debris reached the warehouse", outcome="ENTRY",
         roles=MALIK,
         expected=[dict(role=None, tool=MOV, args=dict(item_name="malba", quantity=15, source_name="Malik sahab",
                                                       destination_name="gudam", date="T"))],
         why="Site → gudam movement"),
    dict(id="PUR-D-10", category="D", hinglish="Haveli ke paison mein se SBI bhatte ka 10000 chukta kiya",
         english="Paid off 10000 to SBI kiln from the haveli money", outcome="ENTRY", roles=R(sbi_bhatta=S),
         expected=[dict(role=S, tool=SPAY, args=dict(supplier_name="SBI Bhatta", amount=10000, date="T"))],
         why="Supplier payment"),

    # =====================================================================  E — MIXED
    dict(id="PUR-E-01", category="E", hinglish="Yadav ji se haveli 4 lakh mein li aur todne pe 6 labour lagaye",
         english="Bought the haveli from Yadav ji for 4 lakh and put 6 labourers on breaking it", outcome="ENTRY",
         roles=YADAV,
         expected=B("Yadav ji", 400000)
                  + [dict(role=None, tool=WORK, args=dict(location_type="site", description="haveli todna", labour_count=6, date="T"))],
         why="Purchase + work log"),
    dict(id="PUR-E-02", category="E", hinglish="Malik sahab ko 50000 diye aur Ram ko 500 dihadi",
         english="Paid Malik sahab 50000 and Ram 500 daily wage", outcome="ENTRY", roles=R(malik_sahab=P, ram=E),
         expected=PP("Malik sahab", 50000)
                  + [dict(role=E, tool=EMP_TXN, args=dict(employee_name="Ram", transaction_type="payment", amount=500, date="T"))],
         why="Purchase payment + employee"),
    dict(id="PUR-E-03", category="E", hinglish="Choudhary ji ki building 8 lakh mein li, 2 lakh bayana diya, JCB ka 5000 kiraya bhi",
         english="Bought Choudhary ji's building for 8 lakh, paid 2 lakh token, and 5000 JCB rent too", outcome="ENTRY",
         roles=CHOU,
         expected=B("Choudhary ji", 800000) + PP("Choudhary ji", 200000) + X("rent", 5000, "JCB kiraya"),
         why="Purchase + payment + expense"),
    dict(id="PUR-E-04", category="E", hinglish="Saini ji ke godown se 1000 eent gudam aayi aur unko 30000 bheje",
         english="1000 bricks came from Saini ji's godown to the warehouse and sent him 30000", outcome="ENTRY",
         roles=SAINI,
         expected=[dict(role=None, tool=MOV, args=dict(item_name="eent", quantity=1000, source_name="Saini ji",
                                                       destination_name="gudam", date="T"))] + PP("Saini ji", 30000),
         why="Same person as site and seller"),
    dict(id="PUR-E-05", category="E", hinglish="Rana ji ki kothi 6 lakh mein pakki, aur Papa 2000 ghar ke liye le gaye",
         english="Rana ji's bungalow fixed at 6 lakh, and Papa took 2000 for home", outcome="ENTRY",
         roles=R(rana_ji=P, papa=F),
         expected=B("Rana ji", 600000)
                  + [dict(role=F, tool=FAM, args=dict(member_name="Papa", transaction_type="kharcha", amount=2000, date="T"))],
         why="Purchase + family"),
    dict(id="PUR-E-06", category="E", hinglish="Pawan se dharamshala 3 lakh mein li, wahan ka 2000 ka malba Sharma ji ko becha",
         english="Bought the dharamshala from Pawan for 3 lakh, sold 2000 worth of its debris to Sharma ji", outcome="ENTRY",
         roles=R(pawan=P, पवन=P, sharma_ji=C),
         expected=B("Pawan", 300000)
                  + [dict(role=C, tool=SALE, args=dict(customer_name="Sharma ji", item_name="malba", amount=2000, date="T"))],
         why="Purchase + sale"),
    dict(id="PUR-E-07", category="E", hinglish="Kal Yadav ji ko 1 lakh diye, aaj haveli se 2000 eent shop pahunchi",
         english="Gave Yadav ji 1 lakh yesterday, today 2000 bricks reached the shop from the haveli", outcome="ENTRY",
         roles=YADAV,
         expected=PP("Yadav ji", 100000, date="T-1")
                  + [dict(role=None, tool=MOV, args=dict(item_name="eent", quantity=2000, source_name="haveli",
                                                         destination_name="shop", date="T"))],
         why="Payment yesterday + movement today"),
    dict(id="PUR-E-08", category="E", hinglish="Malik sahab ka sauda 1.5 lakh, Kitanu aaj aaya, 800 ka diesel",
         english="Malik sahab's deal 1.5 lakh, Kitanu came today, 800 of diesel", outcome="ENTRY",
         roles=R(malik_sahab=P, kitanu=E),
         expected=B("Malik sahab", 150000)
                  + [dict(role=E, tool=ATT, args=dict(employee_name="Kitanu", attendance="P", date="T"))]
                  + X("fuel", 800, "diesel"),
         why="Four entries in short words"),
    dict(id="PUR-E-09", category="E", hinglish="SBI bhatte ko 5000 aur Choudhary ji ko building ke 1 lakh diye",
         english="Paid 5000 to SBI kiln and 1 lakh to Choudhary ji for the building", outcome="ENTRY",
         roles=R(sbi_bhatta=S, choudhary_ji=P),
         expected=[dict(role=S, tool=SPAY, args=dict(supplier_name="SBI Bhatta", amount=5000, date="T"))]
                  + PP("Choudhary ji", 100000),
         why="Supplier payment + purchase payment"),
    dict(id="PUR-E-10", category="E", hinglish="Rana ji ko 2 lakh diye aur Suresh Traders se 10000 aaye",
         english="Paid Rana ji 2 lakh and received 10000 from Suresh Traders", outcome="ENTRY",
         roles=R(rana_ji=P, suresh_traders=C),
         expected=PP("Rana ji", 200000)
                  + [dict(role=C, tool=CPAY, args=dict(customer_name="Suresh Traders", amount=10000, date="T"))],
         why="Money out + money in"),
]

CATEGORY_LABELS = {"A": "A - Daily", "B": "B - Tricky", "C": "C - Edge", "D": "D - Other business", "E": "E - Mixed"}

HINDI = {
    "PUR-A-01": "रोहतक रोड वाली हवेली 4 लाख में खरीदी यादव जी से",
    "PUR-A-02": "यादव जी को हवेली के 50000 दिए",
    "PUR-A-03": "मलिक साहब की पुरानी दुकान 1.5 लाख में तय हुई तोड़ने को",
    "PUR-A-04": "मलिक साहब को 1 लाख पकड़ा दिए दुकान के",
    "PUR-A-05": "चौधरी जी से स्कूल की पुरानी बिल्डिंग 8 लाख में ली",
    "PUR-A-06": "चौधरी जी को 2 लाख एडवांस दिए बिल्डिंग का",
    "PUR-A-07": "कल सैनी जी का गोदाम 2.5 लाख में लिया, तोड़ के माल निकालना है",
    "PUR-A-08": "सैनी जी को आज 50 हज़ार और भेजे",
    "PUR-A-09": "राणा जी की कोठी का सौदा 6 लाख में पक्का हुआ",
    "PUR-A-10": "राणा जी का बाकी 4 लाख चुका दिया",
    "PUR-B-01": "हवेली तोड़ने का सौदा यादव जी से 4 लाख में, 1 लाख अभी दे दिया",
    "PUR-B-02": "मलिक साहब की दुकान का पूरा मलबा 1.5 लाख में उठा लिया",
    "PUR-B-03": "चौधरी जी वाली बिल्डिंग के 2 लाख और दे आए",
    "PUR-B-04": "सैनी जी का गोदाम लिया था 2.5 लाख का, आज आधा दे दिया",
    "PUR-B-05": "राणा जी ने अपनी कोठी 6 लाख में दे दी, पैसे अगले हफ्ते देंगे",
    "PUR-B-06": "पुरानी धर्मशाला का ठेकेदार पवन है, उससे 3 लाख में डील हुई",
    "PUR-B-07": "हवेली पक्की करने को यादव जी के हाथ 21000 बयाना रख आए",
    "PUR-B-08": "मलिक साहब से दुकान 1.5 लाख में ली, 50000 कैश दिए और 1 लाख फोनपे किए",
    "PUR-B-09": "चौधरी जी की बिल्डिंग का सौदा 8 से घट के 7.5 लाख पे हुआ",
    "PUR-B-10": "कल राणा जी को कोठी के 2 लाख दिए थे, आज 1 लाख और",
    "PUR-C-01": "हवेली तोड़ने को ले ली यादव जी वाली, रकम अभी लिखी नहीं",
    "PUR-C-02": "एक पुराना मकान 2 लाख में ले लिया आज",
    "PUR-C-03": "अगले महीने मलिक साहब की दुकान लेने की सोच रहे हैं",
    "PUR-C-04": "राणा जी से कोठी 5 लाख, नहीं नहीं 5.5 लाख में ली",
    "PUR-C-05": "सैनी जी का गोदाम ढाई लाख में ले लिया",
    "PUR-C-06": "चौधरी जी के बिल्डिंग वाले कितने देने बाकी हैं?",
    "PUR-C-07": "यादव जी की हवेली 4 लाख मे ले ली",
    "PUR-C-08": "पवन वाला सौदा टूट गया, धर्मशाला नहीं ली",
    "PUR-C-09": "मलिक साहब को 50 हज़ार दे दिए",
    "PUR-C-10": "कोठी के लिए राणा जी 6-7 लाख बोल रहे हैं, अभी पक्का नहीं",
    "PUR-D-01": "ट्रैक्टर तीन चक्कर लगा के यादव जी की हवेली वाली 3000 ईंट गोदाम ले आया",
    "PUR-D-02": "मलिक साहब की दुकान तोड़ने में आज 6 लेबर लगे",
    "PUR-D-03": "चौधरी जी वाली बिल्डिंग का मलबा शर्मा जी को 5000 में बेचा",
    "PUR-D-04": "राम को हवेली पे काम के 600 दिए",
    "PUR-D-05": "हवेली तोड़ने के लिए जेसीबी का किराया 8000 दिया",
    "PUR-D-06": "राणा जी की कोठी के काम पे सोहन की हाज़िरी लगा दो",
    "PUR-D-07": "सैनी जी के गोदाम की 40 कड़ियां सुरेश ट्रेडर्स को 6000 में दीं",
    "PUR-D-08": "कोठी वाले काम से लौटते हुए ट्रैक्टर में 1500 का डीज़ल डलवाया",
    "PUR-D-09": "मलिक साहब की दुकान का काम खत्म, 15 ट्रॉली मलबा गोदाम पहुंचा",
    "PUR-D-10": "हवेली के पैसों में से एसबीआई भट्टे का 10000 चुकता किया",
    "PUR-E-01": "यादव जी से हवेली 4 लाख में ली और तोड़ने पे 6 लेबर लगाए",
    "PUR-E-02": "मलिक साहब को 50000 दिए और राम को 500 दिहाड़ी",
    "PUR-E-03": "चौधरी जी की बिल्डिंग 8 लाख में ली, 2 लाख बयाना दिया, जेसीबी का 5000 किराया भी",
    "PUR-E-04": "सैनी जी के गोदाम से 1000 ईंट गोदाम आईं और उनको 30000 भेजे",
    "PUR-E-05": "राणा जी की कोठी 6 लाख में पक्की, और पापा 2000 घर के लिए ले गए",
    "PUR-E-06": "पवन से धर्मशाला 3 लाख में ली, वहां का 2000 का मलबा शर्मा जी को बेचा",
    "PUR-E-07": "कल यादव जी को 1 लाख दिए, आज हवेली से 2000 ईंट दुकान पहुंचीं",
    "PUR-E-08": "मलिक साहब का सौदा 1.5 लाख, कितनू आज आया, 800 का डीज़ल",
    "PUR-E-09": "एसबीआई भट्टे को 5000 और चौधरी जी को बिल्डिंग के 1 लाख दिए",
    "PUR-E-10": "राणा जी को 2 लाख दिए और सुरेश ट्रेडर्स से 10000 आए",
}

ENGLISH_INPUT = {t["id"]: t["english"] for t in TESTCASES}

for _t in TESTCASES:
    _t["hindi"] = HINDI[_t["id"]]
    _t["english_input"] = ENGLISH_INPUT[_t["id"]]
assert set(HINDI) == set(ENGLISH_INPUT) == {t["id"] for t in TESTCASES}
assert len(TESTCASES) == 50
