# test/testcases/fam_testcases.py — Ghar / Family bundle, test set v1 (LOCKED 2026-10-06).
#
# Har test case:
#   id        : FAM-<category>-<no>
#   category  : A Daily | B Tricky | C Edge | D Other business | E Mixed
#   hinglish  : statement jo system ko diya jayega
#   english   : professors ke liye anuvaad
#   outcome   : ENTRY | ASK | NO-ENTRY   (kya hona CHAHIYE)
#   roles     : beech mein role ka sawaal aaye to runner kya jawaab de {naam: role}
#   expected  : har expected entry — role, tool, key arguments
#               date: "T" = test ka din, "T-1" = ek din pehle, "T-2" = parso
#   ask       : (ASK ke liye) kya poochna chahiye tha
#   why       : ye test kyun hai
#
# Family ka model: record_family_transaction (galle ke nazariye se)
#   kharcha = paisa galle se ghar / family ko gaya (cash OUT)
#   jama    = family member ne galle mein paisa daala / lautaya (cash IN)
# Bina naam wala ghar ka kharcha ("ghar ka ration", "shagun") → member_name = "Ghar".
#
# Statements user (Sahil) ke saath tay kiye; har statement prompt ke saare examples aur
# pichhle bundles ke test statements se milaaya gaya (difflib ≤ 0.69).
#
# Seed (test/seed_data.py): employees Ram, Sohan, Kitanu; customers Suresh Traders, Sharma ji;
# supplier SBI Bhatta; family Papa. Mummy, Bhai, Beta, Beti, Rohit, Chhote, Gupta ji naye hain.
#
# Is file ke statements aur expected jawaab LOCKED hain (v1). Badlaav = naya version.

BUNDLE = "Family"
PREFIX = "FAM"

S, C, E, F, P = "Supplier", "Customer", "Employee", "Family Member", "Property / Site Owner"
FAM = "record_family_transaction"
EXP = "record_expense"
EPAY = "record_expense_payment"
STX = "record_supplier_transaction"
SPAY = "record_supplier_payment"
SALE = "record_sale_transaction"
CPAY = "record_sale_payment"
EMP_TXN = "record_employee_transaction"
ATT = "record_attendance"
MOV = "record_material_movement"
PUR = "record_purchase"


def R(**kw):
    """roles: R(mummy=F, मम्मी=F) → {"mummy": "Family Member", "मम्मी": "Family Member"}"""
    return {k.replace("_", " "): v for k, v in kw.items()}


def K(member, amount, date="T", role=F, **extra):
    """family kharcha (paisa galle se bahar)"""
    return [dict(role=None if member == "Ghar" else role, tool=FAM,
                 args=dict(member_name=member, transaction_type="kharcha", amount=amount, date=date, **extra))]


def J(member, amount, date="T", role=F, **extra):
    """family jama (paisa galle mein aaya)"""
    return [dict(role=role, tool=FAM,
                 args=dict(member_name=member, transaction_type="jama", amount=amount, date=date, **extra))]


def X(category, amount, desc, date="T", **extra):
    """dukaan ka kharcha + uski payment (dono)"""
    return [dict(role=None, tool=EXP, args=dict(category=category, amount=amount, description=desc, date=date, **extra)),
            dict(role=None, tool=EPAY, args=dict(amount=amount, date=date))]


def EP(name, amount, date="T"):
    return [dict(role=E, tool=EMP_TXN, args=dict(employee_name=name, transaction_type="payment", amount=amount, date=date))]


MUMMY = R(mummy=F, मम्मी=F)

