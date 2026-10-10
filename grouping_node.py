from langchain_core.messages import SystemMessage, HumanMessage
from llm_setup import llm
import re
from schemas import GroupedIntent, RecordType
from item_mapper import ITEM_ALIASES, LOCATION_ALIASES

# "unko 15000 diye" resolve nahi hua → group ka naam "UNKNOWN"/"unko". Ye kisi insaan ka naam nahi —
# role ka sawaal ("unko kaun hai?") bekaar hai aur galat entry bana sakta hai. Aise group ki entry nahi
# banegi; jawaab mein user ko bataya jayega "samajh nahi aaya — kisko diye likh ke bhejo".
_REFERENCE_ONLY = {"", "unknown", "unko", "usko", "unhe", "unhein", "use", "inko", "isko", "bhatte", "bhatta",
                   "bhate", "bhata", "bhatte wale", "bhatte wala", "them", "him", "the kiln", "kiln", "supplier",
                   "उनको", "उसको", "उन्हें", "इनको", "भट्टे", "भट्टा", "भट्टे वाले"}


def unresolved_reference(group) -> bool:
    if group.record_type != RecordType.NEED_PERSON:
        return False
    key = " ".join(str(group.identity_key or "").strip().lower().split())
    return key in _REFERENCE_ONLY


structured_llm = llm.with_structured_output(GroupedIntent)

