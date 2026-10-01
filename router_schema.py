from pydantic import BaseModel
from typing import Literal
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv 
from langchain_core.prompts import ChatPromptTemplate

class IntentRouter(BaseModel):
    intent: Literal["general_chat", "accounting"]
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
        - profit/loss or account/balance queries about any
          person or entity above
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
        GENERAL_CHAT includes
        ═══════════════════════════════
        - factual/general-knowledge questions
        - casual greetings and small talk
        - casual questions about a person's wellbeing (NOT
          their profile, work, or financial record)
        - weather, sports, news, or any topic unrelated to
          this business

        CRITICAL — Casual/personal talk about a NAMED PERSON
        is general_chat UNLESS money, work, attendance,
        material/stock, or profile info (phone/address/role)
        is explicitly mentioned.

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
        'Ram ka hisab bata' → accounting
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
        'SBI bhate ka kitna baaki hai' → accounting

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

        -- General chat --
        'India ki rajdhani kya hai' → general_chat
        'Aap kaise ho' → general_chat
        'Kya haal hai' → general_chat
        'Aaj mausam kaisa hai' → general_chat
        'Cricket match kaun jeeta' → general_chat
        'Tum kaun ho' → general_chat
        'Thank you' → general_chat

        Return only the classification.
        """
    ),
    ("human", "{input}")
])

router_chain = (router_prompt | llm.with_structured_output(IntentRouter, method="function_calling"))

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