TESTCASES = [
    # =====================================================================  A — DAILY
    dict(id="FAM-A-01", category="A", hinglish="Mummy ko sabzi ke liye 500 de diye galle se",
         english="Gave Mummy 500 from the till for vegetables", outcome="ENTRY", roles=MUMMY,
         expected=K("Mummy", 500, purpose="sabzi"), why="Daily family kharcha, new member"),
    dict(id="FAM-A-02", category="A", hinglish="Papa 2000 le gaye ghar ke kharche ke liye",
         english="Papa took 2000 for household expenses", outcome="ENTRY", roles=R(papa=F),
         expected=K("Papa", 2000), why="Seed member takes money → kharcha"),
    dict(id="FAM-A-03", category="A", hinglish="Chhote bhai Rohit ki tuition fees 3500 bhar di",
         english="Paid younger brother Rohit's tuition fees, 3500", outcome="ENTRY", roles=R(rohit=F, रोहित=F),
         expected=K("Rohit", 3500, purpose="tuition fees", relation="bhai"), why="Name + relation"),
    dict(id="FAM-A-04", category="A", hinglish="Ghar ka gas cylinder aaya 1100 ka, paise galle se diye",
         english="The home's gas cylinder came for 1100, paid from the till", outcome="ENTRY", roles={},
         expected=K("Ghar", 1100, purpose="gas cylinder"), why="Home spending, no person → Ghar, not record_expense"),
    dict(id="FAM-A-05", category="A", hinglish="Beti ki school van ke 1200 diye aaj",
         english="Paid 1200 for my daughter's school van today", outcome="ENTRY", roles=R(beti=F, बेटी=F),
         expected=K("Beti", 1200, purpose="school van"), why="Relation word as member"),
    dict(id="FAM-A-06", category="A", hinglish="Papa ne dukaan ke galle mein 10000 daal diye",
         english="Papa put 10000 into the shop's till", outcome="ENTRY", roles=R(papa=F),
         expected=J("Papa", 10000), why="Money IN from family → jama"),
    dict(id="FAM-A-07", category="A", hinglish="Mummy ki dawai 650 ki aayi, paise dukaan se gaye",
         english="Mummy's medicine cost 650, the money went from the shop", outcome="ENTRY", roles=MUMMY,
         expected=K("Mummy", 650, purpose="dawai"), why="Kharcha with 'aayi' verb"),
    dict(id="FAM-A-08", category="A", hinglish="Bhai jo udhaar le gaya tha, uske 3000 aaj wapas aa gaye galle mein",
         english="The 3000 my brother had borrowed came back into the till today", outcome="ENTRY",
         roles=R(bhai=F, भाई=F),
         expected=J("Bhai", 3000), why="'le gaya tha' is past — today's money is IN → jama"),
    dict(id="FAM-A-09", category="A", hinglish="Kal ghar ka ration 4200 ka aaya, galle se diya",
         english="Yesterday the home groceries came for 4200, paid from the till", outcome="ENTRY", roles={},
         expected=K("Ghar", 4200, date="T-1", purpose="ration"), why="Home spending, yesterday"),
    dict(id="FAM-A-10", category="A", hinglish="Mandir mein daan dena tha, Papa galle se 1100 nikal ke le gaye",
         english="Had to give a donation at the temple, Papa took 1100 out of the till", outcome="ENTRY",
         roles=R(papa=F),
         expected=K("Papa", 1100, purpose="mandir daan"), why="Purpose before the action"),

    # =====================================================================  B — TRICKY
    dict(id="FAM-B-01", category="B", hinglish="Bhai ne 2000 liye the, aaj usme se 1500 wapas kiye",
         english="My brother had taken 2000, today he returned 1500 of it", outcome="ENTRY", roles=R(bhai=F, भाई=F),
         expected=J("Bhai", 1500), why="Two amounts — only today's 1500 back, jama"),
    dict(id="FAM-B-02", category="B", hinglish="Beta bike mein petrol dalwane 300 le gaya",
         english="My son took 300 to fill petrol in his bike", outcome="ENTRY", roles=R(beta=F, बेटा=F),
         expected=K("Beta", 300, purpose="petrol"), why="Petrol looks like fuel expense — it is family"),
    dict(id="FAM-B-03", category="B", hinglish="Ghar ki chhat pe pani ki tanki lagwayi 6500 ki, paise dukaan se",
         english="Got a water tank installed on the house roof for 6500, money from the shop", outcome="ENTRY",
         roles={},
         expected=K("Ghar", 6500, purpose="pani ki tanki"), why="Tank looks like goods — it is home kharcha"),
    dict(id="FAM-B-04", category="B", hinglish="Ghar ke liye 10 bori cement aayi 3800 ki",
         english="10 bags of cement came for the house, 3800", outcome="ENTRY", roles={},
         expected=K("Ghar", 3800, purpose="cement"), why="Cement is trade goods, but for home — no stock / movement"),
    dict(id="FAM-B-05", category="B", hinglish="Mummy ne 5000 diye the business ke liye, aaj wo unko wapas kar diye",
         english="Mummy had given 5000 for the business, today I returned it to her", outcome="ENTRY", roles=MUMMY,
         expected=K("Mummy", 5000), why="'Mummy ne diye the' is past — today money went OUT → kharcha"),
    dict(id="FAM-B-06", category="B", hinglish="Rohit ne apni salary mein se 5000 galle mein daale",
         english="Rohit put 5000 from his salary into the till", outcome="ENTRY", roles=R(rohit=F, रोहित=F),
         expected=J("Rohit", 5000), why="'salary' must not pull it to employee"),
    dict(id="FAM-B-07", category="B", hinglish="Chhote ki fees ke 2500 aur ration ke 1800 diye",
         english="Paid 2500 for the youngest one's fees and 1800 for groceries", outcome="ENTRY",
         roles=R(chhote=F, छोटे=F),
         expected=K("Chhote", 2500, purpose="fees") + K("Ghar", 1800, purpose="ration"),
         why="Two family kharche in one line"),
    dict(id="FAM-B-08", category="B", hinglish="Mummy ne kal 1500 rakhe the galle mein, aaj wahi wapas le gayi",
         english="Mummy had put 1500 in the till yesterday, today she took the same back", outcome="ENTRY",
         roles=MUMMY,
         expected=J("Mummy", 1500, date="T-1") + K("Mummy", 1500),
         why="Two days, two directions"),
    dict(id="FAM-B-09", category="B", hinglish="Shaadi mein shagun dena tha, 2100 galle se nikale",
         english="Had to give a wedding gift, took 2100 out of the till", outcome="ENTRY", roles={},
         expected=K("Ghar", 2100, purpose="shagun"), why="No member named → Ghar"),
    dict(id="FAM-B-10", category="B", hinglish="Papa ke haath galle se 3000 gaye, ghar pe kaam tha",
         english="3000 went from the till through Papa, there was work at home", outcome="ENTRY", roles=R(papa=F),
         expected=K("Papa", 3000), why="Unusual phrasing 'ke haath … gaye'"),

    # =====================================================================  C — EDGE
    dict(id="FAM-C-01", category="C", hinglish="Papa kuch paise le gaye ghar ke liye, kitne bataye nahi",
         english="Papa took some money for home, didn't say how much", outcome="ASK", roles=R(papa=F),
         expected=[], ask="How much?", why="No amount — must ask, not guess"),
    dict(id="FAM-C-02", category="C", hinglish="Ghar ke kharche ke 2000 diye, nahi nahi 2500 the",
         english="Gave 2000 for household expenses, no no, it was 2500", outcome="ENTRY", roles={},
         expected=K("Ghar", 2500), why="Self-correction — exactly ONE entry of 2500"),
    dict(id="FAM-C-03", category="C", hinglish="Shaam ko Papa ne galla gin liya, hisab barabar tha",
         english="In the evening Papa counted the till, the accounts matched", outcome="NO-ENTRY", roles={},
         expected=[], why="No money moved"),
    dict(id="FAM-C-04", category="C", hinglish="Kal Mummy ko 2000 dene hain dawai ke liye",
         english="Have to give Mummy 2000 tomorrow for medicine", outcome="NO-ENTRY", roles={},
         expected=[], why="Future plan — nothing happened yet"),
    dict(id="FAM-C-05", category="C", hinglish="Mummy ko 1.5 hazaar diye sabzi ke liye",
         english="Gave Mummy 1.5 thousand for vegetables", outcome="ENTRY", roles=MUMMY,
         expected=K("Mummy", 1500, purpose="sabzi"), why="'1.5 hazaar' = 1500"),
    dict(id="FAM-C-06", category="C", hinglish="Rohit ki coaching ke paanch hazaar bhar diye",
         english="Paid five thousand for Rohit's coaching", outcome="ENTRY", roles=R(rohit=F, रोहित=F),
         expected=K("Rohit", 5000, purpose="coaching"), why="Number in words"),
    dict(id="FAM-C-07", category="C", hinglish="Ghar ke liye do-dhai hazaar nikale the",
         english="Took out two to two-and-a-half thousand for home", outcome="ASK", roles={},
         expected=[], ask="Exact amount?", why="Range amount — must not pick 2000 or 2500 by itself"),
    dict(id="FAM-C-08", category="C", hinglish="Papa ne subah 2000 liye aur shaam ko 2000 waapas rakh diye",
         english="Papa took 2000 in the morning and put 2000 back in the evening", outcome="ENTRY", roles=R(papa=F),
         expected=K("Papa", 2000) + J("Papa", 2000), why="Same amount, opposite directions — both entries"),
    dict(id="FAM-C-09", category="C", hinglish="Parso Papa 4000 le gaye the bijli ke bill ke liye",
         english="Day before yesterday Papa took 4000 for the electricity bill", outcome="ENTRY", roles=R(papa=F),
         expected=K("Papa", 4000, date="T-2", purpose="bijli bill"),
         why="Parso date; 'bijli bill' looks like an expense but Papa took the money"),
    dict(id="FAM-C-10", category="C", hinglish="mumy ko 700 diye ghr ke liye",
         english="gave mom 700 for home", outcome="ENTRY", roles=R(mumy=F, mummy=F, मम्मी=F),
         expected=K("Mummy", 700), why="Spelling mistakes (mumy, ghr)"),

    # =====================================================================  D — OTHER BUSINESS
    dict(id="FAM-D-01", category="D", hinglish="Gupta ji ka purana makaan todne ke liye 1.5 lakh mein le liya",
         english="Bought Gupta ji's old house for demolition for 1.5 lakh", outcome="ENTRY",
         roles=R(gupta_ji=P, गुप्ता=P),
         expected=[dict(role=P, tool=PUR, args=dict(seller_name="Gupta ji", total_amount=150000, date="T"))],
         why="'makaan' must not go to family — property purchase"),
    dict(id="FAM-D-02", category="D", hinglish="Ram ne Sharma ji ke ghar maal utara, usko 500 diye",
         english="Ram unloaded goods at Sharma ji's house, paid him 500", outcome="ENTRY", roles=R(ram=E),
         expected=EP("Ram", 500), why="'ghar' is a customer's place — employee payment"),
    dict(id="FAM-D-03", category="D", hinglish="Papa ghar pe the, Suresh Traders ka aadmi unko 4000 pakda gaya",
         english="Papa was at home, Suresh Traders' man handed him 4000", outcome="ENTRY",
         roles=R(suresh_traders=C),
         expected=[dict(role=C, tool=CPAY, args=dict(customer_name="Suresh Traders", amount=4000, date="T"))],
         why="Papa only received it — customer payment, not family"),
    dict(id="FAM-D-04", category="D", hinglish="Shop ke meter ka bill aaya 1300, abhi nahi bhara",
         english="The shop's meter bill came, 1300, not paid yet", outcome="ENTRY", roles={},
         expected=[dict(role=None, tool=EXP, args=dict(category="misc", amount=1300, description="shop bijli bill", date="T"))],
         why="Shop expense, unpaid → only expense"),
    dict(id="FAM-D-05", category="D", hinglish="Beta SBI bhatte se 2000 eent le aaya, 12000 dene baaki hain",
         english="My son brought 2000 bricks from SBI kiln, 12000 still to pay", outcome="ENTRY",
         roles=R(sbi_bhatta=S),
         expected=[dict(role=S, tool=STX, args=dict(supplier_name="SBI Bhatta", item_name="eent", quantity=2000, amount=12000, date="T"))],
         why="'Beta' only fetched — supplier purchase, not family"),
    dict(id="FAM-D-06", category="D", hinglish="Mummy ne bola to 2 purani khidkiyan Sharma ji ko 3000 mein bech di, cash le liya",
         english="Mummy said so, so I sold 2 old windows to Sharma ji for 3000, took cash", outcome="ENTRY",
         roles=R(sharma_ji=C),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Sharma ji", item_name="khidki", quantity=2, amount=3000, date="T")),
                   dict(role=C, tool=CPAY, args=dict(customer_name="Sharma ji", amount=3000, date="T"))],
         why="Mummy only advised — sale + payment"),
    dict(id="FAM-D-07", category="D", hinglish="Papa ne Kitanu ko 1000 advance de diya",
         english="Papa gave Kitanu 1000 as advance", outcome="ENTRY", roles=R(kitanu=E),
         expected=EP("Kitanu", 1000), why="Papa is the giver — employee advance, no family entry"),
    dict(id="FAM-D-08", category="D", hinglish="Ghar ka nahi, gudam ka kiraya 8000 diya",
         english="Not the house, paid the warehouse rent of 8000", outcome="ENTRY", roles={},
         expected=X("rent", 8000, "gudam kiraya"), why="Negated 'ghar ka' — shop rent expense"),
    dict(id="FAM-D-09", category="D", hinglish="Bhai gudam se 50 kadiyan Sharma ji ke ghar chhod aaya",
         english="My brother dropped 50 beams from the warehouse at Sharma ji's house", outcome="ASK",
         roles=R(sharma_ji=C),
         expected=[], ask="For how much? (goods to a customer = sale, like CUS-C-02)",
         why="Goods to a customer without price — ask amount; 'Bhai' only carried it (v1.1: user ke saath badla)"),
    dict(id="FAM-D-10", category="D", hinglish="Papa Sohan ki aaj ki hazri laga gaye, pura din tha",
         english="Papa marked Sohan's attendance for today, full day", outcome="ENTRY", roles=R(sohan=E),
         expected=[dict(role=E, tool=ATT, args=dict(employee_name="Sohan", attendance="P", date="T"))],
         why="Attendance — Papa only marked it"),

    # =====================================================================  E — MIXED
    dict(id="FAM-E-01", category="E", hinglish="Papa 3000 le gaye ghar ke liye aur Ram ko 500 dihadi di",
         english="Papa took 3000 for home and paid Ram 500 daily wage", outcome="ENTRY", roles=R(papa=F, ram=E),
         expected=K("Papa", 3000) + EP("Ram", 500), why="Family + employee"),
    dict(id="FAM-E-02", category="E", hinglish="Mummy ko 2000 pakdaye, ye paisa Sharma ji wale 5000 mein se tha jo aaj mile",
         english="Handed Mummy 2000, this was out of the 5000 received from Sharma ji today", outcome="ENTRY",
         roles=R(sharma_ji=C, mummy=F, मम्मी=F),
         expected=[dict(role=C, tool=CPAY, args=dict(customer_name="Sharma ji", amount=5000, date="T"))] + K("Mummy", 2000),
         why="Customer payment + family kharcha, reversed order"),
    dict(id="FAM-E-03", category="E", hinglish="Gudam ka kiraya 6000 aur ghar ka kiraya 4000 diya",
         english="Paid warehouse rent 6000 and house rent 4000", outcome="ENTRY", roles={},
         expected=X("rent", 6000, "gudam kiraya") + K("Ghar", 4000, purpose="kiraya"),
         why="Shop rent vs home rent in one line"),
    dict(id="FAM-E-04", category="E", hinglish="Bhai ne galle mein 10000 daale, usi se SBI bhatte ka 5000 chuka diya",
         english="My brother put 10000 in the till, from that paid SBI kiln 5000", outcome="ENTRY",
         roles=R(bhai=F, भाई=F, sbi_bhatta=S),
         expected=J("Bhai", 10000) + [dict(role=S, tool=SPAY, args=dict(supplier_name="SBI Bhatta", amount=5000, date="T"))],
         why="Family jama + supplier payment"),
    dict(id="FAM-E-05", category="E", hinglish="Kitanu ko 800 diye aur Beti ki fees ke 2200 bhi",
         english="Gave Kitanu 800 and also 2200 for my daughter's fees", outcome="ENTRY",
         roles=R(kitanu=E, beti=F, बेटी=F),
         expected=EP("Kitanu", 800) + K("Beti", 2200, purpose="fees"), why="Employee + family, short second clause"),
    dict(id="FAM-E-06", category="E", hinglish="Tractor mein 600 ka diesel dalwaya aur ghar ki gaadi mein 400 ka petrol",
         english="Put 600 of diesel in the tractor and 400 of petrol in the home car", outcome="ENTRY", roles={},
         expected=X("fuel", 600, "tractor diesel") + K("Ghar", 400, purpose="petrol"),
         why="Business fuel vs home fuel in one line"),
    dict(id="FAM-E-07", category="E", hinglish="Suresh Traders ko 30 fatte 4500 mein diye, aur Papa ne 1000 le liye",
         english="Gave Suresh Traders 30 planks for 4500, and Papa took 1000", outcome="ENTRY",
         roles=R(suresh_traders=C, papa=F),
         expected=[dict(role=C, tool=SALE, args=dict(customer_name="Suresh Traders", item_name="fatta", quantity=30, amount=4500, date="T"))]
                  + K("Papa", 1000),
         why="Sale (unpaid) + family — Papa's 1000 is not a sale payment"),
    dict(id="FAM-E-08", category="E", hinglish="Mummy ne 2000 galle mein daale, usme se Sohan ko 600 dihadi di",
         english="Mummy put 2000 in the till, from it paid Sohan 600 daily wage", outcome="ENTRY",
         roles=R(mummy=F, मम्मी=F, sohan=E),
         expected=J("Mummy", 2000) + EP("Sohan", 600), why="Family jama + employee"),
    dict(id="FAM-E-09", category="E", hinglish="Kal ghar ka ration 3500 ka aaya aur aaj dukaan ka 900 ka bijli bill bhara",
         english="Yesterday home groceries came for 3500 and today paid the shop's electricity bill of 900", outcome="ENTRY",
         roles={},
         expected=K("Ghar", 3500, date="T-1", purpose="ration") + X("misc", 900, "dukaan bijli bill"),
         why="Home vs shop, two dates"),
    dict(id="FAM-E-10", category="E", hinglish="Rohit ne 5000 wapas kiye aur Papa 1500 le gaye dawai ke liye",
         english="Rohit returned 5000 and Papa took 1500 for medicine", outcome="ENTRY",
         roles=R(rohit=F, रोहित=F, papa=F),
         expected=J("Rohit", 5000) + K("Papa", 1500, purpose="dawai"), why="Two family entries, opposite directions"),
]