GROUPING_PROMPT = """
You are a Business Action Grouping Engine.

You will receive a FINAL list of extracted business actions.
The actions are already finalized.

Your ONLY responsibility is to organize the existing actions into Action Groups.

═══════════════════════════════
IMPORTANT — GROUPING NEVER CHANGES EXTRACTION
═══════════════════════════════

DO NOT:
- Create actions
- Delete actions
- Merge actions
- Split actions
- Rewrite actions
- Reorder actions

Every input action MUST appear exactly once, unchanged, in exactly one group.

═══════════════════════════════
WHAT IS AN ACTION GROUP?
═══════════════════════════════

An Action Group bundles ALL actions that describe the SAME
real-world entity or the SAME single transaction, based on
matching identity keys (see below).

IMPORTANT — A group is NOT the same as a single database record.
A group can contain MULTIPLE distinct transactions (e.g., a work
entry, a payment, and a query) that all belong to the SAME entity
— each of these may still become a SEPARATE database entry
downstream. Grouping's job is only to bundle actions by shared
identity, not to decide how many database records will result.

This system is designed to be business-agnostic — the same 3
generic grouping types apply whether the business trades bricks,
groceries, hardware, or anything else.

Grouping never uses business-specific labels such as:

- Employee
- Supplier
- Customer
- Contractor
- Driver

Those business-specific roles are resolved in a LATER stage.

Grouping only cares about:

- generic event type
- explicit material movement
- explicit person identity
- grouping identity

The grouping types are:

- NEED_PERSON
- MATERIAL_MOVEMENT
- STANDALONE_TRANSACTION

═══════════════════════════════
THE 4 GROUPING TYPES
═══════════════════════════════

Every action belongs to EXACTLY ONE of these 4 generic grouping
categories:

- NEED_PERSON
- MATERIAL_MOVEMENT
- STANDALONE_TRANSACTION
- CORRECTION

1. NEED_PERSON

A specifically named individual is mentioned, but their business
role is AMBIGUOUS and needs to be resolved later.

Examples:
- "Ram ko 200 diye"
- "Sandeep ne kaam kiya"
- "Ram ka hisab bata"
- "Ram aaj aaya"
- "Rakesh aaj nahi aaya"
- "Satpal ne driving ki"
- "Vikram pura din aaya driving ki, 5 chakar mare"

CRITICAL — A specifically named individual's attendance status
(present/absent/driving), even with NO amount and NO work
description, is STILL NEED_PERSON — never STANDALONE_TRANSACTION.
The presence of a specific person's name is what matters, not
whether an amount or detailed work description is present.

IMPORTANT:
A generic reference such as "5 labour", "workers", "majdoor",
or "labour" without a specific person's name is NOT NEED_PERSON.
The distinguishing factor is whether an ACTUAL PERSON'S NAME
is present — "Rakesh nahi aaya" has a name (NEED_PERSON), while
"5 labour the" has only a count, no name (STANDALONE_TRANSACTION).


2. MATERIAL_MOVEMENT

The action explicitly describes material, item, or goods moving
from a source to a destination.

At the grouping stage, DO NOT decide whether the movement is:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

Those classifications require business/location information
that will be resolved in a later stage.

Examples:
- "SBI Bhatta se 500 eent Haasi Gate bheji"
- "Haasi Gate se 250 eent gudam gayi"
- "Gudam se 100 eent shop gaya"
- "Shop se customer Verma ko malba becha"


3. STANDALONE_TRANSACTION

A business event that:

- does NOT describe material/item movement, and
- does NOT contain a specifically named person whose role is
  ambiguous.

Examples:
- "Diesel par 2000 rupaye kharch hue"
- "Office ka kiraya diya"
- "Shyam ke saath deal hui"
- "Haasi Gate pe 5 labour the aur todne ka kaam hua"


IMPORTANT:

Grouping only determines:

- Need Person
- Material Movement
- Standalone Transaction

Grouping MUST NOT determine:

- IN
- OUT
- Direct Sale
- Internal Movement

Those classifications happen later after the relevant
business/location information has been resolved.

4. CORRECTION

The user is explicitly reporting that a PREVIOUSLY recorded
entry was WRONG and needs to be fixed/corrected. This is
fundamentally different from a new business event — the user
is not describing something that happened, they are describing
a MISTAKE in something already recorded earlier.

CORRECTION applies when the statement contains language like:
- "galat tha/thi" (was wrong)
- "galti se ho gaya" (happened by mistake)
- "sahi karo" / "theek karo" (fix it / correct it)
- "wo entry cancel karo" (cancel that entry)
- referring to a past entry that needs updating/undoing

Examples:
- "Ram ka pichla entry galat tha"
- "2 din pehle jo 500 dala tha, wo galat tha"
- "Kal wali kiraya wali entry sahi karo"
- "Suresh ka jo kaam wala amount dala tha, wo theek nahi tha"

CRITICAL — AN OLD BALANCE IS NOT A CORRECTION:
A statement that simply STATES an old/opening balance — money that
was already due BEFORE this app started — is NOT a correction.
Nothing was recorded wrong; it is a one-time starting figure that
still has to be recorded.

Signals: "pichla / pichli / purana / pehle ka ... baaki hai",
"... udhaar hai", "... dena hai / lena hai", "advance le rakha hai",
"shuru mein ... cash tha", "opening balance".

- "Ram ki pichli 1500 mazdoori baaki hai"   → NEED_PERSON (Ram)
- "Suresh pe pehle ka 6000 udhaar hai"      → NEED_PERSON (Suresh)
- "Jai Bhatte ko pichla 5000 dena hai"       → NEED_PERSON (Jai Bhatta)
- "Hemant ne pehle 2000 advance le rakha hai" → NEED_PERSON (Hemant)
- "Shuru mein galle mein 40000 cash tha"     → STANDALONE_TRANSACTION

The words "pichla / pichli / purana / pehle" ALONE never make a
statement a correction. A correction must say that an entry was
WRONG or must be undone: "galat tha", "galti se", "sahi karo",
"theek karo", "cancel karo", "hata do", "dobara daalo".
- "Ram ka pichla entry galat tha"   → CORRECTION (entry was wrong)
- "Ram ki pichli mazdoori baaki hai" → NOT correction (old balance)

CRITICAL DISTINCTION — CORRECTION vs NEED_PERSON:
"Ram ne 500 ka kaam kiya" describes a NEW event → NEED_PERSON.
"Ram ka 500 wala kaam galat tha" describes a MISTAKE in an
ALREADY-RECORDED event → CORRECTION.

The deciding signal is whether the statement is describing
something that JUST HAPPENED (new event) or something that WAS
RECORDED WRONG previously (correction to existing data).

CORRECTION does NOT need a source→destination pair, a person's
business role, or any of the other business classifications —
it only needs to be recognized AS a correction request. All the
details of WHICH entry and WHAT changed are resolved in a later
stage, not during grouping.

═══════════════════════════════
CRITICAL — DID GOODS MOVE TODAY?  (ask this FIRST for every action)
═══════════════════════════════

YES — goods physically came / went / were unloaded / sent NOW
      (aayi, utri, gayi, bheji, le gaya, pahunch gayi, laya)
      → MATERIAL_MOVEMENT. This holds even if money is ALSO
        mentioned — the payment is recorded inside the movement.

NO  — only MONEY changed hands (diye, bheje, jama kara aaye,
      chuka diya, thama aaye, payment kar di, hisab clear kiya),
      EVEN IF an item is NAMED — old goods, a bill, or an advance
      for goods that will come later
      → NEED_PERSON, identity_key = the person / party.

NO  — and there is no person or party at all
      → STANDALONE_TRANSACTION.

A party's description ("reta wale", "aara wale", "bhatta",
"the sand supplier") is NOT an item — "Jagga reta wale ko 2500
bhej diye" moves no sand.

Examples:

"Narayan bhatte ki 3000 eent aaj utri, 9000 de bhi diye"
→ MATERIAL_MOVEMENT (bricks moved today; the 9000 is paid inside it)

"Pichle mahine wali eent ke paise Hari bhatte ko aaj de diye"
→ NEED_PERSON, identity_key = "Hari bhatte" (bricks named, nothing moved today)

"Hari bhatte ko agle hafte ki eent ke liye 5000 advance de diye"
→ NEED_PERSON, identity_key = "Hari bhatte" (goods will come later)

"Jagga reta wale ko trolley ke 2500 online bhej diye"
→ NEED_PERSON, identity_key = "Jagga"

"Jai Mata Di bhatte wale ka 6000 ka hisab clear kiya"
→ NEED_PERSON, identity_key = "Jai Mata Di bhatte"

"Mohan timber wale ka 3000 ka bill aaya"
→ NEED_PERSON, identity_key = "Mohan" (a bill — no goods moved in this sentence)

"हरि भट्टे को पिछली ईंटों के 7000 दे दिए"
→ NEED_PERSON, identity_key = "हरि भट्टे"

"नारायण भट्टे से आज 2500 ईंट उतरी"
→ MATERIAL_MOVEMENT

"Sent 6000 to Hari kiln for last month's bricks"
→ NEED_PERSON, identity_key = "Hari kiln"

"Narayan kiln's truck unloaded 2500 bricks at the shop today"
→ MATERIAL_MOVEMENT

═══════════════════════════════
CRITICAL — MONEY IS NEVER MATERIAL
═══════════════════════════════

MATERIAL_MOVEMENT needs a PHYSICAL ITEM that changes place.
Money (rupaye, paise, salary, mazdoori, dihadi, tankhwah,
advance, UPI, bank, cash, ₹, payment) is NEVER an item.

An action where money is given to / received from / sent to /
put in the account of a NAMED person or party, and NO item
moves, is NEED_PERSON with identity_key = that name
(the role — employee, customer, supplier — is resolved later).
Never write "UNKNOWN → <name>" or "<name> → UNKNOWN" for it.

Examples:

"Vinod ko pichle hafte ki dihadi ke 800 de diye"
→ NEED_PERSON, identity_key = "Vinod"

"Gupta ji se 7000 mil gaye"
→ NEED_PERSON, identity_key = "Gupta ji"

"Jindal bhatte ko 12000 bhej diye"
→ NEED_PERSON, identity_key = "Jindal bhatte"

"Deepak ke account mein 4000 daal diye"
→ NEED_PERSON, identity_key = "Deepak"

"विनोद को 800 रुपये दिए"
→ NEED_PERSON, identity_key = "विनोद"

"गुप्ता जी से 7000 आए"
→ NEED_PERSON, identity_key = "गुप्ता जी"

"Sent Deepak 4000 on UPI"
→ NEED_PERSON, identity_key = "Deepak"

"Received 7000 from Gupta ji"
→ NEED_PERSON, identity_key = "Gupta ji"

A PURPOSE word (hisab, tankhwah, salary, advance, bhugtaan,
mazdoori, payment, wages) is NEVER the identity_key. When money
goes to / comes from a NAMED person, the identity_key is that
PERSON'S NAME, even if a purpose word is also present:

"Hafte ke aakhir mein Deepak ko 2100 dekar hisab barabar kiya"
→ NEED_PERSON, identity_key = "Deepak"   (NOT "hisab")

"Vinod ko tankhwah ke 5000 bank mein bheje"
→ NEED_PERSON, identity_key = "Vinod"   (NOT "tankhwah")

"हफ्ते के आखिर में दीपक को 2100 देकर हिसाब बराबर किया"
→ NEED_PERSON, identity_key = "दीपक"   (NOT "हिसाब")

"Paid Vinod 1500 as advance for his wages"
→ NEED_PERSON, identity_key = "Vinod"   (NOT "advance")

Contrast — an ITEM moved, money is only a detail of it:

"Gupta ji ko 300 eent di, 7000 mile"
→ MATERIAL_MOVEMENT, identity_key = "UNKNOWN → Gupta ji"

═══════════════════════════════
CRITICAL — WORK AT A LOCATION IS NOT A MOVEMENT
═══════════════════════════════

Work done AT one place (todna, girana, safai, chhat todi,
deewar giraayi, labour lage) where NO item goes from a source
to a destination is a work/activity log →
STANDALONE_TRANSACTION, identity_key = the place name.
A place name alone never makes MATERIAL_MOVEMENT.

EXCEPTION — a NAMED person did the work and their amount is given:
that is the PERSON'S work → NEED_PERSON, identity_key = the person,
even though a place is mentioned.
"Deepak ne aaj dukaan mein saaf-safai ki, 350 bante hain"
→ NEED_PERSON, identity_key = "Deepak"   (NOT "dukaan")
"दीपक ने आज दुकान में सफाई की, 350 बनते हैं"
→ NEED_PERSON, identity_key = "दीपक"

Examples:

"Nehru colony wali site pe aaj deewar giraayi"
→ STANDALONE_TRANSACTION, identity_key = "Nehru colony wali site"

"नेहरू कॉलोनी वाली साइट पे आज दीवार गिराई"
→ STANDALONE_TRANSACTION, identity_key = "नेहरू कॉलोनी वाली साइट"

"Pulled down a wall at the Nehru colony site today"
→ STANDALONE_TRANSACTION, identity_key = "Nehru colony site"

═══════════════════════════════
HOW TO DECIDE THE GROUPING TYPE
═══════════════════════════════

Ask in this order:

Step 0 — Is the user explicitly describing a MISTAKE in a
PREVIOUSLY recorded entry (not a new event)? Look for correction
language ("galat tha", "sahi karo", "galti se", referring to a
past recorded entry needing a fix). An old balance statement
("pichli mazdoori baaki hai", "pehle ka udhaar hai") is NOT a
mistake — answer NO for it.

YES → CORRECTION

NO → go to Step 1


Step 1 — Does the action explicitly describe a PHYSICAL ITEM/
MATERIAL (eent, malba, khidki, lakdi, sariya ... — NEVER money)
moving from a source to a destination AS THE SUBJECT of the
action (not merely a named person's own activity that happens
to mention locations/counts)? Apply the SUBJECT TEST, BRIEF-NOTE
TEST, and COUNTERPARTY TEST described below before answering.

YES → MATERIAL_MOVEMENT

NO → go to Step 2


Step 2 — Is there a SPECIFICALLY NAMED individual whose business
role is AMBIGUOUS and needs to be resolved later?

YES → NEED_PERSON

NO → STANDALONE_TRANSACTION


IMPORTANT:

At the grouping stage, do NOT decide whether a material movement
is:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

Those classifications are NOT grouping decisions.

The grouping stage does not know whether a location is:

- an inventory/storage location
- an internal site
- an external supplier/source
- a customer
- another business location

Do NOT infer or guess these location roles from words such as
"gudam", "shop", "site", "ghar", or "bhatta".

Those business/location roles will be resolved in a later stage.

═══════════════════════════════
CRITICAL — DISTINGUISHING A PERSON'S OWN ACTIVITY FROM A
MATERIAL MOVEMENT / BUSINESS TRANSACTION
═══════════════════════════════

A statement may mention BOTH a named person AND locations/items
together. This does NOT automatically make it MATERIAL_MOVEMENT.
Apply the following tests, in order, whenever a named person AND
a location/item both appear in the same action.

SUBJECT TEST:
Remove the person's name from the action. If the remaining text
feels INCOMPLETE (you would ask "by whom?"), the person is the
SUBJECT of the action — this is NEED_PERSON, even if locations,
item names, or counts (chakkar, trip, pheri) are mentioned.

If the remaining text is still a COMPLETE, meaningful statement
on its own, the person was only a supporting attribute (like a
driver) — this is MATERIAL_MOVEMENT.

Examples:

"Ram ne 8 chakkar mare gudam se site tak"
Remove "Ram": "8 chakkar mare gudam se site tak" → incomplete
(by whom?) → NEED_PERSON, identity_key = "Ram"

"Gudam se 8 window shop pr bheji, driver Ram tha"
Remove "Ram": "Gudam se 8 window shop pr bheji" → complete and
meaningful on its own → MATERIAL_MOVEMENT, identity_key =
"gudam → shop"

──────────────────────────────

BRIEF PERSONAL-ACTIVITY NOTE vs FORMAL MOVEMENT RECORD:
A brief, casual mention of a person's own work — a count of
chakkar/trips/pheri with NO separately-named driver, NO full
formal item+source+destination description — is a PERSONAL WORK
NOTE about that individual. This is NEED_PERSON, and the work
description (including any counts) stays together as one note
for that person's entry — it is NOT a material-movement identity.

A formal movement record — explicit item, explicit source,
explicit destination, AND a driver named as a SEPARATE attribute
("driver X tha") — documents the business event itself. This is
MATERIAL_MOVEMENT, and the driver is just one attribute of that
record.

Examples:

"Ram ne 6 chakkar eent ke mare site se gudam, aur 2 malba ke,
aur Hasi Gate site pe kaam kiya"
→ NEED_PERSON, identity_key = "Ram" (a brief personal work-note
about Ram — no separately-named driver, no formal item+source+
destination record; the chakkar counts describe Ram's activity,
not a material-movement identity)

"Gudam se 200 eent site tak gayi, driver Ram tha"
→ MATERIAL_MOVEMENT, identity_key = "gudam → site" (a formal
movement record — explicit item, explicit source+destination,
driver named as a separate attribute)

──────────────────────────────

COUNTERPARTY TEST — TWO ENTITIES WITH DISTINCT ROLES:
If a named person delivers/carries MATERIAL TO a SECOND named
entity (a customer, or any individual acting as a counterparty —
even "apne ghar" or a personal destination counts as a
counterparty-like destination), possibly also collecting payment
FOR THAT MATERIAL, this is a business TRANSACTION between two
parties, not one person's own activity.
(This test needs a PHYSICAL ITEM that moved. Money paid or
received with NO item moving is NEVER this test — see
"MONEY IS NEVER MATERIAL".) This is MATERIAL_MOVEMENT — the carrier's
name becomes a supporting attribute (like a driver), and the
counterparty becomes part of the destination side. This holds
even when the source is not explicitly stated — use UNKNOWN for
a missing source rather than inventing one.

Examples:

"Ram 200 eent shop se Shyam ji ke yaha pocha kar aaya, ulte
paise mile 4000"
→ MATERIAL_MOVEMENT, identity_key = "shop → Shyam ji" (Ram is
the carrier; Shyam ji is the counterparty who received the
material and paid — this is a two-party transaction, not Ram's
personal work note)

"Ram ne Sharma ji ko malba diya, 2 trip lagayi, koi paisa nahi
liya"
→ MATERIAL_MOVEMENT, identity_key = "UNKNOWN → Sharma ji" (two
named entities with distinct roles — Ram the carrier, Sharma ji
the counterparty — even though the source location and payment
are not stated, do NOT invent them; use UNKNOWN for the missing
source)

Contrast with a SINGLE-entity case:

"Ram ne 8 chakkar mare gudam se site tak"
→ NEED_PERSON, identity_key = "Ram" (only Ram is involved; no
second named entity/counterparty; this is Ram's own activity)

═══════════════════════════════
CRITICAL — GENERIC WORKER REFERENCES
═══════════════════════════════

Generic references to workers/labour WITHOUT a specific person's
name are NEVER NEED_PERSON.

Examples:

- "5 labour"
- "3 majdoor"
- "workers"
- "labour"
- "kuch majdoor lage"

These are generic worker references, not person identities.

Example:

"Haasi Gate pe 5 labour the aur todne ka kaam hua."

→ record_type = STANDALONE_TRANSACTION

There is no specifically named individual whose role is ambiguous.

IMPORTANT:

NEED_PERSON requires an actual named individual.

A worker count or generic worker reference MUST NOT create
NEED_PERSON.

═══════════════════════════════
CRITICAL — IDENTITY KEYS KEEP THE USER'S SPELLING AND SCRIPT
═══════════════════════════════

Copy names into identity_key EXACTLY as they appear in the
action text — same spelling, same script. NEVER transliterate
or translate:
- "जिंदल भट्टे से 1800 ईंट दुकान पर आई"
  → identity_key = "जिंदल भट्टे → दुकान"   (NOT "Jindal Bhatta → shop")
- "विनोद को 450 दिए" → identity_key = "विनोद"   (NOT "Vinod")
- "Vinod ko 450 diye" → identity_key = "Vinod"   (NOT "विनोद")

═══════════════════════════════
CRITICAL — ONE NEED_PERSON GROUP = ONE PERSON
═══════════════════════════════

A NEED_PERSON identity_key is always exactly ONE person's name.
Never "X aur Y", "X and Y", "X, Y". If an action talks about
several people, each person gets their own group.

═══════════════════════════════
IDENTITY KEY — HOW TO MATCH RECORDS
═══════════════════════════════

Each record type has its own identity key.

Two actions belong to the SAME group ONLY if BOTH of these match:

  1. SAME record_type
  2. SAME identity_key value (exact match)


┌───────────────────────────────────────────────────────────────
│ Record Type              Identity Key
├───────────────────────────────────────────────────────────────
│ NEED_PERSON               the exact person's name
│
│ MATERIAL_MOVEMENT         EXACT source → destination pair.
│                           Both source and destination must come
│                           from the extracted action.
│
│ STANDALONE_TRANSACTION    the explicit transaction or entity
│                           identity present in the action
│
│ CORRECTION                the person/entity name mentioned in
│                           the correction statement, if any,
│                           otherwise the word "correction"
└───────────────────────────────────────────────────────────────


NEED_PERSON:

Identity key = the exact person's name.

Example:

"Ram ne kaam kiya"
"Ram ko 500 diye"

→ SAME record_type
→ SAME identity_key = "Ram"
→ SAME GROUP


"Sandeep ne kaam kiya"
"Ram ko 500 diye"

→ DIFFERENT identity_key
→ DIFFERENT GROUP


IMPORTANT:

Generic references such as:

- labour
- majdoor
- workers
- 5 labour
- 3 majdoor

are NOT person identities.

Do NOT create NEED_PERSON for a generic worker reference.


MATERIAL_MOVEMENT:

Identity key = EXACT source → destination pair.

Both source and destination must be explicitly available
in the extracted action.

Example:

"SBI Bhatta se 500 eent Haasi Gate bheji"

→ identity_key = "SBI Bhatta → Haasi Gate"


"Haasi Gate se 250 eent gudam gayi"

→ identity_key = "Haasi Gate → gudam"


These are DIFFERENT groups because the complete
source → destination pairs are different.


IMPORTANT:

For MATERIAL_MOVEMENT:

- material type does NOT define identity
- quantity does NOT define identity
- date does NOT define identity
- sequence does NOT define identity
- continuous flow does NOT define identity

Only the COMPLETE source → destination pair defines identity.


Example:

"Haasi Gate se 500 eent gudam gayi"
"Haasi Gate se 300 kg loha gudam gaya"

→ SAME record_type
→ SAME source
→ SAME destination
→ SAME identity_key
→ SAME GROUP


MISSING SOURCE OR DESTINATION:

If source or destination is not explicitly available,
DO NOT invent or assume the missing location.

Example:

"Mahesh Bhatte se 1500 eent aayi"

Do NOT create:

"Mahesh Bhatte → storage"

because "storage" was not explicitly stated.

Use:

"Mahesh Bhatte → UNKNOWN"


Likewise:

"1500 eent gudam bheji"

if the source is not explicitly stated:

"UNKNOWN → gudam"


STANDALONE_TRANSACTION:

Identity key = the explicit transaction or entity identity
present in the extracted action.

Use only information actually present in the action.

Do NOT invent:

- person identity
- location
- business role
- transaction type

if it was not explicitly extracted.


CORE MATCHING RULE:

Match record_type FIRST.

Then match identity_key within that record_type.

Different record types NEVER merge, even if they share:

- the same location
- the same date
- the same person name
- the same material
- the same message


CRITICAL:

Do NOT infer business roles from location names.

For example, do NOT assume:

- gudam = storage
- shop = inventory
- site = external
- ghar = external source
- bhatta = supplier

Location/business roles will be resolved in a later stage.

Grouping uses only the explicit information available
in the extracted action.


IMPORTANT:

At the grouping stage, identity_key must NOT depend on:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

These classifications happen later after location/business
information has been resolved.

═══════════════════════════════
CRITICAL — MATERIAL MOVEMENT GROUPING IS STRICT
═══════════════════════════════

For every MATERIAL_MOVEMENT action, the identity is the COMPLETE
(source, destination) pair.

Only an EXACT match of the COMPLETE source → destination pair
allows actions to share the same group.


IMPORTANT:

For MATERIAL_MOVEMENT:

- Material type does NOT create a separate group.
- Quantity does NOT create a separate group.
- Date does NOT create a separate group.
- Sequence does NOT create a separate group.
- Continuous flow does NOT create a separate group.
- Separate quantities do NOT create separate groups if the
  source → destination pair is exactly the same.


Example:

"Site A se 200 eent gudam gayi."
"Site A se 100 cement gudam gaya."

→ SAME GROUP

Both actions have:

record_type = MATERIAL_MOVEMENT

identity_key = "Site A → gudam"


NEVER merge MATERIAL_MOVEMENT actions merely because:

- the material/item is the same
- the date is the same
- the source of one action is the destination of another
- the movements happen sequentially
- the actions appear to be part of the same overall material flow
- they share only the source
- they share only the destination


CONNECTED FLOW IS NOT ONE GROUP:

Example:

A → B
B → C
C → D

These are THREE separate groups:

G1 = A → B
G2 = B → C
G3 = C → D


The fact that B connects two movements does NOT make them
the same group.

Only an EXACT match of the COMPLETE source → destination pair
allows two MATERIAL_MOVEMENT actions to share a group.


MISSING LOCATION:

If source or destination is missing, do NOT invent it.

Example:

"Mahesh Bhatte se 1500 eent aayi."

If destination is not explicitly stated:

→ MATERIAL_MOVEMENT
→ identity_key = "Mahesh Bhatte → UNKNOWN"


Do NOT assume:

"Mahesh Bhatte → gudam"

or:

"Mahesh Bhatte → storage"


Similarly:

"1500 eent gudam bheji."

If source is not explicitly stated:

→ MATERIAL_MOVEMENT
→ identity_key = "UNKNOWN → gudam"


CRITICAL:

Grouping must never use assumed business knowledge to complete
a missing source or destination.

Do NOT assume that:

- gudam is storage
- shop is inventory
- site is external
- ghar is external
- bhatta is supplier
- customer is a destination type

These roles will be resolved in a later stage.


IMPORTANT:

At this stage, NEVER classify a MATERIAL_MOVEMENT as:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

The grouping stage only identifies:

MATERIAL_MOVEMENT

The final movement classification happens later after the
relevant location and business information has been resolved.

═══════════════════════════════
RULE — ACCOUNT QUERIES
═══════════════════════════════

An account query such as "Ram ka hisab bata" belongs to the
record of the person or entity being queried.

If the queried person's business role is ambiguous, classify the
action as NEED_PERSON and use the person's exact name as the
identity_key.

Example:

"Ram ka hisab bata"

→ record_type = NEED_PERSON
→ identity_key = "Ram"


An account query does NOT create a separate record type.

Account queries are grouped according to the same three grouping
types:

- NEED_PERSON
- MATERIAL_MOVEMENT
- STANDALONE_TRANSACTION


If the queried entity is a specifically named person whose role
is ambiguous, use NEED_PERSON.

Do NOT infer or assign the person's business role during
grouping.

═══════════════════════════════
CORE PRINCIPLE
═══════════════════════════════

Grouping MUST use ONLY the extracted actions.

Grouping must never infer, assume, or invent information that is
not explicitly present in the extracted action.

The grouping stage has ONLY THREE possible record types:

- NEED_PERSON
- MATERIAL_MOVEMENT
- STANDALONE_TRANSACTION


If two actions are not explicitly connected by:

- SAME record_type
- SAME identity_key

they MUST be treated as DIFFERENT groups.

This remains true even if the actions:

- occur on the same date
- appear in the same user message
- appear in the same conversation
- mention the same location
- mention the same material
- mention the same person name incidentally
- appear to be part of the same overall business activity


ONLY:

SAME record_type + SAME identity_key

allows two actions to belong to the SAME group.


IMPORTANT — RECORD TYPE FIRST:

For EVERY action, determine the record_type BEFORE deciding
whether it belongs to an existing group.

Then determine the identity_key according to the rules for that
record_type.

Never use identity alone to merge actions from different
record types.


IMPORTANT — NO BUSINESS-ROLE INFERENCE:

Grouping does NOT determine whether a location is:

- storage
- inventory
- supplier
- customer
- internal site
- external site

Grouping also does NOT determine:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT


These classifications require business/location information
that is resolved in a later stage.


IMPORTANT — NO MISSING INFORMATION INFERENCE:

If the extracted action does not explicitly contain a source
or destination, do NOT invent one.

Do NOT assume a missing destination is "gudam", "storage", or
any other location.

Do NOT assume a missing source from previous or following actions.

Use UNKNOWN for a missing source or destination when required
for the identity_key.


Example:

"Mahesh Bhatte se 1500 eent aayi"

If destination is not explicitly stated:

→ record_type = MATERIAL_MOVEMENT
→ identity_key = "Mahesh Bhatte → UNKNOWN"


The grouping stage must preserve what was extracted rather than
trying to complete the business meaning.


CRITICAL:

Grouping connects extracted actions.

Grouping does NOT resolve business meaning.

Later stages may use:

- location master data
- person/entity information
- business rules
- HITL confirmation

to determine the final business classification.

═══════════════════════════════
EXAMPLES — SIMPLE (single record type)
═══════════════════════════════

NEED_PERSON — same person, multiple actions

Ram ne 500 ka kaam kiya.
Ram ko 300 diye.
Ram ka hisab bata.

→ SAME GROUP (record_type: NEED_PERSON, identity_key: "Ram" —
   note: these are 3 distinct transactions [work, payment, query]
   that will likely become 3 separate database entries, but they
   share one group because they share one entity)

──────────────────────────────

NEED_PERSON — different people

Ram ne 500 ka kaam kiya.
Mohan ne 700 ka kaam kiya.

→ DIFFERENT GROUPS (identity_key differs: "Ram" vs "Mohan")

──────────────────────────────

NEED_PERSON — pure attendance, no amount, no work description

Rakesh aaj nahi aaya.

→ record_type = NEED_PERSON
→ identity_key = "Rakesh"

A specifically named individual's presence/absence status is
enough to trigger NEED_PERSON — an amount or work description
is NOT required. Contrast this with generic worker references
like "5 labour the" (no name) which are STANDALONE_TRANSACTION.

──────────────────────────────

NEED_PERSON — attendance + work combined, still one named person

Vikram pura din aaya driving ki, usne 5 chakar mare.

→ record_type = NEED_PERSON
→ identity_key = "Vikram"

Both the attendance detail ("pura din aaya driving ki") and the
work detail ("5 chakar mare") belong to the same named individual,
Vikram — this is NEED_PERSON, not STANDALONE_TRANSACTION, even
though the work-description part alone might resemble a generic
activity log.

──────────────────────────────

MATERIAL_MOVEMENT — attributes of one movement

SBI bhatte se 2500 eent aayi.
Driver Kitanu tha.
Gudam mein utari.

→ SAME GROUP

record_type = MATERIAL_MOVEMENT

identity_key = "SBI Bhatta → gudam"

The driver detail belongs to the same movement because it does
not create a separate material movement identity.

IMPORTANT:

At the grouping stage, do NOT classify this as IN.

Whether this movement is IN, OUT, DIRECT_SALE, or INTERNAL
MOVEMENT will be determined later after the relevant business
and location information has been resolved.

──────────────────────────────

MATERIAL_MOVEMENT — SAME source and destination

SBI se 2500 eent aayi, gudam mein utari.
SBI se 3000 eent aayi, gudam mein utari.

→ SAME GROUP

Both actions explicitly describe movement with the same:

source = SBI
destination = gudam

Therefore:

record_type = MATERIAL_MOVEMENT
identity_key = "SBI → gudam"

The fact that both actions have their own quantities does NOT
create separate groups at the grouping stage.

IMPORTANT:

Do NOT decide whether these are separate IN shipments.

Shipment/event separation is a later business-level decision.

Grouping only determines whether the extracted actions share the
same generic movement identity.

──────────────────────────────

STANDALONE_TRANSACTION — different transactions, same day

Office ka kiraya diya.
Bijli ka bill diya.

→ DIFFERENT GROUPS (identity_key differs: "kiraya" vs "bijli
   bill" — each is independent unless the actions explicitly
   describe the SAME transaction)

──────────────────────────────

STANDALONE_TRANSACTION — a deal, party role already clear

Shyam se purana makan todne ki deal hui.
5 lakh mein deal final hui.
1 lakh advance diya.

→ SAME GROUP (record_type: STANDALONE_TRANSACTION, identity_key:
   "Shyam" — Shyam's role as the deal party is already clear from
   context, no role ambiguity to resolve, so this is NOT
   NEED_PERSON)

═══════════════════════════════
EXAMPLES — MEDIUM (cross-type, same message)
═══════════════════════════════

NEED_PERSON vs STANDALONE_TRANSACTION — same message, unrelated

Ram ne 500 ka kaam kiya.
Office ka kiraya diya.

→ DIFFERENT GROUPS (different record types: NEED_PERSON vs
   STANDALONE_TRANSACTION — no shared identity_key)

──────────────────────────────

NEED_PERSON vs MATERIAL_MOVEMENT — different identities

Ram ne diwar todi.
Sharma ji ko 1000 eent di.

→ DIFFERENT GROUPS

Action 1:
record_type = NEED_PERSON
identity_key = "Ram"

Action 2:
record_type = MATERIAL_MOVEMENT
identity_key depends ONLY on the explicitly extracted
source → destination information.

If the source is not explicitly stated, do NOT invent it.

For example, if the extracted action only contains:

destination = Sharma ji

then:

record_type = MATERIAL_MOVEMENT
identity_key = "UNKNOWN → Sharma ji"

IMPORTANT:

Do NOT classify this as OUT during grouping.

Do NOT assume "gudam/shop → Sharma ji".

The later location/business-resolution stage will determine
whether this movement is OUT, DIRECT_SALE, or another movement
classification.

The two actions remain separate because their record_type and/or
identity_key are different.

──────────────────────────────

MATERIAL_MOVEMENT — same source+destination pair, different items

Hasi Gate se 250 purani eent gudam gai.
Hasi Gate se 500 kg scrap gudam gaya.

→ SAME GROUP (identity_key: "Hasi Gate→gudam" pair matches on
   both actions, even though the items differ)

──────────────────────────────

MATERIAL_MOVEMENT — different destination

Hasi Gate se 250 eent gudam gai.
Gudam se 100 eent shop gaya.

→ DIFFERENT GROUPS (identity_key differs: "Hasi Gate→gudam" vs
   "gudam→shop" — different pairs, even though "gudam" appears in
   both)

═══════════════════════════════
EXAMPLES — COMPLEX (mixed record types, shared surface details)
═══════════════════════════════

A location is never a person/party identity

Haasi Gate se 250 eent gudam gayi, driver Mohan tha.

→ SAME GROUP

record_type = MATERIAL_MOVEMENT

identity_key = "Haasi Gate → gudam"

"Haasi Gate" is treated only as the explicitly stated source
location.

Do NOT treat "Haasi Gate" as a person, supplier, or customer.

"Mohan" is only a driver detail in this action. His name does
not automatically create a NEED_PERSON group because the action
does not establish that Mohan's business role is ambiguous and
requires person-role resolution.

IMPORTANT:

Do NOT classify this movement as:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

The grouping stage only identifies the generic
MATERIAL_MOVEMENT type.

The final movement classification happens later after location
and business-role information has been resolved.

──────────────────────────────

MATERIAL_MOVEMENT vs STANDALONE_TRANSACTION — SAME location
mentioned, but different record types

Haasi Gate pe aaj 5 labour the aur todne ka kaam hua.
Haasi Gate se 500 eent gudam bhej di.

→ DIFFERENT GROUPS

Action 1:
record_type = STANDALONE_TRANSACTION

There is no specifically named person whose role is ambiguous.
"5 labour" is a generic worker reference and therefore does NOT
create NEED_PERSON.

Action 2:
record_type = MATERIAL_MOVEMENT
identity_key = "Haasi Gate → gudam"

Sharing the location name "Haasi Gate" does NOT make these actions
the same group.

The first action describes a work/business event.
The second action describes material movement.

Different record types MUST remain in different groups.

──────────────────────────────

MATERIAL_MOVEMENT — chained flow, SAME "gudam" word appears
in both, but different source → destination pairs

SBI Bhatte se 2500 eent aayi, gudam mein utaari.
Gudam se 500 eent shop bhej di.

→ DIFFERENT GROUPS

Action 1:
record_type = MATERIAL_MOVEMENT
identity_key = "SBI Bhatta → gudam"

Action 2:
record_type = MATERIAL_MOVEMENT
identity_key = "gudam → shop"

These are DIFFERENT GROUPS because the complete
source → destination pairs are different.

The word "gudam" appears in both actions, but sharing one
location is NOT enough to create the same group.

IMPORTANT:

Do NOT classify Action 1 as IN.

Do NOT classify Action 2 as OUT.

Both actions remain MATERIAL_MOVEMENT at the grouping stage.

Their final movement classifications will be determined later
after the relevant location and business information has been
resolved.

A connected flow chain does NOT create one group:

SBI Bhatta → gudam
gudam → shop

→ TWO DIFFERENT GROUPS

──────────────────────────────

MATERIAL_MOVEMENT vs NEED_PERSON — unrelated actions, same
message

dinod site se 3 chakkar gudam gaye.
Ram ko 200 diye.

→ DIFFERENT GROUPS

Action 1:
record_type = MATERIAL_MOVEMENT
identity_key = "dinod site → gudam"

Action 2:
record_type = NEED_PERSON
identity_key = "Ram"

These actions remain in different groups.

The first action describes explicit material movement.

The second action refers to a specifically named person whose
business role is ambiguous.

The fact that both actions appear in the same message does NOT
connect them.

Different record types and/or different identity keys MUST remain
separate.

──────────────────────────────

═══════════════════════════════
Four different groups in one message
═══════════════════════════════

Ram ne 500 ka kaam kiya.
SBI Bhatte se 2500 eent aayi, Kitanu driver tha, gudam mein utari.
Hasi Gate se 300 eent gudam gai.
Office ka kiraya diya.

→ FOUR DIFFERENT GROUPS

G1:
record_type = NEED_PERSON
identity_key = "Ram"

The action refers to a specifically named person whose business
role is ambiguous.

G2:
record_type = MATERIAL_MOVEMENT
identity_key = "SBI Bhatta → gudam"

Kitanu is only a driver detail of this movement. His name does
not automatically create a separate NEED_PERSON group.

G3:
record_type = MATERIAL_MOVEMENT
identity_key = "Hasi Gate → gudam"

G4:
record_type = STANDALONE_TRANSACTION
identity_key = "kiraya"


IMPORTANT:

There are FOUR actions and FOUR groups.

G2 and G3 have the SAME record_type:

MATERIAL_MOVEMENT

but their identity_key values are different:

"SBI Bhatta → gudam"
"Hasi Gate → gudam"

Therefore, G2 and G3 MUST remain separate groups.


IMPORTANT:

Do NOT classify G2 or G3 as:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

Those final movement classifications happen later after the
relevant location and business information has been resolved.

──────────────────────────────

Same person name appears with and without material movement —
name alone is not enough; record_type must also match

Ram ne 500 ka kaam kiya.
Ram ko 800 mazdoori di.
Hasi Gate se 300 eent gudam gai.

→ TWO GROUPS

G1:
record_type = NEED_PERSON
identity_key = "Ram"

Both Ram actions belong to the SAME group because they have:

- SAME record_type = NEED_PERSON
- SAME identity_key = "Ram"

The two actions are different business events, but grouping
connects them to the same person identity.


G2:
record_type = MATERIAL_MOVEMENT
identity_key = "Hasi Gate → gudam"

This remains a separate group because its record_type and
identity_key are different from G1.


IMPORTANT:

The name "Ram" appearing in one group does NOT cause unrelated
material movement to be grouped with Ram.

Likewise, the presence of a person's name in a material movement
action does not automatically create NEED_PERSON.

Grouping depends on:

SAME record_type + SAME identity_key


Do NOT classify G2 as:

- IN
- OUT
- DIRECT_SALE
- INTERNAL MOVEMENT

The final movement classification happens later after location
and business information has been resolved.

──────────────────────────────

CORRECTION — mixed with a normal new event

Ram ne 500 ka kaam kiya.
Mohan ka pichla entry galat tha.

→ TWO DIFFERENT GROUPS

G1:
record_type = NEED_PERSON
identity_key = "Ram"
(This describes a NEW work event.)

G2:
record_type = CORRECTION
identity_key = "Mohan"
(This describes a MISTAKE in an already-recorded entry — not
a new event. Even though Mohan is a named person, this is NOT
NEED_PERSON because the statement is about fixing something
already recorded, not about a new business role to resolve.)

──────────────────────────────

CORRECTION — no person mentioned

Kal wali kiraya ki entry galat thi.

→ record_type = CORRECTION
→ identity_key = "correction"

No specific person is named, so the generic identity_key
"correction" is used.

═══════════════════════════════
GROUP IDS
═══════════════════════════════

Assign sequential IDs: G1, G2, G3, ...

═══════════════════════════════
OUTPUT
═══════════════════════════════

Return ONLY a valid GroupedIntent object.
"""

