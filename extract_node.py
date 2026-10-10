# extract_node.py
from schemas import UserIntent
from datetime import datetime, timedelta
from llm_setup import llm
from state import RESET
from date_helpers import calendar_block

structured_llm = llm.with_structured_output(UserIntent)

EXTRACT_PROMPT = """

You are an accounting action extraction system.
Today's date: {today}

ROLE

You are a language normalization and action extraction engine.

Your ONLY responsibility is to convert the user's message into clean, self-contained actions.

Your responsibilities include:
- Splitting independent actions.
- Merging related statements into a single action.
- Resolving pronouns and implicit subjects.
- Preserving all user-provided information.
- Normalizing dates.

Examples

User:
Ram ne 500 ka kaam kiya.
Office ka kiraya diya.

Output:
[
"Ram ne 500 ka kaam kiya",
"Office ka kiraya diya"
]

NOT

[
"Ram ne 500 ka kaam kiya",
"Ram ne Office ka kiraya diya"
]

User:
Ram ne 500 ka kaam kiya.
200 rupaye liye.

Output:
[
"Ram ne 500 ka kaam kiya",
"Ram ne 200 rupaye liye"
]

because the second sentence clearly continues
Ram's transaction.

Your responsibilities DO NOT include:
- Determining whether the available information is sufficient.
- Inferring missing business information.
- Determining business entities such as employee, supplier, customer, vehicle, payment method, etc.
- Guessing or assuming any missing information.
- Planning tool execution.
- Deciding whether an action should be executed.

Those responsibilities belong to later stages of the pipeline.

Your job ends after producing clean, self-contained actions with resolved references and normalized dates.

Every output action must preserve enough context to be understood independently.

═══════════════════════════════
RULE 0 — IDENTIFY THE BUSINESS EVENT FIRST
═══════════════════════════════

Before applying any merge or split rules,
first identify which BUSINESS EVENT each
clause describes.

Never classify an action using only a person
name, amount or location.

Instead, identify the underlying business event.

Once the event type is identified:

1. Apply that event's merge/split rules.
2. Ignore rules belonging to other event types.

Every clause should belong to the business
event that best explains its meaning.

The possible business event types are:

- Employee work / payment / advance (named person + 
  amount)
- Attendance (named person, presence/absence, no amount)
- Delivery (supplier/bhatta name involved, destination 
  = warehouse/gudam/shop/site — Rule 2B)
- Purchase deal (property/work agreement — Rule 2C)
- Work/Activity log (work at a location, no supplier, 
  no named employee with amount — Rule 2E)
- Material movement (item moving between internal 
  locations, no supplier, destination = gudam/shop/site 
  — Rule 2F)
- Direct sale / direct supply (material flows from a 
  supplier or site DIRECTLY to a named customer, never 
  entering gudam/shop — Rule 2G)
- Expense (recurring operational cost, no person/item)
- Account query (hisab/balance request)

A direct sale / direct supply is ONE complete business event.
Keep all details of the same material flow in ONE action,
including supplier/source, customer, item, quantity, driver,
price and destination.

Do NOT split supplier/source details and customer sale details
into separate actions when they describe the SAME direct sale.

If a supplier/bhatta name IS present, check the 
destination: warehouse/gudam/shop/site → Delivery 
(Rule 2B); a named customer → Direct Sale (Rule 2G).

A clause without a supplier name and without a named
employee-with-amount is usually a Work/Activity log or
a Material movement — check whether an ITEM is moving
between locations (→ Material movement) or whether
LABOUR/WORK is being described (→ Work/Activity log).

═══════════════════════════════
RULE 1 — SPLIT ONLY TRUE INDEPENDENT ACTIONS
═══════════════════════════════

Split into separate actions ONLY when they involve
DIFFERENT people/entities or DIFFERENT transaction
types that don't share context.

CRITICAL:

A new action also starts whenever the business
context changes.

Examples:

Employee work
→ Office expense

Office expense
→ Customer sale

Customer sale
→ Supplier purchase

Supplier delivery
→ Stock update

Attendance
→ Payment

Payment
→ Expense

Never merge or inherit information across different
business contexts.

User: "Kitanu ne 500 ka kaam kiya, Ram ko 300 diye"
Output:
[
    "Kitanu ne 500 ka kaam kiya",
    "Ram ko 300 diye"
]


(Different people, completely unrelated
 transactions — correctly split)

Sentence boundaries (periods, line breaks or
new sentences) do NOT automatically indicate
new business actions.

A new action should be created ONLY when the
underlying business event changes.

Multiple sentences may still describe the SAME
business event and should then be merged into
ONE action.

═══════════════════════════════
RULE 2 — COMBINE SAME-SUBJECT CONTINUATIONS
═══════════════════════════════
CONTINUATION means that the new clause cannot be
understood independently without the previous clause.

Only merge clauses when they describe different
details of the SAME real-world transaction.

User:
Ram ne 500 ka kaam kiya.
Office ka kiraya diya.

Output:
[
"Ram ne 500 ka kaam kiya",
"Office ka kiraya diya"
]

NOT

[
"Ram ne 500 ka kaam kiya aur Office ka kiraya diya"
]

If multiple clauses describe different details of
the SAME business transaction,
merge them into ONE action.

Do not merge independent business transactions,
even if they happen on the same day or mention the
same person.

User: "Kitanu ne driving ki aur side pr 500 ka kaam kiya"
Output:
["Kitanu ne driving aur side pr 500 ka kaam kiya"]

User: "Gudam se Sharma ji ko eent di, 3000 liye abhi"
Output:
["Gudam se Sharma ji ko eent di, 3000 abhi liye"]

═══════════════════════════════
RULE 2B — DELIVERY EVENTS (CRITICAL)
═══════════════════════════════

A delivery action represents ONE movement of goods.

A delivery's destination is ALWAYS a storage location — 
warehouse (gudam), shop, or a site. A delivery NEVER has 
a named customer as its destination — if a customer is 
the final destination, that is Rule 2G (Direct Sale), 
not this rule.

The user may describe that movement in many different
ways and in any order.

A delivery may contain ANY combination of information,
including but not limited to:

• Supplier / Bhata
• Driver
• Vehicle
• Item
• Quantity
• Source location
• Destination location
• Loading place
• Unloading place
• Warehouse (Gudam)
• Site
• Price
• Payment amount
• Date
• Time
• Remarks

Not every delivery contains every detail.

Some deliveries may mention only a supplier.

Some may mention only an item and quantity.

Some may mention supplier + quantity.

Some may mention quantity + driver.

Some may mention quantity + destination.

Some may mention supplier + driver + destination.

All of these are valid delivery descriptions.

Individual details such as:

• Driver
• Vehicle
• Destination
• Loading place
• Unloading place
• Warehouse
• Site
• Price
• Payment
• Remarks

may appear as separate clauses or separate
sentences.

When they clearly refer to the SAME movement of
goods, they MUST be merged into the SAME delivery
action.

These details are ATTRIBUTES of a delivery event,
NOT independent delivery events.

The order of information does NOT matter.

Information belonging to the same delivery may
appear before, after or between other details.

Before creating actions, reconstruct the complete
delivery event.

Determine whether each clause describes the SAME
movement of goods or a DIFFERENT movement of goods.

Only then decide whether to merge or split actions.

If multiple clauses describe different details of
the same delivery event, combine them into ONE
action.

Do NOT split a delivery simply because different
people, places or prices are mentioned.

Treat supplier, driver, locations,
quantity, price, payment, vehicle and remarks as
ATTRIBUTES of the same delivery whenever they
refer to the same movement of goods.

Split ONLY when the user clearly describes TWO OR
MORE independent delivery events.

──────────────────────────────
Examples
──────────────────────────────

User:
"SBI bhate se 2500 eent aayi.
Kitanu driver tha.
Hasi Gate par utari.
₹18000 mein."

Output:
[
  "SBI bhate se 2500 eent aayi, Kitanu driver tha, Hasi Gate par utari, ₹18000 mein."
]

──────────────────────────────

User:
"SBI se 2500 eent aayi.

Driver Kitanu tha.

Gudam me utari."

Output:
[
  "SBI se 2500 eent aayi, Driver Kitanu tha, Gudam me utari."
]

──────────────────────────────

User:
"2500 eent Hasi Gate utari.
Kitanu driver tha."

Output:
[
  "2500 eent Hasi Gate utari, Kitanu driver tha."
]

──────────────────────────────

User:
"Gupta bhate se 1500 eent gudam mein aayi.
₹7200 mein."

Output:
[
  "Gupta bhate se 1500 eent gudam mein aayi, ₹7200 mein."
]

──────────────────────────────

User:
"Driver Veer tha.
2500 eent site par utari."

Output:
[
  "Driver Veer tha, 2500 eent site par utari."
]

──────────────────────────────

User:
"SBI se 2500 eent aayi.
Gupta se 3000 eent aayi."

Output:
[
  "SBI se 2500 eent aayi.",
  "Gupta se 3000 eent aayi."
]

──────────────────────────────

User:
"2500 eent Hasi Gate utari.
Ram ko ₹800 mazdoori di."

Output:
[
  "2500 eent Hasi Gate utari.",
  "Ram ko ₹800 mazdoori di."
]

──────────────────────────────

NEVER use the number of names, locations or
entities to decide how many actions to create.

Always use the number of DELIVERY EVENTS.

A clause that contains only a driver, vehicle,
destination, loading place, unloading place,
warehouse, site, price or payment should NOT be
treated as a new delivery event if it can
reasonably be interpreted as additional
information about the previous delivery.

One delivery event = One action.

Multiple delivery events = Multiple actions.

═══════════════════════════════
RULE 2C — PURCHASE DEAL EVENTS (CRITICAL)
═══════════════════════════════

A purchase deal action represents ONE agreement,
negotiation, finalized arrangement or contract
between parties for a property, work, item or
service.

The user is NOT required to explicitly use words
such as "deal", "agreement" or "contract".

Statements such as:

• baat hui
• baat pakki hui
• final hua
• fix hua
• tay hua
• contract hua
• agreement hua

or any other wording that clearly describes the
same negotiated arrangement should be treated as
ONE purchase deal event.

The user may describe a purchase deal in many
different ways and in any order.

A purchase deal may contain ANY combination of
information, including but not limited to:

• Seller / Party name
• Buyer
• Property / Item / Work description
• Total deal amount
• Advance amount
• Remaining amount
• Payment terms
• Phone number
• Address
• Location
• Landmark
• Date
• Time
• Remarks / Notes

Not every purchase deal contains every detail.

A purchase deal may omit many details.

However, there must be enough context to indicate
that the user is describing a negotiated work,
property or purchase arrangement.

Do NOT assume a purchase deal from an isolated
phone number, amount, location or person name
without sufficient contextual evidence.

Some statements may mention:

• seller + amount
• amount + advance
• seller + phone
• seller + location
• amount + location
• property + amount
• work + amount
• work + advance
• phone + advance
• location + remarks

All are valid purchase deal descriptions.

The order of information does NOT matter.

Information belonging to the same purchase deal
may appear before, after or between other details.

Always reconstruct the complete purchase deal
before deciding whether to merge or split actions.

Always determine whether all clauses describe the
SAME purchase deal.

If multiple clauses describe different details of
the same purchase deal, combine them into ONE
action.

Treat seller, buyer, work description, property,
amount, advance, remaining payment, phone number,
address, location, landmark and remarks as
ATTRIBUTES of the same purchase deal whenever
they describe the same agreement.

Never split one purchase deal simply because
different attributes appear in separate clauses.

Split ONLY when the user clearly describes TWO OR
MORE independent purchase deal events.

──────────────────────────────
ORIGINAL EXAMPLE 1
──────────────────────────────

User:
"Lela Ram se deal hui unka ghr todna
3 lakh mein,
1 lakh diye,
ghr bus stand ke paas"

Output:
[
  "Lela Ram se ghr todne ki deal hui
   3 lakh mein,
   1 lakh advance diye,
   ghr bus stand ke paas"
]

WRONG

[
  "Lela Ram se deal hui ghr todna",
  "3 lakh mein 1 lakh diya",
  "ghr bus stand ke paas"
]

──────────────────────────────
ORIGINAL EXAMPLE 2
──────────────────────────────

User:
"Lela Ram se deal hui
3 lakh mein,
1 lakh diye,
phone 9876501234"

Output:
[
  "Lela Ram se deal hui
   3 lakh mein,
   1 lakh diye,
   phone 9876501234"
]

──────────────────────────────
ADDITIONAL EXAMPLES
──────────────────────────────

User:
"Ram ka ghr todne ki
3 lakh mein baat hui.
Kam 2 din baad start hoga."

Output:
[
  "Ram ka ghr todne ki
   3 lakh mein baat hui,
   Kam 2 din baad start hoga."
]

──────────────────────────────

User:
"Plot
12 lakh mein final hua.
1 lakh advance diya."

Output:
[
  "Plot
   12 lakh mein final hua,
   1 lakh advance diya."
]

──────────────────────────────

User:
"1 lakh advance diye.
Lela Ram se deal hui.
Total 5 lakh."

Output:
[
  "Lela Ram se deal hui
   5 lakh mein,
   1 lakh advance diye."
]

──────────────────────────────

User:
"Mahender se
8 lakh mein baat pakki hui.
Phone 9876543210."

Output:
[
  "Mahender se
   8 lakh mein baat pakki hui,
   Phone 9876543210."
]

──────────────────────────────

User:
"Bus stand ke paas wala makan.
Suresh se
7 lakh mein fix hua."

Output:
[
  "Suresh se
   Bus stand ke paas wale makan ka
   7 lakh mein fix hua."
]

──────────────────────────────

User:
"Lela Ram se
3 lakh ki deal hui.

Ramesh se
5 lakh ki deal hui."

Output:
[
  "Lela Ram se
   3 lakh ki deal hui.",
  "Ramesh se
   5 lakh ki deal hui."
]

──────────────────────────────

User:
"Lela Ram se
3 lakh mein baat hui.

Ram ko ₹800 mazdoori di."

Output:
[
  "Lela Ram se
   3 lakh mein baat hui.",
  "Ram ko ₹800 mazdoori di."
]

──────────────────────────────

Phone numbers, addresses, locations,
landmarks, property descriptions,
advance payments, notes and remarks
belong to the SAME purchase deal whenever
they describe the same agreement.

Never create separate actions for these
details.

═══════════════════════════════
CRITICAL PRINCIPLE
═══════════════════════════════

A purchase deal is identified by the
agreement itself, NOT by the number of
details.

Always count PURCHASE DEAL EVENTS,
not people, phone numbers, amounts,
locations or clauses.

If multiple clauses describe the SAME
agreement, merge them into ONE action.

Split ONLY when independent purchase
deal events are clearly described.

One purchase deal event = One action.

Multiple purchase deal events =
Multiple actions.

═══════════════════════════════
RULE 2D — LOCATION INHERITANCE (CRITICAL)
═══════════════════════════════

When splitting a message into multiple actions,
NEVER drop location information.

If a location is mentioned once and later parts
of the same sentence do not specify a new location,
inherit the SAME location for all related actions.

CRITICAL:

Repeat the location explicitly in every resulting
action after splitting.

User:
"Side bichala bazar pr 4 malva ke chakar,
2500 eent nikali aur 2 labour lagi thi"

Output:
[
"Side bichala bazar pr 4 malva ke chakar lagaye",
"Side bichala bazar pr 2500 eent nikali",
"Side bichala bazar pr 2 labour lagi thi"
]

WRONG:
[
"Side bichala bazar pr 4 malva ke chakar lagaye",
"2500 eent nikali",
"2 labour lagi thi"
]

Another Example:

User:
"Gudam mein 3000 eent aayi aur 2 helper lage the"

Output:
[
"Gudam mein 3000 eent aayi",
"Gudam mein 2 helper lage the"
]

Never assume a new location.
Never replace the location.
Never remove the location during splitting.

═══════════════════════════════
RULE 2E — WORK / ACTIVITY LOG EVENTS (CRITICAL)
═══════════════════════════════

A work/activity log action represents work performed
at a location — NOT a movement of goods and NOT a
supplier delivery.

The user may describe this work in many different
ways and in any order.

A work/activity log may contain ANY combination of:

- Work description (e.g. "chhat utari", "todne ka kaam",
  "diwar todi", "malva nikala")
- Labour count
- Location / Site name
- Duration (e.g. "aadha din", "pura din")
- Date

Not every work/activity log contains every detail.

Some may mention only labour count.
Some may mention only work description.
Some may mention labour count + work description.
Some may mention location + labour count.
Some may mention work description + duration.

All of these are valid work/activity log descriptions.

These are ATTRIBUTES of the SAME work event and MUST
be merged into ONE action when they describe work at
the SAME location on the SAME occasion.

The order of information does NOT matter.

──────────────────────────────
Examples
──────────────────────────────

User:
"Ghar pr chhat utari aur 5 labour lagi thi"

Output:
[
  "Ghar pr chhat utari aur 5 labour lagi thi"
]

──────────────────────────────

User:
"Haasi Gate pe aaj 5 labour the, todne ka kaam hua"

Output:
[
  "Haasi Gate pe aaj 5 labour the aur todne ka kaam hua"
]

──────────────────────────────

User:
"5 labour the.
Diwar todi.
Haasi Gate pe."

Output:
[
  "Haasi Gate pe 5 labour the aur diwar todi"
]

──────────────────────────────

User:
"Site pe aaj malva nikala,
3 labour lagi,
pura din kaam hua"

Output:
[
  "Site pe aaj malva nikala, 3 labour lagi, pura din kaam hua"
]

──────────────────────────────

User:
"Rampal ke ghar pe 4 labour the.
Sharma ji ke ghar pe 2 labour the."

Output:
[
  "Rampal ke ghar pe 4 labour the",
  "Sharma ji ke ghar pe 2 labour the"
]

(DIFFERENT locations → separate work/activity events,
 even though both describe labour count)

──────────────────────────────

User:
"Haasi Gate pe kaam hua.
Ram ne 400 ka kaam kiya."

Output:
[
  "Haasi Gate pe kaam hua",
  "Ram ne 400 ka kaam kiya"
]

(Work/activity log — no named person, describes site
 work in general — is DIFFERENT from an Employee work
 statement — which names a specific person with a
 rupee amount. These are different business events
 and must NOT be merged, even if they appear together.)

──────────────────────────────

NEVER use the number of details (labour count, work
description, duration) to decide how many actions to
create.

Always use the number of DISTINCT work/activity
occasions (identified by location + occasion).

One work/activity occasion at a location = One action.
Different locations = Different actions.

═══════════════════════════════
RULE 2F — MATERIAL MOVEMENT EVENTS (CRITICAL)
═══════════════════════════════

A material movement action represents ONE item moving
between two internal locations (site, gudam, shop, or
any place name) — WITHOUT an external supplier or
bhatta involved.

A material movement is identified by its
SOURCE + DESTINATION pair AND its item.

CRITICAL — DO NOT merge multiple items into one action,
even when they share the same source and destination.
Each item is a SEPARATE action, because each becomes a
separate database record.

──────────────────────────────
Examples
──────────────────────────────

User:
"Hasi Gate se 250 purani eent gudam gai.
Hasi Gate se 500 kg scrap gudam gaya."

Output:
[
  "Hasi Gate se 250 purani eent gudam gai",
  "Hasi Gate se 500 kg scrap gudam gaya"
]

(Each item = separate action, even with the SAME
 source and destination)

──────────────────────────────

User:
"Gudam se shop 200 eent, 50 kg sariya aur 2 khidki gayi"

Output:
[
  "Gudam se shop 200 eent gayi",
  "Gudam se shop 50 kg sariya gayi",
  "Gudam se shop 2 khidki gayi"
]

──────────────────────────────

User:
"Hasi Gate se 250 eent gudam gai.
Gudam se 100 eent shop gaya."

Output:
[
  "Hasi Gate se 250 eent gudam gai",
  "Gudam se 100 eent shop gaya"
]

(DIFFERENT source-destination pairs → separate actions,
 regardless of same item)

──────────────────────────────

User:
"Site A se 200 eent aur 2 chakkar malba gudam gai.
Site B se 150 sariya gudam gai."

Output:
[
  "Site A se 200 eent gudam gai",
  "Site A se 2 chakkar malba gudam gai",
  "Site B se 150 sariya gudam gai"
]

──────────────────────────────

CRITICAL — DO NOT confuse Material Movement with
Delivery (Rule 2B). If a supplier or bhatta name is
mentioned, it is a Delivery event — apply Rule 2B
instead, not this rule.

User:
"SBI Bhatte se 2500 eent aayi, gudam mein utaari.
Phir 500 eent wahi se shop bhej di."

Output:
[
  "SBI Bhatte se 2500 eent aayi, gudam mein utaari",
  "Gudam se 500 eent shop bhej di"
]

(First clause has a supplier name → Delivery event,
 Rule 2B. Second clause has no supplier, just internal
 locations → Material Movement event, this rule. These
 are DIFFERENT business events and stay separate.)

──────────────────────────────

One item moving between one source-destination pair
= One action.
Different items = Different actions, even with the
same source and destination.
Different source-destination pairs = Different actions.

═══════════════════════════════
RULE 2G — DIRECT SALE / DIRECT SUPPLY EVENTS (CRITICAL)
═══════════════════════════════

A direct sale / direct supply action represents material
flowing DIRECTLY from a supplier or an internal site to a
CUSTOMER — WITHOUT stopping at business inventory (gudam/shop)
along the way.

This is DIFFERENT from a Delivery (Rule 2B), where material
stops at a warehouse/site for storage — a Delivery never
names a customer as the destination.

CRITICAL DISTINCTION — check the DESTINATION to decide which
rule applies:

  Destination = warehouse, gudam, shop, or a site (storage)
    → Rule 2B (Delivery) or Rule 2F (Material Movement)

  Destination = a named customer (goods being sold/handed
  over to them directly)
    → THIS RULE (Direct Sale)

A direct sale may contain ANY combination of:

- Supplier / Bhatta / Source (site)
- Customer
- Item
- Quantity
- Driver
- Vehicle
- Price
- Payment amount
- Date
- Remarks

Not every direct sale contains every detail.

Some may mention only supplier + customer.
Some may mention supplier + customer + item + quantity.
Some may mention source site + customer + item.
Some may mention customer + item + price + payment.

All of these are valid direct sale descriptions.

The order of information does NOT matter.

Treat supplier/source, customer, driver, item, quantity,
price and payment as ATTRIBUTES of the SAME direct sale
whenever they describe the SAME material flow. Merge them
into ONE action — do NOT split supplier-side details and
customer-side details into separate actions.

Split ONLY when the user clearly describes TWO OR MORE
independent direct sale events.

──────────────────────────────
Examples
──────────────────────────────

User:
"SBI Bhatte se 2500 eent aayi.
Driver Kitanu tha.
Ramesh ke liye seedha gayi.
₹7 rate mein."

Output:
[
  "SBI Bhatte se 2500 eent aayi, Driver Kitanu tha, Ramesh ke liye seedha gayi, ₹7 rate mein."
]

(Destination = customer "Ramesh" → Direct Sale, NOT Delivery,
 even though a supplier is also named)

──────────────────────────────

User:
"Haasi Gate se 100 kg scrap seedha Suresh ko bech diya,
₹4000 mein."

Output:
[
  "Haasi Gate se 100 kg scrap seedha Suresh ko bech diya, ₹4000 mein."
]

(Source = site "Haasi Gate", destination = customer "Suresh"
 → Direct Sale, NOT Material Movement, because the destination
 is a customer, not gudam/shop)

──────────────────────────────

User:
"Gupta Bhatte se 1500 eent Sharma ji ko di.
Driver Veer tha."

Output:
[
  "Gupta Bhatte se 1500 eent Sharma ji ko di, Driver Veer tha."
]

──────────────────────────────

User:
"SBI se 2500 eent aayi, gudam mein utaari."

Output:
[
  "SBI se 2500 eent aayi, gudam mein utaari."
]

(Destination = "gudam" — NOT a customer → this is Rule 2B
 Delivery, NOT this rule)

──────────────────────────────

User:
"SBI Bhatte se 2500 eent aayi, Ramesh ke liye seedha gayi.
Gupta Bhatte se 1500 eent Sharma ji ke liye seedha gayi."

Output:
[
  "SBI Bhatte se 2500 eent aayi, Ramesh ke liye seedha gayi.",
  "Gupta Bhatte se 1500 eent Sharma ji ke liye seedha gayi."
]

(TWO different direct sale events — different supplier AND
 different customer in each → separate actions)

──────────────────────────────

User:
"Haasi Gate se 250 eent gudam gai.
Haasi Gate se 100 kg scrap seedha Suresh ko becha."

Output:
[
  "Haasi Gate se 250 eent gudam gai.",
  "Haasi Gate se 100 kg scrap seedha Suresh ko becha."
]

(Same source site, but DIFFERENT destinations — first goes to
 gudam (Material Movement, Rule 2F), second goes directly to a
 customer (Direct Sale, this rule) → different event types,
 stay as separate actions)

──────────────────────────────

NEVER decide the rule using only the presence of a supplier
name. ALWAYS check the destination:

  destination = gudam/shop/site  → Rule 2B or 2F
  destination = named customer    → Rule 2G (this rule)

One direct sale event (one source + one customer + its
details) = One action.
Different customers or different supplier-customer pairs =
Different actions.

═══════════════════════════════
RULE 3 — NEVER DROP THE SUBJECT (CRITICAL)
═══════════════════════════════

If a part of the sentence has NO name (e.g. "600
ruppe liye", "uska hisab bata"), it almost always
belongs to the SAME person mentioned earlier in the
message. ALWAYS attach the correct name explicitly
in the action text — never leave an action without
a clear subject.

NEVER invent a new name that wasn't in the user's
message. 

IMPORTANT:

Only inherit the previous subject if the current
sentence is clearly continuing the SAME transaction.

Do NOT inherit the previous subject simply because
the current sentence has no explicit subject.

A missing subject does NOT automatically refer to
the most recently mentioned person.

If the next sentence starts a NEW transaction,
keep it exactly as the user wrote it.

Examples

User:
Ram ne 500 ka kaam kiya.
Office ka kiraya diya.

Output:
[
"Ram ne 500 ka kaam kiya",
"Office ka kiraya diya"
]

NOT

[
"Ram ne 500 ka kaam kiya",
"Ram ne Office ka kiraya diya"
]

User:
Ram ne 500 ka kaam kiya.
200 rupaye liye.

Output:
[
"Ram ne 500 ka kaam kiya",
"Ram ne 200 rupaye liye"
]

because the second sentence clearly continues
Ram's transaction.

User: "Kitanu ne driving ki aur side pr 500 ka kaam
       kiya, or 600 ruppe liye"
Output:
[
    "Kitanu ne driving aur side pr 500 ka kaam kiya aur Kitanu ne 600 ruppe liye"
]

WRONG (subject dropped):
[
    "Kitanu ne driving aur side pr 500 ka kaam kiya",
    "600 ruppe liye"
]

WRONG (invented name):
[
    "Kitanu ne driving aur side pr 500 ka kaam kiya",
    "Ram ko 600 ruppe diye"
]

NOTE: It's OK to have 2 actions here since "kaam
kiya" (work) and "ruppe liye" (payment) are different
transaction_types — but BOTH must explicitly say
"Kitanu".

═══════════════════════════════
RULE 3B — NAMES STAY EXACTLY AS THE USER WROTE THEM (CRITICAL)
═══════════════════════════════

Copy every person, party and place name EXACTLY as written —
same spelling, same script. NEVER transliterate or translate a
name:
- Devanagari stays Devanagari:  "विनोद" stays "विनोद" (NOT "Vinod"),
  "जिंदल भट्टे" stays "जिंदल भट्टे" (NOT "Jindal Bhatta")
- Latin stays Latin:  "Vinod" stays "Vinod" (NOT "विनोद")
The rest of the sentence may be in any language, but names are
copied character by character.

A JOB WORD next to a name (beldar, cook, driver, mistri, munshi,
helper, chowkidar, "dukaan wala ladka", बेलदार, कुक, ड्राइवर …) only
describes THAT SAME person. It is NOT a second person and must
never become a subject ("Beldar ne …").

User: "Mistri Deepak ko 900 de diye"
Output: ["Mistri Deepak ko 900 de diye"]
WRONG:  ["Mistri ne Deepak ko 900 de diye"]

User: "मिस्त्री दीपक को 900 दे दिए"
Output: ["मिस्त्री दीपक को 900 दे दिए"]

User: "Paid mason Deepak 900"
Output: ["Paid mason Deepak 900"]

═══════════════════════════════
RULE 3C — "KO" = RECEIVER; THE OWNER IS THE GIVER (CRITICAL)
═══════════════════════════════

The user is the business OWNER. A clause like "X ko 5000 diye /
de diye / bheje / pakdaye / thamaye" WITHOUT its own "ne" means
the OWNER paid X. Keep it exactly like that.

NEVER add a giver ("Y ne …") to a "ko … diye" clause unless the
user himself wrote "Y ne" INSIDE THAT SAME clause. A person who
gave or took money in an EARLIER clause is NOT the giver of the
next "ko … diye" clause — RULE 3 inheritance does not apply here.

SHORT REFERENCES — "unko", "usko", "unhe", "use", "inko",
"bhatte ko", "bhatte wale ko", "supplier ko", उनको, उसको, भट्टे को:
- If the message names exactly ONE party that fits (one bhatta /
  one supplier / one shop), write THAT party's name exactly as
  the user wrote it.
- ONLY if two or more parties fit (or none), keep the words exactly
  as the user wrote them (the system will ask). ONE fitting party →
  ALWAYS write its name.

User: "Hanuman bhatte wali 1500 eent Gupta ji ke plot pe giri,
       Gupta ji ne poore 13500 chuka diye aur bhatte ko 9000 pakdaye"
Output: [
  "Hanuman bhatte wali 1500 eent Gupta ji ke plot pe giri",
  "Gupta ji ne poore 13500 chuka diye",
  "Hanuman bhatte ko 9000 pakdaye"
]
WRONG: "Gupta ji ne bhatte ko 9000 pakdaye"   (Gupta ji did not pay the kiln)

User: "Mama ji ne shaadi ke kapdon ke liye 1000 liye, Bajrang traders ko 4000 de diye"
Output: ["Mama ji ne shaadi ke kapdon ke liye 1000 liye", "Bajrang traders ko 4000 de diye"]
WRONG: "Mama ji ne Bajrang traders ko 4000 de diye"

User: "Ganesh bhatte wali 3000 eent parso utri thi, wahi shaam unko 8000 bheje"
Output: ["Ganesh bhatte wali 3000 eent parso utri thi", "Ganesh bhatte ko 8000 bheje"]

User: "Ganesh bhatte aur Hanuman bhatte dono se eent aayi, unko 5000 diye"
Output: ["Ganesh bhatte aur Hanuman bhatte dono se eent aayi", "unko 5000 diye"]
(two kilns fit — keep "unko", do not guess)

User: "हनुमान भट्टे से 1500 ईंट आई, उनको 9000 दिए"
Output: ["हनुमान भट्टे से 1500 ईंट आई", "हनुमान भट्टे को 9000 दिए"]

User: "Gupta ji paid 13500 and we paid the kiln 9000"   (Hanuman kiln named earlier)
Output: ["Gupta ji paid 13500", "Paid Hanuman kiln 9000"]

═══════════════════════════════
RULE 4 — ATTENDANCE VS WORK/PAYMENT (CRITICAL)
═══════════════════════════════

Distinguish between two different concepts:

ATTENDANCE statements (no money amount mentioned
for that specific part):
- "aaya" / "aaj aaya" / "pura din aaya"
- "nahi aaya" / "absent tha"
- "drivery ki" / "driving ki" (without amount)
- "aadha din kaam kiya" (without amount)
- "aadha din driving ki" / "aadha drivery ki"

These describe PRESENCE/ABSENCE/DRIVING status only
— no rupee amount is involved.

CRITICAL EXCEPTION: If "driver" or "driving" is
mentioned INSIDE a delivery/supplier transaction
context (see RULE 2B — supplier + quantity + driver
+ destination/price all together), this is NOT an
attendance statement.It is simply naming WHO
performed the delivery as part of a larger
transaction. Do not treat "Kitanu driver tha" as a
standalone attendance fact when it appears inside a
delivery sentence — it must stay merged into the
single delivery action per RULE 2B, not be pulled
out as separate attendance info.

Pure standalone attendance only applies when there
is NO supplier/delivery context, e.g.:
"Kitanu pura din aaya aur drivery ki" (standalone,
 no supplier/customer/price mentioned)

WORK/PAYMENT statements (money amount mentioned):
- "500 ka kaam kiya"
- "300 ruppe liye/diye"
- "side pr 400 ka kaam"

RULE: If the SAME employee's message has BOTH
attendance-type info AND amount-type info, keep
the attendance part as ONE combined action, and
the amount parts as SEPARATE action(s).

User: "Kitanu pura din aaya or drivery ki, side pr
       400 ka kaam kiya or 500 ruppe liye"

Output:
[
    "Kitanu pura din aaya aur drivery ki",
    "Kitanu ne side pr 400 ka kaam kiya",
    "Kitanu ne 500 ruppe liye"
]

User: "Ram pura din aaya aur aadha drivery ki, side
       pr eent bhari aur utari 350 ka kaam kiya aur
       200 ruppe liye"

Output:
[
    "Ram pura din aaya aur aadha drivery ki",
    "Ram ne side pr eent bhari aur utari 350 ka kaam kiya",
    "Ram ne 200 ruppe liye"
]

More examples:

User: "Ram aaj aaya"
Output: ["Ram aaj aaya"]

User: "Ram aaj nahi aaya"
Output: ["Ram aaj nahi aaya"]

User: "Satpal aaj driving ki"
Output: ["Satpal aaj driving ki"]

═══════════════════════════════
RULE 4B — ONE EVENT FOR SEVERAL NAMED PEOPLE
═══════════════════════════════

When one clause says the SAME thing about two or more named
people ("X aur Y", "X and Y", "dono", "both"), write ONE action
PER PERSON, each with only that person's name.

User: "Vinod aur Deepak dono aaj aadha din aaye"
Output:
[
    "Vinod aaj aadha din aaya",
    "Deepak aaj aadha din aaya"
]

User: "विनोद और दीपक आज नहीं आए"
Output:
[
    "विनोद आज नहीं आया",
    "दीपक आज नहीं आया"
]

User: "Vinod and Deepak both worked the full day"
Output:
[
    "Vinod worked the full day",
    "Deepak worked the full day"
]

User: "Vinod aur Deepak ko 500-500 diye"
Output:
[
    "Vinod ko 500 diye",
    "Deepak ko 500 diye"
]

If ONE total amount is given for several people without saying
each person's share ("dono ko milake 1000 diye"), do NOT invent a
split — keep it as ONE action exactly as said.

CRITICAL — split ONLY the clause that names the several people.
Every OTHER clause in the message (money from/to a third party, a
sale, an expense, material) belongs to NOBODY in that list — write
it ONCE, exactly as said. NEVER copy an amount into each person's
action. An amount that appears once in the user's message appears
in exactly ONE action.

User: "Vinod aur Deepak dono aaye, Gupta ji se 3000 aaye"
Output:
[
    "Vinod aaj aaya",
    "Deepak aaj aaya",
    "Gupta ji se 3000 aaye"
]

User: "विनोद और दीपक दोनों आए, गुप्ता जी से 3000 आए"
Output:
[
    "विनोद आज आया",
    "दीपक आज आया",
    "गुप्ता जी से 3000 आए"
]

User: "Vinod and Deepak both came today, got 3000 from Gupta ji"
Output:
[
    "Vinod came today",
    "Deepak came today",
    "Got 3000 from Gupta ji"
]

WRONG (amount copied into each person — this records the money
twice):
[
    "Vinod ne 3000 Gupta ji se liye",
    "Deepak ne 3000 Gupta ji se liye"
]

═══════════════════════════════
RULE 4C — A REASON STAYS WITH ITS ATTENDANCE
═══════════════════════════════

A reason or explanation for being absent, late, or leaving
early ("ghar pe kaam tha", "shaadi mein gaya", "bimaar tha",
"he had a wedding") is PART OF THE ATTENDANCE action. It is NOT
work, NOT a separate action, and NOT a work log.

User: "Deepak aaj nahi aaya, shaadi mein gaya tha"
Output:
["Deepak aaj nahi aaya, shaadi mein gaya tha"]

User: "दीपक आज नहीं आया, बीमार था"
Output:
["दीपक आज नहीं आया, बीमार था"]

User: "Deepak was absent today, he had to attend a wedding"
Output:
["Deepak was absent today, he had to attend a wedding"]

Only a clause with its OWN money or its OWN work becomes a new
action:
User: "Deepak aaj nahi aaya, par 300 udhaar le gaya"
Output:
[
    "Deepak aaj nahi aaya",
    "Deepak 300 udhaar le gaya"
]

═══════════════════════════════
RULE 4D — DESCRIPTION AND AMOUNT OF THE SAME WORK = ONE ACTION
═══════════════════════════════

When one clause says WHAT work a person did and the next clause
gives the AMOUNT for that same work ("uska 300", "uske 300",
"300 for that"), they are ONE work action.

User: "Vinod ne trolley khali ki, uske 300"
Output:
["Vinod ne trolley khali ki, 300 ka kaam"]

User: "विनोद ने ट्रॉली खाली की, उसके 300"
Output:
["विनोद ने ट्रॉली खाली की, 300 का काम"]

User: "Vinod unloaded the trolley, 300 for that"
Output:
["Vinod unloaded the trolley, work worth 300"]

RULE 4D joins ONLY when the SAME NAMED PERSON did the described
work. Work done at a PLACE with no person named ("site pe chhat
todi", "roof was broken at the site") is a separate work-log
action, even if the next clause gives some person's amount.

User: "Mandi wali site pe deewar giraayi, Vinod ne wahan 500 ka
       kaam kiya"
Output:
[
    "Mandi wali site pe deewar giraayi",
    "Vinod ne mandi wali site pe 500 ka kaam kiya"
]

User: "Pulled down a wall at the mandi site, Vinod did 500 of work
       there"
Output:
[
    "Pulled down a wall at the mandi site",
    "Vinod did 500 of work at the mandi site"
]

(This is different from RULE 5B: ATTENDANCE and WORK stay
separate. RULE 4D only joins a work description with ITS OWN
amount.)

═══════════════════════════════
RULE 4E — DRIVER OF A DELIVERY SAID IN ITS OWN CLAUSE
═══════════════════════════════

When material comes or goes and a SEPARATE clause says who drove
or brought it ("X gaadi lekar gaya", "X tractor laya", "X drove"),
the driver belongs INSIDE the material action (as "driver X").
Money paid to that driver is a SEPARATE action.

User: "Jindal bhatte se 2000 eent shop pe aayi, Deepak tractor
       laya tha, use 250 diye"
Output:
[
    "Jindal bhatte se 2000 eent shop pe aayi, driver Deepak",
    "Deepak ko 250 diye"
]

User: "जिंदल भट्टे से 2000 ईंट दुकान पे आई, दीपक ट्रैक्टर लाया था"
Output:
["जिंदल भट्टे से 2000 ईंट दुकान पे आई, ड्राइवर दीपक"]

User: "2000 bricks came to the shop from Jindal kiln, Deepak drove
       the tractor"
Output:
["2000 bricks came to the shop from Jindal kiln, driver Deepak"]

═══════════════════════════════
RULE 5 — RESOLVE PRONOUNS
═══════════════════════════════

Replace usko/uski/uska/use/usne/iska/isko with the
actual name from context.

User: "Ram ne 500 ka kaam kiya. Usko 200 diye. 
       Uska hisab bata."
Output:
[
    "Ram ne 500 ka kaam kiya",
    "Ram ko 200 diye",
    "Ram ka hisab bata"
]

═══════════════════════════════
RULE 5B — ATTENDANCE AND WORK STAY SEPARATE, EVEN WITH "usne"/"uska"
═══════════════════════════════

This reinforces Rule 4 for a specific pattern: a sentence that
states attendance/driving status, then continues with "usne"/
"uska" + a work activity (chakkar, trip, malva, eent, etc. —
NO rupee amount).

Even without a comma or "aur" between the two parts, and even
though it looks like one flowing sentence, these are TWO
different business events (Rule 4) and must become TWO actions.
Resolve "usne"/"uska" to the actual name (Rule 5) while splitting.

User: "Aaj Suresh pura din aaya drivery ki usne 3 chakar mare"
Output:
[
    "Suresh aaj pura din aaya drivery ki",
    "Suresh ne 3 chakar mare"
]

User: "Ram pura din aaya or 2 chakar mare"
Output:
[
    "Ram pura din aaya",
    "Ram ne 2 chakar mare"
]

User: "Kitanu aadha din aaya, 400 ka kaam kiya"
Output:
[
    "Kitanu aadha din aaya",
    "Kitanu ne 400 ka kaam kiya"
]

WRONG (merged into one action, work detail lost into a note):
[
    "Suresh aaj pura din aaya drivery ki, usne 3 chakar mare"
]

═══════════════════════════════
RULE 6 — DATE HANDLING
═══════════════════════════════

Convert all dates to YYYY-MM-DD and ALWAYS attach
to every action. Never create date as a separate
action.

- "aaj" / "today"  → {today}
- "kal"            → {yesterday}
- "parso"          → {parso}
- "11 june"        → {year}-06-11
- "11 june 2025"   → 2025-06-11
- "11/06/2025"     → 2025-06-11

User: "Kal Kitanu ne 500 ka kaam kiya"
Output: ["Kitanu ne 500 ka kaam kiya on {yesterday}"]

WEEKDAY NAMES — read the date from this table, never calculate:
{calendar}
User: "Budhvaar ko Vinod nahi aaya"
Output: ["Vinod Budhvaar ko nahi aaya"]   (keep the weekday word in the text)

"agle hafte ki mazdoori", "is mahine ki salary", "kal ki dihadi",
"next week's wages" say WHAT the money is for — NOT when it was
paid. Do not turn them into a date; keep them in the action text.
User: "Vinod ko agle mahine ki tankhwah ke 4000 abhi de diye"
Output: ["Vinod ko agle mahine ki tankhwah ke 4000 de diye"]

═══════════════════════════════
RULE 7 — ACCOUNT QUERIES STAY DATE-FREE BY DEFAULT
═══════════════════════════════

"hisab bata" / "poora hisab" / "baaki kitna hai"
→ NO specific date needed in the action — leave it
  general (don't attach today's date as a filter
  unless user explicitly says "aaj ka", "is mahine
  ka", "is saal ka").

═══════════════════════════════
RULE 8 — GENERAL
═══════════════════════════════

- Never calculate anything.
- Never summarize.
- Never call tools.
- Never change the meaning of the user's request.
- Preserve all details: names, amounts, dates,
  quantities, work descriptions.
- Keep original language style (Hinglish stays
  Hinglish).

Never introduce words that the user did not
explicitly say.

Do NOT rewrite

Office ka kiraya diya

as

Ram ne Office ka kiraya diya.

Do NOT rewrite

Diesel bharwaya

as

Ram ne Diesel bharwaya.

Do NOT rewrite

Bijli ka bill diya

as

Ram ne Bijli ka bill diya.

Only add a subject when the sentence is clearly
continuing the SAME transaction.

Never classify business intent beyond what is explicitly stated by the user.
"""


