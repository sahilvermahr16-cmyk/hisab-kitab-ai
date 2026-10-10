# test/testcases/stk_testcases.py — Stock / Gudam bundle, test set v1 (LOCKED 2026-10-07).
#
# Har test case:
#   id        : STK-<category>-<no>
#   category  : A Daily | B Tricky | C Edge | D Other business | E Mixed
#   hinglish  : statement jo system ko diya jayega
#   english   : professors ke liye anuvaad
#   outcome   : ENTRY | ASK | NO-ENTRY   (kya hona CHAHIYE)
#   roles     : beech mein role / jagah ki kism ka sawaal aaye to runner kya jawaab de {naam: role}
#               ("Site" → jagah ki kism site)
#   expected  : har expected entry — role, tool, key arguments
#               date: "T" = test ka din, "T-1" = ek din pehle
#   ask       : (ASK ke liye) kya poochna chahiye tha
#   why       : ye test kyun hai
#
# Stock ke 3 tool:
#   record_material_movement — maal ek jagah se doosri (gudam ↔ shop ↔ site)
#   record_adjustment        — stock badla bina movement (toota, kharab, ginti mein kam/zyada); quantity_change +/−
#   record_work_log          — site/gudam/shop pe kaam hua (kya kaam, kitne labour)
#
# Statements user (Sahil) ke saath tay kiye; har statement prompt ke saare examples aur
# pichhle bundles ke test statements se milaaya gaya (difflib ≤ 0.69).
#
# Seed (test/seed_data.py): jagah Gudam, Shop; employees Ram, Sohan, Kitanu; customers Suresh Traders,
# Sharma ji; supplier SBI Bhatta; family Papa. "Model Town" nayi site hai, Gupta ji naye hain.
#
# Is file ke statements aur expected jawaab LOCKED hain (v1). Badlaav = naya version.

BUNDLE = "Stock"
PREFIX = "STK"

S, C, E, F, P, SITE = "Supplier", "Customer", "Employee", "Family Member", "Property / Site Owner", "Site"
MOV = "record_material_movement"
ADJ = "record_adjustment"
WORK = "record_work_log"
SALE = "record_sale_transaction"
STX = "record_supplier_transaction"
EXP = "record_expense"
EPAY = "record_expense_payment"
FAM = "record_family_transaction"
EMP_TXN = "record_employee_transaction"
ATT = "record_attendance"
PUR = "record_purchase"


def R(**kw):
    return {k.replace("_", " "): v for k, v in kw.items()}


def M(item, qty, src, dst, date="T"):
    return [dict(role=None, tool=MOV, args=dict(item_name=item, quantity=qty, source_name=src,
                                                destination_name=dst, date=date))]


def A(loc, item, change, date="T", **extra):
    return [dict(role=None, tool=ADJ, args=dict(location=loc, item_name=item, quantity_change=change, date=date, **extra))]


def W(ltype, desc, date="T", **extra):
    return [dict(role=None, tool=WORK, args=dict(location_type=ltype, description=desc, date=date, **extra))]


def X(category, amount, desc, date="T"):
    return [dict(role=None, tool=EXP, args=dict(category=category, amount=amount, description=desc, date=date)),
            dict(role=None, tool=EPAY, args=dict(amount=amount, date=date))]


MT = R(model_town=SITE, मॉडल=SITE)