def _normalize_identity_key(key: str) -> str:
    """
    Lowercase + strip, so "Sandeep" and "sandeep " are treated as the
    same person when checking for duplicate groups.
    """
    return key.strip().lower()

def _merge_duplicate_groups(groups: list) -> list:
    """
    Safety net after grouping: the LLM sometimes splits the SAME
    person/entity (same record_type + same identity_key) into two
    separate groups instead of one — e.g. "Sandeep ne 500 liye" and
    "Sandeep driver hai" landing in G1 and G2 instead of both in G1.

    This is a data-integrity risk: it causes the same person's role
    to be asked/resolved TWICE, and if the user picks a different
    role each time, the person's data gets split across two
    inconsistent identities.

    This merge is deterministic (string matching), not LLM-based, so
    it never misfires and never depends on model non-determinism.
    Only groups with a MATCHING record_type AND MATCHING normalized
    identity_key are merged — different people or different event
    types are never touched.
    """
    merged_by_key = {}
    ordered_keys = []

    for group in groups:
        merge_key = (group.record_type, _normalize_identity_key(group.identity_key))

        if merge_key not in merged_by_key:
            merged_by_key[merge_key] = group
            ordered_keys.append(merge_key)
            continue

        # Duplicate found — merge this group's actions into the
        # first-seen group for this (record_type, identity_key) pair.
        existing = merged_by_key[merge_key]
        existing.actions.extend(group.actions)
        if group.need_person and not existing.need_person:
            existing.need_person = group.need_person

    # Re-assign group_ids sequentially (G1, G2, ...) so downstream
    # code sees a clean, gap-free sequence after merging.
    merged_groups = [merged_by_key[key] for key in ordered_keys]
    for i, group in enumerate(merged_groups, start=1):
        group.group_id = f"G{i}"

    return merged_groups