# ───────────────────────────────────────────────────────────────
# Guard 1 — paisa double na ho:
#   statement mein jo number jitni baar likha hai, actions mein usse
#   zyada baar nahi aa sakta ("Sohan aur Kitanu aaye, Sharma ji se 5000
#   aaye" → 5000 dono ke naam chala gaya tha). Aisa ho to LLM ko galti
#   bata ke EK baar dobara poochte hain.
# ───────────────────────────────────────────────────────────────
import re as _re

_DATE_IN_TEXT = _re.compile(r"\d{4}-\d{2}-\d{2}")
_NUM = _re.compile(r"(?<![\d.])\d[\d,]*(?:\.\d+)?(?![\d.])")


def _numbers(text):
    out = {}
    for n in _NUM.findall(_DATE_IN_TEXT.sub(" ", text or "")):
        n = n.replace(",", "")
        out[n] = out.get(n, 0) + 1
    return out


def _duplicated_amounts(user_message, actions):
    said = _numbers(user_message)
    used = {}
    for a in actions:
        for n, c in _numbers(a.text).items():
            used[n] = used.get(n, 0) + c
    return sorted(n for n, c in used.items() if n in said and c > said[n])


# ───────────────────────────────────────────────────────────────
# Guard 2 — ek hi kaam ke do tukde jodo:
#   "Ram ne load karwayi" + "Ram ne 400 ka kaam kiya"  →
#   "Ram ne load karwayi, 400 ka kaam kiya"
#   Sirf tab: same aadmi (pehla shabd), same date, pehle mein koi number
#   aur haazri ka shabd NAHI, doosra sirf "N ka kaam / work is N" hai.
#   (Haazri + kaam kabhi nahi judte — RULE 5B.)
# ───────────────────────────────────────────────────────────────
_ATTEND = _re.compile(
    r"\b(aaya|aayi|aaye|nahi aaya|chutti|chhutti|aadha din|pura din|poora din|haazri|haaziri|"
    r"drivery|driving|came|absent|present|leave|half day|full day)\b|आया|आई|छुट्टी|आधा दिन|पूरा दिन|हाज़िरी",
    _re.IGNORECASE)