TESTCASES = [
    # =====================================================================  A — DAILY (seedhe)
    dict(id="STK-A-01", category="A", hinglish="Shop pe 40 fatte gudam se aaye",
         english="40 planks came to the shop from the warehouse", outcome="ENTRY", roles={},
         expected=M("fatta", 40, "gudam", "shop"), why="Simple movement, destination first"),
    dict(id="STK-A-02", category="A", hinglish="6 khidkiyan dukaan pe rakhwayi, gudam wali",
         english="Had 6 windows from the warehouse placed at the shop", outcome="ENTRY", roles={},
         expected=M("khidki", 6, "gudam", "shop"), why="Source as 'gudam wali' at the end"),
    dict(id="STK-A-03", category="A", hinglish="Shop ki 10 kadiyan gudam pahunchi",
         english="10 beams from the shop reached the warehouse", outcome="ENTRY", roles={},
         expected=M("kadi", 10, "shop", "gudam"), why="Shop → gudam"),
    dict(id="STK-A-04", category="A", hinglish="Gudam mein 25 eent tooti mili",
         english="Found 25 bricks broken in the warehouse", outcome="ENTRY", roles={},
         expected=A("gudam", "eent", -25), why="Damage → negative adjustment"),
    dict(id="STK-A-05", category="A", hinglish="Shop pe 2 chaukhat kam hain",
         english="2 door frames are short at the shop", outcome="ENTRY", roles={},
         expected=A("shop", "chaukhat", -2), why="Shortage → negative adjustment"),
    dict(id="STK-A-06", category="A", hinglish="Gudam mein 5 darwaze zyada nikle",
         english="5 extra doors turned up in the warehouse", outcome="ENTRY", roles={},
         expected=A("gudam", "darwaza", 5), why="Extra → positive adjustment"),
    dict(id="STK-A-07", category="A", hinglish="Gudam mein do mazdooron ne saara maal set kiya aaj",
         english="Two labourers arranged all the goods in the warehouse today", outcome="ENTRY", roles={},
         expected=W("gudam", "maal set kiya", labour_count=2), why="Work log with labour count in words"),
    dict(id="STK-A-08", category="A", hinglish="Shop pe aaj rang-rogan ka kaam hua",
         english="Painting work was done at the shop today", outcome="ENTRY", roles={},
         expected=W("shop", "rang-rogan"), why="Work log at shop"),
    dict(id="STK-A-09", category="A", hinglish="Kal shop ke liye 100 eent nikali gudam se",
         english="Yesterday took out 100 bricks from the warehouse for the shop", outcome="ENTRY", roles={},
         expected=M("eent", 100, "gudam", "shop", date="T-1"), why="Movement, yesterday"),
    dict(id="STK-A-10", category="A", hinglish="Gudam mein 3 gate jung lagne se bekaar ho gaye",
         english="3 gates in the warehouse got ruined by rust", outcome="ENTRY", roles={},
         expected=A("gudam", "gate", -3), why="Damage with reason"),

    # =====================================================================  B — TRICKY
    dict(id="STK-B-01", category="B", hinglish="Subah tractor mein 300 eent bhar ke dukaan pahuncha di gudam wali",
         english="In the morning loaded 300 bricks from the warehouse on the tractor and delivered them to the shop",
         outcome="ENTRY", roles={},
         expected=M("eent", 300, "gudam", "shop"), why="Source at the end ('gudam wali'), tractor mention"),
    dict(id="STK-B-02", category="B", hinglish="Shop se 20 kadiyan wapas gudam mein rakhwa di",
         english="Had 20 beams put back in the warehouse from the shop", outcome="ENTRY", roles={},
         expected=M("kadi", 20, "shop", "gudam"), why="'wapas' must not look like a return/sale"),
    dict(id="STK-B-03", category="B", hinglish="Gudam mein 50 eent toot gayi aaj utarte waqt",
         english="50 bricks broke in the warehouse today while unloading", outcome="ENTRY", roles={},
         expected=A("gudam", "eent", -50), why="'utarte waqt' must not become a movement"),
    dict(id="STK-B-04", category="B", hinglish="Shop pe ginti ki to 4 darwaze kam nikle",
         english="Counted at the shop and 4 doors were short", outcome="ENTRY", roles={},
         expected=A("shop", "darwaza", -4), why="Count correction"),
    dict(id="STK-B-05", category="B", hinglish="Aaj gudam ki safai karwayi, 3 labour lage the",
         english="Got the warehouse cleaned today, 3 labourers worked", outcome="ENTRY", roles={},
         expected=W("gudam", "safai", labour_count=3), why="Labour must not become an employee payment"),
    dict(id="STK-B-06", category="B", hinglish="Model Town wali site pe aaj pichli deewar todi",
         english="Broke the back wall at the Model Town site today", outcome="ENTRY", roles=MT,
         expected=W("site", "deewar todi", location_name="Model Town"), why="'todi' must not become a demolition deal"),
    dict(id="STK-B-07", category="B", hinglish="Gudam mein ginti karte waqt 10 bori cement zyada mili",
         english="While counting in the warehouse found 10 extra bags of cement", outcome="ENTRY", roles={},
         expected=A("gudam", "cement", 10), why="Positive adjustment"),
    dict(id="STK-B-08", category="B", hinglish="Model Town ke kaam se tractor 2000 eent laya, sab gudam mein khali kar di",
         english="The tractor brought 2000 bricks from the Model Town job, unloaded all in the warehouse",
         outcome="ENTRY", roles=MT,
         expected=M("eent", 2000, "Model Town", "gudam"), why="Site → gudam, not a purchase/sale"),
    dict(id="STK-B-09", category="B", hinglish="Kal shop se 15 fatte gudam bhej diye the",
         english="Yesterday sent 15 planks from the shop to the warehouse", outcome="ENTRY", roles={},
         expected=M("fatta", 15, "shop", "gudam", date="T-1"), why="Past-date movement"),
    dict(id="STK-B-10", category="B", hinglish="Barish mein gudam ki 5 khidkiyan kharab ho gayi",
         english="5 windows in the warehouse got spoiled in the rain", outcome="ENTRY", roles={},
         expected=A("gudam", "khidki", -5), why="Reason first, damage"),

    # =====================================================================  C — EDGE
    dict(id="STK-C-01", category="C", hinglish="Kuch eent dukaan pe pahunchi hain gudam se, ginti yaad nahi",
         english="Some bricks reached the shop from the warehouse, don't remember the count", outcome="ASK", roles={},
         expected=[], ask="How many?", why="No quantity — must ask"),
    dict(id="STK-C-02", category="C", hinglish="Shop pe abhi kitni eent padi hain?",
         english="How many bricks are lying at the shop right now?", outcome="NO-ENTRY", roles={},
         expected=[], why="Question — report, not an entry"),
    dict(id="STK-C-03", category="C", hinglish="Kal 200 eent gudam se dukaan bhejni hai",
         english="Have to send 200 bricks from the warehouse to the shop tomorrow", outcome="NO-ENTRY", roles={},
         expected=[], why="Future plan"),
    dict(id="STK-C-04", category="C", hinglish="Gudam ki tooti eent 30 likhna, nahi nahi 40 thi",
         english="Write 30 broken bricks in the warehouse, no no, it was 40", outcome="ENTRY", roles={},
         expected=A("gudam", "eent", -40), why="Self-correction — one adjustment of −40"),
    dict(id="STK-C-05", category="C", hinglish="Dukaan pe dhai sau eent gudam se aa gayi",
         english="Two hundred fifty bricks came to the shop from the warehouse", outcome="ENTRY", roles={},
         expected=M("eent", 250, "gudam", "shop"), why="Number in words"),
    dict(id="STK-C-06", category="C", hinglish="Gudam mein 2 ton loha kam nikla",
         english="2 tons of iron short in the warehouse", outcome="ENTRY", roles={},
         expected=A("gudam", "loha", -2, unit="ton"), why="Ton unit (−2000 kg also correct)"),
    dict(id="STK-C-07", category="C", hinglish="dukan pr gudm se 12 kadi aai",
         english="12 beams came to the shop from the warehouse", outcome="ENTRY", roles={},
         expected=M("kadi", 12, "gudam", "shop"), why="Spelling mistakes"),
    dict(id="STK-C-08", category="C", hinglish="Gudam mein sab theek tha, ginti barabar nikli",
         english="Everything was fine in the warehouse, the count matched", outcome="NO-ENTRY", roles={},
         expected=[], why="No change"),
    dict(id="STK-C-09", category="C", hinglish="Gudam ka thoda maal dukaan pe le gaye",
         english="Took some goods from the warehouse to the shop", outcome="ASK", roles={},
         expected=[], ask="Which item, how many?", why="No item, no quantity"),
    dict(id="STK-C-10", category="C", hinglish="Parso Model Town site pe kaam nahi hua, barish thi",
         english="No work happened at the Model Town site day before yesterday, it rained", outcome="NO-ENTRY",
         roles=MT, expected=[], why="Work did not happen"),

    # =====================================================================  D — OTHER BUSINESS
    dict(id="STK-D-01", category="D", hinglish="Sharma ji ki site pe gudam wali 200 eent gayi, 1600 tay hue",
         english="200 bricks from the warehouse went to Sharma ji's site, settled at 1600", outcome="ENTRY",
         roles=R(sharma_ji=C),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Sharma ji", item_name="eent", quantity=200, amount=1600, date="T"))],
         why="Goods to a customer with price = sale, not just movement"),
    dict(id="STK-D-02", category="D", hinglish="SBI ki gaadi aayi, 3000 eent seedha gudam mein khali, bill 18000 ka",
         english="SBI's vehicle came, 3000 bricks unloaded straight in the warehouse, bill of 18000", outcome="ENTRY",
         roles=R(sbi=S, sbi_bhatta=S),
         expected=[dict(role=S, tool=STX, args=dict(supplier_name="SBI Bhatta", item_name="eent", quantity=3000, amount=18000, date="T"))],
         why="Supplier purchase into gudam"),
    dict(id="STK-D-03", category="D", hinglish="Gudam ke maalik ko is mahine ka 5000 kiraya pakda diya",
         english="Handed the warehouse owner 5000 rent for this month", outcome="ENTRY", roles={},
         expected=X("rent", 5000, "gudam kiraya"), why="Rent expense — 'maalik' is not a party"),
    dict(id="STK-D-04", category="D", hinglish="Sohan subah se gudam pe hai, present likh lo",
         english="Sohan has been at the warehouse since morning, mark him present", outcome="ENTRY", roles=R(sohan=E),
         expected=[dict(role=E, tool=ATT, args=dict(employee_name="Sohan", attendance="P", date="T"))],
         why="Attendance, not work log"),
    dict(id="STK-D-05", category="D", hinglish="Shop ka 1500 ka bijli bill bhara",
         english="Paid the shop's electricity bill of 1500", outcome="ENTRY", roles={},
         expected=X("misc", 1500, "shop bijli bill"), why="Shop expense"),
    dict(id="STK-D-06", category="D", hinglish="Suresh Traders shop se 30 fatte le gaye 4500 mein, paise baad mein",
         english="Suresh Traders took 30 planks from the shop for 4500, payment later", outcome="ENTRY",
         roles=R(suresh_traders=C),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Suresh Traders", item_name="fatta", quantity=30, amount=4500, date="T"))],
         why="Credit sale from shop"),
    dict(id="STK-D-07", category="D", hinglish="Papa gudam ke galle se 2000 le gaye ghar ke liye",
         english="Papa took 2000 from the warehouse till for home", outcome="ENTRY", roles=R(papa=F),
         expected=[dict(role=F, tool=FAM, args=dict(member_name="Papa", transaction_type="kharcha", amount=2000, date="T"))],
         why="Family kharcha — gudam is only the till's place"),
    dict(id="STK-D-08", category="D", hinglish="Gupta ji ka purana makaan 2 lakh mein liya, maal baad mein gudam aayega",
         english="Bought Gupta ji's old house for 2 lakh, the material will come to the warehouse later", outcome="ENTRY",
         roles=R(gupta_ji=P, गुप्ता=P),
         expected=[dict(role=P, tool=PUR, args=dict(seller_name="Gupta ji", total_amount=200000, date="T"))],
         why="Purchase; future material must not become a movement"),
    dict(id="STK-D-09", category="D", hinglish="Kitanu ne gudam saaf kiya, 400 usko de diye",
         english="Kitanu cleaned the warehouse, gave him 400", outcome="ENTRY", roles=R(kitanu=E),
         expected=[dict(role=E, tool=EMP_TXN, args=dict(employee_name="Kitanu", transaction_type="payment", amount=400, date="T"))],
         why="Employee payment"),
    dict(id="STK-D-10", category="D", hinglish="Shop ka shutter theek karwaya 900 mein",
         english="Got the shop shutter repaired for 900", outcome="ENTRY", roles={},
         expected=X("repair", 900, "shop shutter"), why="Repair expense, not work log"),

    # =====================================================================  E — MIXED
    dict(id="STK-E-01", category="E", hinglish="500 eent gudam se dukaan bheji, 20 dukaan pahunch ke tooti nikli",
         english="Sent 500 bricks from the warehouse to the shop, 20 turned out broken on reaching the shop",
         outcome="ENTRY", roles={},
         expected=M("eent", 500, "gudam", "shop") + A("shop", "eent", -20), why="Movement + damage at destination"),
    dict(id="STK-E-02", category="E", hinglish="Shop se 10 kadiyan gudam bheji, Kitanu ko 300 bhaada diya",
         english="Sent 10 beams from the shop to the warehouse, paid Kitanu 300 freight", outcome="ENTRY",
         roles=R(kitanu=E),
         expected=M("kadi", 10, "shop", "gudam")
                  + [dict(role=E, tool=EMP_TXN, args=dict(employee_name="Kitanu", transaction_type="payment", amount=300, date="T"))],
         why="Movement + employee payment"),
    dict(id="STK-E-03", category="E", hinglish="Gudam mein 4 labour ne maal sambhala, aur 6 darwaze kam nikle",
         english="4 labourers handled the goods in the warehouse, and 6 doors were short", outcome="ENTRY", roles={},
         expected=W("gudam", "maal sambhala", labour_count=4) + A("gudam", "darwaza", -6), why="Work log + adjustment"),
    dict(id="STK-E-04", category="E", hinglish="Model Town site pe kaam chala, wahan se 1500 eent gudam aayi",
         english="Work went on at the Model Town site, 1500 bricks came from there to the warehouse", outcome="ENTRY",
         roles=MT,
         expected=W("site", "kaam chala", location_name="Model Town") + M("eent", 1500, "Model Town", "gudam"),
         why="Work log + site → gudam"),
    dict(id="STK-E-05", category="E", hinglish="Gudam se 100 eent Sharma ji ko 900 mein gayi aur 200 shop pe",
         english="100 bricks went from the warehouse to Sharma ji for 900 and 200 to the shop", outcome="ENTRY",
         roles=R(sharma_ji=C),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Sharma ji", item_name="eent", quantity=100, amount=900, date="T"))]
                  + M("eent", 200, "gudam", "shop"),
         why="Sale + movement from the same source"),
    dict(id="STK-E-06", category="E", hinglish="Shop pe 8 khidkiyan tooti mili, aur gudam ka kiraya 5000 diya",
         english="Found 8 windows broken at the shop, and paid the warehouse rent of 5000", outcome="ENTRY", roles={},
         expected=A("shop", "khidki", -8) + X("rent", 5000, "gudam kiraya"), why="Adjustment + expense"),
    dict(id="STK-E-07", category="E", hinglish="Kal gudam se 50 fatte shop gaye, aaj shop pe 5 kam nikle",
         english="Yesterday 50 planks went from the warehouse to the shop, today 5 were short at the shop", outcome="ENTRY",
         roles={},
         expected=M("fatta", 50, "gudam", "shop", date="T-1") + A("shop", "fatta", -5),
         why="Two dates, movement + adjustment at destination"),
    dict(id="STK-E-08", category="E", hinglish="SBI wali 2000 eent aaj gudam aayi, unme 100 tooti nikli",
         english="The 2000 bricks from SBI came to the warehouse today, 100 of them were broken", outcome="ENTRY",
         roles=R(sbi=S, sbi_bhatta=S),
         expected=[dict(role=S, tool=STX, args=dict(supplier_name="SBI Bhatta", item_name="eent", quantity=2000, date="T"))]
                  + A("gudam", "eent", -100),
         why="Supplier purchase + damage"),
    dict(id="STK-E-09", category="E", hinglish="Sohan aaj gudam pe tha, 30 bori cement dukaan pahunchayi",
         english="Sohan was at the warehouse today, delivered 30 bags of cement to the shop", outcome="ENTRY",
         roles=R(sohan=E),
         expected=[dict(role=E, tool=ATT, args=dict(employee_name="Sohan", attendance="P", date="T"))]
                  + M("cement", 30, "gudam", "shop"),
         why="Attendance + movement"),
    dict(id="STK-E-10", category="E", hinglish="Gudam mein 15 bori cement zyada mili aur 10 chaukhat shop bhej di",
         english="Found 15 extra bags of cement in the warehouse and sent 10 door frames to the shop", outcome="ENTRY",
         roles={},
         expected=A("gudam", "cement", 15) + M("chaukhat", 10, "gudam", "shop"), why="Adjustment + movement"),
]