# ───────────────────────────────────────────────────────────────
# Safety net: "Sohan ko 1000 de diye" ko LLM kabhi "UNKNOWN → Sohan"
# (Material Movement) bana deta hai. Paisa maal nahi hai — agar
#   • ek taraf UNKNOWN hai, doosri taraf koi naam (jagah nahi),
#   • paise ka SAAF shabd hai (ya "se 5000 aaye"),
#   • aur koi maal ka naam nahi hai,
# to ye us aadmi ka paise ka len-den hai → NEED_PERSON.
# ───────────────────────────────────────────────────────────────
_MONEY_WORDS = re.compile(
    r"\b(paise|paisa|paisey|rupaye|rupay|rupees?|rs\.?|salary|mazdoori|majdoori|dihadi|"
    r"tankhwah|tankha|advance|upi|bank|cash|payment|paid|bhugtaan|overtime|kharche?|account|khate|khaate|khata|khaata|"
    r"chukta|chuka\w*)\b|₹"
    r"|पैसे|पैसा|रुपये|रुपए|सैलरी|मज़दूरी|मजदूरी|दिहाड़ी|तनख्वाह|तनख़्वाह|एडवांस|यूपीआई|बैंक|कैश|भुगतान|खाते",
    re.IGNORECASE,
)
_MONEY_CAME = re.compile(
    r"(\bse|से)\s+\d[\d,]*\s*(aaye|aaya|aayi|mile|mila|mil gaye|आए|आये|आया|आई|मिले|मिला)"
    r"|\breceived\s+\d[\d,]*\b",
    re.IGNORECASE,
)
# "SBI bhatte ko 3000 de diye" — rakam + dene ki kriya, koi saamaan nahi → paisa
_MONEY_GIVEN = re.compile(
    r"(\bko|को)\s+(?:₹\s*)?\d[\d,]*\s*(?:rupaye|rs)?\s*(de diye|de diya|de di|diye|diya|di|bheje|bheja|chukaye|chuka diye)\b"
    r"|(को)\s+\d[\d,]*\s*(दे दिए|दिए|दिया|भेजे|चुकाए)"
    r"|\b(paid|gave|sent)\s+(?:\w+\s+){0,3}(?:₹\s*)?\d[\d,]*\b",
    re.IGNORECASE,
)
# "सोहन के खाते" / "Ram ke account" → sirf naam
_ACCOUNT_SUFFIX = re.compile(
    r"\s+(ke|ka|ki)\s+(khate|khata|khaate|khaata|account)$|\s+(के|का|की)\s+(खाते|खाता|अकाउंट)$",
    re.IGNORECASE,
)
_EXTRA_ITEMS = ["eent", "ईंट", "brick", "bricks", "malba", "मलबा", "khidki", "khidkiyan",
                "खिड़की", "खिड़कियाँ", "lakdi", "लकड़ी", "timber", "patthar", "पत्थर", "reta", "रेत",
                "bajri", "बजरी", "cement", "सीमेंट", "maal", "माल", "saman", "samaan", "सामान",
                "gate", "गेट", "darwaza", "darwaje", "दरवाज़ा", "tile", "tiles", "टाइल"]
_ITEM_WORDS = re.compile(
    r"(?<!\w)(" + "|".join(sorted({re.escape(w) for w in list(ITEM_ALIASES) + _EXTRA_ITEMS},
                                    key=len, reverse=True)) + r")(?!\w)",
    re.IGNORECASE,
)


def _money_not_material(groups: list) -> list:
    for group in groups:
        if group.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in group.identity_key:
            continue
        sides = [x.strip() for x in group.identity_key.split("→", 1)]
        unknown = [x.upper() in ("UNKNOWN", "") for x in sides]
        if unknown.count(True) != 1:
            continue
        name = _ACCOUNT_SUFFIX.sub("", sides[1] if unknown[0] else sides[0]).strip()
        if name.strip().lower() in LOCATION_ALIASES:
            continue
        text = " ".join(a.text for a in group.actions)
        if _ITEM_WORDS.search(text):
            continue
        if _MONEY_WORDS.search(text) or _MONEY_CAME.search(text) or _MONEY_GIVEN.search(text):
            print(f"🔀 GROUPING: '{group.identity_key}' paise ka len-den hai, maal nahi "
                  f"— Need Person '{name}' banaya")
            group.record_type = RecordType.NEED_PERSON
            group.identity_key = name
            group.need_person = True
    return groups


# ───────────────────────────────────────────────────────────────
# Safety net: "Sohan aur Kitanu" jaisa ek NEED_PERSON group → har aadmi
# ka alag group, har action ki copy mein sirf us aadmi ka naam.
# ("dono" / "both" / "दोनों" hata dete hain.)
# ───────────────────────────────────────────────────────────────
_JOINER = re.compile(r"\s*(?:,|\band\b|\baur\b|\bor\b|(?<!\S)और(?!\S))\s*", re.IGNORECASE)
_BOTH = re.compile(r"\s+(dono|donon|both|all|sab|दोनों|सब)\b", re.IGNORECASE)


def _split_multi_person(groups: list) -> list:
    out = []
    for group in groups:
        key = group.identity_key.strip()
        if group.record_type != RecordType.NEED_PERSON or not _JOINER.search(key):
            out.append(group)
            continue
        names = [n.strip() for n in _JOINER.split(_BOTH.sub("", key)) if n.strip()]
        if len(names) < 2 or any(len(n.split()) > 3 for n in names):
            out.append(group)
            continue
        print(f"🔀 GROUPING: '{key}' mein {len(names)} log hain — har ek ka alag group")
        for name in names:
            acts = []
            for a in group.actions:
                text = a.text.replace(key, name) if key in a.text else a.text
                text = _BOTH.sub("", text)
                acts.append(a.model_copy(update={"text": text}))
            out.append(group.model_copy(update={"identity_key": name, "actions": acts}))
    return out


# ───────────────────────────────────────────────────────────────
# Safety net: "Ram ka aaj ka hisab 500 cash mein kar diya" ko LLM ne
# Standalone ("hisab") bana diya — naam chhoot gaya. Agar Standalone
# group ke text mein DB ka EK jaana-pehchaana aadmi hai aur paise/hisab
# ki baat hai → NEED_PERSON (aage role confirm hoga).
# ───────────────────────────────────────────────────────────────
_HISAB = re.compile(r"\b(hisab|hisaab|chukta|chukaya)\b|हिसाब|चुकता", re.IGNORECASE)
# "400 banta hai" / "400 ka kaam" / "₹400" — aadmi ke kaam ka amount
_WORK_AMOUNT = re.compile(
    r"\d[\d,]*\s*(banta|bante|banti|ka kaam|ke kaam|rupaye|rupay|rs)\b|₹\s*\d"
    r"|\d[\d,]*\s*(बनता|बनते|का काम|रुपये)",
    re.IGNORECASE)


# "Sohan ka phone number badal gaya" — aadmi ki profile ki baat
_PROFILE_WORDS = re.compile(
    r"\b(phone|mobile|number|nambar|address|pata|rehta|rehti)\b|फोन|मोबाइल|नंबर|पता|रहता|रहती",
    re.IGNORECASE)