_ONLY_AMOUNT = _re.compile(
    r"^\s*(?P<name>[^\s,']+)(?:'s|\s+ne|\s+का|\s+की|\s+ने|\s+ka|\s+ki)?\s+"
    r"(?P<rest>(?:\S+\s+){0,2}?\d[\d,]*\s*(?:ka kaam(?:\s+(?:aur|bhi))?(?:\s+kiya)?|ke kaam|का काम(?:\s+(?:और|भी))?(?:\s+किया)?)"
    r"|(?:work is|work was|work worth|did work worth|worth of work)\s+\d[\d,]*"
    r"|\d[\d,]*\s*(?:worth of work|of work))\s*\.?\s*$",
    _re.IGNORECASE)


def _first_word(text):
    w = (text or "").strip().split()
    return _re.sub(r"'s$", "", w[0]).lower() if w else ""


# "2 ghante extra ruka" — overtime (kaam), haazri nahi; ghante ka number amount nahi
_OVERTIME = _re.compile(
    r"\b(extra ruka|extra ruki|der tak ruka|der tak ruki|overtime|stayed late|ghante extra|ghanta extra|extra kaam)\b"
    r"|एक्स्ट्रा रुका|देर तक रुका|ओवरटाइम|घंटे एक्स्ट्रा",
    _re.IGNORECASE)
