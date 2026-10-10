# test/testcases/exp_testcases.py — Kharcha (Expense) bundle, test set v1 (LOCKED 2026-10-06).
#
# Har test case:
#   id        : EXP-<category>-<no>
#   category  : A Daily | B Tricky | C Edge | D Other business | E Mixed
#   hinglish  : statement jo system ko diya jayega
#   english   : professors ke liye anuvaad
#   outcome   : ENTRY | ASK | NO-ENTRY   (kya hona CHAHIYE)
#   roles     : beech mein role ka sawaal aaye to runner kya jawaab de {naam: role}
#   expected  : har expected entry — role, tool, key arguments
#               date: "T" = test ka din, "T-1" = ek din pehle
#   ask       : (ASK ke liye) kya poochna chahiye tha
#   why       : ye test kyun hai
#
# Kharche ka model: record_expense = kharcha / bill (category + description + amount),
# record_expense_payment = paisa diya (CashLedger). "kharcha kiya / diya / lage" = DONO;
# sirf "bill aaya, abhi nahi diya" = sirf expense; purane kharche ka paisa aaj = sirf payment.
# Category sirf 5: fuel, repair, rent, salary, misc (bijli, chai, recharge, bhaada → misc).
#
# Statements user (Sahil) ke saath tay kiye; har statement prompt ke saare examples aur
# pichhle bundles ke test statements se milaaya gaya (difflib ≤ 0.69).
#
# Seed (test/seed_data.py): employees Ram, Sohan, Kitanu; customer Sharma ji; family Papa.
# Baaki naam (Gupta ji, Verma ji, Om bhatta, Mahadev, Lucky) naye hain.
#
# Is file ke statements aur expected jawaab LOCKED hain (v1). Badlaav = naya version.

BUNDLE = "Expense"
PREFIX = "EXP"

S, C, E, F = "Supplier", "Customer", "Employee", "Family Member"
EXP = "record_expense"
EPAY = "record_expense_payment"
FAM = "record_family_transaction"
STX = "record_supplier_transaction"
SPAY = "record_supplier_payment"
SALE = "record_sale_transaction"
CPAY = "record_sale_payment"
EMP_TXN = "record_employee_transaction"
ATT = "record_attendance"


def R(**kw):
    """roles: R(gupta_ji=C, गुप्ता=C) → {"gupta ji": "Customer", "गुप्ता": "Customer"}"""
    return {k.replace("_", " "): v for k, v in kw.items()}


def X(category, amount, desc, date="T", **extra):
    """kharcha + uski payment (dono)"""
    return [dict(role=None, tool=EXP, args=dict(category=category, amount=amount, description=desc, date=date, **extra)),
            dict(role=None, tool=EPAY, args=dict(amount=amount, date=date))]


