from pydantic import BaseModel
from typing import Literal
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv 
from langchain_core.prompts import ChatPromptTemplate

class IntentRouter(BaseModel):
    intent: Literal["general_chat", "accounting", "report"]
load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

router_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are an intent classifier for a business accounting
        assistant app. Real users (including non-technical family
        members) will use this app for BOTH casual conversation
        AND business record-keeping. Your job is to correctly
        separate the two.

        Return:
        general_chat
        or
        accounting
        or
        report

        ═══════════════════════════════
        ACCOUNTING includes
        ═══════════════════════════════
        - employee payments, work entries, attendance,
          driving status, profile creation/update
        - customer sales, payments, profile creation/update,
          returns
        - supplier material transactions, payments, profile
          creation/update
        - material moving between locations (site/gudam/shop)
        - stock damage, wastage, count correction, opening stock
        - work/activity logs at a location (labour, general work)
        - business expenses (fuel, rent, repair, bills)
        - property/deal purchases and their advances
        - ANY buying/purchasing/selling statement, even
          informally worded
        - CORRECTIONS: any statement saying a PREVIOUSLY recorded
          entry was wrong, or asking to fix/cancel/delete/undo an
          earlier entry, even with no amount or full detail given

        CRITICAL — These are ALL accounting, even without
        words like "entry karo" or "record karo":
        - "bike li" / "kuch kharida" / "machine li"
        - "deal hui" / "advance diya"
        - "ghr todne ki deal"
        - "X lakh mein liya/kharida/becha"

        CRITICAL — Correction statements are ALWAYS accounting,
        never general_chat, even when they sound like casual talk
        or a question about a named person:
        - "Mohan ka pichla entry galat tha"
        - "Mohan ka 2 din pehle wala galat tha"
        - "kal wali entry sahi karo"
        - "wo entry cancel karo" / "wo entry hata do"
        - "galti se 500 dal diya tha"

        ═══════════════════════════════
        ATTENDANCE / HAAZRI — ALWAYS accounting
        ═══════════════════════════════
        Any STATEMENT (not a question) about a worker's presence on
        a day is attendance = accounting, even with no money and
        even if the word "attendance" is never used:
        - came / did not come          (aaya / nahi aaya / आया / नहीं आया)
        - half day, left early, went home midway
                                       (aadha din / beech mein chala gaya / आधा दिन)
        - came late / came on time     (der se aaya / time pe aaya / देर से आया)
        - leave, holiday, day off      (chutti / छुट्टी / on leave)
        - on duty / driving / trips the whole day
                                       (poora din gaadi chalayi / पूरा दिन ड्यूटी पर)
        A reason added to it ("ghar pe kaam tha", "he was sick")
        does NOT make it casual talk — it is still attendance.

        CRITICAL — attendance vs general_chat:
        - STATEMENT about coming/leaving/leave on a day → accounting
          ("Vinod aaj der se pahuncha", "Raju took leave today")
        - QUESTION about where/how a person is → general_chat
          ("Vinod kahan hai?", "How is Raju doing?")

        ═══════════════════════════════
        REPORT includes
        ═══════════════════════════════
        The user wants to SEE / READ existing records — nothing new
        is being recorded:
        - "hisab dikhao / batao / bhejo", "report do", "khata dikhao"
        - balance / baaki / udhaar QUESTIONS: "kitna baaki hai?",
          "kitna lena hai?", "kitna dena hai?"
        - "poore business ka hisab", "is mahine ka hisab",
          "pichle 15 din ka kharcha dikhao", "cash kitna hai"
        - a named person's account: "Ram ka hisab bata",
          "Suresh ka khata dikhao"
        - registers: "kis din kya kaam hua", "maal kahan se kahan gaya"

        CRITICAL — report vs accounting:
        - QUESTION / request to SEE → report
          ("SBI bhate ka kitna baaki hai?", "Ram ka hisab bata")
        - STATEMENT that records something → accounting
          ("Sharma ji ka 20000 baaki hai" = recording a balance,
           "Ram ko 500 diye" = recording a payment)
        - Correction of an old entry is ALWAYS accounting, never report.

        ═══════════════════════════════
        GENERAL_CHAT includes
        ═══════════════════════════════
        - factual/general-knowledge questions
        - casual greetings and small talk
        - casual questions about a person's wellbeing (NOT
          their profile, work, or financial record)
        - weather, sports, news, or any topic unrelated to
          this business

        CRITICAL — Casual/personal talk about a NAMED PERSON
        is general_chat UNLESS money, work, attendance (coming,
        not coming, leave, half day, late, leaving early — see
        ATTENDANCE above), material/stock, or profile info
        (phone/address/role) is mentioned.

        ═══════════════════════════════
        EXAMPLES BY CATEGORY
        ═══════════════════════════════

        -- Employee --
        'Ram hamara employee hai, driver hai, phone 9876543210 hai' → accounting
        'Ram ka phone number badal do' → accounting
        'Ram ne 500 ka kaam kiya' → accounting
        'Ram ko 300 diye' → accounting
        'Ram aaj aaya' → accounting
        'Satpal ne driving ki' → accounting
        'Ram ka hisab bata' → report
        'Ram kaisa hai' → general_chat
        'Ram se baat hui kya' → general_chat
        'Ram aaj kya kar raha hai' → general_chat

        -- Customer --
        'Sharma ji naye customer hain, phone 9876543210 hai' → accounting
        'Sharma ji ko 2500 eent 35000 mein bechi' → accounting
        'Sharma ji ne 5000 rupaye diye' → accounting
        'Sharma ji ka 20000 baaki hai' → accounting
        'Shyam ne window return ki' → accounting
        'Sharma ji kaisa hai, mila kal' → general_chat

        -- Supplier --
        'SBI bhata supplier hai, address Bhiwani hai' → accounting
        'SBI Bhatte se 2500 eent aayi' → accounting
        'SBI Bhatte ko 5000 diye' → accounting
        'SBI bhate ka kitna baaki hai' → report

        -- Material Movement / Stock --
        'Gudam se shop 200 eent gayi' → accounting
        'Site A se malba gudam aaya' → accounting
        'Gudam mein 500 eent kharab ho gayi' → accounting
        'Gudam mein ginti ki, 30 eent kam nikli' → accounting

        -- Work / Activity Log --
        'Haasi Gate pe 5 labour the, todne ka kaam hua' → accounting
        'Gudam par 3 helper lage the' → accounting

        -- Expense --
        'Diesel par 2000 kharch hue' → accounting
        'Office ka bijli bill 1500 diya' → accounting
        'Generator ki servicing karayi, 600 ka' → accounting

        -- Purchase / Deal --
        'aaj bike li 2 lakh mein' → accounting
        'gudam ke liye machine li' → accounting
        'Shyam se ghar todne ki deal hui, 5 lakh mein' → accounting
        'Shyam ko 1 lakh advance diye' → accounting

        -- Mixed message --
        'Namaste, Ram ko 300 diye' → accounting
        'Kaise ho? Aaj SBI se maal aaya' → accounting

        -- Correction --
        'Mohan ka pichla entry galat tha' → accounting
        'Mohan ka 2 din pehle wala galat tha' → accounting
        'Ram ka kal ka 500 galat tha' → accounting
        'kal wali kiraya ki entry sahi karo' → accounting
        'wo entry cancel karo' → accounting
        'galti se 500 dal diya tha, hata do' → accounting
        'Ram ka pichla hisab galat dala' → accounting

        -- Report --
        'poore business ka hisab dikhao' → report
        'is mahine ka hisab bhejo' → report
        'Suresh ka khata dikhao' → report
        'Suresh se kitna lena hai' → report
        'pichle 15 din ka kharcha dikhao' → report
        'cash kitna hai galle mein' → report
        'kis din kya kaam hua dikhao' → report
        'Ram ka september ka hisab hindi mein' → report

        -- General chat --
        'India ki rajdhani kya hai' → general_chat
        'Aap kaise ho' → general_chat
        'Kya haal hai' → general_chat
        'Aaj mausam kaisa hai' → general_chat
        'Cricket match kaun jeeta' → general_chat
        'Tum kaun ho' → general_chat
        'Thank you' → general_chat

        -- Attendance (Hinglish) --
        'Vinod aaj aaya hi nahi' → accounting
        'Deepak dopahar ko beech mein chala gaya' → accounting
        'Raju aaj der se pahuncha' → accounting
        'Satpal kal aadha din raha' → accounting
        'Pappu ne aaj chutti li, shaadi mein gaya' → accounting
        'Mohan ne poora din tractor chalaya' → accounting
        'Vinod kahan hai?' → general_chat
        'Deepak ki tabiyat kaisi hai' → general_chat

        -- Attendance (Hindi) --
        'विनोद आज आया ही नहीं' → accounting
        'दीपक दोपहर में बीच में चला गया' → accounting
        'राजू आज देर से पहुँचा' → accounting
        'सतपाल ने कल आधा दिन काम किया' → accounting
        'पप्पू आज छुट्टी पर है' → accounting
        'विनोद कहाँ है?' → general_chat
        'राजू कैसा है?' → general_chat

        -- Attendance (English) --
        'Vinod was absent today' → accounting
        'Deepak left early this afternoon' → accounting
        'Raju reported late today' → accounting
        'Satpal worked only half the day yesterday' → accounting
        'Pappu is on leave today, family function' → accounting
        'Mohan drove the tractor the whole day' → accounting
        'Where is Vinod?' → general_chat
        'How is Raju doing?' → general_chat

        -- Hindi (Devanagari) --
        'विनोद को 400 दिए' → accounting
        'सतपाल ने 700 का काम किया' → accounting
        'गुप्ता जी को 1500 ईंट 12000 में बेची' → accounting
        'गुप्ता जी ने 3000 रुपये दिए' → accounting
        'जिंदल भट्टे से 2000 ईंट आई' → accounting
        'जिंदल भट्टे को 4000 दिए' → accounting
        'दुकान से साइट पर 100 ईंट गई' → accounting
        'ट्रैक्टर का टायर बदलवाया, 1500 लगे' → accounting
        'नई मशीन 50 हज़ार में ली' → accounting
        'विनोद की कल वाली एंट्री गलत है' → accounting
        'विनोद का हिसाब दिखाओ' → report
        'गुप्ता जी से कितना लेना है' → report
        'इस महीने का खर्चा दिखाओ' → report
        'भारत की राजधानी क्या है' → general_chat
        'नमस्ते, कैसे हो' → general_chat

        -- English --
        'Paid Vinod 400' → accounting
        'Satpal did work worth 700' → accounting
        'Sold 1500 bricks to Gupta ji for 12000' → accounting
        'Gupta ji paid 3000' → accounting
        'Received 2000 bricks from Jindal kiln' → accounting
        'Paid 4000 to Jindal kiln' → accounting
        'Moved 100 bricks from the shop to the site' → accounting
        'Got the tractor tyre changed, cost 1500' → accounting
        'Bought a new machine for 50 thousand' → accounting
        "Vinod's entry from yesterday is wrong" → accounting
        "Show Vinod's account" → report
        'How much does Gupta ji owe us?' → report
        "Show this month's expenses" → report
        'What is the capital of India?' → general_chat
        'Good morning, how are you?' → general_chat

        Return only the classification.
        """
    ),
    ("human", "{input}")
])

router_chain = (router_prompt | llm.with_structured_output(IntentRouter, method="function_calling"))


# ───────────────────────────────────────────────────────────────
# Safety net: LLM ne haazri wali baat ko "general_chat" bola, par
#   (1) ye sawaal nahi hai,
#   (2) haazri ka shabd hai (aaya / chutti / aadha din / left early ...),
#   (3) koi jaana-pehchaana employee ka naam ya kaam ka role likha hai
# → accounting. (Aage role confirm + final "yes" phir bhi hota hai.)
# ───────────────────────────────────────────────────────────────
import re

_ATTENDANCE_WORDS = re.compile(
    r"\b(aaya|aayi|aaye|aa gaya|aa gayi|nahi aaya|nhi aaya|nahin aaya|chhutti|chutti|chhuti|"
    r"aadha din|aadhe din|adha din|half day|haazri|haaziri|hazri|hajri|haziri|chala gaya|chali gayi|"
    r"der se|time pe|time par|absent|present|duty|"
    r"came|come|didn'?t come|did not come|day off|on leave|leave|half the day|half a day|"
    r"left early|went home|late|on time|all day|whole day|full day)\b"
    r"|आया|आई|आए|आये|छुट्टी|छुट्टी|आधा दिन|आधे दिन|हाज़िरी|हाजिरी|हाज़री|हाजरी|देर से|चला गया|चली गई|ड्यूटी",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"\?|\b(kya|kahan|kaha|kaisa|kaisi|kaise|kab|kyun|kyon|kaun|how|where|what|why|when|who)\b"
    r"|^\s*(did|does|do|is|are|was|were|has|have)\b"          # English sawaal shuru mein hi
    r"|क्या|कहाँ|कहां|कैसा|कैसी|कैसे|कब|क्यों|कौन",
    re.IGNORECASE,
)
_ROLE_WORDS = re.compile(
    r"\b(driver|mazdoor|majdoor|labour|labor|helper|mistri|munshi|cook|worker|karigar)\b"
    r"|ड्राइवर|मज़दूर|मजदूर|हेल्पर|मिस्त्री|मुंशी|कारीगर",
    re.IGNORECASE,
)


def _known_employee_named(text):
    """Text mein DB ka koi employee ka naam hai? (DB na mile to False — net bas band rahega.)"""
    try:
        from db import SessionLocal
        from models import Employee
        db = SessionLocal()
        try:
            names = [n for (n,) in db.query(Employee.name).all() if n]
        finally:
            db.close()
    except Exception:
        return False
    low = text.lower()
    for name in names:
        n = name.strip().lower()
        if n and re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", low):
            return True
    return False


def attendance_safety_net(text: str) -> bool:
    """True → ye haazri ka bayan hai, chat nahi."""
    if not text or _QUESTION.search(text) or not _ATTENDANCE_WORDS.search(text):
        return False
    return bool(_ROLE_WORDS.search(text)) or _known_employee_named(text)

# tests = [
#     "India ki rajdhani kya hai?",
#     "Ram ko 500 diye",
#     "Ram ne 600 ka kaam kiya",
#     "Ram ka hisab bata",
#     "Kal Ram ko 200 diye aur 500 ka kaam kiya"
# ]
# for t in tests:
#     print(t)
#     print(router_chain.invoke({"input": t}))
#     print("-" * 50)