_HOURS = _re.compile(r"\d+\s*(ghante|ghanta|ghante|hours?|hrs?|घंटे|घंटा)", _re.IGNORECASE)


def _merge_split_work(actions):
    out = []
    for a in actions:
        if out:
            prev = out[-1]
            m = _ONLY_AMOUNT.match(a.text)
            prev_plain = _DATE_IN_TEXT.sub(" ", prev.text)
            overtime = bool(_OVERTIME.search(prev_plain))
            if overtime:
                prev_plain = _HOURS.sub(" ", prev_plain)     # "2 ghante" amount nahi hai
            if (m and prev.date == a.date
                    and _first_word(prev.text) == _first_word(a.text)
                    and not _NUM.search(prev_plain)
                    and (overtime or not _ATTEND.search(prev.text))):
                print(f"🔗 EXTRACT: '{prev.text}' + '{a.text}' → ek hi kaam")
                prev.text = f"{prev.text.rstrip(' .')}, {m.group('rest').strip()}"
                continue
        out.append(a)
    return out


# "…, uski bahan ki shaadi ke liye" — sirf maksad / wajah wala tukda (na amount, na apna kaam)
# alag action nahi hota; pichhle action ka hissa hai (note mein jayega).
_PURPOSE_ONLY = _re.compile(
    r"\b(ke liye|ke liya|ki wajah se|ke wajah se|kyunki|kyonki|kyuki|ke waste|ke vaaste)\b"
    r"|के लिए|की वजह से|क्योंकि|\b(for (?:his|her|their|the|a)|because)\b",
    _re.IGNORECASE)
_OWN_VERB = _re.compile(
    r"\b(diye|diya|de di|de diye|bheje|bheja|le liye|liya|mile|mila|aaya|aayi|kiya|kiye|"
    r"nikale|nikala|bechi|becha|layi|laya|gaya|gayi|chalayi|paid|gave|sent|came|did|took)\b"
    r"|दिए|दिया|भेजे|लिया|मिले|आया|किया|निकाले|बेची|गया|चलाई",
    _re.IGNORECASE)


def _merge_purpose(actions):
    from attendance_rules import strip_non_money, ATTEND_WORDS, _TASK
    out = []
    for a in actions:
        t = _DATE_IN_TEXT.sub(" ", a.text)
        rest = _PURPOSE_ONLY.sub(" ", t)
        first = (t.split() or [""])[0]
        other_person = bool(out) and first[:1].isupper() and first.isascii() and first.lower() != _first_word(out[-1].text)
        if (out and out[-1].date == a.date and _PURPOSE_ONLY.search(t)
                and not _re.search(r"\d", strip_non_money(t))
                and not _OWN_VERB.search(rest) and not ATTEND_WORDS.search(rest) and not _TASK.search(rest)
                and not _re.search(r"\b(laga do|lagao|lagana|laga de)\b|लगा दो|लगाओ", rest, _re.IGNORECASE)
                and not other_person):
            prev = out[-1]
            print(f"🔗 EXTRACT: '{a.text}' sirf maksad/wajah hai — '{prev.text}' ke saath joda")
            prev.text = f"{prev.text.rstrip(' .')}, {a.text.strip()}"
            continue
        out.append(a)
    return out


# "Ram aur Sohan ne load ki, dono ko 300-300 diye" — har aadmi ko 300 (kul 600 nahi, ek ko 600 nahi).
# Aise vaakya ko har aadmi ke alag action mein todo; baaki hissa (bikri) apne action mein rahe.
_TWO_NAMES = _re.compile(
    r"(?P<a>[A-Z][\w]*|[\u0900-\u097F]+)\s+(?:aur|और|and|&)\s+(?P<b>[A-Z][\w]*|[\u0900-\u097F]+)")
_EACH = _re.compile(
    r"(?:(?:dono|donon|dono\s+hi|both|har\s+ek|harek|each\s+of\s+them|दोनों|हर\s+एक)\s*(?:ko|को|ke|ka)?\s*)"
    r"(?:₹\s*)?(?P<n>\d[\d,]*)(?:\s*-\s*(?P=n)|\s+each|\s+per\s+head)?"
    r"|(?:₹\s*)?(?P<m>\d[\d,]*)\s*-\s*(?P=m)"
    r"|(?:₹\s*)?(?P<e>\d[\d,]*)\s+each",
    _re.IGNORECASE)



# RULE 3C ka safety net: "bhatte ko 12000 diye" → LLM ne "Saini ji ne bhatte ko 12000 diye" bana diya.
# User ne us clause mein "Saini ji ne" likha hi nahi tha → wo jodna galat hai, hata do.
_GIVER_KO = _re.compile(
    r"^(?P<pre>.*?)(?P<giver>[^\s,]+(?:\s+(?:ji|jee|sahab|saab|जी|साहब))?)\s+(?:ne|ने)\s+"
    r"(?P<rest>.*?\S\s+(?:ko|ka|ki|ke|को|का|की|के)\s+.*?(?P<amt>\d+(?:\.\d+)?).*)$", _re.IGNORECASE)
_PAY_VERB = _re.compile(
    r"\b(diye|diya|di|de\s+di|de\s+diye|de\s+diya|bheje|bheja|pakdaye|pakda|thamaye|thama|chuka\w*|bhara|bhar\s+di\w*|"
    r"paid|gave|sent)\b"
    r"|दिए|दिया|भेजे|भेजा|थमा|चुका", _re.IGNORECASE)
_CLAUSE_SPLIT = _re.compile(r"[,;।]|\s(?:aur|और|and|phir|fir)\s", _re.IGNORECASE)


_GIVER_START = _re.compile(r"^\s*(?P<giver>[^\s,]+(?:\s+(?:ji|jee|sahab|saab|जी|साहब))?)\s+(?:ne|ने)\s+", _re.IGNORECASE)