TESTCASES = [
    # =====================================================================  A — DAILY
    dict(id="EXP-A-01", category="A", hinglish="Tractor ki tanki full karwayi, 3200 ka diesel",
         english="Filled the tractor's tank, diesel for 3200", outcome="ENTRY", roles={},
         expected=X("fuel", 3200, "tractor diesel"), why="Daily fuel expense, paid"),
    dict(id="EXP-A-02", category="A", hinglish="Bijli ka bill aaya 1850 ka, PhonePe se bhar diya",
         english="Electricity bill of 1850 came, paid it by PhonePe", outcome="ENTRY", roles={},
         expected=X("misc", 1850, "bijli bill", payment_method="upi"), why="Utility bill → misc, UPI"),
    dict(id="EXP-A-03", category="A", hinglish="Shop ka is mahine ka kiraya 6000 de diya",
         english="Paid this month's shop rent, 6000", outcome="ENTRY", roles={},
         expected=X("rent", 6000, "shop kiraya"), why="Rent"),
    dict(id="EXP-A-04", category="A", hinglish="Dumper ka tyre puncture tha, 250 lage",
         english="The dumper had a flat tyre, it cost 250", outcome="ENTRY", roles={},
         expected=X("repair", 250, "dumper tyre puncture"), why="Small repair"),
    dict(id="EXP-A-05", category="A", hinglish="Mazdooron ke liye chai-nashta 180 ka aaya",
         english="Tea and snacks for the labourers cost 180", outcome="ENTRY", roles={},
         expected=X("misc", 180, "chai-nashta"), why="'180 ka aaya' = spent 180 (decided with the user)"),
    dict(id="EXP-A-06", category="A", hinglish="Kal JCB ka engine oil badalwaya, 4500 lage",
         english="Yesterday got the JCB's engine oil changed, it cost 4500", outcome="ENTRY", roles={},
         expected=X("repair", 4500, "JCB engine oil", date="T-1"), why="Repair, yesterday"),
    dict(id="EXP-A-07", category="A", hinglish="Gudam ke liye naya taala aur chain 650 ki li",
         english="Bought a new lock and chain for the warehouse for 650", outcome="ENTRY", roles={},
         expected=X("misc", 650, "taala chain"), why="Goods bought for own use — expense, NOT a supplier purchase"),
    dict(id="EXP-A-08", category="A", hinglish="Motorcycle ki tanki mein 500 ka petrol bharwaya",
         english="Filled 500 worth of petrol in the motorcycle", outcome="ENTRY", roles={},
         expected=X("fuel", 500, "motorcycle petrol"), why="Fuel"),
    dict(id="EXP-A-09", category="A", hinglish="Gudam wale phone ka 299 ka recharge karaya",
         english="Recharged the warehouse phone for 299", outcome="ENTRY", roles={},
         expected=X("misc", 299, "phone recharge"), why="Misc"),
    dict(id="EXP-A-10", category="A", hinglish="Tractor ka hydraulic theek karwaya, 1400 cash diye",
         english="Got the tractor's hydraulics fixed, paid 1400 cash", outcome="ENTRY", roles={},
         expected=X("repair", 1400, "tractor hydraulic", payment_method="cash"), why="Repair, cash"),

    # =====================================================================  B — TRICKY
    dict(id="EXP-B-01", category="B", hinglish="Lucky mechanic se tractor ka clutch theek karwaya, 1800 lage",
         english="Got the tractor's clutch fixed by Lucky the mechanic, it cost 1800", outcome="ENTRY", roles={},
         expected=X("repair", 1800, "tractor clutch"),
         why="A named mechanic is NOT an employee or supplier — expense, name in note (decided with the user)"),
    dict(id="EXP-B-02", category="B", hinglish="Generator ka 2400 ka bill aaya hai, abhi diya nahi",
         english="The generator bill of 2400 has come, not paid yet", outcome="ENTRY", roles={},
         expected=[dict(role=None, tool=EXP, args=dict(category="repair", amount=2400, description="generator bill", date="T"))],
         why="Bill came but not paid — expense only, NO payment"),
    dict(id="EXP-B-03", category="B", hinglish="Pichle hafte wali servicing ke 3000 baaki the, aaj de diye",
         english="3000 was pending for last week's servicing, paid it today", outcome="ENTRY", roles={},
         expected=[dict(role=None, tool=EPAY, args=dict(amount=3000, date="T"))],
         why="Old expense paid today — payment only, NO new expense"),
    dict(id="EXP-B-04", category="B", hinglish="Diesel 95 rupaye litre, 40 litre dalwaya tractor mein",
         english="Diesel at 95 a litre, put 40 litres in the tractor", outcome="ENTRY", roles={},
         expected=X("fuel", 3800, "tractor diesel"), why="Rate × quantity = 3800"),
    dict(id="EXP-B-05", category="B", hinglish="Bijli ka bill 2100 aaya, aadha abhi bhara baaki agle mahine",
         english="Electricity bill of 2100 came, paid half now, the rest next month", outcome="ENTRY", roles={},
         expected=[dict(role=None, tool=EXP, args=dict(category="misc", amount=2100, description="bijli bill", date="T")),
                   dict(role=None, tool=EPAY, args=dict(amount=1050, date="T"))],
         why="Full bill as expense, half (1050) paid now"),
    dict(id="EXP-B-06", category="B", hinglish="Truck ka bhaada 2500 diya, maal Rewari se aaya tha",
         english="Paid 2500 truck freight, the goods came from Rewari", outcome="ENTRY", roles={},
         expected=X("misc", 2500, "truck bhaada"),
         why="Freight is an expense — NOT a supplier entry even though 'maal aaya'"),
    dict(id="EXP-B-07", category="B", hinglish="₹450 ka tel daala, tractor wala",
         english="Put in 450 rupees of fuel, the tractor", outcome="ENTRY", roles={},
         expected=X("fuel", 450, "tractor tel"), why="Short spoken sentence, amount first"),
    dict(id="EXP-B-08", category="B", hinglish="Machine theek karwane mein dedh hazaar lag gaye",
         english="It took one and a half thousand to get the machine fixed", outcome="ENTRY", roles={},
         expected=X("repair", 1500, "machine"), why="Amount in words (dedh hazaar = 1500)"),
    dict(id="EXP-B-09", category="B", hinglish="JCB mein 3500 aur dono tractoron mein milake 2000 ka diesel gaya",
         english="3500 of diesel went into the JCB and 2000 into both tractors together", outcome="ENTRY", roles={},
         expected=X("fuel", 3500, "JCB diesel") + X("fuel", 2000, "tractor diesel"),
         why="Two expenses in one sentence"),
    dict(id="EXP-B-10", category="B", hinglish="Site pe paani ka tanker mangwaya, 800 GPay kiye",
         english="Ordered a water tanker at the site, paid 800 by GPay", outcome="ENTRY", roles={},
         expected=X("misc", 800, "paani tanker", payment_method="upi"), why="Misc, UPI"),

    # =====================================================================  C — EDGE
    dict(id="EXP-C-01", category="C", hinglish="Diesel dalwaya aaj tractor mein",
         english="Put diesel in the tractor today", outcome="ASK", roles={},
         expected=[], ask="How much?", why="No amount — must ask, not guess"),
    dict(id="EXP-C-02", category="C", hinglish="Agle hafte JCB ka engine khulwana hai, 2000 lagenge",
         english="Next week the JCB engine has to be opened, it will cost 2000", outcome="NO-ENTRY", roles={},
         expected=[], why="Future plan — nothing happened yet"),
    dict(id="EXP-C-03", category="C", hinglish="1200 ka kharcha hua aaj",
         english="There was an expense of 1200 today", outcome="ASK", roles={},
         expected=[], ask="What was it for?", why="No description / category — must ask"),
    dict(id="EXP-C-04", category="C", hinglish="Tractor ki servicing 2500 mein karwayi, nahi nahi 2800 lage",
         english="Got the tractor serviced for 2500, no no, it cost 2800", outcome="ENTRY", roles={},
         expected=X("repair", 2800, "tractor servicing"), why="Self-correction — exactly ONE expense of 2800"),
    dict(id="EXP-C-05", category="C", hinglish="Is mahine diesel pe kitna kharch hua?",
         english="How much was spent on diesel this month?", outcome="NO-ENTRY", roles={},
         expected=[], why="A question (report), not an entry"),
    dict(id="EXP-C-06", category="C", hinglish="Kal petrol ke 300 likhwaye the, wo galat the, 350 the",
         english="Yesterday I recorded 300 for petrol, that was wrong, it was 350", outcome="ASK", roles={},
         expected=[], ask="Correction of yesterday's entry", why="Correction of an old entry — no new entry"),
    dict(id="EXP-C-07", category="C", hinglish="Dukaan ka kiraya is baar abhi nahi diya",
         english="Haven't paid the shop rent this time yet", outcome="NO-ENTRY", roles={},
         expected=[], why="Negation — nothing happened"),
    dict(id="EXP-C-08", category="C", hinglish="Mistri ne generator dekh liya, paise baad mein denge",
         english="The mechanic checked the generator, will pay later", outcome="ASK", roles={},
         expected=[], ask="How much?", why="Work done but no amount and not paid — ask, do not guess"),
    dict(id="EXP-C-09", category="C", hinglish="Diesel 3000",
         english="Diesel 3000", outcome="ENTRY", roles={},
         expected=X("fuel", 3000, "diesel"), why="Shortest possible statement"),
    dict(id="EXP-C-10", category="C", hinglish="Ghar ki bijli ka bill 1600 bhara",
         english="Paid the home electricity bill, 1600", outcome="ENTRY", roles={},
         expected=[dict(role=None, tool=FAM, args=dict(member_name="Ghar", transaction_type="kharcha", amount=1600, date="T"))],
         why="HOME bill = family expense, not a business expense"),

    # =====================================================================  D — OTHER BUSINESS
    dict(id="EXP-D-01", category="D", hinglish="Kirana dukaan ke liye packing ki thailiyan 350 ki li",
         english="Bought packing bags for the grocery shop for 350", outcome="ENTRY", roles={},
         expected=X("misc", 350, "packing thailiyan"), why="Shop supplies — expense, NOT stock from a supplier"),
    dict(id="EXP-D-02", category="D", hinglish="Dairy ka freezer theek karwaya electrician se, 2200 lage",
         english="Got the dairy's freezer fixed by an electrician, it cost 2200", outcome="ENTRY", roles={},
         expected=X("repair", 2200, "freezer"), why="Repair"),
    dict(id="EXP-D-03", category="D", hinglish="Hardware shop ka mahine ka kiraya 9000, cheque se diya",
         english="Hardware shop's monthly rent 9000, paid by cheque", outcome="ENTRY", roles={},
         expected=X("rent", 9000, "shop kiraya", payment_method="cheque"), why="Rent, cheque"),
    dict(id="EXP-D-04", category="D", hinglish="Dhaba ka gas cylinder bharwaya 1100 mein",
         english="Got the dhaba's gas cylinder refilled for 1100", outcome="ENTRY", roles={},
         expected=X("fuel", 1100, "gas cylinder"), why="Cooking gas = fuel"),
    dict(id="EXP-D-05", category="D", hinglish="Silai machine ki sui aur tel 120 ka aaya, tailor shop ke liye",
         english="Needles and oil for the sewing machine cost 120, for the tailor shop", outcome="ENTRY", roles={},
         expected=X("misc", 120, "sui tel"), why="Small supplies"),
    dict(id="EXP-D-06", category="D", hinglish="Mobile shop ka WiFi bill 799 bank account se kat gaya",
         english="The mobile shop's WiFi bill of 799 was debited from the bank account", outcome="ENTRY", roles={},
         expected=X("misc", 799, "wifi bill"), why="Auto-debit"),
    dict(id="EXP-D-07", category="D", hinglish="Medical store ke AC mein gas bharwayi, 2800 lage",
         english="Got gas refilled in the medical store's AC, it cost 2800", outcome="ENTRY", roles={},
         expected=X("repair", 2800, "AC gas"), why="AC gas refill = repair, NOT fuel"),
    dict(id="EXP-D-08", category="D", hinglish="Dairy ki delivery van mein 1500 ki CNG dalwayi",
         english="Put 1500 of CNG in the dairy's delivery van", outcome="ENTRY", roles={},
         expected=X("fuel", 1500, "van CNG"), why="Fuel"),
    dict(id="EXP-D-09", category="D", hinglish="Kirana ki dukaan ke bahar naya board banwaya 1800 ka",
         english="Got a new board made outside the grocery shop for 1800", outcome="ENTRY", roles={},
         expected=X("misc", 1800, "board"), why="Misc"),
    dict(id="EXP-D-10", category="D", hinglish="Chai ki dukaan ka bijli meter kharab tha, lineman ko 500 diye",
         english="The tea shop's electricity meter was faulty, paid the lineman 500", outcome="ENTRY", roles={},
         expected=X("repair", 500, "bijli meter"), why="'lineman ko diye' is not an employee — expense"),

    # =====================================================================  E — MIXED
    dict(id="EXP-E-01", category="E", hinglish="Ram ko 800 de diye, saath mein dumper ki tanki 1500 se bharwayi",
         english="Gave Ram 800, and also filled the dumper's tank for 1500", outcome="ENTRY", roles=R(ram=E),
         expected=[dict(role=E, tool=EMP_TXN, args=dict(employee_name="Ram", transaction_type="payment", amount=800, date="T"))]
                  + X("fuel", 1500, "dumper diesel"),
         why="Employee payment + fuel"),
    dict(id="EXP-E-02", category="E", hinglish="Gupta ji ne 5000 jama karaye aur dukaan ka 2000 kiraya chuka diya",
         english="Gupta ji deposited 5000 and I paid the shop rent of 2000", outcome="ENTRY",
         roles=R(gupta_ji=C, gupta=C, गुप्ता=C),
         expected=[dict(role=C, tool=CPAY, args=dict(customer_name="Gupta ji", amount=5000, date="T"))]
                  + X("rent", 2000, "dukaan kiraya"),
         why="Customer payment + rent"),
    dict(id="EXP-E-03", category="E", hinglish="Om bhatte wali 2000 eent 14000 mein aayi, upar se truck wale ne 1500 bhaada liya",
         english="2000 bricks from Om kiln came for 14000, and the truck driver took 1500 freight on top", outcome="ENTRY",
         roles=R(om=S, ओम=S),
         expected=[dict(role=S, tool=STX, args=dict(supplier_name="Om", item_name="eent", quantity=2000, amount=14000, date="T"))]
                  + X("misc", 1500, "truck bhaada"),
         why="Supplier purchase + freight as a separate expense"),
    dict(id="EXP-E-04", category="E", hinglish="Papa ne ghar ke liye 3000 liye aur generator ki marammat 1200 mein hui",
         english="Papa took 3000 for the house and the generator repair cost 1200", outcome="ENTRY", roles=R(papa=F),
         expected=[dict(role=F, tool=FAM, args=dict(member_name="Papa", transaction_type="kharcha", amount=3000, date="T"))]
                  + X("repair", 1200, "generator"),
         why="Family + repair"),
    dict(id="EXP-E-05", category="E", hinglish="Aaj Sohan ki haazri lagao, aur dukaan ki safai ka saamaan 250 ka laaye",
         english="Mark Sohan present today, and bought cleaning supplies for the shop for 250", outcome="ENTRY", roles=R(sohan=E),
         expected=[dict(role=E, tool=ATT, args=dict(employee_name="Sohan", attendance="P", date="T"))]
                  + X("misc", 250, "safai saamaan"),
         why="Attendance + expense"),
    dict(id="EXP-E-06", category="E", hinglish="Bijli ka bill 2300 bhara, Verma ji 300 eent 2400 mein le gaye",
         english="Paid the electricity bill of 2300, Verma ji took 300 bricks for 2400", outcome="ENTRY",
         roles=R(verma_ji=C, verma=C, वर्मा=C),
         expected=X("misc", 2300, "bijli bill")
                  + [dict(role=C, tool=SALE, args=dict(customer_name="Verma ji", item_name="eent", quantity=300, amount=2400, date="T"))],
         why="Expense + sale"),
    dict(id="EXP-E-07", category="E", hinglish="JCB mein 2500 ka diesel, operator Kitanu ko 600 ki dihaadi di",
         english="2500 of diesel in the JCB, paid operator Kitanu 600 for the day", outcome="ENTRY", roles=R(kitanu=E),
         expected=X("fuel", 2500, "JCB diesel")
                  + [dict(role=E, tool=EMP_TXN, args=dict(employee_name="Kitanu", transaction_type="payment", amount=600, date="T"))],
         why="Fuel + employee daily wage"),
    dict(id="EXP-E-08", category="E", hinglish="Kal dukaan ka kiraya 6000 diya, aaj tractor ka tyre 3500 ka badalwaya",
         english="Paid the shop rent of 6000 yesterday, got the tractor tyre changed today for 3500", outcome="ENTRY", roles={},
         expected=X("rent", 6000, "dukaan kiraya", date="T-1") + X("repair", 3500, "tractor tyre"),
         why="Two expenses on two different dates"),
    dict(id="EXP-E-09", category="E", hinglish="Mahadev reta wale ko 4000 bheje aur gaadi ki service 1800 mein karwayi",
         english="Sent 4000 to Mahadev the sand supplier and got the vehicle serviced for 1800", outcome="ENTRY",
         roles=R(mahadev=S, महादेव=S),
         expected=[dict(role=S, tool=SPAY, args=dict(supplier_name="Mahadev", amount=4000, date="T"))]
                  + X("repair", 1800, "gaadi service"),
         why="Supplier payment + repair"),
    dict(id="EXP-E-10", category="E", hinglish="Chai-pani 200, diesel 2000 aur Ram ko 500 advance",
         english="Tea 200, diesel 2000 and 500 advance to Ram", outcome="ENTRY", roles=R(ram=E),
         expected=X("misc", 200, "chai-pani") + X("fuel", 2000, "diesel")
                  + [dict(role=E, tool=EMP_TXN, args=dict(employee_name="Ram", transaction_type="payment", amount=500, date="T"))],
         why="Three items in very short words"),
]