# Correction tabhi jab galti / badlaav ka saaf shabd ho. "pichhle mahine ka baaki tha" correction nahi.
_CORRECTION_WORDS = re.compile(
    r"\b(galat|galt|galti|galati|sahi kar|sahi karo|theek kar|thik kar|badal do|badlo|badal de|badla|"
    r"cancel|hata do|hatao|hata de|delete|remove|mistake|wrong|correct|instead|ki jagah|ke jagah|"
    r"entry|likha|likhe|likhi|likh diya|dala tha|daala tha|dobara daalo|theek nahi tha|chadha diya|record kiya tha|update kar)\b"
    r"|\d+\s*(nahi|nahin|not|नहीं)\s*,?\s*\d+"
    r"|गलत|गलती|सही कर|ठीक कर|बदल दो|बदलो|हटा दो|हटाओ|कैंसल|की जगह|एंट्री|लिखा था",
    re.IGNORECASE)


_SAID_BEFORE = re.compile(r"\b(bola|boli|bole|kaha|maange|maanga|mange|manga|socha)\s+(tha|thi|the)\b", re.IGNORECASE)


def _not_a_correction(groups: list) -> list:
    """LLM ne CORRECTION kaha par galti/badlaav ka koi shabd nahi → normal entry (jaana-pehchaana aadmi ho to)."""
    people = None
    for group in groups:
        if group.record_type != RecordType.CORRECTION:
            continue
        text = " ".join(a.text for a in group.actions)
        if _CORRECTION_WORDS.search(text):
            continue
        if _SAID_BEFORE.search(text) and any(g is not group and re.search(r"\d", " ".join(x.text for x in g.actions))
                                              for g in groups):
            # "Ram ko 700 pakdaye aaj, pehle 600 bola tha" — sirf pehle kahi baat, galti ka shabd nahi → hatao
            print(f"✂️ GROUPING: '{text}' sirf pehle kahi baat hai, correction nahi — hata diya")
            group.actions = []
            continue
        if people is None:
            people = _known_people()
        low = text.lower()
        found = {n.strip() for n in people if n.strip() and
                 re.search(r"(?<!\w)" + re.escape(n.strip().lower()) + r"(?!\w)", low)}
        if len(found) == 1:
            name = found.pop()
            print(f"🔀 GROUPING: '{text}' mein galti ka koi shabd nahi — correction nahi, "
                  f"'{name}' ki nayi entry (Need Person)")
            group.record_type = RecordType.NEED_PERSON
            group.identity_key = name
            group.need_person = True
    return [g for g in groups if g.actions]


# Material movement ki jagah ke naam mein kachra: sirf number ("8"), ya role ka shabd ("customer"),
# ya naam ka tukda ("tradrs" jabki likha "Suresh tradrs") → statement ke shuru wala naam lo.
_ROLE_WORDS = {"customer", "customers", "grahak", "party", "supplier", "vendor", "ग्राहक", "पार्टी", "naya customer"}
_LEAD_NAME = re.compile(
    r"^\s*((?:[A-Z][\w]*|[\u0900-\u097F]+)(?:\s+[\w\u0900-\u097F]+){0,2}?)\s+"
    r"(?:ko|ne|naya|nayi|wale|wala|को|ने|नया|नई|वाले|वाला)(?=[\s,.]|$)")


def _bad_side(side, text):
    if not side or side.strip().upper() == "UNKNOWN":
        return False
    s = side.strip()
    if s.replace(",", "").replace(".", "").isdigit() or s.lower() in _ROLE_WORDS:
        return True
    # naam ka tukda: chhote akshar ka ek shabd, aur text mein usse pehle bada-akshar wala naam
    return (len(s.split()) == 1 and s[:1].islower()
            and re.search(r"[A-Z][\w]*\s+" + re.escape(s) + r"\b", text) is not None)


_DEST_MARK = r"\s+(?:pe|par|tak|mein|me|main|पे|पर|तक|में)(?![\w\u0900-\u097F])"
_SRC_MARK = r"\s+(?:(?:pe|par|mein|me|main|पे|पर|में)\s+)?(?:se|से)(?![\w\u0900-\u097F])"   # "shop pe se" = source


def _fix_movement_sides(groups: list) -> list:
    for group in groups:
        if group.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in (group.identity_key or ""):
            continue
        text = group.actions[0].text if group.actions else ""
        src, dst = [x.strip() for x in group.identity_key.split("→", 1)]
        m = _LEAD_NAME.match(text)
        lead = m.group(1).strip() if m else None
        changed = False
        if _bad_side(dst, text) and lead and lead != src:
            dst, changed = lead, True
        elif _bad_side(src, text) and lead and lead != dst:
            src, changed = lead, True
        # "Yadav ji ki site PE reta gaya" — 'pe/par/tak/mein' = pahunchne ki jagah. LLM ne use source
        # likha aur destination UNKNOWN → ulta. ('X se' likha ho to source sahi hai — mat chhedo.)
        if (dst.upper() == "UNKNOWN" and src and src.upper() != "UNKNOWN"
                and re.search(re.escape(src) + _DEST_MARK, text, re.IGNORECASE)
                and not re.search(re.escape(src) + _SRC_MARK, text, re.IGNORECASE)):
            print(f"🔀 GROUPING: '{src}' ke baad pe/par/tak/mein hai — ye pahunchne ki jagah hai, source nahi")
            src, dst, changed = "UNKNOWN", src, True
        if changed:
            new_key = f"{src} → {dst}"
            print(f"🔀 GROUPING: movement '{group.identity_key}' mein jagah ka naam galat — '{new_key}'")
            group.identity_key = new_key
    return groups


# "Sharma ji ko 1000 eent di, Kitanu gaadi lekar gaya" — Kitanu us maal ka DRIVER hai,
# alag haazri nahi. Aadmi ke group mein SIRF gaadi ki baat (na amount, na haazri ka shabd)
# aur statement mein maal-movement hai → aadmi ka group hatao, movement ke text mein jodo.
def _driver_of_movement(groups: list) -> list:
    from attendance_rules import DRIVING_WORDS, ATTEND_WORDS, FULL_DAY, HALF_DAY, _no_amount
    moves = [g for g in groups if g.record_type == RecordType.MATERIAL_MOVEMENT]
    if len(moves) != 1:
        return groups
    out = []
    for g in groups:
        texts = [a.text for a in g.actions]
        if (g.record_type == RecordType.NEED_PERSON and texts
                and all(DRIVING_WORDS.search(t) and _no_amount(t) and not ATTEND_WORDS.search(t)
                        and not FULL_DAY.search(t) and not HALF_DAY.search(t) for t in texts)):
            mv = moves[0]
            first = mv.actions[0]
            mv.actions[0] = first.model_copy(update={"text": f"{first.text.rstrip(' .')}, {' '.join(texts)}"})
            print(f"🚚 GROUPING: '{g.identity_key}' sirf gaadi le gaya — maal ka driver, alag entry nahi "
                  f"('{mv.actions[0].text}')")
            continue
        out.append(g)
    return out


# "Tractor mein 400 ka diesel dalwaya" — kharcha hai, maal ki aavak-jaavak nahi.
_EXPENSE_WORDS = re.compile(
    r"\b(diesel|deezal|dijal|petrol|fuel|tel|bijli|bijlee|electricity|bill|kiraya|kiraaya|rent|"
    r"repair|marammat|mistri ka kharcha|chai|nashta|kharcha|kharche)\b"
    r"|डीज़ल|डीजल|पेट्रोल|बिजली|बिल|किराया|मरम्मत|खर्चा|खर्चे",
    re.IGNORECASE)


# "Bijli wale ko gudam ke meter ke 2300 de aaye" / "rassi aur taala laaye gudam ke liye" — ek taraf apni jagah ho
# tab bhi kharcha hai (maal nahi), agar bechne wala maal ka koi shabd nahi.
_OWN_PLACE_SIDE = re.compile(r"^(GUDAM|GODAM|GODOWN|SHOP|DUKAAN|DUKAN|STORE)$")


def _expense_not_material(groups: list) -> list:
    from expense_rules import EXPENSE_WORD
    for group in groups:
        if group.record_type != RecordType.MATERIAL_MOVEMENT:
            continue
        sides = [x.strip().upper() for x in (group.identity_key or "").split("→")]
        if any(x not in ("UNKNOWN", "") and not _OWN_PLACE_SIDE.match(x) for x in sides):
            continue
        own = any(_OWN_PLACE_SIDE.match(x) for x in sides)
        if own and all(_OWN_PLACE_SIDE.match(x) for x in sides):
            continue                                       # "Shop se gudam" — dono apni jagah = asli maal ki aawajahi
        text = " ".join(a.text for a in group.actions)
        hit = _EXPENSE_WORDS.search(text) or (own and EXPENSE_WORD.search(text))
        if hit and not _ITEM_WORDS.search(text) and re.search(r"\d", text):
            word = hit.group(0)
            print(f"🔀 GROUPING: '{text}' kharcha hai ({word}), maal nahi — Standalone banaya")
            group.record_type = RecordType.STANDALONE_TRANSACTION
            group.identity_key = word
            group.need_person = None
    return groups


# Customer ne maal LIYA ("Suresh Traders wale 1500 eent le gaye") → maal customer ko GAYA, aaya nahi.
# Purani bikri ka sirf zikr ("jo 1000 eent li thi uske 4000 aaj de gaye") → sirf paisa, maal nahi.
_TOOK = re.compile(
    r"\b(le gaye|le gaya|le gayi|le gye|le gyi|le liye|le li|li|liye|li thi|le jaa|le ja|took|bought|purchased)\b"
    r"|ले गए|ले गया|ले गई|ली|लिए",
    re.IGNORECASE)


def _customer_side_fixes(groups: list) -> list:
    from sale_rules import is_return, past_sale_reference
    for group in groups:
        if group.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in (group.identity_key or ""):
            continue
        src, dst = [x.strip() for x in group.identity_key.split("→", 1)]
        text = " ".join(a.text for a in group.actions)
        named = [x for x in (src, dst) if x and x.upper() != "UNKNOWN" and x.lower() not in LOCATION_ALIASES]
        if past_sale_reference(text) and len(named) == 1:
            print(f"🔀 GROUPING: '{text}' purani bikri ka zikr hai — sirf paisa, Need Person '{named[0]}'")
            group.record_type = RecordType.NEED_PERSON
            group.identity_key = named[0]
            group.need_person = True
            continue
        if (dst.upper() == "UNKNOWN" and src and src.upper() != "UNKNOWN" and src.lower() not in LOCATION_ALIASES
                and _TOOK.search(text) and not is_return(text)):
            new_key = f"UNKNOWN → {src}"
            print(f"🔀 GROUPING: '{text}' — '{src}' ne maal liya, disha palti: '{new_key}'")
            group.identity_key = new_key
    return groups


# "Raju hotel wale" → naam "Raju" ("hotel wale" pehchaan hai, naam nahi)
_DESCRIPTOR = re.compile(r"^(?:[\w\u0900-\u097F]+\s+)?(?:wale|wala|wali|वाले|वाला|वाली)$", re.IGNORECASE)



# "Krishna bhatte ka 14000 ka bill aaya" — kisi PARTY ka bill = us supplier ki entry, dukaan ka kharcha nahi.
# (bijli / kiraya / phone ka bill → party ka shabd nahi → waise hi kharcha rahega)
_PARTY_BILL = re.compile(
    r"^\s*(?P<p>[^\d,;]+?)\s+(?:ka|ki|ke|का|की|के)\s+\d[\d,]*\s*(?:rupaye\s+)?(?:ka|ki|ke|का|की|के)\s+(?:bill|bil|बिल)",
    re.IGNORECASE)
_PARTY_WORD = re.compile(
    r"\b(bhatte|bhatta|bhate|bhata|traders|trader|wale|wala|ji|jee|sahab|saab|bhai|mills|store|dealer|supplier)\b"
    r"|भट्टे|भट्टा|ट्रेडर्स|वाले|जी|साहब|भाई", re.IGNORECASE)


def _party_bill(groups: list) -> list:
    for g in groups:
        if g.record_type != RecordType.STANDALONE_TRANSACTION or len(g.actions) != 1:
            continue
        m = _PARTY_BILL.search(g.actions[0].text or "")
        if m and _PARTY_WORD.search(m.group("p")) and len(m.group("p").split()) <= 5:
            party = m.group("p").strip()
            print(f"🧾 GROUPING: '{g.actions[0].text}' — '{party}' ka bill hai (supplier), kharcha nahi")
            g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, party, True
    return groups



# "Balaji bhatte ko 200 tooti eent wapas bheji" — maal SUPPLIER ko wapas = supplier ki minus entry,
# material movement nahi (warna source khaali → Unresolved → kuch nahi banta).
_RETURN_WORD = re.compile(r"\b(wapas|vapas|waapas|lauta\w*|return\w*)\b|वापस|लौटा", re.IGNORECASE)
_SUPPLIER_PARTY = re.compile(r"\b(bhatte|bhatta|bhate|bhata|traders|trader|supplier)\b|भट्टे|भट्टा|ट्रेडर्स", re.IGNORECASE)