def _drop_invented_giver(actions, user_message):
    if not user_message:
        return actions
    clauses = [c.strip().lower() for c in _CLAUSE_SPLIT.split(user_message) if c and c.strip()]
    for a in actions:
        m = _GIVER_KO.match(a.text or "")
        if not m or not _PAY_VERB.search(m.group("rest")):
            continue
        if not _re.search(r"\s(?:ko|को)\s", " " + m.group("rest")) and not _re.search(
                r"(?:\b[A-Z][\w]*|\b(?:bhatte|bhatta|traders|ji|wale|wala))\s+(?:ka|ki|ke)\s", m.group("rest")):
            continue                                   # "bill ka 5000" — 'ka' se pehle koi party nahi, chhedo mat
        giver, amt = m.group("giver").lower(), m.group("amt")
        with_amt = [c for c in clauses if _re.search(rf"(?<!\d){_re.escape(amt)}(?!\d)", c)]
        if len(with_amt) != 1:
            continue                                   # rakam ka clause pakka nahi — chhedo mat
        clause = with_amt[0]
        if _re.search(rf"{_re.escape(giver)}\s+(?:ne|ने)(?![\w\u0900-\u097F])", clause):
            continue                                   # user ne khud "Y ne" likha — sahi hai
        new = (m.group("pre") + m.group("rest")).strip()
        print(f"⚠️ EXTRACT: '{a.text}' — user ne '{m.group('giver')} ne' nahi bola tha, hataya → '{new}'")
        a.text = new
    # Kharche wala action: "Mahadev ne gaadi ki service 1800 mein karwayi" — user ne "Mahadev ne" kaha hi nahi
    from expense_rules import EXPENSE_WORD
    for a in actions:
        g = _GIVER_START.match(a.text or "")
        if not g or not EXPENSE_WORD.search(a.text or ""):
            continue
        nums = _re.findall(r"\d[\d,]*", a.text)
        with_amt = [c for c in clauses if nums and _re.search(rf"(?<!\d){_re.escape(nums[0])}(?!\d)", c)]
        if len(with_amt) != 1 or _re.search(rf"{_re.escape(g.group('giver').lower())}\s+(?:ne|ने)(?![\w\u0900-\u097F])",
                                             with_amt[0]):
            continue
        new = a.text[g.end():].strip()
        new = new[:1].upper() + new[1:]
        print(f"⚠️ EXTRACT: '{a.text}' — kharcha hai, user ne '{g.group('giver')} ne' nahi bola tha → '{new}'")
        a.text = new
    return actions



# "unko 15000 de diye" / "bhatte ko 12000 diye" — message mein EK hi bhatta/supplier ho to wahi naam.
# Naam user ke apne message se aata hai; do ya zero mile to kuch nahi badalta (system poochhega).
_LEAD_TIME = r"(?:(?:aaj|kal|parso|phir|fir|usi\s+din|wahi\s+shaam|usi\s+waqt|आज|कल|फिर|उसी\s+दिन)\s+)*"
_REF_START = _re.compile(
    r"^(?P<lead>\s*" + _LEAD_TIME + r")(?P<ref>unko|usko|unhe|unhein|unhen|inko|isko|use|"
    r"bhatte\s+wale\s+ko|bhatte\s+ko|bhatta\s+ko|bhate\s+ko|bhatthe\s+ko|"
    r"उनको|उसको|उन्हें|इनको|भट्टे\s+वाले\s+को|भट्टे\s+को)(?![\wऀ-ॿ])", _re.IGNORECASE)
_OTHER_PERSON = _re.compile(r"\b(driver|ji|jee|sahab|saab|laya|layi|chala|chalaya|beldar|mistri|munshi)\b"
                           r"|ड्राइवर|जी|साहब|लाया|बेलदार|मिस्त्री", _re.IGNORECASE)
_REF_EN = _re.compile(r"\bthe\s+kiln\b", _re.IGNORECASE)
_PARTY_SUFFIX = {"bhatte", "bhatta", "bhate", "bhata", "bhatha", "bhatthe", "traders", "trader",
                 "भट्टे", "भट्टा", "ट्रेडर्स", "kiln"}
_NOT_PARTY_WORD = {"aur", "se", "ko", "ne", "ki", "ke", "ka", "dono", "the", "a", "from", "and", "paid", "us",
                   "is", "un", "unke", "uske", "pe", "par", "mein", "main", "me", "tha", "thi", "aayi", "aaya",
                   "gayi", "diye", "diya", "kal", "aaj", "parso", "usi", "din", "phir", "fir", "driver",
                   "yesterday", "today", "came", "bricks", "eent", "int", "और", "से", "को", "ने", "की", "के",
                   "का", "दोनों", "उस", "इस", "पे", "में", "था", "थी", "आई", "कल", "आज", "परसों", "ईंट", "ड्राइवर"}
_JOINER = {"wale", "wali", "wala", "वाले", "वाली", "वाला"}
_SUFFIX_CANON = {"bhatte": "bhatta", "bhate": "bhatta", "bhata": "bhatta", "bhatha": "bhatta",
                 "bhatthe": "bhatta", "भट्टे": "भट्टा", "trader": "traders", "kiln": "bhatta"}


def _parties_in(message):
    """Message ke 'X bhatte / X wale bhatte / X traders / X kiln' wale naam — jaise user ne likhe."""
    found, keys = [], set()
    for clause in _re.split(r"[,;।.!?]", message):
        toks = _re.findall(r"[A-Za-zऀ-ॿ]+", clause)
        for i, t in enumerate(toks):
            if t.lower() not in _PARTY_SUFFIX:
                continue
            name, j = [], i - 1
            while j >= 0 and len(name) < 3 and toks[j].lower() not in _NOT_PARTY_WORD \
                    and toks[j].lower() not in _PARTY_SUFFIX:
                name.insert(0, toks[j])
                j -= 1
            while name and name[0].lower() in _JOINER:
                name.pop(0)
            if not name or all(w.lower() in _JOINER for w in name):
                continue                                # akela "bhatte" — naam nahi
            core = " ".join(w.lower() for w in name if w.lower() not in _JOINER)
            key = (core, _SUFFIX_CANON.get(t.lower(), t.lower()))
            if key not in keys:
                keys.add(key)
                found.append(" ".join(name + [t]))
    return found


def _resolve_reference(actions, user_message):
    if not user_message:
        return actions
    parties = _parties_in(user_message)
    if len(parties) != 1:
        return actions                                  # 0 ya 2+ — andaza nahi
    party = parties[0]
    hindi = bool(_re.search(r"[ऀ-ॿ]", party))
    # "unko/usko" kisi aur insaan (driver, Sharma ji…) ke liye bhi ho sakta hai — tab andaza nahi.
    other_person = bool(_OTHER_PERSON.search(user_message))
    for a in actions:
        text = a.text or ""
        m = _REF_START.match(text)
        if m and other_person and not _re.search(r"bhatt?h?[ae]|भट्टे", m.group("ref"), _re.IGNORECASE):
            continue
        if m:
            new = f"{m.group('lead')}{party} {'को' if hindi else 'ko'}{text[m.end():]}"
        elif _REF_EN.search(text) and party.lower().split()[-1] == "kiln":
            new = _REF_EN.sub(party, text, count=1)
        else:
            continue
        print(f"🔗 EXTRACT: '{text}' — '{(m.group('ref') if m else 'the kiln')}' = '{party}' "
              f"(message mein yahi ek party) → '{new}'")
        a.text = new
    return actions



# "Shiv bhatte se 3000 eent aayi 21000 ki, driver Kitanu ko 300 diye" — driver ki payment maal ke
# action mein dab jaati thi. Alag action: "Kitanu ko 300 diye (driver)" → employee payment.
_DRIVER_PAY = _re.compile(
    r"[,;]?\s*(?:aur\s+|और\s+)?(?:driver|ड्राइवर)\s+(?P<name>[A-Za-zऀ-ॿ]+)\s+(?:ko|को)\s+"
    r"(?P<amt>₹?\s*\d[\d,]*(?:\.\d+)?)\s*(?:rupaye|rs\.?|₹|रुपये)?\s*"
    r"(?P<verb>de\s+diye|de\s+diya|diye|diya|bheje|pakdaye|thamaye|दे\s+दिए|दे\s+दिया|दिए|दिया)"
    r"(?![\wऀ-ॿ])", _re.IGNORECASE)
# "Kitanu laya, usko 200 diye" — laane / chalaane wala hi "usko" hai (driver), supplier nahi
_DRIVER_REF_PAY = _re.compile(
    r"(?P<name>[A-Z][A-Za-z]+|[\u0900-\u097F]+)\s+(?:gaadi\s+|tractor\s+|tempo\s+)?(?:laya|layi|lekar\s+aaya|chala\s+raha\s+tha|"
    r"chalaya|लाया|चला\s+रहा\s+था)\s*[,;]?\s*(?:aur\s+|और\s+)?(?P<ref>usko|use|unko|उसको|उसे|उनको)\s+"
    r"(?P<amt>₹?\s*\d[\d,]*(?:\.\d+)?)\s*(?:rupaye|rs\.?|₹|रुपये)?\s*"
    r"(?P<verb>de\s+diye|de\s+diya|diye|diya|दे\s+दिए|दिए|दिया)(?![\w\u0900-\u097F])")
_DRIVER_PAY_EN = _re.compile(
    r"(?:,\s*|\s+and\s+)?paid\s+(?:the\s+)?driver\s+(?P<name>[A-Za-z]+)\s+(?P<amt>₹?\s*\d[\d,]*(?:\.\d+)?)",
    _re.IGNORECASE)


def _split_driver_pay(actions):
    out = []
    for a in actions:
        text = a.text or ""
        r = _DRIVER_REF_PAY.search(text)
        if r:
            # "Kitanu laya, usko 200 diye" → maal wale action mein "Kitanu laya" rahe, payment alag
            cut = text[r.start("ref"):r.end()]
            rest = " ".join(text.replace(cut, " ").split()).strip(" ,;").replace(" ,", ",")
            rest = _re.sub(r"[,;]\s*(?:aur|और)?\s*(?=[,;]|$)", "", rest).strip(" ,;")
            if _re.search(r"\d", rest):
                hindi = bool(_re.search(r"[\u0900-\u097F]", r.group(0)))
                amt = r.group("amt").replace(" ", "")
                pay = f"{r.group('name')} {'को' if hindi else 'ko'} {amt} {'दिए' if hindi else 'diye'}"
                print(f"🚚 EXTRACT: '{text}' — '{r.group('ref')}' = laane wala {r.group('name')}: '{rest}' + '{pay}'")
                out.append(a.model_copy(update={"text": rest}))
                out.append(a.model_copy(update={"text": pay}))
                continue
        m = _DRIVER_PAY.search(text) or _DRIVER_PAY_EN.search(text)
        rest = (text[:m.start()] + text[m.end():]).strip(" ,;") if m else ""
        if not m or not _re.search(r"\d", rest):
            out.append(a)                                  # sirf driver ki payment — waise hi rakho
            continue
        name, amt = m.group("name"), m.group("amt").replace(" ", "")
        hindi = bool(_re.search(r"[ऀ-ॿ]", m.group(0)))
        english = m.re is _DRIVER_PAY_EN
        rest = f"{rest}, {'ड्राइवर' if hindi else 'driver'} {name}"
        # "(driver)" nahi jodte — "driver" shabd se haazri/driving ka tool lag sakta hai; ye sirf payment hai
        pay = (f"{name} को {amt} दिए" if hindi else f"Paid {name} {amt}" if english else f"{name} ko {amt} diye")
        print(f"🚚 EXTRACT: '{text}' — driver ki payment alag: '{rest}' + '{pay}'")
        out.append(a.model_copy(update={"text": rest}))
        out.append(a.model_copy(update={"text": pay}))
    return out



# "Mahadev reta wale se saman 600 ka aaya" + "payment kar di" — tukde mein na naam, na rakam.
# Pichhle action mein jis party SE maal aaya / jiska bill aaya, payment usi ko: "Mahadev reta wale ko payment kar di".
# Rakam baad mein argument step bharega (poori ya aadhi). Party na mile to kuch nahi badalta.
_PAY_FRAGMENT = _re.compile(
    r"\b(payment|pement|paymnt)\s+(kar|kr|ho)\s+(di|diya|dia|gayi|gai|gyi)\b"
    r"|\b(cash|nakad|paise|paisa|poore|pure|poora|aadha|adha|aadhe|adhe|half)\s+(paise\s+|payment\s+)?"
    r"(de\s+diye|de\s+diya|de\s+di|diye|diya|di|kar\s+diye|chuka\s+diye|chuka\s+diya)\b"
    r"|\b(paid\s+(in\s+)?(cash|full|half)|paid\s+half|payment\s+done)\b"
    r"|पेमेंट\s+कर\s+दी|पैसे\s+दे\s+दिए|नकद\s+दिए|कैश\s+दिया|आधा\s+दे\s+दिया|आधे\s+पैसे\s+दे\s+दिए|पूरे\s+दे\s+दिए",
    _re.IGNORECASE)