CATEGORY_LABELS = {"A": "A - Daily", "B": "B - Tricky", "C": "C - Edge", "D": "D - Other business", "E": "E - Mixed"}

HINDI = {
    "STK-A-01": "दुकान पे 40 फट्टे गोदाम से आए",
    "STK-A-02": "6 खिड़कियां दुकान पे रखवाईं, गोदाम वाली",
    "STK-A-03": "दुकान की 10 कड़ियां गोदाम पहुंचीं",
    "STK-A-04": "गोदाम में 25 ईंट टूटी मिलीं",
    "STK-A-05": "दुकान पे 2 चौखट कम हैं",
    "STK-A-06": "गोदाम में 5 दरवाज़े ज़्यादा निकले",
    "STK-A-07": "गोदाम में दो मज़दूरों ने सारा माल सेट किया आज",
    "STK-A-08": "दुकान पे आज रंग-रोगन का काम हुआ",
    "STK-A-09": "कल दुकान के लिए 100 ईंट निकालीं गोदाम से",
    "STK-A-10": "गोदाम में 3 गेट जंग लगने से बेकार हो गए",
    "STK-B-01": "सुबह ट्रैक्टर में 300 ईंट भर के दुकान पहुंचा दीं गोदाम वाली",
    "STK-B-02": "दुकान से 20 कड़ियां वापस गोदाम में रखवा दीं",
    "STK-B-03": "गोदाम में 50 ईंट टूट गईं आज उतारते वक्त",
    "STK-B-04": "दुकान पे गिनती की तो 4 दरवाज़े कम निकले",
    "STK-B-05": "आज गोदाम की सफाई करवाई, 3 लेबर लगे थे",
    "STK-B-06": "मॉडल टाउन वाली साइट पे आज पिछली दीवार तोड़ी",
    "STK-B-07": "गोदाम में गिनती करते वक्त 10 बोरी सीमेंट ज़्यादा मिली",
    "STK-B-08": "मॉडल टाउन के काम से ट्रैक्टर 2000 ईंट लाया, सब गोदाम में खाली कर दीं",
    "STK-B-09": "कल दुकान से 15 फट्टे गोदाम भेज दिए थे",
    "STK-B-10": "बारिश में गोदाम की 5 खिड़कियां खराब हो गईं",
    "STK-C-01": "कुछ ईंट दुकान पे पहुंची हैं गोदाम से, गिनती याद नहीं",
    "STK-C-02": "दुकान पे अभी कितनी ईंट पड़ी हैं?",
    "STK-C-03": "कल 200 ईंट गोदाम से दुकान भेजनी है",
    "STK-C-04": "गोदाम की टूटी ईंट 30 लिखना, नहीं नहीं 40 थीं",
    "STK-C-05": "दुकान पे ढाई सौ ईंट गोदाम से आ गईं",
    "STK-C-06": "गोदाम में 2 टन लोहा कम निकला",
    "STK-C-07": "दुकन पर गोदम से 12 कड़ी आई",
    "STK-C-08": "गोदाम में सब ठीक था, गिनती बराबर निकली",
    "STK-C-09": "गोदाम का थोड़ा माल दुकान पे ले गए",
    "STK-C-10": "परसों मॉडल टाउन साइट पे काम नहीं हुआ, बारिश थी",
    "STK-D-01": "शर्मा जी की साइट पे गोदाम वाली 200 ईंट गईं, 1600 तय हुए",
    "STK-D-02": "एसबीआई की गाड़ी आई, 3000 ईंट सीधा गोदाम में खाली, बिल 18000 का",
    "STK-D-03": "गोदाम के मालिक को इस महीने का 5000 किराया पकड़ा दिया",
    "STK-D-04": "सोहन सुबह से गोदाम पे है, प्रेज़ेंट लिख लो",
    "STK-D-05": "दुकान का 1500 का बिजली बिल भरा",
    "STK-D-06": "सुरेश ट्रेडर्स दुकान से 30 फट्टे ले गए 4500 में, पैसे बाद में",
    "STK-D-07": "पापा गोदाम के गल्ले से 2000 ले गए घर के लिए",
    "STK-D-08": "गुप्ता जी का पुराना मकान 2 लाख में लिया, माल बाद में गोदाम आएगा",
    "STK-D-09": "कितनू ने गोदाम साफ किया, 400 उसको दे दिए",
    "STK-D-10": "दुकान का शटर ठीक करवाया 900 में",
    "STK-E-01": "500 ईंट गोदाम से दुकान भेजीं, 20 दुकान पहुंच के टूटी निकलीं",
    "STK-E-02": "दुकान से 10 कड़ियां गोदाम भेजीं, कितनू को 300 भाड़ा दिया",
    "STK-E-03": "गोदाम में 4 लेबर ने माल संभाला, और 6 दरवाज़े कम निकले",
    "STK-E-04": "मॉडल टाउन साइट पे काम चला, वहां से 1500 ईंट गोदाम आईं",
    "STK-E-05": "गोदाम से 100 ईंट शर्मा जी को 900 में गईं और 200 दुकान पे",
    "STK-E-06": "दुकान पे 8 खिड़कियां टूटी मिलीं, और गोदाम का किराया 5000 दिया",
    "STK-E-07": "कल गोदाम से 50 फट्टे दुकान गए, आज दुकान पे 5 कम निकले",
    "STK-E-08": "एसबीआई वाली 2000 ईंट आज गोदाम आईं, उनमें 100 टूटी निकलीं",
    "STK-E-09": "सोहन आज गोदाम पे था, 30 बोरी सीमेंट दुकान पहुंचाई",
    "STK-E-10": "गोदाम में 15 बोरी सीमेंट ज़्यादा मिली और 10 चौखट दुकान भेज दीं",
}

ENGLISH_INPUT = {t["id"]: t["english"] for t in TESTCASES}

for _t in TESTCASES:
    _t["hindi"] = HINDI[_t["id"]]
    _t["english_input"] = ENGLISH_INPUT[_t["id"]]
assert set(HINDI) == set(ENGLISH_INPUT) == {t["id"] for t in TESTCASES}
assert len(TESTCASES) == 50