def _supplier_return(groups: list) -> list:
    for g in groups:
        if g.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in (g.identity_key or ""):
            continue
        text = " ".join(a.text for a in g.actions)
        src, dst = [x.strip() for x in g.identity_key.split("→", 1)]
        if (_RETURN_WORD.search(text) and src.upper() == "UNKNOWN" and _SUPPLIER_PARTY.search(dst)
                and re.search(re.escape(dst) + r"\s+(?:ko|को)(?![\wऀ-ॿ])", text, re.IGNORECASE)):
            print(f"↩️ GROUPING: '{text}' — maal supplier '{dst}' ko wapas, Need Person (supplier ki minus entry)")
            g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, dst, True
    return groups


# "Ganpati bhatte ke 8000 purane chadhe hue hain humare upar" — party ka purana baaki.
# Standalone rahega to galla (cash) ka opening balance ban jaata hai → party ke naam Need Person.
_OLD_BALANCE = re.compile(
    r"\b(purane|purana|purani|pichle|pichla|chadhe|chadha|chadhi|bakaya|udhaar|udhar|humare upar|hamare upar|"
    r"unke upar|lene hain|lena hai|dene hain|dena hai)\b|पुराने|पुराना|चढ़े|बकाया|उधार|लेने हैं|देने हैं", re.IGNORECASE)
_PARTY_KE_NUM = re.compile(r"^\s*(?P<p>[^\d,;]+?)\s+(?:ke|ka|ki|के|का|की)\s+\d", re.IGNORECASE)


def _old_balance_party(groups: list) -> list:
    for g in groups:
        if g.record_type != RecordType.STANDALONE_TRANSACTION or len(g.actions) != 1:
            continue
        text = g.actions[0].text or ""
        m = _PARTY_KE_NUM.search(text)
        if m and _OLD_BALANCE.search(text) and _PARTY_WORD.search(m.group("p")) and len(m.group("p").split()) <= 5:
            party = m.group("p").strip()
            print(f"🔀 GROUPING: '{text}' — '{party}' ka purana baaki, Need Person (galla nahi)")
            g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, party, True
    return groups



# "Pichle hafte wali servicing ke 3000 baaki the, aaj de diye" — koi naam nahi, kharche ka shabd hai →
# grouping NEED_PERSON 'UNKNOWN' likh deta tha (phir entry chhoot jaati). Ye kharcha hai → Standalone.
def _unknown_person_expense(groups: list) -> list:
    from expense_rules import EXPENSE_WORD
    for g in groups:
        if g.record_type != RecordType.NEED_PERSON or str(g.identity_key or "").strip().upper() not in ("UNKNOWN", ""):
            continue
        text = " ".join(a.text for a in g.actions)
        m = EXPENSE_WORD.search(text)
        if m and re.search(r"\d", text):
            print(f"🔀 GROUPING: '{text}' — naam nahi, kharcha hai ({m.group(0)}) — Standalone")
            g.record_type, g.identity_key, g.need_person = RecordType.STANDALONE_TRANSACTION, m.group(0), None
    return groups



# Kharcha jise insaan samjha gaya: group ka "naam" ek CHEEZ / DUKAAN ("tractor", "Medical store", "tailor shop")
# ya bahar ka SEVA wala ("Lucky mechanic", "lineman") — ye hamare employee/supplier/customer nahi. → Standalone kharcha.
# "mistri" jaan-boojh ke nahi: "Sohan mistri" hamara mazdoor hai (Employee bundle).
_THING = re.compile(
    r"\b(tractor|dumper|jcb|gaadi|gadi|machine|generator|freezer|fridge|ac|truck|van|bike|motorcycle|scooty|tanki|"
    r"dukaan|dukan|shop|store|medical|dairy|dhaba|kirana|tailor|office|meter|godown)\b"
    r"|ट्रैक्टर|डंपर|जेसीबी|गाड़ी|मशीन|जनरेटर|दुकान|स्टोर|डेयरी|ढाबा|किराना|मीटर", re.IGNORECASE)
_SERVICE_TITLE = re.compile(
    r"\b(mechanic|mekanik|mistry\s+mechanic|electrician|bijli\s*wala|lineman|plumber|technician|painter\s+wala)\b"
    r"|मैकेनिक|इलेक्ट्रीशियन|लाइनमैन|प्लंबर", re.IGNORECASE)
_HIRE_WALE = re.compile(r"\b(jcb|crane|hydra|tanker|tempo|tent|dumper|tractor|truck|cylinder)\s+(wale|wala|vale|vala|wali)\b"
                        r"|जेसीबी\s+वाले|टैंकर\s+वाले", re.IGNORECASE)
_PERSON_HONORIFIC = re.compile(r"\b(ji|jee|sahab|saab|bhai|bhaiya)\b|जी|साहब|भाई", re.IGNORECASE)


def _expense_not_person(groups: list) -> list:
    from expense_rules import EXPENSE_WORD
    changed = []
    for g in groups:
        if g.record_type != RecordType.NEED_PERSON:
            continue
        key = str(g.identity_key or "")
        text = " ".join(a.text for a in g.actions)
        thing = _THING.search(key) and not _PERSON_HONORIFIC.search(key) and EXPENSE_WORD.search(text)
        service = _SERVICE_TITLE.search(key) or _SERVICE_TITLE.search(text) and key.strip().lower() in (
            "lineman", "mechanic", "electrician", "plumber", "technician")
        hire = _HIRE_WALE.search(key)                     # "JCB wale" / "tanker wala" — cheez wala, insaan nahi
        if (thing or service or hire) and re.search(r"\d", text):
            why = "cheez/dukaan ka naam" if thing else "bahar ka seva wala (mechanic/lineman…)"
            print(f"🔀 GROUPING: '{key}' {why} hai, insaan/party nahi — '{text}' kharcha (Standalone)")
            g.record_type, g.need_person = RecordType.STANDALONE_TRANSACTION, None
            m = EXPENSE_WORD.search(text)
            g.identity_key = m.group(0) if m else key
            changed.append(g)
    # "Chai ki dukaan ka bijli meter kharab tha" (bina rakam) + "lineman ko 500 diye" → ek hi kharcha
    for g in changed:
        for other in list(groups):
            if other is g or other.record_type != RecordType.STANDALONE_TRANSACTION:
                continue
            otext = " ".join(a.text for a in other.actions)
            if not re.search(r"\d", otext) and other.actions and g.actions and other.actions[0].date == g.actions[0].date:
                first = g.actions[0]
                g.actions[0] = first.model_copy(update={"text": f"{otext.rstrip(' .')}, {first.text}"})
                print(f"🔗 GROUPING: '{otext}' (bina rakam) usi kharche ka hissa — '{g.actions[0].text}'")
                groups.remove(other)
    return groups


# "Truck ka bhaada 2500 diya" + "Maal Rewari se aaya tha" — doosra tukda sirf bhaade ki baat hai, maal-entry nahi.
# "Dukaan ki safai ka saamaan 250 ka laaye" — apne kaam ka saamaan = kharcha, bechne wala maal nahi.
_FREIGHT = re.compile(r"\b(bhaada|bhada|bhaade|freight|transport|kiraya\s+gaadi)\b|भाड़ा|भाड़े", re.IGNORECASE)
_OWN_USE_GOODS = re.compile(
    r"\b(safai|cleaning|packing|office|pooja|puja|stationery|stationary|rassi|jhaadu|jhadu)\s+(ka|ki|ke)\s+(saamaan|saman|samaan)\b"
    r"|सफाई\s+का\s+सामान|पैकिंग\s+का\s+सामान", re.IGNORECASE)


def _expense_context_not_material(groups: list) -> list:
    freight = next((g for g in groups if g.record_type == RecordType.STANDALONE_TRANSACTION
                    and _FREIGHT.search(" ".join(a.text for a in g.actions))), None)
    for g in list(groups):
        if g.record_type != RecordType.MATERIAL_MOVEMENT:
            continue
        text = " ".join(a.text for a in g.actions)
        if freight is not None and not re.search(r"\d", text):
            first = freight.actions[0]
            freight.actions[0] = first.model_copy(update={"text": f"{first.text.rstrip(' .')} ({text.strip(' .')})"})
            print(f"🔗 GROUPING: '{text}' sirf bhaade ki baat hai, maal-entry nahi — '{freight.actions[0].text}'")
            groups.remove(g)
        elif _OWN_USE_GOODS.search(text) and re.search(r"\d", text):
            word = _OWN_USE_GOODS.search(text).group(0)
            print(f"🔀 GROUPING: '{text}' apne kaam ka saamaan ({word}) — kharcha (Standalone), maal nahi")
            g.record_type, g.identity_key, g.need_person = RecordType.STANDALONE_TRANSACTION, word, None
    return groups



# "Kal petrol ke 300 likhwaye the, wo galat the, 350 the" — PURANI entry ki galti. Extraction tod deta hai aur
# "galat" kho jaata hai → naye kharche ban jaate the. Asli message mein "likhwaya/likha … tha" + "galat" → Correction.
_PAST_RECORD = re.compile(
    r"\b(likhwaye|likhwaya|likhwayi|likhaye|likhaya|likha|likhe|likhi|darj\s+kiy\w*|entry\s+ki|record\s+kiy\w*|"
    r"chadhaya|chadhaye|daala|dala|daale)\s+(tha|the|thi)\b|लिखवाए\s+थे|लिखा\s+था|दर्ज\s+किया\s+था", re.IGNORECASE)
_WRONG = re.compile(r"\b(galat|galt|galti|wrong|mistake)\b|गलत|गलती", re.IGNORECASE)


def _old_entry_correction(groups: list, statement: str) -> list:
    if not statement or not (_PAST_RECORD.search(statement) and _WRONG.search(statement)):
        return groups
    if any(g.record_type == RecordType.CORRECTION for g in groups):
        return groups
    actions = [a for g in groups for a in g.actions]
    if not actions:
        return groups
    first = actions[0]
    merged = first.model_copy(update={"text": statement.strip()})
    print(f"✏️ GROUPING: '{statement}' purani entry ki galti batayi hai — Correction (naya kharcha nahi)")
    g0 = groups[0]
    g0.record_type, g0.identity_key, g0.need_person, g0.actions = RecordType.CORRECTION, "correction", None, [merged]
    return [g0]


# "Kitanu ko 2 din pehle 800 diye the, wo 600 the, theek kar do" / "Papa ne kal 2000 liye the wali entry hata do" —
# extraction correction ko tod deta hai: purani entry ki baat ("diye THE", "aaya hi nahi THA", "wo 600 the") ya khaali
# hukm ("Entry hata do") alag tukda ban jaata hai → us par NAYI entry ban jaati thi. Statement mein galti/theek-karo ka
# shabd ho to aise tukde correction mein jodo (aaj wali nayi baat — "Ram ko aaj 500 diye" — alag hi rehti hai).
_FIX_WORD = re.compile(
    r"\b(galat|galt|galti|galati|mistake|wrong|cancel|delete|remove)\b"
    r"|\b(theek|thik|sahi)\s+kar\s+(do|de|dena|dijiye|na)\b|\b(hata|hatwa)\s+(do|de|dijiye|dena)\b"
    r"|\bhatwa(ni|na)\b|\bhatao\b|गलत|गलती|ठीक\s+कर\s+दो|सही\s+कर\s+दो|हटा\s+दो|हटवानी|कैंसल", re.IGNORECASE)
_OLD_TALK = re.compile(r"\b(tha|the|thi)\b|था|थे|थी", re.IGNORECASE)
_TODAY_NEW = re.compile(r"\b(aaj|aj|abhi)\b|आज|अभी", re.IGNORECASE)
_BARE_FIX = re.compile(
    r"^\s*(?:(?:wo|woh|ye|yeh|uski|unki|is\s+ki)\s+)?(?:entry|entri)?\s*"
    r"(?:hata\s+do|hata\s+de|cancel\s+kar\w*|delete\s+kar\w*|theek\s+kar\s+do|thik\s+kar\s+do|sahi\s+kar\s+do)\s*$"
    r"|^\s*(?:एंट्री\s+)?(?:हटा\s+दो|ठीक\s+कर\s+दो|सही\s+कर\s+दो)\s*$", re.IGNORECASE)
_ON_DATE = re.compile(r"\s+on\s+\d{4}-\d{2}-\d{2}\.?\s*$")