_RECEIPT_PARTY = (
    _re.compile(r"^\s*(?P<p>[^\d,;]+?)\s+(?:se|से|from)\s+(?=.*\b(?:aaya|aayi|aaye|aai|liya|li|liye|khareeda|"
                r"khareedi|utri|utra|pahunchi|came|bought)\b|.*(?:आया|आई|आए|लिया|ली|खरीदा|उतरी))", _re.IGNORECASE),
    _re.compile(r"^\s*(?P<p>[^\d,;]+?)\s+(?:ka|ki|ke|का|की|के)\s+\d[\d,]*\s*(?:rupaye\s+)?(?:ka|ki|ke|का|की|के)\s+"
                r"(?:bill|bil|बिल)", _re.IGNORECASE),
)
_GIVER_NE = _re.compile(r"^\s*(?P<g>[^\s,]+(?:\s+(?:ji|jee|sahab|जी|साहब))?)\s+(?:ne|ने)\s+", _re.IGNORECASE)


def _attach_payment_party(actions, user_message):
    out = []
    for a in actions:
        text = a.text or ""
        bare = _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", text).strip(" .")).strip(" .")
        g = _GIVER_NE.match(bare)
        if g and not _re.search(rf"{_re.escape(g.group('g'))}\s+(?:ne|ने)(?![\wऀ-ॿ])",
                                user_message or "", _re.IGNORECASE):
            bare = bare[g.end():]                      # "Krishna ne aadha de diya" — user ne 'ne' nahi bola
        if out and not _re.search(r"\d", bare) and _PAY_FRAGMENT.search(bare) \
                and not _re.search(r"\b(ko|को)\b", bare, _re.IGNORECASE) and len(bare.split()) <= 6:
            prev = _DATE_IN_TEXT.sub(" ", out[-1].text or "")
            party = None
            for rx in _RECEIPT_PARTY:
                m = rx.search(prev)
                if m and len(m.group("p").split()) <= 5:
                    party = m.group("p").strip()
                    break
            if party:
                hindi = bool(_re.search(r"[ऀ-ॿ]", bare))
                new = f"{party} {'को' if hindi else 'ko'} {bare[:1].lower() + bare[1:]}"
                print(f"💳 EXTRACT: '{text}' — payment '{party}' ko (pichhla maal/bill usi se) → '{new}'")
                out.append(a.model_copy(update={"text": new}))
                continue
        out.append(a)
    return out



# "Bijli ka bill aaya 1850 ka" + "PhonePe se bhar diya" / "aadha abhi bhara" — paisa dene wala tukda
# (na rakam, na naam) pichhle KHARCHE ka hissa hai → jod do, taaki payment usi kharche ki bane.
_EXP_PAY_FRAGMENT = _re.compile(
    r"\b(bhar\s+diya|bhar\s+diye|bhara|bhare|de\s+diya|de\s+diye|diya|diye|chuka\s+diya|chukaya|cash|nakad|phonepe|"
    r"gpay|google\s+pay|paytm|upi|online|aadha|aadhe|half|paid)\b|भर\s+दिया|भरा|दे\s+दिया|दिए|आधा|नकद", _re.IGNORECASE)


def _merge_expense_payment(actions):
    from expense_rules import EXPENSE_WORD
    out = []
    for a in actions:
        t = _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", a.text or "").strip(" .")).strip(" .")
        if out and out[-1].date == a.date and not _re.search(r"\d", t) and _EXP_PAY_FRAGMENT.search(t) \
                and not _re.search(r"(?<![\wऀ-ॿ])(ko|ne|को|ने)(?![\wऀ-ॿ])", t, _re.IGNORECASE) \
                and len(t.split()) <= 8:
            prev = out[-1]
            pt = _DATE_IN_TEXT.sub(" ", prev.text or "")
            if EXPENSE_WORD.search(pt) and _re.search(r"\d", pt) \
                    and not _re.search(r"(?<![\wऀ-ॿ])(ko|ne|को|ने)(?![\wऀ-ॿ])", pt, _re.IGNORECASE):
                print(f"🔗 EXTRACT: '{a.text}' kharche ka paisa hai — '{prev.text}' ke saath joda")
                prev.text = f"{prev.text.rstrip(' .')}, {t}"
                continue
        # ulta: "Tractor ka hydraulic theek karwaya" (bina rakam) + "1400 cash diye" (sirf rakam, koi naam nahi)
        if out and out[-1].date == a.date and _re.search(r"\d", t) and _EXP_PAY_FRAGMENT.search(t) \
                and not _re.search(r"(?<![\w\u0900-\u097F])(ko|ne|को|ने)(?![\w\u0900-\u097F])", t, _re.IGNORECASE) \
                and len(_re.sub(r"[\d,₹]+", " ", t).split()) <= 4 and not EXPENSE_WORD.search(t):
            prev = out[-1]
            pt = _DATE_IN_TEXT.sub(" ", prev.text or "")
            if EXPENSE_WORD.search(pt) and not _re.search(r"\d", pt) \
                    and not _re.search(r"(?<![\w\u0900-\u097F])(ko|ne|को|ने)(?![\w\u0900-\u097F])", pt, _re.IGNORECASE):
                print(f"🔗 EXTRACT: '{a.text}' bina-rakam kharche '{prev.text}' ki rakam hai — joda")
                prev.text = f"{prev.text.rstrip(' .')}, {t}"
                continue
        out.append(a)
    return out



# "2500 mein karwayi, nahi nahi 2800 lage" / "400 diye, nahi nahi 450 diye the" — user ne khud rakam sudhaari.
# Sirf AAKHRI rakam rahegi: N1 ki jagah N2, aur sudhaar wala tukda hat jayega (do entry nahi banegi).
_SELF_FIX = (r"(?:nahi\s+nahi|nahin\s+nahin|na\s+na|sorry|galti\s+se|matlab|i\s+mean|no\s+no|no\s+wait|"
             r"नहीं\s+नहीं|मतलब)")
_SELF_FIX_RX = _re.compile(rf"(?P<n1>\d[\d,]*)\D{{0,60}}?{_SELF_FIX}\D{{0,20}}?(?P<n2>\d[\d,]*)", _re.IGNORECASE)


def _self_correction(actions, user_message):
    m = _SELF_FIX_RX.search(user_message or "")
    if not m or m.group("n1").replace(",", "") == m.group("n2").replace(",", ""):
        return actions
    n1, n2 = m.group("n1").replace(",", ""), m.group("n2").replace(",", "")
    num = lambda n: _re.compile(rf"(?<![\d,]){_re.escape(n)}(?![\d,])")
    if not any(num(n1).search(a.text or "") for a in actions):
        return actions                                  # LLM ne pehle hi sahi kar diya
    out = []
    for a in actions:
        t = _re.sub(rf"[,;]?\s*{_SELF_FIX}\s*[^,;]*", "", a.text or "", flags=_re.IGNORECASE).strip(" ,;")
        if num(n1).search(t):
            t = num(n1).sub(n2, t, count=1)
        elif num(n2).search(t) and len(_re.sub(r"\d{4}-\d{2}-\d{2}|\bon\b", " ", t).split()) <= 5:
            print(f"✏️ EXTRACT: '{a.text}' sirf sudhaar tha ({n1} → {n2}) — alag entry nahi")
            continue
        if not t:
            continue
        if t != a.text:
            print(f"✏️ EXTRACT: '{a.text}' — user ne {n1} ko {n2} sudhaara → '{t}'")
        out.append(a.model_copy(update={"text": t}))
    return out


# "Bhai ne 2000 liye the, aaj usme se 1500 wapas kiye" / "Mummy ne 5000 diye the, aaj wo unko wapas kar diye" —
# "…the/thi" wali PURANI baat sirf sandarbh hai (wo len-den pehle ho chuka). Apni tareekh (kal/parso) na ho to
# uska alag action nahi banega; aaj wale bina-rakam action ("wahi wapas", "wo unko wapas") mein wahi rakam jaayegi.
_PAST_CLAUSE = _re.compile(
    r"(?P<who>[^\s,]+(?:\s+(?:ji|jee|sahab|saab))?)\s+(?:ne|ने)\s+(?P<mid>(?:[^\s,\d]+\s+){0,3}?)(?P<amt>\d[\d,]*)\s+(?:[^\s,\d]+\s+){0,4}?"
    r"(?:liye|liya|li|diye|diya|di|rakhe|rakha|rakhi|daale|daala|dale)\s+(?:the|thi|tha)\b"
    r"|(?P<who2>\S+)\s+ने\s+(?P<mid2>(?:\S+\s+){0,3}?)(?P<amt2>\d[\d,]*)\s+(?:\S+\s+){0,4}?(?:लिए|दिए|रखे|डाले)\s+(?:थे|थी)",
    _re.IGNORECASE)
_PAST_DATE = _re.compile(r"\b(kal|parso|pichle|pichhle|pehle\s+hafte|last)\b|कल|परसों|पिछले", _re.IGNORECASE)
_TODAY_BACK = _re.compile(r"\b(usme\s+se|usmein\s+se|wahi|wo|woh|wapas|waapas|lauta\w*)\b|उसमें से|वही|वापस",
                          _re.IGNORECASE)
_BACK_PRONOUN = _re.compile(r"\b(unko|usko|inko|unhe|unhein|use)\b|उनको|उसको|उन्हें", _re.IGNORECASE)


def _past_background(actions, user_message):
    m = _PAST_CLAUSE.search(user_message or "")
    if not m:
        return actions
    who = m.group("who") or m.group("who2")
    amt = (m.group("amt") or m.group("amt2")).replace(",", "")
    mid = m.group("mid") or m.group("mid2") or ""
    rest = user_message[m.end():] or ""
    if "," in rest:
        rest = rest.split(",", 1)[1]               # "…rakhe the galle mein, aaj wahi…" → aaj wala hissa
    rest = rest.strip(" ,.;")
    if not _TODAY_BACK.search(rest):
        return actions
    keep_past = bool(_PAST_DATE.search(mid))
    clean = lambda t: _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", t or "")).strip(" .")
    out = []
    for a in actions:
        t = clean(a.text)
        low = t.lower()
        is_past = who.lower() in low and _re.search(rf"(?<!\d){amt}(?!\d)", t.replace(",", "")) \
            and _re.search(r"\b(the|thi|tha)\b|थे|थी", low)
        if is_past:
            if not keep_past:
                print(f"🕰️ EXTRACT: '{a.text}' purani baat hai (sirf sandarbh) — alag entry nahi")
                continue
            out.append(a)
            continue
        if not _re.search(r"\d", t) and _TODAY_BACK.search(t):
            r = _re.sub(r"^\s*(aaj|आज)\s+", "", rest, flags=_re.IGNORECASE)
            if _BACK_PRONOUN.search(rest):
                new = f"{who} ko {amt} wapas kar diye"
            else:
                r = _re.sub(r"\b(wahi|wo|woh)\b|वही", amt, r, count=1, flags=_re.IGNORECASE)
                if not _re.search(r"\d", r):
                    r = f"{amt} {r}"
                new = r if who.lower() in r.lower() else f"{who} {r}"
            print(f"🕰️ EXTRACT: '{a.text}' — rakam purani baat se ({amt}) → '{new}'")
            out.append(a.model_copy(update={"text": new}))
            continue
        if _re.search(rf"\b{_re.escape(who)}\s+ko\b", t, _re.IGNORECASE) and not _re.search(r"\bko\b|को", rest) \
                and not _BACK_PRONOUN.search(rest) and _re.search(r"\b(wapas|waapas|lauta\w*)\b|वापस", t, _re.IGNORECASE):
            new = _re.sub(rf"\b{_re.escape(who)}\s+ko\b", f"{who} ne", t, count=1, flags=_re.IGNORECASE)
            print(f"🕰️ EXTRACT: '{a.text}' — {who} ne khud wapas kiye (user ne '{who} ko' nahi kaha) → '{new}'")
            out.append(a.model_copy(update={"text": new}))
            continue
        out.append(a)
    return out


# "Beta SBI bhatte se 2000 eent le aaya" + "12000 dene baaki hain" — bina naam ki baaki rakam usi maal ki hai.
_DUE_FRAGMENT = _re.compile(
    r"^\s*(?:₹\s*)?\d[\d,]*\s*(?:rupaye|rs)?\s*(?:dene|lene|dena|lena)?\s*(?:baaki|baki|udhaar|udhar)\s*(?:hain|hai|he|h)?\s*$"
    r"|^\s*\d[\d,]*\s*(?:dene|lene)\s+(?:hain|hai)\s*$", _re.IGNORECASE)


def _merge_due_amount(actions):
    from sale_rules import has_goods
    out = []
    for a in actions:
        t = _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", a.text or "")).strip(" .")
        if out and out[-1].date == a.date and _DUE_FRAGMENT.match(t):
            prev = out[-1]
            if has_goods(prev.text) and len(_re.findall(r"\d[\d,]*", _DATE_IN_TEXT.sub(" ", prev.text))) <= 1:
                print(f"🔗 EXTRACT: '{a.text}' usi maal ki baaki rakam — '{prev.text}' ke saath joda")
                prev.text = f"{prev.text.rstrip(' .')}, {t}"
                continue
        out.append(a)
    return out


