# test/testcases/rtr_testcases.py — Router bundle (30), test set v1 (LOCKED 2026-10-08).
#
# Sirf router jaancha jaata hai: statement kahan gaya — general_chat / accounting / report.
# ROUTE_ONLY = True → runner sirf router_node chalata hai (LLM + haazri / paise wale safety nets), aage ki pipeline nahi.
# Statements user (Sahil) ke saath tay kiye; prompt / purane tests se milaaye (difflib ≤ 0.69).

BUNDLE = "Router"
PREFIX = "RTR"
ROUTE_ONLY = True

CHAT, ACC, REP = "general_chat", "accounting", "report"


def tc(id_, hg, hi, en, route, why=""):
    return dict(id=id_, category=id_.split("-")[1], hinglish=hg, hindi=hi, english=en, english_input=en,
                outcome=route, route=route, roles={}, expected=[], why=why)


TESTCASES = [
    # =====================================================================  A — saaf general chat
    tc("RTR-A-01", "Good morning bhai, chai pi li?", "गुड मॉर्निंग भाई, चाय पी ली?",
       "Good morning brother, had your tea?", CHAT),
    tc("RTR-A-02", "Diwali kab hai is saal?", "दिवाली कब है इस साल?", "When is Diwali this year?", CHAT),
    tc("RTR-A-03", "Mujhe ek achhi si shayari sunao", "मुझे एक अच्छी सी शायरी सुनाओ", "Tell me a nice couplet", CHAT),
    tc("RTR-A-04", "Haryana ka CM kaun hai abhi", "हरियाणा का सीएम कौन है अभी", "Who is the Haryana CM right now", CHAT),
    tc("RTR-A-05", "Tum Hindi samajh lete ho kya", "तुम हिंदी समझ लेते हो क्या", "Do you understand Hindi", CHAT),
    tc("RTR-A-06", "Theek hai, shukriya", "ठीक है, शुक्रिया", "Okay, thanks", CHAT),

    # =====================================================================  B — chat jo business jaisi lagti hai
    tc("RTR-B-01", "Ram ki beti ki shaadi kab hai?", "राम की बेटी की शादी कब है?", "When is Ram's daughter's wedding?",
       CHAT, "employee name, personal question"),
    tc("RTR-B-02", "GST kya hota hai, eent pe kitna lagta hai?", "जीएसटी क्या होता है, ईंट पे कितना लगता है?",
       "What is GST, how much applies on bricks?", CHAT, "'eent', 'kitna' — general knowledge"),
    tc("RTR-B-03", "Sohan ki tabiyat ab kaisi hai, kal bukhar tha", "सोहन की तबीयत अब कैसी है, कल बुखार था",
       "How is Sohan's health now, he had fever yesterday", CHAT, "name + 'kal'"),
    tc("RTR-B-04", "Sharma ji ka beta bada hoshiyar nikla, doctor ban gaya",
       "शर्मा जी का बेटा बड़ा होशियार निकला, डॉक्टर बन गया", "Sharma ji's son turned out very smart, became a doctor",
       CHAT, "customer name, small talk"),
    tc("RTR-B-05", "Hisab kitab rakhne ka sabse aasaan tareeka kya hai?", "हिसाब किताब रखने का सबसे आसान तरीका क्या है?",
       "What is the easiest way to keep accounts?", CHAT, "'hisab' — advice, not a report"),
    tc("RTR-B-06", "Kitanu kahan gaya, phone nahi utha raha", "कितनू कहाँ गया, फ़ोन नहीं उठा रहा",
       "Where did Kitanu go, he isn't picking up the phone", CHAT, "'gaya' — question, not attendance"),

    # =====================================================================  C — accounting jo chat jaisi lagti hai
    tc("RTR-C-01", "Arre yaar Sohan aaj phir late aaya", "अरे यार सोहन आज फिर लेट आया", "Oh man, Sohan came late again today",
       ACC, "attendance"),
    tc("RTR-C-02", "Ram ki tabiyat kharab thi to wo aaj nahi aaya", "राम की तबीयत खराब थी तो वो आज नहीं आया",
       "Ram was unwell so he didn't come today", ACC, "attendance + reason"),
    tc("RTR-C-03", "Ram Ram ji, Sharma ji 2000 de gaye subah", "राम राम जी, शर्मा जी 2000 दे गए सुबह",
       "Ram Ram, Sharma ji paid 2000 in the morning", ACC, "greeting + payment"),
    tc("RTR-C-04", "Suresh Traders ka naya number 9812345678 hai", "सुरेश ट्रेडर्स का नया नंबर 9812345678 है",
       "Suresh Traders' new number is 9812345678", ACC, "profile"),
    tc("RTR-C-05", "Chalo aaj gudam ki safai ho gayi, 300 lage", "चलो आज गोदाम की सफाई हो गई, 300 लगे",
       "Okay, the warehouse got cleaned today, cost 300", ACC, "expense"),
    tc("RTR-C-06", "Papa galle se kuch paise le gaye the shaam ko", "पापा गल्ले से कुछ पैसे ले गए थे शाम को",
       "Papa took some money from the till in the evening", ACC, "family, no amount"),
    tc("RTR-C-07", "Kal wali Kitanu ki entry thodi gadbad lag rahi hai", "कल वाली कितनू की एंट्री थोड़ी गड़बड़ लग रही है",
       "Kitanu's entry from yesterday looks a bit off", ACC, "soft correction"),
    tc("RTR-C-08", "Bas aaj SBI wale 3000 eent utaar gaye", "बस आज एसबीआई वाले 3000 ईंट उतार गए",
       "Just today the SBI people unloaded 3000 bricks", ACC, "supplier goods"),
    tc("RTR-C-09", "Accha suno, ek nayi trolley le li 2 lakh ki", "अच्छा सुनो, एक नई ट्रॉली ले ली 2 लाख की",
       "Listen, bought a new trolley for 2 lakh", ACC, "purchase"),

    # =====================================================================  D — report ya entry (sawaal vs bayan)
    tc("RTR-D-01", "Abhi tak Sharma ji ne humein kitna chukana hai?", "अभी तक शर्मा जी ने हमें कितना चुकाना है?",
       "How much does Sharma ji still have to pay us?", REP, "balance question"),
    tc("RTR-D-02", "Sharma ji pe 3000 baaki reh gaye hain pichle", "शर्मा जी पे 3000 बाकी रह गए हैं पिछले",
       "3000 from before is still due from Sharma ji", ACC, "balance statement"),
    tc("RTR-D-03", "Is hafte kitna diesel gaya, dikha do", "इस हफ्ते कितना डीज़ल गया, दिखा दो",
       "Show how much diesel went this week", REP),
    tc("RTR-D-04", "Kitanu ka hisab bhej do Papa ko", "कितनू का हिसाब भेज दो पापा को", "Send Kitanu's account to Papa",
       REP, "'Papa ko' — not family money"),
    tc("RTR-D-05", "Kitanu ka hisab kar diya, 1500 diye", "कितनू का हिसाब कर दिया, 1500 दिए",
       "Settled Kitanu's account, paid 1500", ACC, "'hisab' but a payment"),
    tc("RTR-D-06", "Galle mein abhi kitna cash pada hai?", "गल्ले में अभी कितना कैश पड़ा है?",
       "How much cash is in the till right now?", REP),
    tc("RTR-D-07", "Galle mein 25000 cash rakha hai shuru ka", "गल्ले में 25000 कैश रखा है शुरू का",
       "There is 25000 starting cash in the till", ACC, "opening cash"),
    tc("RTR-D-08", "Suresh Traders ko kitna dena baaki hai, bata do", "सुरेश ट्रेडर्स को कितना देना बाकी है, बता दो",
       "Tell me how much is still to be paid to Suresh Traders", REP),
    tc("RTR-D-09", "Ram ne kitne din kaam kiya is mahine?", "राम ने कितने दिन काम किया इस महीने?",
       "How many days did Ram work this month?", REP, "work register question"),
]

CATEGORY_LABELS = {"A": "A - General chat", "B": "B - Chat that looks like business",
                   "C": "C - Entry that sounds like chat", "D": "D - Report or entry"}

assert len(TESTCASES) == 30 and len({t["id"] for t in TESTCASES}) == 30