def _correction_absorb(groups: list, statement: str) -> list:
    if not statement or not _FIX_WORD.search(statement):
        return groups
    corr = next((g for g in groups if g.record_type == RecordType.CORRECTION), None)
    absorbed, owners = [], []
    corr_name = (corr.identity_key or "").strip().lower() if corr is not None else ""
    corr_name = "" if corr_name == "correction" else corr_name
    for g in groups:
        if g is corr:
            continue
        other = (g.identity_key or "").strip().lower()
        if corr_name and g.record_type == RecordType.NEED_PERSON and other.split()[:1] != corr_name.split()[:1]:
            continue                        # "Ram 500 le gaya tha, Mohan wali entry galat" — Ram ki baat alag hai
        keep = []
        for a in g.actions:
            t = _ON_DATE.sub("", a.text or "").strip(" .")
            if (_OLD_TALK.search(t) and not _TODAY_NEW.search(t)) or _BARE_FIX.match(t):
                absorbed.append(a)
                owners.append(g)
            else:
                keep.append(a)
        g.actions = keep
    if not absorbed:
        return groups
    name = None
    if corr is not None and (corr.identity_key or "").strip().lower() not in ("", "correction"):
        name = corr.identity_key
    if name is None:
        for g in owners:
            if g.record_type == RecordType.NEED_PERSON and g.identity_key and g.identity_key.upper() != "UNKNOWN":
                name = g.identity_key
                break
    rest = [g for g in groups if g is not corr and g.actions]
    if not rest:
        text = statement.strip()                 # poora statement hi correction hai — "2 din pehle" / "kal" bhi saath
    else:
        parts = [_ON_DATE.sub("", a.text).strip(" .") for a in absorbed]
        parts += [a.text.strip(" .") for a in (corr.actions if corr is not None else [])]
        text = ", ".join(parts)
    base = corr.actions[0] if corr is not None and corr.actions else absorbed[0]
    merged = base.model_copy(update={"text": text})
    if corr is None:
        corr = owners[0].model_copy(update={"actions": []})
        if any(g is owners[0] for g in rest):
            nums = [int(m.group(1)) for g in groups for m in [re.match(r"G(\d+)$", g.group_id or "")] if m]
            corr.group_id = f"G{max(nums or [0]) + 1}"
    corr.record_type, corr.need_person = RecordType.CORRECTION, None
    corr.identity_key = name or "correction"
    corr.actions = [merged]
    print(f"✏️ GROUPING: correction ke saath purani entry ki baat {[a.text for a in absorbed]} — nayi entry nahi, "
          f"correction mein joda ('{text}', naam: {corr.identity_key})")
    return rest + [corr]


# Profile statement ("Gill saw mill Charkhi Dadri road pe hai, number 98…") standalone ban gaya → shuru ka naam = party.
_PROFILE_HINT_G = re.compile(r"(?<!\d)\d{10}(?!\d)|\b(pata|address)\b|पता",
                             re.IGNORECASE)
_DEAL_VERB_G = re.compile(r"\b(diye|diya|di|aaye|aaya|aayi|mile|mila|becha|bechi|li|liya|liye|bheji|kaam\s+kiya|kharid\w*)\b",
                          re.IGNORECASE)
_NAME_STOP = {"ka", "ki", "ke", "ko", "ne", "pe", "par", "mein", "me", "se", "wale", "wala", "wali", "hai", "hain",
              "number", "nambar", "mobile", "phone", "pata", "address", "naya", "nayi"}


def _lead_name(statement: str):
    words = re.findall(r"[A-Za-z]+", statement or "")
    if not words or not words[0][:1].isupper():
        return None
    name = []
    for i, w in enumerate(words):
        if w.lower() in _NAME_STOP:
            break
        if i > 0 and w[:1].isupper() and not words[i - 1][:1].isupper():
            break                                      # "Gill saw mill Charkhi" — Charkhi naya naam (jagah)
        name.append(w)
        if len(name) == 4:
            break
    return " ".join(name) or None


def _profile_person(groups: list, statement: str) -> list:
    if not statement or not _PROFILE_HINT_G.search(statement) or _DEAL_VERB_G.search(statement):
        return groups
    if len(groups) != 1 or groups[0].record_type != RecordType.STANDALONE_TRANSACTION:
        return groups
    name = _lead_name(statement)
    if not name:
        return groups
    g = groups[0]
    print(f"📇 GROUPING: '{statement}' profile ki baat — '{name}' party hai (Need Person), standalone nahi")
    g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, name, True
    return groups


# "Aaj gudam ki safai karwayi" + "Aaj gudam pe 3 labour lage the" — ek hi kaam, labour ki ginti alag tukda ban gayi.
_LABOUR_COUNT = re.compile(r"\b\d+\s+(labour|labor|mazdoor\w*|majdoor\w*|beldar\w*|aadmi|mistri|helper)\b", re.IGNORECASE)
_MONEY_HINT = re.compile(r"\b(rupaye|rs|diye|diya|de\s+diye|ka|ki|ke)\s*$|₹|\b\d{3,}\b", re.IGNORECASE)


def _merge_labour_count(groups: list) -> list:
    for g in groups:
        if len(g.actions) != 2:
            continue
        a, b = g.actions
        for cnt, work in ((a, b), (b, a)):
            if _LABOUR_COUNT.search(cnt.text or "") and not _MONEY_HINT.search(cnt.text or "") \
                    and not re.search(r"\d", work.text or "") and cnt.date == work.date:
                merged = work.model_copy(update={"text": f"{work.text.rstrip(' .')}, {cnt.text.strip(' .')}"})
                print(f"🔗 GROUPING: '{cnt.text}' sirf labour ki ginti — '{work.text}' ke kaam mein joda")
                g.actions = [merged]
                break
    return groups


def _descriptor_identity(groups: list) -> list:
    for group in groups:
        if group.record_type != RecordType.NEED_PERSON or not _DESCRIPTOR.match((group.identity_key or "").strip()):
            continue
        text = " ".join(a.text for a in group.actions)
        m = re.search(r"([A-Z][\w]*|[\u0900-\u097F]+)\s+" + re.escape(group.identity_key.strip()), text)
        if m and m.group(1).lower() not in ("ko", "ne"):
            print(f"🔀 GROUPING: '{group.identity_key}' naam nahi, pehchaan hai — naam '{m.group(1)}'")
            group.identity_key = m.group(1)
    return groups


# Maal aaj hila nahi (koi saamaan nahi, sirf rakam) → Material Movement nahi.
# Naam wali side ho to Need Person, warna Standalone. Dono side jagah (gudam/shop) hon to chhod do.
def _no_goods_not_material(groups: list) -> list:
    from sale_rules import has_goods
    for group in groups:
        if group.record_type != RecordType.MATERIAL_MOVEMENT:
            continue
        text = " ".join(a.text for a in group.actions)
        if has_goods(text) or not re.search(r"\d", text):
            continue
        sides = [x.strip() for x in (group.identity_key or "").split("→")]
        named = [x for x in sides if x and x.upper() != "UNKNOWN" and x.lower() not in LOCATION_ALIASES]
        places = [x for x in sides if x and x.lower() in LOCATION_ALIASES]
        if places:
            continue
        if named:
            print(f"🔀 GROUPING: '{text}' mein koi maal nahi hila, sirf paisa — Need Person '{named[0]}'")
            group.record_type = RecordType.NEED_PERSON
            group.identity_key = named[0]
            group.need_person = True
        else:
            print(f"🔀 GROUPING: '{text}' mein na maal na party — Standalone")
            group.record_type = RecordType.STANDALONE_TRANSACTION
            group.identity_key = "payment"
            group.need_person = None
    return groups


def _known_people():
    try:
        from db import SessionLocal
        from models import Employee, Customer, Supplier, FamilyMember
        db = SessionLocal()
        try:
            names = []
            for model in (Employee, Customer, Supplier, FamilyMember):
                names += [n for (n,) in db.query(model.name).all() if n]
            return names
        finally:
            db.close()
    except Exception:
        return []


def _stem_name_rx(name: str) -> str:
    """'SBI Bhatta' → 'sbi\s+bhatt[aeo]?' — 'SBI bhatte' / 'SBI bhatta' dono mile (aakhri a/e/o ka fark)."""
    words = []
    for w in name.strip().lower().split():
        if len(w) >= 4 and w[-1] in "aeo":
            words.append(re.escape(w[:-1]) + "[aeo]?")
        else:
            words.append(re.escape(w))
    return r"\s+".join(words)


def _named_person_in_standalone(groups: list) -> list:
    people = None
    for group in groups:
        if group.record_type != RecordType.STANDALONE_TRANSACTION:
            continue
        text = " ".join(a.text for a in group.actions)
        money = bool(_MONEY_WORDS.search(text) or _HISAB.search(text) or _PROFILE_WORDS.search(text))
        work_amt = bool(_WORK_AMOUNT.search(text))
        if not (money or work_amt):
            continue
        if people is None:
            people = _known_people()
        low = text.lower()
        found = {n.strip() for n in people if n.strip() and
                 re.search(r"(?<!\w)" + _stem_name_rx(n) + r"(?!\w)", low)}
        if len(found) == 1 and not money:
            # sirf "400 banta / 400 ka kaam" — tabhi jab wahi aadmi kaam karne wala ho ("Ram ne …")
            only = next(iter(found)).lower()
            if not re.search(r"(^|[\s,])" + re.escape(only) + r"\s+(ne|ने)\b|^\s*" + re.escape(only) + r"(?!\w)", low):
                found = set()
        if len(found) == 1:
            name = found.pop()
            print(f"🔀 GROUPING: Standalone '{group.identity_key}' mein jaana-pehchaana naam '{name}' "
                  f"— Need Person banaya")
            group.record_type = RecordType.NEED_PERSON
            group.identity_key = name
            group.need_person = True
    return groups


# ───────────────────────────────────────────────────────────────
# Safety net: NEED_PERSON ka naam sirf kaam ka naam ho ("Beldar",
# "driver", "cook") → action mein DB ka EK jaana-pehchaana aadmi dhoondo,
# group usi ke naam pe. ("Beldar ne Sohan ko 3600…" → "Sohan")
# ───────────────────────────────────────────────────────────────
def _title_only_person(groups: list) -> list:
    from helpers import _strip_titles
    people = None
    for group in groups:
        if group.record_type != RecordType.NEED_PERSON or _strip_titles(group.identity_key):
            continue
        if people is None:
            people = _known_people()
        low = " ".join(a.text for a in group.actions).lower()
        found = {n.strip() for n in people if n.strip() and
                 re.search(r"(?<!\w)" + re.escape(n.strip().lower()) + r"(?!\w)", low)}
        if len(found) == 1:
            name = found.pop()
            print(f"🔀 GROUPING: '{group.identity_key}' sirf kaam ka naam hai — asli aadmi '{name}'")
            group.identity_key = name
    return groups


# ───────────────────────────────────────────────────────────────
# Safety net: ek hi aadmi ki haazri do tukdon mein ("Kitanu ki haaziri lagao"
# + "Kitanu ne aadha din gaadi chalayi") → ek action, taaki ek hi din ki do
# haazri na banein. Amount/task wale action kabhi nahi judte.
# ───────────────────────────────────────────────────────────────
def _merge_attendance_driving(groups: list) -> list:
    from attendance_rules import attendance_and_driving_pair
    for group in groups:
        if group.record_type != RecordType.NEED_PERSON or len(group.actions) < 2:
            continue
        merged = []
        for a in group.actions:
            if merged and merged[-1].date == a.date and attendance_and_driving_pair(merged[-1].text, a.text):
                prev = merged[-1]
                print(f"🔗 GROUPING: haazri + driving ek kiye: '{prev.text}' + '{a.text}'")
                merged[-1] = prev.model_copy(update={"text": f"{prev.text.rstrip(' .')} aur {a.text}"})
                continue
            merged.append(a)
        group.actions = merged
    return groups