# "Sharma ji ka hisab clear ho gaya" + "4000 de gaye" — bina naam ki rakam usi naam wale ki hai.
# "Jindal steel se sariya aaya" + "10,000 diye" → "Jindal steel KO 10,000 diye" (humne liya, humne diya);
# "Sharma ji ko eent gayi" + "3000 haath mein diye" → "Sharma ji NE 3000 haath mein diye" (humne becha, unhone diya).
_NAMELESS_AMOUNT = _re.compile(
    r"^\s*(?:₹\s*)?(\d[\d,]*)\s*(?:rupaye|rs)?\s*(?:(haath\s+mein|haath\s+me|cash|nakad|online|phonepe|gpay|paytm)\s+)?"
    r"(de\s+ga\w*|de\s+diye|de\s+diya|diye|diya|kiye|mile|aaye|aa\s+gaye|pakdaye)\s*$", _re.IGNORECASE)
_LEAD_NAME = _re.compile(r"^\s*((?:[A-Z][a-z]+\s+){0,2}[A-Z][a-z]+\s+(?:ji|jee|sahab|saab|seth|bhai))\b"
                         r"|^\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:ka|ki|ke)\b")
_LEAD_PARTY = _re.compile(r"^\s*([A-Z][\w]*(?:\s+[\w]+){0,2}?)\s+(se|ko)\s+")
_GOT_GOODS = _re.compile(r"\b(aaya|aayi|aaye|aa\s+gay\w*|li|liya|liye|kharid\w*|khareed\w*|utri|utra|utre)\b", _re.IGNORECASE)
_GAVE_GOODS = _re.compile(r"\b(di|diye|diya|gayi|gaya|gaye|becha|bechi|beche|bheji|bheja|bheje)\b", _re.IGNORECASE)
_BIG_THING = _re.compile(r"\b(haveli|kothi|makaan|makan|dukaan|dukan|building|plot|dharamshala|godown|machine|generator|"
                         r"tractor|trolley|jcb|gaadi|truck|sariya|shahteer|girder|lakdi|malba)\b", _re.IGNORECASE)
_HIRE_THING = _re.compile(r"\b(jcb|crane|hydra|tempo|tanker|tent)\b", _re.IGNORECASE)
_THEY_PAID = _re.compile(r"^(de\s+ga\w*|mile|aaye|aa\s+gaye)$", _re.IGNORECASE)


def _nameless_amount(actions, user_message=""):
    msg = (user_message or "").lower()
    out = []
    for a in actions:
        t = _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", a.text or "")).strip(" .")
        m = _NAMELESS_AMOUNT.match(t)
        prev = out[-1] if (m and out and out[-1].date == a.date) else None
        frag = None
        if prev is not None:
            amt, method, verb = m.group(1), m.group(2), m.group(3)
            mid = f"{amt} {method} {verb}" if method else f"{amt} {verb}"
            from sale_rules import has_goods
            if _re.search(r"\b(usko|unko|use|isko|inko|usse|unhe|use)\s+(?:₹\s*)?" + _re.escape(amt.replace(",", "")) + r"\b",
                          msg.replace(",", "")):
                # "Kitanu laya, usko 200 diye" — 'usko' = driver / pichhla aadmi, party nahi
                dm = _re.search(r"\bdriver\s+([A-Z][a-z]+)\b|\b([A-Z][a-z]+)\s+(?:\S+\s+)?(?:laya|layi|le\s+aaya|le\s+gaya|"
                                r"chhod\w*|lekar)\b", prev.text or "")
                if dm:
                    frag = f"{(dm.group(1) or dm.group(2))} ko {mid}"
                    print(f"🔗 EXTRACT: '{a.text}' — 'usko' = {(dm.group(1) or dm.group(2))} (maal laane wala) → '{frag}'")
                    a.text = frag
                out.append(a)
                continue
            pp = _LEAD_PARTY.match(prev.text or "")
            if pp and not (has_goods(prev.text) or _BIG_THING.search(prev.text)):
                pp = None                                          # sirf paisa tha ("Ramesh ko 500 diye") — disha pakki nahi
            if pp and pp.group(2).lower() == "se" and _GOT_GOODS.search(prev.text):
                frag = f"{pp.group(1).strip()} ko {mid}"           # humne maal liya → humne paisa diya
            elif pp and pp.group(2).lower() == "ko" and _GAVE_GOODS.search(prev.text):
                frag = f"{pp.group(1).strip()} ne {mid}"           # humne maal diya → unhone paisa diya
            elif _HIRE_THING.search(prev.text or "") and not _re.search(r"\b(ko|ne)\b", prev.text or ""):
                # "JCB 3 ghante chali Haluwas site pe" + "3600 de diye" — usi kiraye ka paisa, alag aadmi nahi
                prev.text = f"{prev.text.rstrip(' .')}, {mid}"
                print(f"🔗 EXTRACT: '{a.text}' bina naam ki rakam — kiraye ki cheez wale tukde mein joda: '{prev.text}'")
                continue
            else:
                nm = _LEAD_NAME.match(prev.text or "")
                if nm and (_THEY_PAID.match(verb) or verb.lower() in ("de diye", "de diya", "diye")) and not method:
                    frag = f"{(nm.group(1) or nm.group(2)).strip()} ne {mid}"
        if frag:
            if not _re.search(r"\d", _DATE_IN_TEXT.sub(" ", prev.text)):
                print(f"🔗 EXTRACT: '{a.text}' bina naam ki rakam — '{prev.text}' ke saath joda → '{frag}'")
                prev.text = f"{frag}, {prev.text.strip(' .')}"
                continue
            print(f"🔗 EXTRACT: '{a.text}' bina naam ki rakam → '{frag}'")
            a.text = frag
        out.append(a)
    return out


# "Kitanu chhod ke aaya" / "Kitanu trolley laya" — sirf driver ki baat; maal wale action mein ", driver Kitanu" jodo.
_DRIVER_ONLY = _re.compile(
    r"^\s*([A-Z][a-z]+)\s+(?:(?:trolley|tractor|gaadi|gadi|tempo|truck)\s+(?:mein|me|se|lekar)?\s*)?"
    r"(?:chhod\s+(?:ke\s+|kar\s+)?(?:aaya|gaya)|le\s+gaya|le\s+aaya|laya|pahuncha\s+(?:ke\s+|kar\s+)?aaya|"
    r"lekar\s+(?:aaya|gaya))\s*$")


def _driver_fragment(actions):
    from sale_rules import has_goods
    out = []
    for a in actions:
        t = _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", a.text or "")).strip(" .")
        m = _DRIVER_ONLY.match(t)
        goods = [b for b in actions if b is not a and has_goods(b.text) and b.date == a.date]
        if m and goods:
            g = goods[0]
            g.text = f"{g.text.rstrip(' .')}, driver {m.group(1)}"
            print(f"🚚 EXTRACT: '{a.text}' sirf driver ki baat — maal wale action mein joda: '{g.text}'")
            continue
        out.append(a)
    return out


# Extract ne "<Naam> ko 3000 …" bana diya par asli message mein "<Naam> ko" hai hi nahi → naam hatao (bana hua).
_INVENTED_KO = _re.compile(r"^\s*([A-Z][\w]*(?:\s+(?:ji|jee|sahab|saab|bhai))?)\s+ko\s+(?=\d)")


def _drop_invented_ko(actions, user_message):
    low = " ".join((user_message or "").lower().split())
    for a in actions:
        m = _INVENTED_KO.match(a.text or "")
        first = _re.escape(m.group(1).split()[0].lower()) if m else ""
        if m and not _re.search(r"(?<!\w)" + first + r"(?:\s+\S+){0,2}?\s+ko\b", low):
            new = (a.text[m.end():]).strip()
            print(f"✂️ EXTRACT: '{a.text}' — '{m.group(1)} ko' message mein nahi tha → '{new}'")
            a.text = new
    return actions


# "Mummy ne 3000 maange the" + "Mummy ko 3000 de diye" — maangna paisa nahi hilaata; wahi rakam di gayi to sirf ek entry.
_REQUEST_ONLY = _re.compile(r"\b(maange|maanga|maangi|mange|manga|mangi|bola|boli|kaha|chahiye)\s+(the|tha|thi)\b", _re.IGNORECASE)
_PAID_IT = _re.compile(r"\b(diye|diya|de\s+diye|de\s+diya|de\s+di|pakdaye|pakda\s+diye|thama\w*|bhej\s+diye)\b",
                       _re.IGNORECASE)


def _drop_request(actions):
    def nums(t):
        return set(_re.findall(r"\d[\d,]*", _DATE_IN_TEXT.sub(" ", t or "")))
    out = list(actions)
    for a in actions:
        if not _REQUEST_ONLY.search(a.text or "") or _PAID_IT.search(a.text or ""):
            continue
        n = nums(a.text)
        if n and any(b is not a and n & nums(b.text) and _PAID_IT.search(b.text or "") for b in actions):
            print(f"✂️ EXTRACT: '{a.text}' sirf maangne ki baat — wahi rakam di gayi, alag entry nahi")
            out.remove(a)
    return out


# "Ghar ke liye 25 kilo aata aaya" + "daal 1800 ki aayi" — 25 KILO hai, rakam nahi → paise wale tukde mein jodo.
_QTY_NUM = _re.compile(r"\d[\d,.]*\s*(kilo|kg|litre|liter|ltr|bori|bag|packet|pack|darjan|dozen|meter|metre|quintal)\b",
                       _re.IGNORECASE)
_HOME_CTX = _re.compile(r"\b(ghar|ghr)\b|घर", _re.IGNORECASE)


def _qty_only_merge(actions):
    def money_nums(t):
        t = _QTY_NUM.sub(" ", _DATE_IN_TEXT.sub(" ", t or ""))
        return _re.findall(r"\d[\d,]*", t)
    out = list(actions)
    for a in actions:
        t = a.text or ""
        if not _QTY_NUM.search(t) or money_nums(t) or not _HOME_CTX.search(t):
            continue
        money = [b for b in out if b is not a and b.date == a.date and money_nums(b.text)]
        if len(money) == 1:
            b = money[0]
            b.text = f"{b.text.rstrip(' .')} ({t.strip(' .')})"
            print(f"🔗 EXTRACT: '{t}' mein sirf maal ki ginti (kilo/bori…) — rakam wale tukde mein joda: '{b.text}'")
            out.remove(a)
    return out


# "Rajbir ka mobile 9416012345, Bhiwani bus adde ke paas dukaan hai" — sirf profile (phone / pata); tukde mat todo.
_PROFILE_HINT = _re.compile(r"(?<!\d)\d{10}(?!\d)|\b(pata|address)\b|पता",
                            _re.IGNORECASE)
_DEAL_VERB = _re.compile(r"\b(diye|diya|di|de\s+diye|aaye|aaya|aayi|mile|mila|becha|bechi|beche|li|liya|liye|bheji|bheja|"
                         r"kaam\s+kiya|kharid\w*|chukaya|chuka\s+diya|le\s+gaya|le\s+gaye)\b"
                         r"|दिए|दिया|आए|आया|बेची|लिया|भेजी", _re.IGNORECASE)


def _profile_whole(actions, user_message):
    msg = (user_message or "").strip()
    if len(actions) < 2 or not _PROFILE_HINT.search(msg) or _DEAL_VERB.search(msg):
        return actions
    first = actions[0]
    print(f"📇 EXTRACT: '{msg}' sirf profile ki baat (phone / pata) — ek hi action rakha")
    return [first.model_copy(update={"text": msg})] if hasattr(first, "model_copy") else actions


# "Papa ke haath galle se 3000 gaye" + "Ghar pe kaam tha" — doosra tukda sirf WAJAH hai, alag kaam nahi.
_REASON_ONLY = _re.compile(
    r"^\s*(?:(?:ghar|gaon|wahan|udhar|unke|uske)\s+(?:pe|par|mein|me)\s+)?(?:kuch\s+)?"
    r"(?:kaam|zaroorat|zarurat|jaroorat|jarurat|function|shaadi|pooja|puja)\s+(?:tha|thi|the|aa\s+gaya\s+tha|aa\s+gayi\s+thi|pad\s+gaya)\s*$"
    r"|^\s*(?:घर|गांव)\s+(?:पे|पर|में)\s+(?:कुछ\s+)?(?:काम|ज़रूरत|जरूरत)\s+(?:था|थी)\s*$", _re.IGNORECASE)


def _merge_reason(actions):
    out = []
    for a in actions:
        t = _re.sub(r"\s+on\s*$", "", _DATE_IN_TEXT.sub(" ", a.text or "")).strip(" .")
        if out and out[-1].date == a.date and _REASON_ONLY.match(t) and _re.search(r"\d", _DATE_IN_TEXT.sub(" ", out[-1].text)):
            prev = out[-1]
            print(f"🔗 EXTRACT: '{a.text}' sirf wajah hai — '{prev.text}' ka purpose")
            prev.text = f"{prev.text.rstrip(' .')}, {t}"
            continue
        out.append(a)
    return out


# "Kitanu ne gudam saaf kiya" + "Kitanu ko 400 de diye" — bina rakam ka kaam usi aadmi ke payment ka purpose hai
# (alag kaam-entry ke liye rakam poochna galat). Haazri wale action ko nahi chhoota.
_WORK_VERB = _re.compile(r"\b(kiya|kiye|lagaya|lagaye|sambhala|saaf|utara|utari|utare|chadhaya|chadhayi|load|bharaya|bhari)\b",
                         _re.IGNORECASE)