CATEGORY_LABELS = {"A": "A - Daily", "B": "B - Tricky", "C": "C - Edge", "D": "D - Other business", "E": "E - Mixed"}

# Hindi (Devanagari) — naam Devanagari mein; seed ke naam test/seed_data.py ke HINDI_NAMES se milte hain.
HINDI = {
    "FAM-A-01": "मम्मी को सब्ज़ी के लिए 500 दे दिए गल्ले से",
    "FAM-A-02": "पापा 2000 ले गए घर के खर्चे के लिए",
    "FAM-A-03": "छोटे भाई रोहित की ट्यूशन फीस 3500 भर दी",
    "FAM-A-04": "घर का गैस सिलेंडर आया 1100 का, पैसे गल्ले से दिए",
    "FAM-A-05": "बेटी की स्कूल वैन के 1200 दिए आज",
    "FAM-A-06": "पापा ने दुकान के गल्ले में 10000 डाल दिए",
    "FAM-A-07": "मम्मी की दवाई 650 की आई, पैसे दुकान से गए",
    "FAM-A-08": "भाई जो उधार ले गया था, उसके 3000 आज वापस आ गए गल्ले में",
    "FAM-A-09": "कल घर का राशन 4200 का आया, गल्ले से दिया",
    "FAM-A-10": "मंदिर में दान देना था, पापा गल्ले से 1100 निकाल के ले गए",
    "FAM-B-01": "भाई ने 2000 लिए थे, आज उसमें से 1500 वापस किए",
    "FAM-B-02": "बेटा बाइक में पेट्रोल डलवाने 300 ले गया",
    "FAM-B-03": "घर की छत पे पानी की टंकी लगवाई 6500 की, पैसे दुकान से",
    "FAM-B-04": "घर के लिए 10 बोरी सीमेंट आई 3800 की",
    "FAM-B-05": "मम्मी ने 5000 दिए थे बिज़नेस के लिए, आज वो उनको वापस कर दिए",
    "FAM-B-06": "रोहित ने अपनी सैलरी में से 5000 गल्ले में डाले",
    "FAM-B-07": "छोटे की फीस के 2500 और राशन के 1800 दिए",
    "FAM-B-08": "मम्मी ने कल 1500 रखे थे गल्ले में, आज वही वापस ले गई",
    "FAM-B-09": "शादी में शगुन देना था, 2100 गल्ले से निकाले",
    "FAM-B-10": "पापा के हाथ गल्ले से 3000 गए, घर पे काम था",
    "FAM-C-01": "पापा कुछ पैसे ले गए घर के लिए, कितने बताए नहीं",
    "FAM-C-02": "घर के खर्चे के 2000 दिए, नहीं नहीं 2500 थे",
    "FAM-C-03": "शाम को पापा ने गल्ला गिन लिया, हिसाब बराबर था",
    "FAM-C-04": "कल मम्मी को 2000 देने हैं दवाई के लिए",
    "FAM-C-05": "मम्मी को 1.5 हज़ार दिए सब्ज़ी के लिए",
    "FAM-C-06": "रोहित की कोचिंग के पांच हज़ार भर दिए",
    "FAM-C-07": "घर के लिए दो-ढाई हज़ार निकाले थे",
    "FAM-C-08": "पापा ने सुबह 2000 लिए और शाम को 2000 वापस रख दिए",
    "FAM-C-09": "परसों पापा 4000 ले गए थे बिजली के बिल के लिए",
    "FAM-C-10": "मम्मि को 700 दिए घर के लिए",
    "FAM-D-01": "गुप्ता जी का पुराना मकान तोड़ने के लिए 1.5 लाख में ले लिया",
    "FAM-D-02": "राम ने शर्मा जी के घर माल उतारा, उसको 500 दिए",
    "FAM-D-03": "पापा घर पे थे, सुरेश ट्रेडर्स का आदमी उनको 4000 पकड़ा गया",
    "FAM-D-04": "दुकान के मीटर का बिल आया 1300, अभी नहीं भरा",
    "FAM-D-05": "बेटा एसबीआई भट्टे से 2000 ईंट ले आया, 12000 देने बाकी हैं",
    "FAM-D-06": "मम्मी ने बोला तो 2 पुरानी खिड़कियां शर्मा जी को 3000 में बेच दीं, कैश ले लिया",
    "FAM-D-07": "पापा ने कितनू को 1000 एडवांस दे दिया",
    "FAM-D-08": "घर का नहीं, गोदाम का किराया 8000 दिया",
    "FAM-D-09": "भाई गोदाम से 50 कड़ियां शर्मा जी के घर छोड़ आया",
    "FAM-D-10": "पापा सोहन की आज की हाज़िरी लगा गए, पूरा दिन था",
    "FAM-E-01": "पापा 3000 ले गए घर के लिए और राम को 500 दिहाड़ी दी",
    "FAM-E-02": "मम्मी को 2000 पकड़ाए, ये पैसा शर्मा जी वाले 5000 में से था जो आज मिले",
    "FAM-E-03": "गोदाम का किराया 6000 और घर का किराया 4000 दिया",
    "FAM-E-04": "भाई ने गल्ले में 10000 डाले, उसी से एसबीआई भट्टे का 5000 चुका दिया",
    "FAM-E-05": "कितनू को 800 दिए और बेटी की फीस के 2200 भी",
    "FAM-E-06": "ट्रैक्टर में 600 का डीज़ल डलवाया और घर की गाड़ी में 400 का पेट्रोल",
    "FAM-E-07": "सुरेश ट्रेडर्स को 30 फट्टे 4500 में दिए, और पापा ने 1000 ले लिए",
    "FAM-E-08": "मम्मी ने 2000 गल्ले में डाले, उसमें से सोहन को 600 दिहाड़ी दी",
    "FAM-E-09": "कल घर का राशन 3500 का आया और आज दुकान का 900 का बिजली बिल भरा",
    "FAM-E-10": "रोहित ने 5000 वापस किए और पापा 1500 ले गए दवाई के लिए",
}

# English run — same meaning, natural English
ENGLISH_INPUT = {t["id"]: t["english"] for t in TESTCASES}

for _t in TESTCASES:
    _t["hindi"] = HINDI[_t["id"]]
    _t["english_input"] = ENGLISH_INPUT[_t["id"]]
assert set(HINDI) == set(ENGLISH_INPUT) == {t["id"] for t in TESTCASES}
assert len(TESTCASES) == 50