# ───────────────────────────────────────────────────────────────
# Ghar / Family nets (family_rules.py):
#   1. "ghar → UNKNOWN" movement + rakam ("ghar ka ration 4200 ka aaya") = ghar ka kharcha, maal nahi hila.
#   2. naam "galle"/"dukaan" (paisa rakhne ki jagah) — bina rakam: pichhle kharche ka hissa ("galle se diya");
#      rakam ho to action ka rishtedaar ("Papa ke haath galle se 3000") ya ghar ka kharcha (Standalone).
#   3. naam ghar ki cheez ("Ration") → Standalone; bina naam + rishte ka shabd ("Beti ki fees") → wahi naam.
#   4. bina rakam ghar ki baat ("Shaadi mein shagun dena tha") → agle/pichhle rakam wale kharche mein.
# ───────────────────────────────────────────────────────────────
def _family_groups(groups: list) -> list:
    from family_rules import TILL, TILL_WORD, HOME_SPEND, OWN_HOME, relation_person
    has_amt = lambda g: bool(re.search(r"\d", " ".join(a.text for a in g.actions)))
    text_of = lambda g: " ".join(a.text for a in g.actions)

    def merge_into(src, groups, home_only=False):
        i = groups.index(src)
        ok = lambda g: (g.record_type == RecordType.STANDALONE_TRANSACTION
                        or (g.record_type == RecordType.NEED_PERSON and relation_person(str(g.identity_key)))) \
            if home_only else g.record_type in (RecordType.STANDALONE_TRANSACTION, RecordType.NEED_PERSON,
                                                 RecordType.MATERIAL_MOVEMENT)
        near = [g for g in groups[:i][::-1] + groups[i + 1:] if g is not src and has_amt(g) and ok(g)]
        if not near:
            return False
        tgt = near[0]
        last = tgt.actions[-1]
        stxt = text_of(src).strip(" .")
        new = f"{last.text.rstrip(' .')}, {stxt}" if groups.index(tgt) < i else f"{stxt}, {last.text}"
        tgt.actions[-1] = last.model_copy(update={"text": new})
        print(f"🔗 GROUPING: '{stxt}' bina rakam — '{tgt.identity_key}' wale kharche ka hissa: '{new}'")
        groups.remove(src)
        return True

    # 1. apne ghar ka "movement"
    for g in groups:
        if g.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in str(g.identity_key):
            continue
        sides = [x.strip() for x in g.identity_key.split("→", 1)]
        home = [bool(OWN_HOME.match(x)) for x in sides]
        other = [x for x, h in zip(sides, home) if not h]
        if any(home) and all(x.upper() in ("UNKNOWN", "") for x in other) and has_amt(g):
            print(f"🏠 GROUPING: '{text_of(g)}' apne ghar ke liye khareeda — ghar ka kharcha (Standalone), maal movement nahi")
            g.record_type, g.identity_key, g.need_person = RecordType.STANDALONE_TRANSACTION, "ghar kharcha", None

    # 1b. "galle → Ghar" movement — galla jagah hai, maal nahi hila ("Papa ke haath galle se 3000 gaye, ghar pe kaam tha")
    from sale_rules import has_goods
    for g in groups:
        if g.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in str(g.identity_key):
            continue
        sides = [x.strip() for x in g.identity_key.split("→", 1)]
        if any((TILL.match(x) and x.lower() not in ("gudam", "godam", "shop", "dukaan", "dukan"))
               or re.search(r"\b(galle|galla|gulak|gullak)\b", x, re.IGNORECASE) for x in sides) \
                and has_amt(g) and not has_goods(text_of(g)):
            person = relation_person(text_of(g))
            print(f"🔀 GROUPING: '{g.identity_key}' galla jagah hai, maal nahi hila — "
                  + (f"Need Person '{person}'" if person else "ghar kharcha (Standalone)"))
            if person:
                g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, person, True
            else:
                g.record_type, g.identity_key, g.need_person = RecordType.STANDALONE_TRANSACTION, "ghar kharcha", None

    # 1c. "Papa ghar pe the" — sirf maujoodgi, na paisa na maal → entry nahi (role ka sawaal bhi nahi)
    for g in list(groups):
        if g.record_type == RecordType.NEED_PERSON and relation_person(str(g.identity_key)) and not has_amt(g) \
                and len(groups) > 1 and re.fullmatch(
                    r"\s*\S+\s+(?:ghar|dukaan|dukan|shop|gudam)\s+(?:pe|par|mein|me)\s+(?:hi\s+)?(?:the|tha|thi)\s*\.?\s*",
                    text_of(g), re.IGNORECASE):
            print(f"🗑️ GROUPING: '{text_of(g)}' sirf kaun kahan tha — len-den nahi, group hataya")
            groups.remove(g)

    # 2. "galle" / "dukaan" naam
    for g in list(groups):
        if g.record_type != RecordType.NEED_PERSON:
            continue
        key = str(g.identity_key or "")
        till = TILL.match(key) or (key.strip().upper() in ("UNKNOWN", "") and TILL_WORD.search(text_of(g)))
        if not till:
            continue
        if not has_amt(g):
            if merge_into(g, groups):
                continue
        person = relation_person(text_of(g))
        if person:
            print(f"🔀 GROUPING: '{key}' paisa rakhne ki jagah hai, party nahi — naam '{person}'")
            g.identity_key = person
        else:
            print(f"🔀 GROUPING: '{key}' paisa rakhne ki jagah hai, party nahi — '{text_of(g)}' kharcha (Standalone)")
            g.record_type, g.need_person = RecordType.STANDALONE_TRANSACTION, None
            m = HOME_SPEND.search(text_of(g))
            g.identity_key = m.group(0) if m else "ghar kharcha"

    # 3. ghar ki cheez naam bani / bina naam rishtedaar
    for g in groups:
        key = str(g.identity_key or "")
        if g.record_type == RecordType.NEED_PERSON and HOME_SPEND.fullmatch(key.strip()):
            print(f"🔀 GROUPING: '{key}' ghar ki cheez hai, insaan nahi — Standalone")
            g.record_type, g.need_person = RecordType.STANDALONE_TRANSACTION, None
            continue
        unnamed = (g.record_type == RecordType.NEED_PERSON and key.strip().upper() in ("UNKNOWN", "")) \
            or g.record_type == RecordType.STANDALONE_TRANSACTION
        if unnamed and has_amt(g):
            person = relation_person(text_of(g))
            if person:
                print(f"🔀 GROUPING: '{text_of(g)}' mein rishtedaar '{person}' — Need Person '{person}'")
                g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, person, True

    # 4. bina rakam ghar ki baat
    for g in list(groups):
        if g.record_type == RecordType.STANDALONE_TRANSACTION and not has_amt(g) and HOME_SPEND.search(text_of(g)) \
                and len(groups) > 1:
            merge_into(g, groups, home_only=True)
    return groups


# ───────────────────────────────────────────────────────────────
# "Papa ne Kitanu ko 1000 advance de diya" / "Papa Sohan ki hazri laga gaye" — group ka naam family member
# (Papa) ban gaya, par len-den ka asli aadmi Kitanu / Sohan hai; Papa sirf owner ki taraf se kaam kar rahe.
# Action mein EK jaana-pehchaana employee/customer/supplier "ko/ki/ke/ka" ke saath ho → wahi naam.
# ───────────────────────────────────────────────────────────────
def _business_people():
    try:
        from db import SessionLocal
        from models import Employee, Customer, Supplier
        db = SessionLocal()
        try:
            names = []
            for model in (Employee, Customer, Supplier):
                names += [n for (n,) in db.query(model.name).all() if n]
            return names
        finally:
            db.close()
    except Exception:
        return []


def _family_giver_identity(groups: list) -> list:
    from family_rules import relation_person
    people = None
    for g in list(groups):
        key = str(g.identity_key or "").strip()
        if g.record_type != RecordType.NEED_PERSON or not relation_person(key):
            continue
        if people is None:
            people = _business_people()
        moved, rest = [], []
        target = None
        for a in g.actions:
            low = a.text.lower()
            found = {n.strip() for n in people if n.strip() and re.search(
                r"(?<!\w)" + re.escape(n.strip().lower()) + r"\s+(ko|ki|ke|ka|को|की|के|का)(?!\w)", low)}
            if len(found) == 1 and (target is None or target == next(iter(found))):
                target = next(iter(found))
                moved.append(a)
            else:
                rest.append(a)
        if not target:
            continue
        strip = lambda t: re.sub(rf"^\s*{re.escape(key)}\s+(?:ne\s+|ने\s+)?", "", t, flags=re.IGNORECASE)
        # bacha hua bina-rakam tukda ("Papa pura din tha") usi kaam ka hissa
        if rest and all(not re.search(r"\d", a.text) and a.date == moved[-1].date for a in rest):
            last = moved[-1]
            moved[-1] = last.model_copy(update={"text": f"{last.text.rstrip(' .')}, " + ", ".join(strip(a.text) for a in rest)})
            rest = []
        moved = [a.model_copy(update={"text": strip(a.text)}) for a in moved]
        print(f"🔀 GROUPING: '{key}' sirf owner ki taraf se kar rahe — len-den '{target}' ka: {[a.text for a in moved]}")
        if rest:
            g.actions = rest
            new = g.model_copy(update={"group_id": f"{g.group_id}b", "identity_key": target, "actions": moved,
                                       "need_person": True})
            groups.insert(groups.index(g) + 1, new)
        else:
            g.identity_key, g.actions, g.need_person = target, moved, True
    return groups


# ───────────────────────────────────────────────────────────────
# "Gudam mein 25 eent tooti mili" — LLM ne "UNKNOWN → gudam" movement bana diya. Maal kahin gaya nahi,
# wahin toota / kam-zyada nikla → stock adjustment (Standalone). Sirf jab doosri side UNKNOWN ya wahi jagah ho.
# ───────────────────────────────────────────────────────────────
def _stock_change_not_movement(groups: list) -> list:
    from stock_rules import stock_sign
    for g in list(groups):
        if g.record_type != RecordType.MATERIAL_MOVEMENT or "→" not in str(g.identity_key):
            continue
        text = " ".join(a.text for a in g.actions)
        if stock_sign(text) is None or not re.search(r"\d", text):
            continue
        sides = [x.strip().lower() for x in g.identity_key.split("→", 1)]
        if len(g.actions) > 1:
            # ek action asli movement, doosra usi maal ka nuksaan ("…gudam mein 100 eent tooti nikli") → alag group
            bad = [a for a in g.actions if stock_sign(a.text) is not None and re.search(r"\d", a.text)]
            if bad and len(bad) < len(g.actions):
                g.actions = [a for a in g.actions if a not in bad]
                new = g.model_copy(update={"group_id": f"{g.group_id}s", "record_type": RecordType.STANDALONE_TRANSACTION,
                                           "identity_key": "stock adjustment", "actions": bad, "need_person": None})
                groups.insert(groups.index(g) + 1, new)
                print(f"🔀 GROUPING: {[a.text for a in bad]} usi maal ka nuksaan — alag stock adjustment group")
                continue
        unknown = [x in ("unknown", "") for x in sides]
        if any(unknown) or sides[0] == sides[1]:
            print(f"🔀 GROUPING: '{text}' — maal kahin gaya nahi, wahin toota/kam-zyada nikla — stock adjustment (Standalone)")
            g.record_type, g.identity_key, g.need_person = RecordType.STANDALONE_TRANSACTION, "stock adjustment", None
    return groups


# ───────────────────────────────────────────────────────────────
# Property ka sauda ("Malik sahab ki dukaan ka malba 1.5 lakh mein utha liya", "Malik sahab se dukaan 1.5 lakh mein li",
# "Malik sahab ka sauda 1.5 lakh") — LLM ne Standalone kharcha / maal movement bana diya. Naam (ji/sahab) + property
# shabd + badi rakam (≥ 10000) → us aadmi ka Need Person (role: Property / Site Owner → purchase).
# ───────────────────────────────────────────────────────────────
_PROPERTY_DEAL = re.compile(
    r"(?P<n>\b[A-Z][a-z]+\s+(?:ji|jee|sahab|saab|seth))\s+(?i:se|ki|ka|ke|wali|wala)\s+(?:[\w-]+\s+){0,3}?"
    r"(?i:haveli|kothi|building|makaan|makan|dukaan|dukan|godown|dharamshala|malba|sauda|deal|property)\b")


def _property_deal_person(groups: list) -> list:
    for g in groups:
        if g.record_type not in (RecordType.STANDALONE_TRANSACTION, RecordType.MATERIAL_MOVEMENT):
            continue
        text = " ".join(a.text for a in g.actions)
        m = _PROPERTY_DEAL.search(text)
        big = [n for n in re.findall(r"(?<![\d.])\d[\d,]*", re.sub(r"\d{4}-\d{2}-\d{2}", " ", text))
               if float(n.replace(",", "")) >= 10000]
        from sale_rules import has_goods
        goods = has_goods(re.sub(r"\bmalba\b", " ", text, flags=re.IGNORECASE))
        if m and big and not goods:
            name = m.group("n").strip()
            print(f"🏚️ GROUPING: '{text}' — property ka sauda/paisa, seller '{name}' — Need Person")
            g.record_type, g.identity_key, g.need_person = RecordType.NEED_PERSON, name, True
    return groups


async def grouping_node(state):

    extracted_intent = state["extracted_intent"]

    print("\n" + "=" * 60)
    print("GROUPING NODE INPUT")
    print("=" * 60)
    print(extracted_intent)

    grouped_intent = structured_llm.invoke(
        [
            SystemMessage(content=GROUPING_PROMPT),
            HumanMessage(
                content=f"""
Final Extracted Actions:

{extracted_intent.actions}
"""
            ),
        ]
    )

    grouped_intent.groups = _merge_duplicate_groups(
        _title_only_person(_split_multi_person(_named_person_in_standalone(
            _no_goods_not_material(_money_not_material(grouped_intent.groups))))))
    grouped_intent.groups = _driver_of_movement(_merge_attendance_driving(_not_a_correction(
        _expense_not_material(_customer_side_fixes(_fix_movement_sides(grouped_intent.groups))))))
    grouped_intent.groups = _old_entry_correction(grouped_intent.groups, state.get("original_user_statement") or "")
    grouped_intent.groups = _descriptor_identity(_expense_context_not_material(_expense_not_person(
        _unknown_person_expense(_old_balance_party(_supplier_return(
        _party_bill(grouped_intent.groups)))))))
    grouped_intent.groups = _family_giver_identity(_family_groups(grouped_intent.groups))
    grouped_intent.groups = _property_deal_person(_stock_change_not_movement(grouped_intent.groups))
    grouped_intent.groups = _correction_absorb(grouped_intent.groups, state.get("original_user_statement") or "")
    grouped_intent.groups = _profile_person(grouped_intent.groups, state.get("original_user_statement") or "")
    grouped_intent.groups = _merge_labour_count(grouped_intent.groups)

    print("\n" + "=" * 60)
    print("GROUPING NODE OUTPUT")
    print("=" * 60)
    print(grouped_intent)

    return {
        "grouped_intent": grouped_intent
    }