_PAY_THIS = _re.compile(r"\b(diye|diya|de\s+diye|de\s+diya|de\s+di|pakda\w*|thama\w*)\b", _re.IGNORECASE)


def _merge_work_into_pay(actions):
    from attendance_rules import ATTEND_WORDS
    out = []
    i = 0
    while i < len(actions):
        a = actions[i]
        nxt = actions[i + 1] if i + 1 < len(actions) else None
        t = _DATE_IN_TEXT.sub(" ", a.text or "")
        g = _GIVER_START.match(t)
        if nxt is not None and g and nxt.date == a.date and not _re.search(r"\d", t) and _WORK_VERB.search(t) \
                and not ATTEND_WORDS.search(t):
            who = g.group("giver")
            nt = _DATE_IN_TEXT.sub(" ", nxt.text or "")
            if _re.search(r"\d", nt) and _PAY_THIS.search(nt) and \
                    _re.search(rf"\b({_re.escape(who)}|usko|unko|use)\b", nt, _re.IGNORECASE):
                new = f"{nxt.text.rstrip(' .')}, {t.strip(' .')}"
                print(f"🔗 EXTRACT: '{a.text}' (bina rakam ka kaam) — '{nxt.text}' ka purpose → '{new}'")
                out.append(nxt.model_copy(update={"text": new}))
                i += 2
                continue
        out.append(a)
        i += 1
    return out


# "SBI wali 2000 eent aaj gudam aayi, unme 100 tooti nikli" — "unme se N tooti" usi maal ka nuksaan hai,
# naya maal nahi (LLM ne "SBI wali 100 tooti eent aayi" bana diya tha) → "<jagah> mein N <maal> tooti nikli"
_PART_DAMAGED = _re.compile(
    r"\b(?:unme|unmein|unmen|usme|usmein|inme|inmein)\s+(?:se\s+)?(\d[\d,]*)\s+(?:\w+\s+){0,2}?"
    r"(tooti|tuti|toot\w*|kharab|bekaar|bekar|kam)\b", _re.IGNORECASE)


def _part_damaged(actions, user_message):
    m = _PART_DAMAGED.search(user_message or "")
    if not m:
        return actions
    from sale_rules import goods_word
    from stock_rules import place_in
    n = m.group(1).replace(",", "")
    item = goods_word(user_message) or "maal"
    place = place_in(user_message) or "Gudam"
    for a in actions:
        if _re.search(rf"(?<!\d){n}(?!\d)", a.text or ""):
            new = f"{place} mein {n} {item} {m.group(2)} nikli"
            if a.text != new:
                print(f"🧱 EXTRACT: '{a.text}' — usi maal ka nuksaan → '{new}'")
                a.text = new
            break
    return actions


# "Saini ji ka godown liya tha 2.5 lakh ka, aaj aadha de diya" — purana sauda sirf sandarbh hai (naya purchase nahi);
# "aadha" = us purane sauda ki aadhi rakam. ("liya tha … N ka" + baad mein "aadha/aadhe/half")
_OLD_DEAL = _re.compile(r"\b(?:liya\s+tha|li\s+thi|kharida\s+tha|khareeda\s+tha|kharidi\s+thi|khareedi\s+thi)\b", _re.IGNORECASE)
_HALF_WORD = _re.compile(r"\b(aadha|aadhe|aadhi|half)\b|आधा|आधे", _re.IGNORECASE)


def _old_deal_half(actions):
    old = [a for a in actions if _OLD_DEAL.search(a.text or "") and _re.search(r"\d", _DATE_IN_TEXT.sub(" ", a.text))]
    if len(old) != 1 or len(actions) < 2:
        return actions
    o = old[0]
    nums = [float(n.replace(",", "")) for n in _re.findall(r"(?<![\d.])\d[\d,]*(?:\.\d+)?", _DATE_IN_TEXT.sub(" ", o.text))]
    if not nums:
        return actions
    total = max(nums)
    out = []
    for a in actions:
        if a is o:
            print(f"🕰️ EXTRACT: '{a.text}' purana sauda hai (sirf sandarbh) — naya purchase nahi")
            continue
        t = _DATE_IN_TEXT.sub(" ", a.text or "")
        if _HALF_WORD.search(t) and not _re.search(r"\d", t):
            new = _HALF_WORD.sub(f"{total / 2:g}", a.text, count=1)
            print(f"🕰️ EXTRACT: '{a.text}' — aadha = purane sauda ({total:g}) ka aadha → '{new}'")
            a = a.model_copy(update={"text": new})
        out.append(a)
    return out


# "Malik sahab se dukaan 150000 mein li, 50000 cash diye, 100000 PhonePe kiye" — ek action mein do payment
# (alag tarike) → har payment ka alag action, taaki dono entry banein (ek action pe ek tool ek hi baar lagta hai)
_PAY_WITH_METHOD = _re.compile(
    r"(?P<amt>\d[\d,]*)\s*(?:rupaye\s*)?(?P<m>cash|nakad|phonepe|phone\s*pe|gpay|google\s*pay|paytm|upi|online|cheque|bank)"
    r"\s+(?:se\s+)?(?:diye|diya|di|kiye|kiya|bheje|bheja|kar\s+diye|transfer\s+kiye)?", _re.IGNORECASE)


def _split_method_payments(actions):
    out = []
    for a in actions:
        t = a.text or ""
        pays = list(_PAY_WITH_METHOD.finditer(t))
        g = _re.match(r"^\s*([A-Z][\w]*(?:\s+(?:ji|sahab|saab|seth))?)\s+(?:se|ko|ne|ka|ki)\b", t)
        if len(pays) < 2 or not g:
            out.append(a)
            continue
        who = g.group(1)
        head = t[:pays[0].start()].rstrip(" ,")
        if _re.search(r"\d", head):
            out.append(a.model_copy(update={"text": head}))
        for p in pays:
            out.append(a.model_copy(update={"text": f"{who} ko {p.group('amt')} {p.group('m')} diye"}))
        print(f"✂️ EXTRACT: '{t}' — do alag payment (tarike alag) — har payment ka alag action")
    return out


def _split_each_person(actions):
    out = []
    for a in actions:
        clauses = [c.strip() for c in _re.split(r"\s*,\s*", a.text) if c.strip()]
        di = next((i for i, c in enumerate(clauses) if _EACH.search(c)), None)
        ni = None
        if di is not None:
            ni = next((i for i in range(di, -1, -1) if _TWO_NAMES.search(clauses[i])), None)
        if di is None or ni is None:
            out.append(a)
            continue
        names = _TWO_NAMES.search(clauses[ni])
        m = _EACH.search(clauses[di])
        n = m.group("n") or m.group("m") or m.group("e")
        hindi = bool(_re.search(r"[\u0900-\u097F]", a.text))
        english = not hindi and bool(_re.search(r"\b(paid|gave|each|both)\b", clauses[di], _re.IGNORECASE))
        task = clauses[ni][names.end():].strip() if ni != di else ""
        dclause = clauses[di] if ni != di else (clauses[di][:names.start()] + clauses[di][names.end():]).strip()
        people = []
        for who in (names.group("a"), names.group("b")):
            if english:
                pay = _EACH.sub(f"{who} {n}", dclause).replace(" both ", " ")
            else:
                pay = _EACH.sub(f"{who} {'को' if hindi else 'ko'} {n}", dclause)
                pay = _re.sub(r"\b(dono|donon|both)\s+", "", pay, flags=_re.IGNORECASE).replace("दोनों ", "")
            # paisa pehle, kaam baad mein (bracket mein) — warna "load ki" ko alag 'work' entry samjha jaata hai
            if task:
                task_txt = f"{who} {task}" if not english else f"{who} {task}"
                text = f"{pay} ({task_txt})"
            else:
                text = pay
            text = " ".join(text.split())
            people.append(a.model_copy(update={"text": text}))
        rest = [c for i, c in enumerate(clauses) if i not in (ni, di)]
        print(f"✂️ EXTRACT: '{a.text}' — har aadmi ko {n} → {[p.text for p in people]}")
        if rest:
            out.append(a.model_copy(update={"text": ", ".join(rest)}))
        out.extend(people)
    return out


from number_words import normalize_numbers


_REDUCE = _re.compile(
    r"\b(kam karne|kam karo|kam kar do|kam kar diye|kaat do|kaatne|kaat lo|minus|ghata do|ghatana|reduce|deduct)\b"
    r"|कम करने|कम कर|काट|घटा", _re.IGNORECASE)


def _merge_sale_fragments(actions):
    """
    "Poore paise mil gaye" / "GPay se payment aayi" (na rakam, na naam) → pichhli bikri ka hissa.
    "Rohit ka phone theek kiya" + "Rohit ko 800 liye" → ek action (seva + uska paisa).
    """
    from attendance_rules import strip_non_money
    from sale_rules import received, SERVICE, is_return
    out = []
    for a in actions:
        t = _DATE_IN_TEXT.sub(" ", a.text)
        if out and out[-1].date == a.date:
            prev = out[-1]
            no_num = not _re.search(r"\d", strip_non_money(t))
            first = (t.split() or [""])[0]
            named = first[:1].isupper() and first.isascii() and first.lower() not in (
                "poore", "pure", "paise", "payment", "gpay", "upi", "cash", "nakad", "phonepe", "paytm", "got", "received")
            if (is_return(prev.text) and _re.search(r"\d", t) and _REDUCE.search(t)
                    and _first_word(prev.text) == _first_word(a.text)):
                print(f"🔗 EXTRACT: '{a.text}' wapsi ki rakam hai — '{prev.text}' ke saath joda")
                prev.text = f"{prev.text.rstrip(' .')}, {a.text.strip()}"
                continue
            if received(t) and no_num and not named and _re.search(r"\d", prev.text):
                print(f"🔗 EXTRACT: '{a.text}' bikri ka paisa hai — '{prev.text}' ke saath joda")
                prev.text = f"{prev.text.rstrip(' .')}, {a.text.strip()}"
                continue
            if (SERVICE.search(prev.text) and not _re.search(r"\d", strip_non_money(prev.text))
                    and _re.search(r"\d", t) and _first_word(prev.text) == _first_word(a.text)):
                print(f"🔗 EXTRACT: '{prev.text}' seva hai — '{a.text}' (uska paisa) ke saath joda")
                prev.text = f"{prev.text.rstrip(' .')}, {a.text.strip()}"
                continue
        out.append(a)
    return out


async def extract_node(state):
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    parso = today - timedelta(days=2)

    prompt = EXTRACT_PROMPT.format(
        today=today.strftime("%Y-%m-%d"),
        yesterday=yesterday.strftime("%Y-%m-%d"),
        parso=parso.strftime("%Y-%m-%d"),
        year=today.year,
        calendar=calendar_block(today.date()),
    )
    user_message = state["messages"][-1].content
    normalized = normalize_numbers(user_message)
    if normalized != user_message:
        print(f"🔢 EXTRACT: number-shabd → ank: '{user_message}' → '{normalized}'")
        user_message = normalized
    result = await structured_llm.ainvoke(f"{prompt}\n\nUser Input:\n{user_message}")

    dup = _duplicated_amounts(user_message, result.actions)
    if dup:
        print(f"⚠️ EXTRACT: amount {dup} statement se zyada baar actions mein aaya — dobara pooch rahe hain")
        bad = "\n".join(f"- {a.text}" for a in result.actions)
        retry = await structured_llm.ainvoke(
            f"{prompt}\n\nUser Input:\n{user_message}\n\n"
            f"Your previous output was WRONG:\n{bad}\n"
            f"The amount(s) {', '.join(dup)} appear in the user's message fewer times than in your "
            f"actions. Each amount must appear in exactly as many actions as the user said it — "
            f"attach it only to the party it belongs to (RULE 4B). Return the corrected actions."
        )
        if not _duplicated_amounts(user_message, retry.actions):
            result = retry
        else:
            print("⚠️ EXTRACT: dobara bhi amount double — dusra jawaab rakha, aage confirmation mein dikhega")
            result = retry

    result.actions = _split_each_person(_merge_sale_fragments(_merge_purpose(_merge_split_work(
        _merge_expense_payment(_attach_payment_party(_split_driver_pay(_resolve_reference(_drop_invented_giver(
            _self_correction(result.actions, user_message), user_message), user_message)), user_message))))))
    result.actions = _merge_reason(_merge_due_amount(_past_background(result.actions, user_message)))
    result.actions = _part_damaged(_merge_work_into_pay(result.actions), user_message)
    result.actions = _nameless_amount(_driver_fragment(_drop_invented_ko(
        _split_method_payments(_old_deal_half(result.actions)), user_message)), user_message)
    result.actions = _qty_only_merge(_drop_request(result.actions))
    result.actions = _profile_whole(result.actions, user_message)
    return {
        "extracted_intent": result,
        "person_role_rankings": RESET,
        "person_role_hitl_requests": RESET,
        "person_role_hitl_responses": RESET,
        "resolved_person_roles": RESET,
        "material_movement_results": RESET,
        "material_movement_progress": RESET,
        "transaction_classifier_results": RESET,
        "tool_decision_results": None,
        "tool_argument_results": None,
        "tool_argument_updates": None,
        "final_confirmation_results": None,
        "tool_execution_results": None,
        "correction_data": None,
    }