CATEGORY_LABELS = {"A": "A - Daily", "B": "B - Tricky", "C": "C - Edge", "D": "D - Other business", "E": "E - Mixed"}

# Hindi (Devanagari) — naam Devanagari mein; seed ke naam test/seed_data.py ke HINDI_NAMES se milte hain.
HINDI = {
    "EXP-A-01": "ट्रैक्टर की टंकी फुल करवाई, 3200 का डीज़ल",
    "EXP-A-02": "बिजली का बिल आया 1850 का, फोनपे से भर दिया",
    "EXP-A-03": "दुकान का इस महीने का किराया 6000 दे दिया",
    "EXP-A-04": "डंपर का टायर पंक्चर था, 250 लगे",
    "EXP-A-05": "मज़दूरों के लिए चाय-नाश्ता 180 का आया",
    "EXP-A-06": "कल जेसीबी का इंजन ऑयल बदलवाया, 4500 लगे",
    "EXP-A-07": "गोदाम के लिए नया ताला और चेन 650 की ली",
    "EXP-A-08": "मोटरसाइकिल की टंकी में 500 का पेट्रोल भरवाया",
    "EXP-A-09": "गोदाम वाले फ़ोन का 299 का रिचार्ज कराया",
    "EXP-A-10": "ट्रैक्टर का हाइड्रोलिक ठीक करवाया, 1400 नकद दिए",
    "EXP-B-01": "लकी मैकेनिक से ट्रैक्टर का क्लच ठीक करवाया, 1800 लगे",
    "EXP-B-02": "जनरेटर का 2400 का बिल आया है, अभी दिया नहीं",
    "EXP-B-03": "पिछले हफ्ते वाली सर्विसिंग के 3000 बाकी थे, आज दे दिए",
    "EXP-B-04": "डीज़ल 95 रुपये लीटर, 40 लीटर डलवाया ट्रैक्टर में",
    "EXP-B-05": "बिजली का बिल 2100 आया, आधा अभी भरा बाकी अगले महीने",
    "EXP-B-06": "ट्रक का भाड़ा 2500 दिया, माल रेवाड़ी से आया था",
    "EXP-B-07": "₹450 का तेल डाला, ट्रैक्टर वाला",
    "EXP-B-08": "मशीन ठीक करवाने में डेढ़ हज़ार लग गए",
    "EXP-B-09": "जेसीबी में 3500 और दोनों ट्रैक्टरों में मिलाके 2000 का डीज़ल गया",
    "EXP-B-10": "साइट पे पानी का टैंकर मंगवाया, 800 जीपे किए",
    "EXP-C-01": "डीज़ल डलवाया आज ट्रैक्टर में",
    "EXP-C-02": "अगले हफ्ते जेसीबी का इंजन खुलवाना है, 2000 लगेंगे",
    "EXP-C-03": "1200 का खर्चा हुआ आज",
    "EXP-C-04": "ट्रैक्टर की सर्विसिंग 2500 में करवाई, नहीं नहीं 2800 लगे",
    "EXP-C-05": "इस महीने डीज़ल पे कितना खर्च हुआ?",
    "EXP-C-06": "कल पेट्रोल के 300 लिखवाए थे, वो गलत थे, 350 थे",
    "EXP-C-07": "दुकान का किराया इस बार अभी नहीं दिया",
    "EXP-C-08": "मिस्त्री ने जनरेटर देख लिया, पैसे बाद में देंगे",
    "EXP-C-09": "डीज़ल 3000",
    "EXP-C-10": "घर की बिजली का बिल 1600 भरा",
    "EXP-D-01": "किराना दुकान के लिए पैकिंग की थैलियाँ 350 की लीं",
    "EXP-D-02": "डेयरी का फ्रीज़र ठीक करवाया इलेक्ट्रीशियन से, 2200 लगे",
    "EXP-D-03": "हार्डवेयर शॉप का महीने का किराया 9000, चेक से दिया",
    "EXP-D-04": "ढाबे का गैस सिलेंडर भरवाया 1100 में",
    "EXP-D-05": "सिलाई मशीन की सुई और तेल 120 का आया, टेलर शॉप के लिए",
    "EXP-D-06": "मोबाइल शॉप का वाईफाई बिल 799 बैंक खाते से कट गया",
    "EXP-D-07": "मेडिकल स्टोर के एसी में गैस भरवाई, 2800 लगे",
    "EXP-D-08": "डेयरी की डिलीवरी वैन में 1500 की सीएनजी डलवाई",
    "EXP-D-09": "किराने की दुकान के बाहर नया बोर्ड बनवाया 1800 का",
    "EXP-D-10": "चाय की दुकान का बिजली मीटर खराब था, लाइनमैन को 500 दिए",
    "EXP-E-01": "राम को 800 दे दिए, साथ में डंपर की टंकी 1500 से भरवाई",
    "EXP-E-02": "गुप्ता जी ने 5000 जमा कराए और दुकान का 2000 किराया चुका दिया",
    "EXP-E-03": "ओम भट्टे वाली 2000 ईंट 14000 में आई, ऊपर से ट्रक वाले ने 1500 भाड़ा लिया",
    "EXP-E-04": "पापा ने घर के लिए 3000 लिए और जनरेटर की मरम्मत 1200 में हुई",
    "EXP-E-05": "आज सोहन की हाज़िरी लगाओ, और दुकान की सफाई का सामान 250 का लाए",
    "EXP-E-06": "बिजली का बिल 2300 भरा, वर्मा जी 300 ईंट 2400 में ले गए",
    "EXP-E-07": "जेसीबी में 2500 का डीज़ल, ऑपरेटर कितनू को 600 की दिहाड़ी दी",
    "EXP-E-08": "कल दुकान का किराया 6000 दिया, आज ट्रैक्टर का टायर 3500 का बदलवाया",
    "EXP-E-09": "महादेव रेता वाले को 4000 भेजे और गाड़ी की सर्विस 1800 में करवाई",
    "EXP-E-10": "चाय-पानी 200, डीज़ल 2000 और राम को 500 एडवांस",
}

# English run — same meaning, natural English
ENGLISH_INPUT = {t["id"]: t["english"] for t in TESTCASES}

for _t in TESTCASES:
    _t["hindi"] = HINDI[_t["id"]]
    _t["english_input"] = ENGLISH_INPUT[_t["id"]]
assert set(HINDI) == set(ENGLISH_INPUT) == {t["id"] for t in TESTCASES}
assert len(TESTCASES) == 50
