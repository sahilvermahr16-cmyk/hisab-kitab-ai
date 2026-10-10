# tool_decision_node.py
from tokenize import group

from schemas import (
    ToolDecisionInput, ToolDecisionResult, ActionToolDecision, ToolName, RecordType,
    PersonRole, TransactionType,
    NEED_PERSON_BUNDLE, MATERIAL_MOVEMENT_BUNDLE, STANDALONE_BUNDLE,
)
from llm_setup import llm
from attendance_rules import presence_only, no_amount_no_task, overtime, strip_non_money
from langchain_core.messages import SystemMessage, HumanMessage

MANAGE_EMPLOYEE_PROMPT = """
═══════════════════════════════
MANAGE_EMPLOYEE
═══════════════════════════════

Use manage_employee ONLY for creating a new employee
or updating an existing employee's PROFILE information.

Profile fields:
- employee_name
- phone
- address
- role (driver / gudam_worker / shop_worker / tod_worker)

Do NOT use this tool for:
- employee ne kya kaam kiya (uska apna individual record)
  → record_employee_transaction
- employee ko payment/advance di → record_employee_transaction
- employee aaya / nahi aaya / driving ki → record_attendance
- general day/location activity log (jisme employee ka
  naam sirf ek context/detail ho, uska individual hisab
  na track ho raha ho) → record_work_log

═══════════════════════════════
PROFILE vs ACTUAL WORK — CRITICAL
═══════════════════════════════

Future/current role or profile information
→ manage_employee

Actual work performed, payment given, or attendance
→ record_employee_transaction / record_attendance / record_work_log

Examples:

"Ram hamare yaha karmchari hai, wo driver hai,
uska phone number 9876543210 hai aur pata Ramnagar hai"
→ manage_employee
employee_name=Ram, role=driver, phone=9876543210, address=Ramnagar

"Ram ab gudam pe kaam karega aur uska naya phone
number 9876543211 hai"
→ manage_employee
employee_name=Ram, role=gudam_worker, phone=9876543211
(address jaisi doosri existing info ko mat badlo)

"Ram ka pata badal kar Shastri Nagar kar do"
→ manage_employee
employee_name=Ram, address=Shastri Nagar

"Ram ab driver hai"
→ manage_employee
employee_name=Ram, role=driver

═══════════════════════════════
WRONG EXAMPLES — CRITICAL DISTINCTION
═══════════════════════════════

"Ram ne aaj gudam pe kaam kiya"
(standalone, Ram-specific — uska individual record track
ho raha hai, chahe amount na ho)
→ NOT manage_employee
→ record_employee_transaction (amount=0, note="gudam pe kaam kiya")

"Ram ne gudam pe kaam kiya aur 5 labour bhi lagi"
(day/location-centric general activity log — Ram sirf ek
context/detail hai, uska individual hisab track nahi ho
raha; "5 labour" jaisa general-activity-signal ise ek
diary/log entry banata hai, na ki Ram ka personal record)
→ NOT manage_employee
→ record_work_log

═══════════════════════════════
PARTIAL UPDATE RULE — CRITICAL
═══════════════════════════════

When updating an existing employee, update ONLY the
fields explicitly provided by the user.

Example:
"Ram ka phone 9876543211 kar do"
→ manage_employee
Update: phone=9876543211
Do NOT change or invent: address, role

Never overwrite an existing field with an empty value,
and never invent a value that wasn't stated.

═══════════════════════════════
NEW EMPLOYEE — MISSING FIELDS
═══════════════════════════════

If profile information is incomplete, use only what
was explicitly given; leave the rest null.

Example:
"Ram ko employee mein add kar do"
→ manage_employee
employee_name=Ram, phone=null, address=null, role=null
"""

RECORD_EMPLOYEE_TRANSACTION_PROMPT = """
═══════════════════════════════
RECORD_EMPLOYEE_TRANSACTION
═══════════════════════════════

Use record_employee_transaction to track a SPECIFIC
NAMED employee's individual work or payment record.

transaction_type:
- work    → employee ne kaam kiya (chahe amount ho ya na ho)
- payment → employee ko paisa diya

This tool represents the employee's OWN individual
account — it is used whenever the statement's focus is
on THIS employee specifically, not a general day/location
activity log.

Do NOT use this tool for:
- employee profile info (name/phone/address/role update)
  → manage_employee
- pure presence/absence/driving status with NO task
  description → record_attendance
- general day/location activity log where the employee's
  name is just one detail among others (e.g. labour count,
  multiple workers, site-level summary) → record_work_log

═══════════════════════════════
CRITICAL — EMPLOYEE-TRANSACTION vs WORK-LOG
═══════════════════════════════

The deciding question is NOT "is there an amount?".
The deciding question is: "Is this statement tracking
THIS employee's own individual record, or is it a
general activity/day-log where the employee's name is
just incidental context?"

Employee-centric (→ record_employee_transaction):
"Ram ne aaj gudam pe kaam kiya"
→ record_employee_transaction
transaction_type=work, amount=0, note="gudam pe kaam kiya"
(Ram's own record is being tracked, even with no amount)

"Ram ne 500 ka kaam kiya"
→ record_employee_transaction
transaction_type=work, amount=500

"Kitanu ne driving aur side pr 500 ka kaam kiya"
→ record_employee_transaction
transaction_type=work, amount=500, note="driving aur side ka kaam"

"Ram ko 300 diye" (no reason given)
→ record_employee_transaction
transaction_type=payment, amount=300

"Ram ko advance ke liye 300 diye"
→ record_employee_transaction
transaction_type=payment, amount=300, note="advance"

"Kitanu ko festival bonus 500 diya"
→ record_employee_transaction
transaction_type=payment, amount=500, note="festival bonus"

"Mohan ko mahine ki poori salary 8000 di"
→ record_employee_transaction
transaction_type=payment, amount=8000, note="poori salary"

Day/location-centric (→ record_work_log, NOT this tool):
"Ram ne gudam pe kaam kiya aur 5 labour bhi lagi"
→ record_work_log
(general activity log — Ram is just one detail alongside
labour count, not an individual record)

"Haasi Gate pe aaj 5 labour the, todne ka kaam hua"
→ record_work_log
(no named individual being tracked — pure site/day log)

═══════════════════════════════
ATTENDANCE vs WORK — CRITICAL
═══════════════════════════════

Pure presence/absence/driving status with NO task
description → record_attendance, NOT this tool.

"Ram aaj aaya" → record_attendance
"Ram aaj nahi aaya" → record_attendance
"Satpal aaj driving ki" → record_attendance
"Ram pura din aaya aur aadha drivery ki" → record_attendance
  (pure status, no specific task described)

The moment the statement describes WHAT was done (a task,
a rupee amount, a specific activity beyond simple presence),
it is no longer pure attendance:

"Ram ne table banai, 6 ghante kaam kiya" (no amount, but a
specific individual task) → record_employee_transaction
(transaction_type=work, amount=0, note="table banai, 6 ghante")

═══════════════════════════════
MIXED STATEMENTS — MULTIPLE TOOLS
═══════════════════════════════

A single statement may contain multiple distinct parts,
each requiring its own tool call.

"Ram pura din aaya aur aadha drivery ki, side pr eent bhari
aur utari 350 ka kaam kiya aur 200 liye"

This has THREE distinct parts:
Part A: "Ram pura din aaya aur aadha drivery ki"
        → pure attendance status → record_attendance
Part B: "side pr eent bhari aur utari, 350 ka kaam kiya"
        → individual work with amount → record_employee_transaction
        (transaction_type=work, amount=350)
Part C: "200 liye"
        → individual payment → record_employee_transaction
        (transaction_type=payment, amount=200)

Selected Tools:
1. record_attendance
2. record_employee_transaction
3. record_employee_transaction

═══════════════════════════════
DRIVER MENTIONED INSIDE A DELIVERY — CRITICAL
═══════════════════════════════

When a driver's name appears INSIDE a supplier/sale
delivery statement (e.g. "SBI Bhatte se 2500 eent aayi,
driver Kitanu tha"), do NOT create a separate
record_employee_transaction or record_attendance for
that driver. The delivery tool already captures the
driver name as a reference field. Only create a separate
employee record if the driver's attendance/work/payment
is EXPLICITLY mentioned as its own, standalone statement.

═══════════════════════════════
FILL UP FIELDS
═══════════════════════════════

Required:
- employee_name
- transaction_type ("work" or "payment")
- amount (0 if no amount mentioned for a work entry)
- transaction_date

Optional:
- payment_method, payment_provider (only if explicitly stated)
- note (work description goes here when there's no amount,
  or as additional detail alongside an amount)
"""

RECORD_ATTENDANCE_PROMPT = """
═══════════════════════════════
RECORD_ATTENDANCE
═══════════════════════════════

Use record_attendance ONLY for pure presence/absence/
driving STATUS statements — with NO task description
and NO rupee amount attached to that part of the text.

Values:
- attendance: "P" (poora din present), "half" (aadha din), "absent" (nahi aaya)
- driving: "P", "half", "absent"

IMPORTANT RULE: If only driving is mentioned (attendance
not explicitly stated), attendance automatically takes
the SAME value as driving.

Do NOT use this tool for:
- employee profile info → manage_employee
- any task/work description, even without an amount
  (e.g. "table banai", "eent bhari") → record_employee_transaction
- any rupee amount (work or payment) → record_employee_transaction
- general day/location activity log with no individual
  attendance status → record_work_log

═══════════════════════════════
DECISION TEST — CRITICAL
═══════════════════════════════

Step 1: Does this part explicitly state attendance/
driving status (aaya / nahi aaya / absent / present /
driving ki / drivery ki / kaam pe tha / duty pe tha /
chutti / aadhe din baad chala gaya / trip pe raha)?
   → YES, continue to Step 2

Step 2: Does this part ALSO describe a specific task,
activity, or amount?
   → YES → that part is NOT attendance (see the correct
     tool for that part instead)
   → NO → this part IS pure attendance → record_attendance

═══════════════════════════════
BEING AT WORK IS ATTENDANCE, NOT A TASK — CRITICAL
═══════════════════════════════

"kaam pe tha", "duty pe tha", "din bhar yahin raha",
"poora din yahin tha", "was at work all day" only say the
person was PRESENT. That is attendance (P), not a task — use
record_attendance and do NOT ask for an amount.

"Deepak subah se raat tak duty par tha"   → record_attendance (P)
"दीपक पूरे दिन ड्यूटी पर रहा"              → record_attendance (P)
"Deepak was on duty the whole day"        → record_attendance (P)
A real task ("deewar banai", "trolley khali ki") or an amount
is still record_employee_transaction.

OVERTIME IS WORK, NOT ATTENDANCE:
"ghante extra ruka", "der tak ruka", "overtime kiya", "stayed late"
describe EXTRA WORK — never record_attendance for it. If an amount is
given, it is record_employee_transaction (work).
"Vinod 3 ghante der tak ruka, uske 300"   → record_employee_transaction
"Vinod stayed 3 hours late, 300 for it"   → record_employee_transaction

LEAVING EARLY = HALF DAY:
"Deepak dopahar ko hi chala gaya"         → record_attendance (half)
"दीपक दोपहर में ही चला गया"                → record_attendance (half)
"Deepak left at lunch"                    → record_attendance (half)

═══════════════════════════════
DRIVING IS ALWAYS ATTENDANCE — CRITICAL
═══════════════════════════════

Driving words also include: trip, chakkar, pheri, gaadi /
tractor / dumper / truck chalaya, drove. With a DAY LENGTH
("poore din", "aadha din", "all day") they are driving status:
"Deepak poore din tractor ke chakkar lagata raha" → record_attendance (P, driving P)
"Deepak drove the dumper all day"                → record_attendance (P, driving P)
A COUNT of trips without day length ("Deepak ne 4 chakkar
lagaye") stays a work note → record_employee_transaction.

Driving-only statements are ALWAYS attendance events,
never record_work_log or record_employee_transaction:

- driving ki / drivery ki / driveri ki
- aadha din driving ki / pura din driving ki

Examples:

"Ram aaj aaya"
→ record_attendance (attendance="P", driving="absent")

"Ram aaj nahi aaya"
→ record_attendance (attendance="absent", driving="absent")

"Satpal aaj driving ki" (poora din implied)
→ record_attendance (attendance="P", driving="P")

"Satpal aadha din driving ki"
→ record_attendance (attendance="half", driving="half")

"Ram pura din aaya aur aadha drivery ki"
→ record_attendance (attendance="P", driving="half")

"Kitanu pura din aaya aur drivery ki"
→ record_attendance (attendance="P", driving="P")

═══════════════════════════════
NEVER ASSUME ATTENDANCE — CRITICAL
═══════════════════════════════

Do NOT create record_attendance unless attendance or
driving is EXPLICITLY mentioned for a NAMED individual.

Generic labour/worker mentions are NEVER attendance,
even if a count is given:

"5 labour lagi thi" → record_work_log, NOT record_attendance
"3 aadmi kaam kar rahe the" → record_work_log
"4 mistri lage the" → record_work_log

NEVER create attendance records for unnamed workers
(e.g. "Labour 1", "Labour 2") — attendance requires an
actual employee name.

═══════════════════════════════
DRIVER MENTIONED INSIDE A DELIVERY — CRITICAL
═══════════════════════════════

When a driver's name appears inside a supplier/sale
delivery statement (e.g. "SBI Bhatte se 2500 eent aayi,
driver Kitanu tha"), do NOT create record_attendance for
that driver. The delivery tool already captures the
driver name as a reference field. Only create
record_attendance if the driver's attendance is
EXPLICITLY mentioned as its own, standalone statement
(e.g. "Kitanu aaj aaya" said separately).

═══════════════════════════════
"PURA DIN / AADHA DIN" + WORK IMPLIES ATTENDANCE TOO — CRITICAL
═══════════════════════════════

When a statement says "pura din" (full day) or "aadha din"
(half day) TOGETHER WITH a work description — even with a
rupee amount — this ALSO implies an attendance/presence
signal, in ADDITION to the work itself. Both tools fire.

"Pura din kaam kiya" or "aadha din kaam kiya" is not JUST a
work description — it also tells you the employee was
PRESENT for that duration. This is different from "500 ka
kaam kiya" (no duration word) — that has no attendance
signal and stays purely record_employee_transaction.

Examples:

"Sandeep ne aaj pura din kaam kiya"
→ record_attendance (attendance="P", driving="absent")
→ record_employee_transaction (transaction_type=work, amount=0)

"Kitanu ne aadha din kaam kiya, 400 liye"
→ record_attendance (attendance="half", driving="absent")
→ record_employee_transaction (transaction_type=work, amount=0)
→ record_employee_transaction (transaction_type=payment, amount=400)

Do NOT apply this rule when there is no "pura din"/"aadha din"
wording — a plain "Ram ne 500 ka kaam kiya" has NO duration
word and stays purely record_employee_transaction, exactly as
before.

═══════════════════════════════
CRITICAL DISTINCTION — TASK DESCRIPTION BREAKS ATTENDANCE
═══════════════════════════════

The moment a part of the text describes WHAT was done
(a specific task, location detail, quantity, or item),
it is NOT attendance — even with no amount and no
explicit "aaya/nahi aaya" word.

"Ram aaj aaya" → record_attendance (pure status)

"Ram ne table banai, 6 ghante kaam kiya"
→ record_employee_transaction (specific task + duration,
   NOT a presence statement)

"Kitanu pura din aaya aur drivery ki"
→ record_attendance (pure status, no specific task)

"Kitanu ne side pr 2 ghante kaam kiya, 550 eent nikali"
→ record_employee_transaction (specific task + quantity)

RULE OF THUMB: record_attendance is ONLY for simple
presence or driving status. The moment the text
describes what was done, it moves to
record_employee_transaction (if a named individual's
own record) or record_work_log (if a general day/
location log).

═══════════════════════════════
MIXED STATEMENTS — MULTIPLE TOOLS
═══════════════════════════════

"Kitanu pura din aaya aur drivery ki, side pr 400 ka
kaam kiya aur 500 rupaye liye"

Three distinct parts:
Part A: "Kitanu pura din aaya aur drivery ki"
        → pure attendance → record_attendance
Part B: "side pr 400 ka kaam kiya"
        → individual work with amount → record_employee_transaction
Part C: "500 rupaye liye"
        → individual payment → record_employee_transaction

Selected Tools:
1. record_attendance
2. record_employee_transaction
3. record_employee_transaction

═══════════════════════════════
FILL UP FIELDS
═══════════════════════════════

Required:
- employee_name
- attendance_date
- attendance ("P" / "half" / "absent")
- driving ("P" / "half" / "absent")

Optional:
- note
"""

MANAGE_CUSTOMER_PROMPT = """
═══════════════════════════════
MANAGE_CUSTOMER
═══════════════════════════════

Use manage_customer ONLY for creating a new customer
or updating an existing customer's PROFILE information.

Profile fields:
- customer_name
- phone
- address

Do NOT use this tool for:
- customer ko maal/samaan becha gaya → record_sale_transaction
- customer se payment mili → record_sale_payment
- customer ka hisab/baaki poochna → (account query tool, not this one)

A customer name appearing INSIDE a sale or payment
statement does NOT automatically mean manage_customer
should be called — record_sale_transaction and
record_sale_payment can create/link the basic customer
identity automatically.

═══════════════════════════════
NEW CUSTOMER
═══════════════════════════════

Use manage_customer when the user explicitly wants to
add/register a customer (not sell to them).

Examples:

"Sharma ji ko customer mein add kar do"
→ manage_customer
customer_name=Sharma ji

"Sharma ji naye customer hain, phone 9876543210 hai,
address Purana Bazar Bhiwani hai"
→ manage_customer
customer_name=Sharma ji, phone=9876543210, address=Purana Bazar Bhiwani

═══════════════════════════════
PARTIAL PROFILE — CRITICAL
═══════════════════════════════

If only some profile fields are explicitly provided,
use only those; never invent the rest.

"Ramesh ji ko customer mein add kar do"
→ manage_customer
customer_name=Ramesh ji, phone=null, address=null

═══════════════════════════════
EXISTING CUSTOMER — UPDATE
═══════════════════════════════

Update ONLY the fields explicitly provided.

"Sharma ji ka phone number 9876543211 hai"
→ manage_customer
Update: phone=9876543211
Do NOT change or invent: address

"Sharma ji ka phone 9876543211 hai aur address Bhiwani hai"
→ manage_customer
Update: phone=9876543211, address=Bhiwani

═══════════════════════════════
WRONG EXAMPLES — CRITICAL DISTINCTION
═══════════════════════════════

"Sharma ji ko 1000 eent 14000 mein bechi"
→ NOT manage_customer
→ record_sale_transaction
(customer identity is created/linked automatically by
the sale tool — a customer name in a sale statement is
NOT profile information)

"Sharma ji ne 5000 rupaye diye"
→ NOT manage_customer
→ record_sale_payment

"Sharma ji ka 20000 baaki hai" / "Sharma ji ka hisab batao"
→ NOT manage_customer
→ (customer account/query tool)
"""

RECORD_SALE_TRANSACTION_PROMPT = """
═══════════════════════════════
RECORD_SALE_TRANSACTION
═══════════════════════════════

Use record_sale_transaction to record the BUSINESS SALE
itself — goods/material sold or delivered to a customer.

This tool does NOT record:
- customer payment received → record_sale_payment
- customer profile creation/update → manage_customer
- supplier-side material receipt → record_supplier_transaction

A customer name appearing here does NOT require calling
manage_customer separately — this tool creates/links the
customer identity automatically.

═══════════════════════════════
FIELDS
═══════════════════════════════

- customer_name (required)
- sale_date
- amount, item_name, unit, quantity, rate
- driver_name (if mentioned)
- source: where the material came from — this business's
  own storage (e.g. "gudam", "shop"), OR an external
  source (a supplier/bhatta name, or a site name) for a
  Direct Sale
- destination_name: where delivery was made, if mentioned
- supplier_name: ONLY set this when the material went
  DIRECTLY from a supplier to this customer, bypassing
  storage entirely (Direct Sale — see below)
- bill_id: for grouping multiple items under one bill
- note
- update_inventory: whether this sale should decrease
  stock. This value is DETERMINED UPSTREAM by the
  Transaction Classifier — do NOT decide this yourself
  from the wording of the statement.

═══════════════════════════════
OUT vs DIRECT SALE — CRITICAL
═══════════════════════════════

This tool is used for BOTH of these transaction types,
but they differ in one key way:

OUT (normal sale — material was already in storage):
- source = this business's own storage (gudam/shop)
- supplier_name = null
- update_inventory = True (stock decreases)

DIRECT SALE (material went straight from supplier/site
to the customer, never entering storage):
- source = the external supplier/bhatta name or site name
- supplier_name = the same supplier, if it's a supplier
  (so record_supplier_transaction can also be called to
  record the cost side — both tools fire together for a
  Direct Sale)
- update_inventory = False (stock must NOT be touched —
  the material was never in storage)

You will be told which case applies (OUT or DIRECT_SALE)
by the upstream Transaction Classifier — set
update_inventory accordingly, do not infer it from the
sentence structure yourself.

Examples:

"Sharma ji ko 1000 eent 15000 mein bechi" (source=gudam)
→ record_sale_transaction
customer_name=Sharma ji, item_name=eent, quantity=1000,
amount=15000, source=gudam, update_inventory=True

"SBI Bhatte se 2500 eent aayi, Ramesh ke liye seedha gayi,
₹7 rate mein" (Direct Sale)
→ record_sale_transaction
customer_name=Ramesh, item_name=eent, quantity=2500, rate=7,
source=SBI Bhatta, supplier_name=SBI Bhatta, update_inventory=False
(record_supplier_transaction is ALSO called for the cost side)

═══════════════════════════════
RETURNS — NEGATIVE QUANTITY/AMOUNT
═══════════════════════════════

A customer return is recorded with this SAME tool, using
NEGATIVE quantity and amount — do not invent a separate
"return" tool.

"Shyam ne window return ki, 300 le gaya"
→ record_sale_transaction
customer_name=Shyam, item_name=window, quantity=-1,
amount=-300, source=<same location the original sale
came from>, update_inventory=<same as the original sale>
note="customer return"

The source/update_inventory for a return should mirror
the ORIGINAL sale (if the original was OUT, the return
also touches inventory; if the original was a Direct
Sale, the return does not).

═══════════════════════════════
MULTI-ITEM SALE — SAME BILL
═══════════════════════════════

If one sale includes multiple different items for the
SAME customer, create one record_sale_transaction call
PER ITEM, sharing the same bill_id.

"Preeti ko gudam se 5 khidki aur 3 darwaze diye, 15000 mein"
→ record_sale_transaction (item_name=khidki, quantity=5, bill_id=BILL-X)
→ record_sale_transaction (item_name=darwaza, quantity=3, bill_id=BILL-X)

═══════════════════════════════
SALE AMOUNT ≠ PAYMENT — CRITICAL
═══════════════════════════════

"Sharma ji ko 2500 eent 35000 mein utari" describes the
sale VALUE, not money received. Do NOT assume a payment
was made just because a sale amount is mentioned.

If a payment is ALSO explicitly mentioned in the same
statement, call record_sale_payment separately (it is
never inferred from the sale amount alone):

"Sharma ji ko 2500 eent 35000 mein utari aur 3000 rupaye diye"
→ record_sale_transaction (amount=35000)
→ record_sale_payment (amount=3000)

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"Sharma ji ne 35000 rupaye diye" → record_sale_payment, NOT this tool
"Sharma ji ka phone 9876543210 hai" → manage_customer, NOT this tool
"SBI se 2500 eent gudam mein aayi" (no customer) → record_supplier_transaction, NOT this tool
"""

RECORD_SALE_PAYMENT_PROMPT = """
═══════════════════════════════
RECORD_SALE_PAYMENT
═══════════════════════════════

Use record_sale_payment ONLY when money was ACTUALLY
RECEIVED from a customer.

This tool records:
- a SalesPayment entry
- a CashLedger cash-IN entry

This tool does NOT record:
- the sale itself (goods/quantity/rate) → record_sale_transaction
- customer profile → manage_customer
- a refund given back to a customer (see RETURNS below)

═══════════════════════════════
SALE AMOUNT ≠ PAYMENT — CRITICAL
═══════════════════════════════

NEVER assume payment just because a sale amount is
mentioned. These are two different business events.

"Sharma ji ko 35000 mein maal utara"
→ record_sale_transaction (sale_amount=35000)
→ do NOT call record_sale_payment unless payment is
  ALSO explicitly stated

"Sharma ji ne 3000 rupaye diye"
→ record_sale_payment (amount=3000)
(this is real money received, separate from any sale amount)

═══════════════════════════════
PAYMENT LANGUAGE — CRITICAL
═══════════════════════════════

Phrases indicating ACTUAL payment received:
- rupaye/paise diye, cash diya, payment ki/kar di
- paisa/rupaye mile, payment receive hui
- purane hisab ke paise diye
- "X se N aaye / aaya / mile / mil gaye" (money CAME from X)
- Hindi or mixed script: "X से N आए", "X से N मिले", "X se N आए"
- English: "received N from X", "got N from X", "X paid N"

Examples (customer named, money came in, no goods):
"Gupta ji se 3000 aaye"            → record_sale_payment
"गुप्ता जी से 3000 आए"              → record_sale_payment
"गुप्ता जी se 3000 मिले"            → record_sale_payment
"Got 3000 from Gupta ji"           → record_sale_payment

Phrases describing SALE VALUE only (not payment):
- "X mein becha/utara/di" — this is the sale amount,
  do NOT treat it as payment received

═══════════════════════════════
PARTIAL / FULL PAYMENT
═══════════════════════════════

"Sharma ji ko maal 35000 mein utara, 3000 rupaye de diye"
→ record_sale_transaction (amount=35000)
→ record_sale_payment (amount=3000)
Remaining balance = 32000 (do NOT treat 3000 as the sale amount)

"Sharma ji ko 2500 eent 35000 mein utari aur poore 35000
rupaye de diye"
→ record_sale_transaction (amount=35000)
→ record_sale_payment (amount=35000)

═══════════════════════════════
PAYMENT WITHOUT SALE DETAILS
═══════════════════════════════

A payment can be recorded even when this statement
doesn't describe the original sale — item/quantity/rate
are NOT required.

"Sharma ji ne 5000 rupaye diye"
→ record_sale_payment
customer_name=Sharma ji, amount=5000
(no item/quantity/sale amount needed)

═══════════════════════════════
BILL / REFERENCE
═══════════════════════════════

If a bill/reference number is explicitly mentioned,
use it for bill_id.

"Bill 125 ke 5000 rupaye Sharma ji ne diye"
→ record_sale_payment
customer_name=Sharma ji, amount=5000, bill_id=125

═══════════════════════════════
MULTIPLE SEPARATE PAYMENTS
═══════════════════════════════

If the user describes separate payment events, each is
its own record_sale_payment call — do not combine them.

"Sharma ji ne 3000 diye aur baad mein 2000 aur diye"
→ record_sale_payment (amount=3000)
→ record_sale_payment (amount=2000)

═══════════════════════════════
REFUNDS — NEGATIVE AMOUNT
═══════════════════════════════

When money is given BACK to a customer (e.g. for a
returned item), use this SAME tool with a NEGATIVE
amount — do not invent a separate "refund" tool.

"Shyam ko return ke 300 wapas diye"
→ record_sale_payment
customer_name=Shyam, amount=-300, note="refund for return"

This should be paired with the corresponding negative
record_sale_transaction for the returned goods (see
record_sale_transaction's RETURNS section).

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"Sharma ji ko 2500 eent 35000 mein utari" → record_sale_transaction, NOT this tool
"Sharma ji ka phone 9876543210 hai" → manage_customer, NOT this tool
"SBI bhate ko 5000 rupaye diye" → record_supplier_payment, NOT this tool (bhata = supplier, never customer)
"Sharma ji ka 20000 baaki hai" → (customer account query tool), NOT this tool
"""

MANAGE_SUPPLIER_PROMPT = """
═══════════════════════════════
MANAGE_SUPPLIER
═══════════════════════════════

Use manage_supplier ONLY for creating a new supplier
or updating an existing supplier's PROFILE information.

Profile fields:
- supplier_name
- supplier_type (e.g. bhata, thekedaar, timber, hardware)
- phone
- address

Do NOT use this tool for:
- material received from supplier → record_supplier_transaction
- money paid to supplier → record_supplier_payment
- supplier ka hisab/baaki poochna → (account query tool, not this one)

A supplier name appearing INSIDE a transaction or payment
statement does NOT automatically mean manage_supplier
should be called — record_supplier_transaction and
record_supplier_payment can create/link the basic
supplier identity automatically.

═══════════════════════════════
NEW SUPPLIER
═══════════════════════════════

Use manage_supplier when the user explicitly wants to
add/register a supplier (not record a delivery from them).

Examples:

"SBI bhata ko supplier mein add kar do"
→ manage_supplier
supplier_name=SBI bhata

"SBI bhata supplier hai, type bhata hai, phone 9876543210
hai aur address Bhiwani hai"
→ manage_supplier
supplier_name=SBI bhata, supplier_type=bhata,
phone=9876543210, address=Bhiwani

═══════════════════════════════
PARTIAL PROFILE — CRITICAL
═══════════════════════════════

If only some profile fields are explicitly provided,
use only those; never invent the rest.

"SBI bhate ka phone number 9876543210 hai"
→ manage_supplier
supplier_name=SBI bhata, phone=9876543210
(supplier_type and address remain null)

═══════════════════════════════
EXISTING SUPPLIER — UPDATE
═══════════════════════════════

Update ONLY the fields explicitly provided.

"SBI bhata ka type thekedaar kar do"
→ manage_supplier
Update: supplier_type=thekedaar
Do NOT change or invent: phone, address

"SBI bhate ka phone 9876543211 kar do"
→ manage_supplier
Update: phone=9876543211
Do NOT change or invent: supplier_type, address

═══════════════════════════════
WRONG EXAMPLES — CRITICAL DISTINCTION
═══════════════════════════════

"SBI bhate se 2500 eent aayi"
→ NOT manage_supplier
→ record_supplier_transaction
(supplier identity is created/linked automatically by
the transaction tool — a supplier name in a delivery
statement is NOT profile information)

"SBI bhate ko 5000 rupaye diye"
→ NOT manage_supplier
→ record_supplier_payment

"SBI bhate ka hisab batao" / "SBI bhate ka baaki kitna hai"
→ NOT manage_supplier
→ (supplier account/query tool)

═══════════════════════════════
NOTE — "BHATA/BHATE" ALWAYS MEANS SUPPLIER
═══════════════════════════════

Whenever the word "bhata" or "bhate" appears, the entity
is always a Supplier — never a Customer.
"""

RECORD_SUPPLIER_TRANSACTION_PROMPT = """
═══════════════════════════════
RECORD_SUPPLIER_TRANSACTION
═══════════════════════════════

Use record_supplier_transaction to record material/goods
RECEIVED FROM a supplier — this is the SUPPLIER-SIDE
material transaction (the cost side of an acquisition).

This tool does NOT record:
- supplier profile → manage_supplier
- money paid to supplier → record_supplier_payment
- the customer-side sale/revenue → record_sale_transaction

A supplier name appearing here does NOT require calling
manage_supplier separately — this tool creates/links the
supplier identity automatically.

═══════════════════════════════
FIELDS
═══════════════════════════════

- supplier_name (required)
- transaction_date
- amount, item_name, quantity, unit, rate
- driver_name (if mentioned)
- destination_location: where the material was unloaded/
  stored (e.g. "gudam", "shop") — set this for the IN case
  (material entering storage)
- customer_name: ONLY set this when the material went
  DIRECTLY from this supplier to a customer, bypassing
  storage entirely (Direct Sale — see below)
- bill_id
- note

Exactly ONE of destination_location or customer_name
should typically be set, not both — they represent the
two different paths material can take after leaving the
supplier.

═══════════════════════════════
IN vs DIRECT SALE — CRITICAL
═══════════════════════════════

This tool is used for BOTH of these transaction types:

IN (material enters storage):
- destination_location = gudam/shop (this business's own storage)
- customer_name = null

DIRECT SALE (material goes straight from supplier to a
customer, never entering storage):
- customer_name = the customer receiving the material
- destination_location = null (or the customer's delivery
  location, not this business's storage)
- record_sale_transaction is ALSO called for the revenue
  side — both tools fire together

You will be told which case applies (IN or DIRECT_SALE)
by the upstream Transaction Classifier.

Examples:

"Gupta Bhatte se 1500 eent gudam mein aayi, ₹7200 mein"
→ record_supplier_transaction
supplier_name=Gupta Bhatta, item_name=eent, quantity=1500,
amount=7200, destination_location=gudam

"SBI Bhatte se 2500 eent aayi, Driver Kitanu tha, Ramesh
ke liye seedha gayi, ₹7 rate mein" (Direct Sale)
→ record_supplier_transaction
supplier_name=SBI Bhatta, item_name=eent, quantity=2500,
rate=7, driver_name=Kitanu, customer_name=Ramesh
(record_sale_transaction is ALSO called for the same event)

═══════════════════════════════
MULTI-ITEM DELIVERY — SAME SUPPLIER
═══════════════════════════════

When a single delivery from ONE supplier brings MULTIPLE
DIFFERENT items, create one record_supplier_transaction
call PER ITEM, repeating the supplier name, destination/
customer, and driver in EVERY item's call.

"Gupta Bhatte se 3 truck malba aur 800 kg loha aaya,
gudam mein utara"
→ record_supplier_transaction (item_name=malba, quantity=3,
  unit=truck, destination_location=gudam, supplier_name=Gupta Bhatta)
→ record_supplier_transaction (item_name=loha, quantity=800,
  unit=kg, destination_location=gudam, supplier_name=Gupta Bhatta)

═══════════════════════════════
ATTRIBUTES OF THE SAME DELIVERY — DO NOT SPLIT
═══════════════════════════════

Driver, destination, price, and remarks mentioned in
separate clauses about the SAME shipment belong to ONE
record_supplier_transaction call — do not create multiple
calls for details of a single delivery.

"SBI bhate se 2500 eent aayi. Driver Kitanu tha. Gudam me
utari. ₹18000 mein."
→ ONE record_supplier_transaction call with all fields combined

But TWO independent shipments from the same supplier
(each stating its own quantity) are TWO separate calls:

"SBI se 2500 eent aayi. SBI se 3000 eent aayi."
→ record_supplier_transaction (quantity=2500)
→ record_supplier_transaction (quantity=3000)

═══════════════════════════════
SUPPLIER AMOUNT ≠ CUSTOMER SALE AMOUNT
═══════════════════════════════

When both a supplier cost and a customer sale amount are
mentioned, keep them separate — never mix them up.

"SBI se 2500 eent 15000 mein aayi, Sharma ji ke 35000 mein utari"
→ record_supplier_transaction (amount=15000)
→ record_sale_transaction (amount=35000)
(do NOT put 35000 into the supplier transaction)

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"SBI bhata supplier hai, phone 9876543210 hai" → manage_supplier, NOT this tool
"SBI bhate ko 5000 rupaye diye" → record_supplier_payment, NOT this tool
"Sharma ji ko 2500 eent 35000 mein bechi" (no supplier mentioned) → record_sale_transaction, NOT this tool
"""

RECORD_SUPPLIER_PAYMENT_PROMPT = """
═══════════════════════════════
RECORD_SUPPLIER_PAYMENT
═══════════════════════════════

Use record_supplier_payment ONLY when money was ACTUALLY
PAID to a supplier.

This tool records:
- a SupplierPayment entry
- a CashLedger cash-OUT entry

This tool does NOT record:
- material received from supplier → record_supplier_transaction
- supplier profile → manage_supplier

═══════════════════════════════
SUPPLIER COST ≠ PAYMENT — CRITICAL
═══════════════════════════════

NEVER assume payment just because a supplier transaction
amount is mentioned. These are two different business
events — the material may have arrived on credit.

"SBI Bhatte se 2500 eent 15000 mein aayi"
→ record_supplier_transaction (amount=15000)
→ do NOT call record_supplier_payment unless payment is
  ALSO explicitly stated

"SBI Bhatte ko 5000 rupaye diye"
→ record_supplier_payment (amount=5000)
(this is real money paid, separate from any transaction amount)

═══════════════════════════════
PAYMENT LANGUAGE — CRITICAL
═══════════════════════════════

Phrases indicating ACTUAL payment made:
- rupaye/paise diye, cash diya, payment ki/kar di
- advance diya, kist di, purane hisab ke paise diye

Phrases describing TRANSACTION VALUE only (not payment):
- "X mein aayi/li/khareedi" — this is the transaction
  amount, do NOT treat it as payment made

═══════════════════════════════
PARTIAL / FULL PAYMENT
═══════════════════════════════

"SBI se 2500 eent 18000 mein aayi, 10000 abhi diye"
→ record_supplier_transaction (amount=18000)
→ record_supplier_payment (amount=10000)
Remaining balance = 8000 (do NOT treat 10000 as the
transaction amount)

"SBI se 2500 eent 18000 mein aayi aur poore 18000 diye"
→ record_supplier_transaction (amount=18000)
→ record_supplier_payment (amount=18000)

═══════════════════════════════
PAYMENT WITHOUT TRANSACTION DETAILS
═══════════════════════════════

A payment can be recorded even when this statement
doesn't describe the delivery itself — item/quantity/
rate are NOT required.

"SBI Bhatte ko 10000 diye"
→ record_supplier_payment
supplier_name=SBI Bhatta, amount=10000
(no item/quantity/transaction amount needed)

═══════════════════════════════
ADVANCE PAYMENTS
═══════════════════════════════

A payment can happen BEFORE any material has arrived
(advance payment). This is still recorded the same way —
the resulting balance may be negative (supplier owes
material), which is expected and valid.

"Mahesh Bhatte ko 20000 advance diye"
→ record_supplier_payment
supplier_name=Mahesh Bhatta, amount=20000, note="advance"

═══════════════════════════════
BILL / REFERENCE
═══════════════════════════════

If a bill/reference number is explicitly mentioned,
use it for bill_id.

"Bill 45 ke 10000 rupaye SBI Bhatte ko diye"
→ record_supplier_payment
supplier_name=SBI Bhatta, amount=10000, bill_id=45

═══════════════════════════════
MULTIPLE SEPARATE PAYMENTS
═══════════════════════════════

If the user describes separate payment events, each is
its own record_supplier_payment call — do not combine them.

"SBI Bhatte ko 10000 diye aur baad mein 5000 aur diye"
→ record_supplier_payment (amount=10000)
→ record_supplier_payment (amount=5000)

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"SBI Bhatte se 2500 eent aayi" → record_supplier_transaction, NOT this tool
"SBI bhata supplier hai, phone 9876543210 hai" → manage_supplier, NOT this tool
"Sharma ji ne 5000 rupaye diye" → record_sale_payment, NOT this tool (customer, not supplier)
"SBI Bhatte ka baaki kitna hai" → (supplier account query tool), NOT this tool
"""

RECORD_MATERIAL_MOVEMENT_PROMPT = """
═══════════════════════════════
RECORD_MATERIAL_MOVEMENT
═══════════════════════════════

Use record_material_movement ONLY when material moves
BETWEEN TWO of this business's OWN internal locations
(site/gudam/shop) — NO external supplier and NO customer
is involved on either end.

This is used when the upstream Transaction Classifier has
already determined this is an INTERNAL_MOVEMENT (both
source and destination are internal/tracked or site
locations belonging to this business).

Do NOT use this tool for:
- material received from a supplier → record_supplier_transaction
- material sold/delivered to a customer → record_sale_transaction
- a direct sale (supplier/site straight to a customer,
  never entering storage) → record_supplier_transaction +
  record_sale_transaction together
- a single-location stock change with no movement (e.g.
  damage, wastage, count correction) → record_adjustment
- general work/labour with no item moving → record_work_log

═══════════════════════════════
FIELDS
═══════════════════════════════

- source_type, source_name (required)
- destination_type, destination_name (required)
- item_name, quantity (required)
- unit
- movement_type (e.g. "transfer", "dump" — if the wording
  suggests a specific kind of movement)
- movement_reason
- movement_date
- note

source_type / destination_type should reflect what kind
of location it is — e.g. "site", "gudam", "shop" — as
already resolved by the Transaction Classifier.

═══════════════════════════════
CORE EXAMPLES
═══════════════════════════════

"Site A se 200 eent gudam gai"
→ record_material_movement
source_type=site, source_name=Site A,
destination_type=gudam, destination_name=gudam,
item_name=eent, quantity=200

"Gudam se site pe 5 bore cement bheja"
→ record_material_movement
source_type=gudam, source_name=gudam,
destination_type=site, destination_name=site,
item_name=cement, quantity=5, unit=bore

"Haasi Gate se 500 eent gudam bhej di" (following a
separate work-log statement about Haasi Gate — the
source location must still be explicitly repeated here,
even if already mentioned in a preceding activity-log
statement)
→ record_material_movement
source_type=site, source_name=Haasi Gate,
destination_type=gudam, destination_name=gudam,
item_name=eent, quantity=500

═══════════════════════════════
MULTI-ITEM MOVEMENT — SAME SOURCE/DESTINATION
═══════════════════════════════

When multiple DIFFERENT items move through the SAME
source-destination pair, create one record_material_movement
call PER ITEM, repeating source and destination in each.

"Gudam se shop 200 eent, 50 kg sariya aur 2 khidki gayi"
→ record_material_movement (item_name=eent, quantity=200,
  source_name=gudam, destination_name=shop)
→ record_material_movement (item_name=sariya, quantity=50,
  unit=kg, source_name=gudam, destination_name=shop)
→ record_material_movement (item_name=khidki, quantity=2,
  source_name=gudam, destination_name=shop)

Do NOT merge these into one call — each item becomes its
own database record.

═══════════════════════════════
CHAINED MOVEMENTS — NEVER MERGE
═══════════════════════════════

A connected material-flow chain (A→B, then B→C) is
recorded as SEPARATE calls — never combine them into one,
even though B connects them.

"Haasi Gate se 250 eent gudam gai, phir gudam se 100 eent
shop gaya"
→ record_material_movement (source=Haasi Gate, destination=gudam, quantity=250)
→ record_material_movement (source=gudam, destination=shop, quantity=100)

═══════════════════════════════
INVENTORY EFFECT
═══════════════════════════════

This tool updates Inventory at BOTH ends automatically —
decreasing stock at the source, increasing it at the
destination. Do not call record_adjustment separately for
either side of this movement.

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"SBI Bhatte se 2500 eent gudam mein aayi" (external
supplier involved) → record_supplier_transaction, NOT this tool

"Sharma ji ko 500 eent shop se di" (customer involved)
→ record_sale_transaction, NOT this tool

"Gudam mein 500 eent kharab ho gayi" (no second location,
no movement — just a quantity change) → record_adjustment,
NOT this tool

"Haasi Gate pe 5 labour the, todne ka kaam hua" (no item
moving, just work) → record_work_log, NOT this tool
"""

RECORD_WORK_LOG_PROMPT = """
═══════════════════════════════
RECORD_WORK_LOG
═══════════════════════════════

Use record_work_log for a GENERAL day/location activity
log — work performed at a location, labour count — where
the focus is "what happened at this location today", NOT
a specific named individual's own account, and NOT an
item physically moving between two locations.

This tool represents a diary-style entry: what work
happened, where, and how many people were involved.

Do NOT use this tool for:
- a specific named employee's own work/payment record
  (even without an amount) → record_employee_transaction
- a named employee's pure attendance/driving status
  → record_attendance
- an item moving from one location to another
  → record_material_movement
- a single-location stock change (damage/wastage/count
  correction) with no work description → record_adjustment

═══════════════════════════════
FIELDS
═══════════════════════════════

- location_type (site / gudam / shop) — required
- location_name (if a specific name is given, e.g.
  "Rampal ka ghar", "Haasi Gate")
- description — required, what work was done
- labour_count (if a number of workers is mentioned)
- activity_date
- note

═══════════════════════════════
CORE EXAMPLES
═══════════════════════════════

"Haasi Gate pe aaj 5 labour the, todne ka kaam hua"
→ record_work_log
location_type=site, location_name=Haasi Gate,
description="todne ka kaam", labour_count=5

"Ghar pr chhat utari aur 5 labour lagi thi"
→ record_work_log
location_type=site, description="chhat utari", labour_count=5

"Side Dinod Gate pr 4 labour lagi"
→ record_work_log
location_type=site, location_name=Dinod Gate,
description="labour lagi", labour_count=4

"Gudam par 3 helper lage the"
→ record_work_log
location_type=gudam, description="helper lage the", labour_count=3

═══════════════════════════════
CRITICAL DISTINCTION — GENERIC vs NAMED INDIVIDUAL
═══════════════════════════════

The deciding question: is a SPECIFIC NAMED individual's
own record being tracked, or is this a general activity
log where any name present is just incidental context?

"Ram ne aaj gudam pe kaam kiya" (Ram-specific, standalone)
→ record_employee_transaction, NOT this tool

"Ram ne gudam pe kaam kiya aur 5 labour bhi lagi" (general
day/location log — Ram is just one detail alongside the
labour count, not an individual record being tracked)
→ record_work_log

Generic worker mentions (no name at all) are ALWAYS this
tool, never attendance:

"5 labour lagi thi" → record_work_log, NOT record_attendance
"3 aadmi kaam kar rahe the" → record_work_log
"4 mistri lage the" → record_work_log

NEVER invent individual attendance records for unnamed
workers (e.g. "Labour 1", "Labour 2", "Labour 3").

═══════════════════════════════
LOCATION NAME — ALWAYS PRESERVE
═══════════════════════════════

Whenever an explicit location name is mentioned, preserve
it exactly — do not generalize or drop it.

"Side Bichala Bazar pr 5 helper lage the"
→ record_work_log
location_name=Bichala Bazar, description="helper lage the",
labour_count=5

If a location is established earlier in the same message
and a later part continues describing the SAME occasion at
that location, the location carries forward — but if a
DIFFERENT event type follows (e.g. a material movement),
the location must be explicitly repeated in that separate
tool call, not assumed.

═══════════════════════════════
NOT A MOVEMENT — CRITICAL
═══════════════════════════════

If no item is explicitly moving from one place to another,
this is NOT record_material_movement, even if quantities
are mentioned as part of describing the work.

"Side Dinod Gate pr 4 labour lagi, malva ke chakar lagaye"
(no destination stated for the malva — describes work
happening, not a completed movement to a second location)
→ record_work_log

Only use record_material_movement when a clear source AND
a clear destination are both stated for an item.

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"Ram ne 500 ka kaam kiya" (named individual + amount) → record_employee_transaction, NOT this tool
"Ram aaj aaya" (named individual, pure attendance) → record_attendance, NOT this tool
"Site A se 200 eent gudam gai" (item moving between two locations) → record_material_movement, NOT this tool
"Gudam mein 500 eent kharab ho gayi" (stock change, no work description) → record_adjustment, NOT this tool
"""

RECORD_ADJUSTMENT_PROMPT = """
═══════════════════════════════
RECORD_ADJUSTMENT
═══════════════════════════════

Use record_adjustment for a stock change that is NOT
caused by a supplier transaction, sale transaction, or
material movement between two locations.

This is a SINGLE-LOCATION event — the item's quantity
changes at one place, with no source/destination pair
involved.

Typical cases:
- stock damaged / wasted
- stock count correction (physical count doesn't match records)
- opening stock (first-time stock entry for an item)
- an UNRESOLVED material movement where the location type
  (storage/site/customer/supplier) could not be confirmed
  (the user skipped the HITL question) — in this case,
  record only what is known; do not guess the missing side

Do NOT use this tool for:
- material received from a supplier → record_supplier_transaction
- material sold to a customer → record_sale_transaction
- an item moving between two of this business's own
  locations → record_material_movement
- general work/labour activity with no stock quantity
  change → record_work_log

═══════════════════════════════
FIELDS
═══════════════════════════════

- location (required)
- item_name (required)
- unit (required)
- quantity_change (required, non-zero — positive increases
  stock, negative decreases it)
- reason (e.g. "damage", "wastage", "count_correction", "opening_stock")
- adjustment_date
- note

═══════════════════════════════
CORE EXAMPLES
═══════════════════════════════

"Gudam mein 500 eent kharab ho gayi"
→ record_adjustment
location=gudam, item_name=eent, quantity_change=-500,
reason="damage"

"Shop mein ginti ki, 30 eent kam nikli"
→ record_adjustment
location=shop, item_name=eent, quantity_change=-30,
reason="count_correction"

"Gudam mein 5000 eent ka opening stock daal do"
→ record_adjustment
location=gudam, item_name=eent, quantity_change=5000,
reason="opening_stock"

═══════════════════════════════
POSITIVE vs NEGATIVE — CRITICAL
═══════════════════════════════

The sign of quantity_change is the ONLY signal for
direction — there is no separate "in/out" field.

- Stock increasing (found extra, opening stock, correction
  upward) → positive quantity_change
- Stock decreasing (damage, wastage, correction downward)
  → negative quantity_change

═══════════════════════════════
NOT A MOVEMENT — CRITICAL
═══════════════════════════════

If the statement describes an item going FROM one place
TO another, that is record_material_movement, not this
tool — even if it sounds like an "adjustment".

"Gudam se shop 5 eent bheji" (source AND destination both
stated) → record_material_movement, NOT this tool

"Gudam mein 500 eent kharab ho gayi" (single location, no
destination) → record_adjustment

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"SBI Bhatte se 500 eent gudam mein aayi" → record_supplier_transaction, NOT this tool
"Sharma ji ko 500 eent shop se di" → record_sale_transaction, NOT this tool
"Site A se 200 eent gudam gai" (two locations) → record_material_movement, NOT this tool
"Haasi Gate pe 5 labour the" (no stock quantity change) → record_work_log, NOT this tool
"""

RECORD_EXPENSE_PROMPT = """
═══════════════════════════════
RECORD_EXPENSE
═══════════════════════════════

Use record_expense for a recurring/operational business
cost — a cost that is NOT tied to a specific employee,
supplier, or customer, and does NOT involve material
moving anywhere.

This tool records the expense itself. It does NOT record
payment and does NOT update CashLedger — use
record_expense_payment for that.

Do NOT use this tool for:
- salary/employee payment → record_employee_transaction
- supplier payment → record_supplier_payment
- property/deal purchase (see PURCHASE vs EXPENSE below)
  → record_purchase
- material received or moved → record_supplier_transaction /
  record_material_movement
- ghar / family ka kharcha (ghar ka saman, bachon ki fees,
  papa/bhai ne paise liye) → record_family_transaction

═══════════════════════════════
FIELDS
═══════════════════════════════

- category (e.g. "transport", "utility", "maintenance", "misc")
- amount (required)
- expense_date
- description
- note

═══════════════════════════════
CORE EXAMPLES
═══════════════════════════════

"Diesel par 2000 rupaye kharch hue"
→ record_expense
category=transport, amount=2000, description="diesel"

"Office ka bijli bill 1500 diya"
→ record_expense
category=utility, amount=1500, description="bijli bill"

"Generator ki servicing karayi, 600 ka"
→ record_expense
category=maintenance, amount=600, description="generator servicing"

"Office ka kiraya diya, 5000"
→ record_expense (category=rent, amount=5000, description="kiraya")
→ record_expense_payment (description="kiraya", amount=5000)
(payment language "diya" is present, so BOTH tools fire —
see RECORD_EXPENSE_PAYMENT's rule: most expenses are paid
immediately in full)

═══════════════════════════════
PURCHASE vs EXPENSE — CRITICAL
═══════════════════════════════

Use record_purchase (NOT this tool) when the statement
describes:
- a house/property demolition deal ("ghar todne ki deal")
- a purchase from a specific named seller where a running
  account/balance needs to be tracked
- partial payment now, with a future outstanding balance

Use record_expense when:
- it's a routine operational cost (fuel, rent, repair, misc)
- there's no ongoing seller account to track — it's a
  one-time cost, fully settled or not, with no negotiated
  deal structure

Examples:

"Sharma ji se ghar todne ki deal 3 lakh mein"
→ record_purchase, NOT record_expense

"Aaj 2 lakh mein bike li" (one-time purchase, no seller
account being tracked)
→ record_expense, NOT record_purchase

"Gudam ke liye ek machine li, 2 lakh mein" (no seller
name, no partial-payment/balance tracking implied)
→ record_expense, NOT record_purchase

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"Ram ko 300 diye" → record_employee_transaction, NOT this tool
"SBI Bhatte ko 5000 diye" → record_supplier_payment, NOT this tool
"Sharma ji se ghar todne ki deal 3 lakh mein" → record_purchase, NOT this tool
"""

RECORD_EXPENSE_PAYMENT_PROMPT = """
═══════════════════════════════
RECORD_EXPENSE_PAYMENT
═══════════════════════════════

Use record_expense_payment when money was ACTUALLY PAID
against a business expense.

This tool records:
- an ExpensePayment entry
- a CashLedger cash-OUT entry

This tool does NOT record:
- the expense itself (category/amount) → record_expense

═══════════════════════════════
EXPENSE ≠ PAYMENT — CRITICAL
═══════════════════════════════

Most expenses are paid immediately in full — in that case,
BOTH record_expense and record_expense_payment should be
called together for the same amount.

An expense is only left unpaid (payment skipped) when the
statement clearly indicates it wasn't settled yet (e.g.
"udhaar", "baad mein denge").

"Diesel par 2000 rupaye kharch hue, cash diya"
→ record_expense (amount=2000)
→ record_expense_payment (amount=2000)

"Generator ki servicing karayi, 600 ka, abhi udhaar hai"
→ record_expense (amount=600) only
→ do NOT call record_expense_payment (not yet paid)

═══════════════════════════════
FIELDS
═══════════════════════════════

- description (used to match this payment to the correct
  expense — use the same description/keyword as the
  related expense)
- amount (required)
- payment_date
- note

═══════════════════════════════
CORE EXAMPLES
═══════════════════════════════

"Office ka bijli bill 1500 diya"
→ record_expense (category=utility, amount=1500, description="bijli bill")
→ record_expense_payment (description="bijli bill", amount=1500)

"Generator ki servicing ke 600 pichle hafte baaki the,
aaj de diye"
→ record_expense_payment
description="generator servicing", amount=600

═══════════════════════════════
PARTIAL PAYMENT
═══════════════════════════════

"Machine repair karayi, 3000 ka, 1000 abhi diye"
→ record_expense (amount=3000, description="machine repair")
→ record_expense_payment (amount=1000, description="machine repair")
Remaining balance = 2000

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"Diesel par 2000 kharch hue" (no payment language) → record_expense only, NOT this tool
"SBI Bhatte ko 5000 diye" → record_supplier_payment, NOT this tool
"Ram ko 300 diye" → record_employee_transaction, NOT this tool
"""

RECORD_PURCHASE_PROMPT = """
═══════════════════════════════
RECORD_PURCHASE
═══════════════════════════════

Use record_purchase for a property/house purchase deal
for salvage — buying a whole house/plot to demolish for
material, or any negotiated deal/agreement with a specific
named seller where a running balance needs to be tracked.

This tool records the deal itself. It does NOT record
payment — use record_purchase_payment for advance/
installment payments.

Do NOT use this tool for:
- routine material supply from a bhatta/supplier
  → record_supplier_transaction
- a customer sale → record_sale_transaction
- a one-time operational cost with no seller account to
  track (see PURCHASE vs EXPENSE below) → record_expense

═══════════════════════════════
FIELDS
═══════════════════════════════

- seller_name (required)
- purchase_date
- total_amount
- description (e.g. "purana makan todne ki deal")
- location
- seller_phone
- note

═══════════════════════════════
PURCHASE vs EXPENSE — CRITICAL
═══════════════════════════════

Use this tool when:
- a house demolition deal is described ("ghar todne ki deal")
- there's a specific named seller
- partial payment is involved, with a future outstanding
  balance to track

Use record_expense instead when:
- it's a routine cost (fuel, rent, repair, misc)
- it's fully settled immediately with no ongoing account
- no seller name / no negotiated deal structure

Examples:

"Shyam se purana makan todne ki deal hui, 5 lakh mein"
→ record_purchase
seller_name=Shyam, description="purana makan todne ki deal",
total_amount=500000

"Lela Ram se ghar todne ki deal hui, 3 lakh mein, ghar
bus stand ke paas"
→ record_purchase
seller_name=Lela Ram, description="ghar todne ki deal",
total_amount=300000, location="bus stand ke paas"

"Aaj 2 lakh mein bike li" (no seller account, one-time cost)
→ record_expense, NOT record_purchase

═══════════════════════════════
TWO AMOUNTS — DEAL vs ADVANCE
═══════════════════════════════

When a statement mentions both a total deal amount and an
advance paid, keep them separate. The total amount goes
here; the advance is a SEPARATE record_purchase_payment call.

"Shyam se purana makan todne ki deal hui, 5 lakh mein deal
final hui, 1 lakh advance diya"
→ record_purchase (total_amount=500000)
→ record_purchase_payment (amount=100000)

Never combine the deal amount and the advance into a
single number.

═══════════════════════════════
ADDITIONAL SELLER DETAILS
═══════════════════════════════

Phone, location, and notes about the seller belong to the
SAME purchase record — do not split them into separate
tool calls.

"Shivraj Bhaisahab ke saath ghar todne ki deal 5 lakh
mein, location Purana Bazar, phone 9812300277, abhi 2 lakh
diye"
→ record_purchase
seller_name=Shivraj Bhaisahab, description="ghar todne ki deal",
total_amount=500000, location="Purana Bazar", seller_phone=9812300277
→ record_purchase_payment (amount=200000)

═══════════════════════════════
VALIDATION
═══════════════════════════════

The advance/payment amount should never exceed the total
deal amount. If it appears to, re-check the statement
before finalizing — the two numbers may have been misread.

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"SBI Bhatte se 2500 eent aayi" → record_supplier_transaction, NOT this tool
"Sharma ji ko 2500 eent 35000 mein bechi" → record_sale_transaction, NOT this tool
"Aaj 2 lakh mein bike li" → record_expense, NOT this tool
"""

RECORD_PURCHASE_PAYMENT_PROMPT = """
═══════════════════════════════
RECORD_PURCHASE_PAYMENT
═══════════════════════════════

Use record_purchase_payment for an advance or installment
payment made against a property purchase deal (see
record_purchase).

This tool records:
- a PurchasePayment entry
- a CashLedger cash-OUT entry

This tool does NOT record:
- the deal itself (seller/total amount) → record_purchase

═══════════════════════════════
FIELDS
═══════════════════════════════

- seller_name (required — used to match this payment to
  the correct purchase deal)
- amount (required)
- payment_date
- note

═══════════════════════════════
CORE EXAMPLES
═══════════════════════════════

"Shyam se purana makan todne ki deal hui, 5 lakh mein,
1 lakh advance diya"
→ record_purchase (seller_name=Shyam, total_amount=500000)
→ record_purchase_payment (seller_name=Shyam, amount=100000)

"Shyam ko 1 lakh aur diye" (installment on an existing deal)
→ record_purchase_payment
seller_name=Shyam, amount=100000

═══════════════════════════════
PAYMENT WITHOUT DEAL DETAILS
═══════════════════════════════

A payment can be recorded even when this statement doesn't
restate the deal amount — this tool only needs the seller
name and the amount being paid now.

"Lela Ram ko 50000 aur diye"
→ record_purchase_payment
seller_name=Lela Ram, amount=50000

═══════════════════════════════
MULTIPLE INSTALLMENTS
═══════════════════════════════

Each installment described is its own separate call — do
not combine them.

"Shyam ko pehle 1 lakh diya, phir 2 lakh aur diya"
→ record_purchase_payment (amount=100000)
→ record_purchase_payment (amount=200000)

═══════════════════════════════
VALIDATION
═══════════════════════════════

The cumulative amount paid should never exceed the total
deal amount for that seller. If a payment appears to
exceed the remaining balance, re-check the statement
before finalizing.

═══════════════════════════════
WRONG EXAMPLES
═══════════════════════════════

"Shyam se ghar todne ki deal 5 lakh mein hui" (deal itself, no payment) → record_purchase, NOT this tool
"SBI Bhatte ko 5000 diye" → record_supplier_payment, NOT this tool
"Ram ko 300 diye" → record_employee_transaction, NOT this tool
"""

RECORD_OPENING_BALANCE_PROMPT = """
═══════════════════════════════
RECORD_OPENING_BALANCE
═══════════════════════════════

Use record_opening_balance ONLY for an OLD balance that existed
BEFORE this app started recording — a one-time starting figure,
not a new business event.

Signals (any of these):
- "pehle ka / purana / pichla baaki / udhaar", "shuru mein",
  "jab se app shuru kiya usse pehle", "opening balance"
- a balance stated as a FACT, with no new sale/payment/work
  happening now: "Suresh pe 6000 udhaar hai", "Jai Bhatte ko
  5000 dene baaki hain"
- cash in hand at the start: "galle mein shuru mein 40000 the",
  "abhi cash 25000 hai, isse shuru karo"

Examples:
"Suresh Traders pe pehle ka 6000 udhaar hai" → record_opening_balance
"Jai Bhatte ko pichla 5000 dena baaki hai" → record_opening_balance
"Ram ne pehle 2000 advance le rakha hai" → record_opening_balance
"Ram ki pichli 1500 mazdoori baaki hai" → record_opening_balance
"Shuru mein galle mein 40000 cash tha" → record_opening_balance

WRONG EXAMPLES:
"Suresh ko 6000 ki eent bechi" → record_sale_transaction (new sale), NOT this tool
"Suresh ne 6000 diye" → record_sale_payment, NOT this tool
"Ram ko 2000 advance diya" → record_employee_transaction (advance given NOW), NOT this tool
"Jai Bhatte se 5000 ka maal aaya" → record_supplier_transaction, NOT this tool
"Suresh ka kitna baaki hai?" → a question (report), NOT this tool
"""

RECORD_FAMILY_TRANSACTION_PROMPT = """
═══════════════════════════════
RECORD_FAMILY_TRANSACTION
═══════════════════════════════

Use record_family_transaction for ANY money between the
business galla and a FAMILY member (papa, mummy, bhai, behen,
chacha, beta...) — family kharcha. It covers BOTH directions:
- money taken from the business for the family / home
  ("papa ne ghar ke liye 5000 liye", "bhai ki fees ke 12000 diye",
   "mummy ko 2000 diye")
- money a family member put into the business
  ("mummy ne galle mein 3000 daale", "bhai ne 5000 wapas diye")

Home spending with no person named ("ghar ke kharche ke liye
5000 nikale", "ghar ka ration 3000") is ALSO family kharcha →
record_family_transaction, NOT record_expense. record_expense is
only for BUSINESS running costs (diesel, bijli of shop, servicing).

One action → exactly one record_family_transaction call.
"""

GLOBAL_START = """
You are the Tool Decision Node of an AI-powered accounting
system. Your responsibility is to determine which
accounting tool(s) should be executed for exactly ONE
Action Group.

The Action Group has already been:
- extracted
- grouped
- classified (record_type is known)
- if a person was involved, their role has already been
  resolved (person_role)
- if this was a material movement, its transaction type
  has already been determined (IN / OUT / Internal
  Movement / Direct Sale / Unresolved)

Your task is ONLY to select the correct tool(s) for this
Action Group from the tools made available to you below.
"""

GLOBAL_RULES = """
═══════════════════════════════
GLOBAL RULES — APPLY TO EVERY DECISION
═══════════════════════════════

1. AVAILABLE TOOLS ONLY
Use ONLY the tools listed in `available_tools`. Never
invent a tool name that isn't in that list, even if it
seems like it would fit.

2. NO INVENTING VALUES
Never invent a name, amount, date, or any other detail
that is not explicitly present in the Action Group's
actions. If something is missing, leave it out — do not
guess.

3. ROLE/TYPE IS ALREADY DECIDED — DO NOT RE-DERIVE IT
The person's role (Employee/Customer/Supplier/Property
Owner) and the transaction type (IN/OUT/Internal Movement/
Direct Sale) have ALREADY been determined by earlier
stages of the pipeline. Do not second-guess or re-classify
them yourself — trust the classification you've been
given and select tools accordingly.

4. ONE GROUP CAN NEED MULTIPLE TOOLS
A single Action Group's actions may require more than one
tool call — e.g., a sale plus a payment, or a supplier
transaction plus a customer sale for a Direct Sale. Select
every tool that applies; do not force everything into one
call, and do not skip a needed one.

5. EVALUATE EACH ACTION INDEPENDENTLY
An Action Group may contain multiple distinct actions
(e.g., work + payment + a query). Evaluate each action on
its own against the rules below — do not assume all
actions in a group need the same tool.

7. ONLY WHAT ACTUALLY HAPPENED — NO TOOL FOR "DID NOT HAPPEN" OR "WILL HAPPEN"
If an action says money/material was NOT given or received
("nahi diye", "nahi bheje", "didn't pay", "नहीं दिए") or is only
a FUTURE PLAN ("kal denge", "dunga", "bhej denge", "will pay",
"देंगे"), nothing happened yet — select NO tool for that action
(empty list). Do not ask for an amount for it.

Examples:
"Vinod ki mazdoori abhi tak nahi di" → []
"Gupta ji kal 4000 bhejenge"        → []
"Deepak ko parso 600 dunga"         → []
"विनोद की मज़दूरी अभी तक नहीं दी"    → []
"गुप्ता जी कल 4000 भेजेंगे"          → []
"Haven't paid Vinod yet"            → []
"Will pay Deepak 600 on Sunday"     → []

EXCEPTION — attendance: "nahi aaya" / "didn't come" / "नहीं आया"
is a real fact (the person was ABSENT) → record_attendance.

If one action has BOTH a done part and a future part
("Vinod ko 300 diye, baaki kal denge"), select tools only for
the done part.

6. SCOPE BOUNDARY — WHAT YOU DO NOT DO
Do NOT extract tool arguments, do NOT execute tools, and
do NOT generate any user-facing text. Your only output is
the list of selected tools per action.

7. WHEN GENUINELY UNCERTAIN BETWEEN TWO TOOLS
Re-read the specific distinguishing rule in the relevant
tool's instructions below (most confusable pairs have an
explicit "WRONG EXAMPLES" section) before deciding —
do not guess.
"""

GLOBAL_END = """
═══════════════════════════════
OUTPUT
═══════════════════════════════

Return ONLY a valid ToolDecisionResult object containing:
- group_id: the Action Group's identifier
- action_decisions: for each action in the group, its
  action_index and the list of selected_tools that apply
  to that specific action

Do not include any explanation, commentary, or text
outside this structured output.
"""


# Har tool ka apna sub-prompt — ek hi jagah se lookup ho sakta hai
TOOL_PROMPT_MAP = {
    ToolName.MANAGE_EMPLOYEE: MANAGE_EMPLOYEE_PROMPT,
    ToolName.RECORD_EMPLOYEE_TRANSACTION: RECORD_EMPLOYEE_TRANSACTION_PROMPT,
    ToolName.RECORD_ATTENDANCE: RECORD_ATTENDANCE_PROMPT,
    ToolName.MANAGE_CUSTOMER: MANAGE_CUSTOMER_PROMPT,
    ToolName.RECORD_SALE_TRANSACTION: RECORD_SALE_TRANSACTION_PROMPT,
    ToolName.RECORD_SALE_PAYMENT: RECORD_SALE_PAYMENT_PROMPT,
    ToolName.MANAGE_SUPPLIER: MANAGE_SUPPLIER_PROMPT,
    ToolName.RECORD_SUPPLIER_TRANSACTION: RECORD_SUPPLIER_TRANSACTION_PROMPT,
    ToolName.RECORD_SUPPLIER_PAYMENT: RECORD_SUPPLIER_PAYMENT_PROMPT,
    ToolName.RECORD_MATERIAL_MOVEMENT: RECORD_MATERIAL_MOVEMENT_PROMPT,
    ToolName.RECORD_WORK_LOG: RECORD_WORK_LOG_PROMPT,
    ToolName.RECORD_ADJUSTMENT: RECORD_ADJUSTMENT_PROMPT,
    ToolName.RECORD_EXPENSE: RECORD_EXPENSE_PROMPT,
    ToolName.RECORD_EXPENSE_PAYMENT: RECORD_EXPENSE_PAYMENT_PROMPT,
    ToolName.RECORD_PURCHASE: RECORD_PURCHASE_PROMPT,
    ToolName.RECORD_PURCHASE_PAYMENT: RECORD_PURCHASE_PAYMENT_PROMPT,
    ToolName.RECORD_OPENING_BALANCE: RECORD_OPENING_BALANCE_PROMPT,
    ToolName.RECORD_FAMILY_TRANSACTION: RECORD_FAMILY_TRANSACTION_PROMPT,
}


# ───────────────────────────────────────────────────────────────
# Family tool sirf tab, jab baat sach mein ghar/family ki ho.
# (Pehle bina naam wala employee ka paisa "Ghar" ke kharche mein chala jaata tha.)
# ───────────────────────────────────────────────────────────────
import re as _re

_FAMILY_WORDS = _re.compile(
    r"\b(ghar|ghr|gharelu|ghar[- ]?kharch[ae]?|family|parivar|pariwar|papa|mummy|mummi|mammi|maa|"
    r"mata ?ji|pita ?ji|beta|beti|bete|wife|biwi|household|home)\b"
    r"|घर|घरेलू|परिवार|पापा|मम्मी|माँ|मां|माता|पिता|बेटा|बेटी|बेटे|पत्नी|बीवी",
    _re.IGNORECASE,
)


def _family_names():
    try:
        from db import SessionLocal
        from models import FamilyMember
        db = SessionLocal()
        try:
            return [n for (n,) in db.query(FamilyMember.name).all() if n]
        finally:
            db.close()
    except Exception:
        return []


def family_context(text: str) -> bool:
    """Text mein ghar/family ka shabd ya DB ke kisi family member ka naam hai?"""
    if _FAMILY_WORDS.search(text or ""):
        return True
    # "Ration ke 1800 diye" / "shagun ke 2100" — ghar ke kharche ka shabd (dukaan/kaam ki jagah nahi)
    from family_rules import HOME_SPEND, relation_person
    if (HOME_SPEND.search(text or "") and not _BUSINESS_PLACE.search(text or "")) or relation_person(text or ""):
        return True
    low = (text or "").lower()
    return any(_re.search(r"(?<!\w)" + _re.escape(n.strip().lower()) + r"(?!\w)", low)
               for n in _family_names() if n.strip())



# ───────────────────────────────────────────────────────────────
# Safety net: jo hua nahi ("nahi diye") ya sirf aage ka plan hai
# ("kal denge") — us action ka koi tool nahi. Agar usi action mein
# koi ho-chuka kaam bhi hai ("kaha tha denge, aaj de diye") to rehne do.
# "nahi aaya" (absent haazri) ko jaan-boojh ke nahi chhoote.
# ───────────────────────────────────────────────────────────────
_FUTURE = _re.compile(
    r"\b(denge|dunga|dungi|dega|degi|de denge|de dunga|bhejenge|bhej denge|bhejunga|bhejega|"
    r"chuka denge|chukayenge|karenge|karunga|karega|lenge|lunga|lega|legi|padenge|padega|padegi|"
    r"rakhne\s+(?:hain|hai|padenge)|rakhna\s+(?:hai|padega)|agle\s+(?:mahine|hafte|saal|baras|din)|"
    r"will (?:pay|give|send|transfer|settle|return)|going to (?:pay|give|send)|(?:dene|bhejne|chukane|lene) (?:ka|ki) (?:plan|soch|baat))\b"
    r"|देंगे|दूंगा|दूँगा|देगा|देगी|भेजेंगे|भेज देंगे|करेंगे|लेंगे|चुका देंगे",
    _re.IGNORECASE)
_NOT_DONE = _re.compile(
    r"\b(?:nahi|nhi|nahin|na)\s+(?:diye|diya|di|de paye|de paya|bheje|bheja|liye|liya|mile|mila|chukaye)\b"
    r"|\b(?:didn'?t|did not|haven'?t|have not|hasn'?t|not yet)\s+(?:pay|paid|give|given|send|sent|receive|received|get|got)\b"
    r"|नहीं\s+(?:दिए|दिया|दी|भेजे|भेजा|मिले|मिला|लिए|लिया)",
    _re.IGNORECASE)
_DONE = _re.compile(
    r"\b(de diye|de diya|de di|diye|diya|bhej diye|bhej diya|bheje|mile|mila|mil gaye|(?<!ke )(?<!ki )liye|liya|le liye|"
    r"bhara|bhari|bhar diya|bhar di|bharwaya|"
    r"chuka diye|paid|gave|sent|received|got)\b|दे दिए|दिए|दिया|भेज दिए|मिले|मिला|(?<!के )लिए|लिया",
    _re.IGNORECASE)


_PROFILE_TOOLS = {t for t in ToolName if t.value in ("manage_employee", "manage_customer", "manage_supplier")}
_PROFILE_DETAIL = _re.compile(
    r"\d{10}|\b(phone|mobile|number|nambar|address|pata|rehta|rehti|gaon|role)\b|फोन|मोबाइल|नंबर|पता|रहता",
    _re.IGNORECASE)


_GIVE_MONEY = _re.compile(
    r"\b(diye|diya|de diye|de diya|de aaye|de aaya|bheje|bheja|bhej diye|thama|thamaye|pakdaye|pakda diye|"
    r"chuka|chuka diya|chuka diye|jama|payment|paid|gave|sent|handed)\b"
    r"|दिए|दिया|भेजे|थमा|चुका|जमा|पेमेंट", _re.IGNORECASE)
_BILL = _re.compile(r"\b(bill|bil|invoice)\b|बिल", _re.IGNORECASE)


def _sale_rules(d, text, available_tools):
    """Bikri / customer ke paise — LLM ke chunav ki code se jaanch (sale_rules.py)."""
    from sale_rules import received, already_paid, service_charge, past_sale_reference, goods_given, has_goods
    allowed = set(available_tools) if available_tools is not None else set(ToolName)
    tools = d.selected_tools
    SALE, PAY = ToolName.RECORD_SALE_TRANSACTION, ToolName.RECORD_SALE_PAYMENT
    # 1. "…bechi, poore paise mil gaye" → bikri ke saath payment bhi
    if SALE in tools and PAY not in tools and PAY in allowed and received(text) and not already_paid(text):
        print(f"➕ TOOL DECISION: '{text}' mein paisa bhi aaya — record_sale_payment joda")
        tools.append(PAY)
    # 2. "5000 advance pehle hi de chuke the" → purana paisa, nayi payment nahi
    if PAY in tools and already_paid(text):
        print(f"🚫 TOOL DECISION: '{text}' — paisa pehle hi aa chuka tha, nayi payment nahi banegi")
        tools.remove(PAY)
    # 3. seva ("phone theek kiya, 800 liye") → bikri + payment
    if SALE in allowed and SALE not in tools and service_charge(text) and (PAY in tools or not tools):
        print(f"➕ TOOL DECISION: '{text}' seva ka kaam hai — record_sale_transaction joda")
        tools.insert(0, SALE)
        if PAY not in tools and PAY in allowed:
            tools.append(PAY)
    # 5. purani bikri ka sirf zikr ("jo li thi uske 4000 aaj de gaye") → nayi bikri nahi, sirf payment
    if past_sale_reference(text) and SALE in tools:
        print(f"🚫 TOOL DECISION: '{text}' purani bikri ka zikr — nayi bikri nahi, sirf payment")
        tools.remove(SALE)
        if PAY not in tools and PAY in allowed:
            tools.append(PAY)
    # 6. "50 kilo aloo … diye" — saamaan diya, ye bikri hai, payment nahi
    if PAY in tools and SALE not in tools and SALE in allowed and goods_given(text):
        print(f"🔀 TOOL DECISION: '{text}' saamaan diya hai — payment ki jagah bikri")
        tools[tools.index(PAY)] = SALE
    # 7. supplier: "Pawan ko 3000 thama aaye" — maal ka koi shabd nahi, sirf paisa → payment
    STX, SPAY = ToolName.RECORD_SUPPLIER_TRANSACTION, ToolName.RECORD_SUPPLIER_PAYMENT
    if (STX in tools and SPAY not in tools and SPAY in allowed and not has_goods(text)
            and _GIVE_MONEY.search(text) and not _BILL.search(text)):
        print(f"🔀 TOOL DECISION: '{text}' mein koi maal nahi, sirf paisa diya — supplier payment")
        tools[tools.index(STX)] = SPAY
    # 8. supplier ko maal wapas ("Balaji bhatte ko 200 eent wapas bheji") → supplier ki minus entry
    from sale_rules import is_return
    if (STX in allowed and STX not in tools and is_return(text) and has_goods(text)
            and SALE not in allowed):
        print(f"↩️ TOOL DECISION: '{text}' — maal supplier ko wapas, record_supplier_transaction (minus)")
        tools[:] = [t for t in tools if t not in (SPAY,)] + [STX]
    # 4. sirf naam wala profile, saath mein doosri entry → profile hatao
    prof = [t for t in tools if t in _PROFILE_TOOLS]
    if prof and len(tools) > len(prof) and not _PROFILE_DETAIL.search(text):
        print(f"🚫 TOOL DECISION: '{text}' mein profile ki koi jaankari nahi — {[t.value for t in prof]} hataya")
        for t in prof:
            tools.remove(t)
    d.selected_tools = tools


def _expense_rules(d, text, available_tools):
    """Kharcha: paisa diya to payment bhi (galla ghatega); purana kharcha = sirf payment (expense_rules.py)."""
    from expense_rules import expense_paid, old_expense_due, EXPENSE_WORD
    allowed = set(available_tools) if available_tools is not None else set(ToolName)
    EXP, EPAY = ToolName.RECORD_EXPENSE, ToolName.RECORD_EXPENSE_PAYMENT
    tools = d.selected_tools
    # "pichle hafte wali servicing ke 3000 baaki the, aaj de diye" → sirf payment, naya kharcha nahi
    if old_expense_due(text) and EPAY in allowed and (EXP in tools or not tools):
        print(f"💸 TOOL DECISION: '{text}' purane kharche ka paisa — sirf record_expense_payment")
        tools[:] = [t for t in tools if t != EXP]
        if EPAY not in tools:
            tools.append(EPAY)
    # "3200 ka diesel dalwaya" → kharcha + payment (sirf "bill aaya, abhi nahi diya / udhaar" mein payment nahi)
    elif EXP in tools and EPAY in allowed and EPAY not in tools and expense_paid(text):
        print(f"➕ TOOL DECISION: '{text}' kharche ka paisa diya — record_expense_payment joda")
        tools.append(EPAY)
    elif EXP in tools and EPAY in tools and not expense_paid(text):
        print(f"🚫 TOOL DECISION: '{text}' paisa abhi nahi diya — record_expense_payment hataya")
        tools.remove(EPAY)
    # "Ghar ki bijli ka bill 1600 bhara" — ghar ka kharcha family hai, dukaan ka nahi (munafa galat na dikhe)
    FAM = ToolName.RECORD_FAMILY_TRANSACTION
    ADJ = ToolName.RECORD_ADJUSTMENT      # "Ghar ke liye 10 bori cement aayi 3800 ki" — ghar ka saamaan, stock nahi
    from family_rules import GHAR_NOT, HOME_SPEND, relation_person
    if GHAR_NOT.search(text):
        # "Ghar ka nahi, gudam ka kiraya 8000 diya" — saaf bola ghar ka NAHI → dukaan ka kharcha
        if FAM in tools and EXP in allowed and not relation_person(text):
            print(f"🏪 TOOL DECISION: '{text}' 'ghar ka nahi' — dukaan ka kharcha (record_expense), family nahi")
            tools[:] = [t for t in tools if t != FAM] + [EXP]
            if EPAY in allowed and expense_paid(text):
                tools.append(EPAY)
    elif FAM in allowed and (EXP in tools or EPAY in tools or not tools or ADJ in tools) and _re.search(r"\d", text) and (
            _GHAR_KA.search(text) or (HOME_SPEND.search(text) and not _BUSINESS_PLACE.search(text)
                                    and not _WORK_MACHINE.search(text))) \
            and not (ADJ in tools and _BUSINESS_PLACE.search(text)) \
            and not (not tools and _PLAN_ONLY.search(text)):
        # "Ghar ki bijli ka bill 1600 bhara" / "Ration ke 1800 diye" — ghar ka kharcha family hai, dukaan ka nahi
        print(f"🏠 TOOL DECISION: '{text}' ghar ka kharcha — record_family_transaction (dukaan ka kharcha nahi)")
        tools[:] = [t for t in tools if t not in (EXP, EPAY, ADJ)] + ([FAM] if FAM not in tools else [])
    d.selected_tools = tools


# "Gas cutter ka cylinder bharwaya" — kaam ki machine ka cylinder dukaan ka kharcha hai, ghar ka nahi
_WORK_MACHINE = _re.compile(r"\b(cutter|welding|machine|generator|tractor|trolley|jcb|dumper|crane|mixer)\b"
                            r"|कटर|वेल्डिंग|मशीन|जनरेटर|ट्रैक्टर", _re.IGNORECASE)
# "Is mahine ki dukaan ki 6000 kiraye ki rakam baad mein denge" — bill / kiraya bana, paisa baad mein → sirf expense
_BILL_WORD = _re.compile(r"\b(kiraya|kiraye|kiraaya|rent|bill|bijli)\b|किराया|बिल|बिजली", _re.IGNORECASE)
_LATER_PAY = _re.compile(r"\bbaad\s+(mein|me|main)\s+(denge|dena|dunga|de\s+denge|chukayenge|bharenge)\b"
                         r"|\babhi\s+nahi\s+(diya|diye|bhara)\b|\budhaar\b|बाद\s+में\s+देंगे", _re.IGNORECASE)


# "Kal Mummy ko 2000 dene hain" — aage dena hai, abhi hua nahi (khaali faisla family mein na badle)
_PLAN_ONLY = _re.compile(r"\b(dene|dena|deni|lene|lena|bharne|bharna|chukane|chukana|chukani|rakhne|rakhna)\s+(hain|hai|he|h|padenge|honge)\b|\b(denge|dunga|dungi|bharenge|padenge)\b"
                         r"|देने\s+हैं|देना\s+है|देंगे", _re.IGNORECASE)


_MOVE_PLAN = _re.compile(
    r"\b(bhejni|bhejna|bhejne|lani|lana|lane|pahunchani|pahunchana|pahunchane|le\s+jani|le\s+jana|utarni|utarna|"
    r"rakhwani|rakhwana|uthwana|uthwani|uthwane|hatwana|hatwani|nikalwana|nikalwani|todna|todni|girana|girani)"
    r"\s+(hai|hain|h|he|padegi|padega)\b"
    r"|\b(bhejenge|bhejunga|bhejegi|aayega|aayegi|aayenge|jayega|jayegi|jaayega|jaayegi|pahunchayenge|layenge|utarenge)\b"
    r"|भेजनी\s+है|भेजना\s+है|आएगा|आएगी|जाएगा|भेजेंगे", _re.IGNORECASE)


_HAZRI = _re.compile(r"\b(hazri|haziri|haazri|haaziri|haajri|hajri|attendance|present)\b|हाज़िरी|हाजिरी|हाजरी", _re.IGNORECASE)
_WORK_DONE_ONLY = _re.compile(r"\bkaam\s+(?:khatam|khtm|pura|poora|ho\s+gaya|band|samapt)\b|काम\s+(?:खत्म|पूरा)",
                              _re.IGNORECASE)
_DEAL_DONE = _re.compile(r"\b(li|liya|le\s+li|kharid\w*|khareed\w*|sauda|deal|tay\s+hu\w*|pakka|pakki)\b|सौदा|ली|खरीद",
                         _re.IGNORECASE)


_AGENT_PAID = _re.compile(
    r"\b(ka|ki|ke)\s+(aadmi|munshi|ladka|naukar|driver|beta)\b.*?\d[\d,]*.*?\b(pakda\w*|de\s+ga\w*|dekar\s+ga\w*|"
    r"thama\w*|de\s+diye|diye|dekar)\b|का\s+(आदमी|मुंशी|लड़का).*?(पकड़ा|दे\s+गया|दे\s+गए)", _re.IGNORECASE)


# dukaan/kaam ki jagah ya cheez — "Dhaba ka gas cylinder" ghar ka nahi
_BUSINESS_PLACE = _re.compile(
    r"\b(dhaba|dukaan|dukan|shop|gudam|godam|site|office|tractor|jcb|dumper|truck|machine|generator|"
    r"mazdoor\w*|labour|majdoor\w*)\b|ढाबा|गोदाम|ट्रैक्टर|मज़दूर|मजदूर", _re.IGNORECASE)


_GHAR_KA = _re.compile(r"\b(ghar|ghr)\s+(ka|ki|ke)\b|घर\s+(का|की|के)", _re.IGNORECASE)


def _not_happened(text: str) -> bool:
    if not (_FUTURE.search(text) or _NOT_DONE.search(text)):
        return False
    rest = _NOT_DONE.sub(" ", _FUTURE.sub(" ", text))
    return not _DONE.search(rest)


_LABOUR_WORK = _re.compile(r"\b(kaam|kam|mazdoor\w*|mazdur\w*|mistri|labour|labor|dihadi|diahdi|beldar\w*|chinai|plaster)\b"
                          r"|\bkarigar\b|काम|मज़दूर|मजदूर|मिस्त्री|दिहाड़ी|लेबर|बेलदार|कारीगर", _re.IGNORECASE)
_OLD_MARK = _re.compile(r"\b(purana|purane|purani|pichla|pichli|pichhla|pichhli|pehle\s+(ka|ki|ke)|"
                        r"(pichhle|pichle)\s+(mahine|saal|baras))\b|पुराना|पुराने|पिछला|पिछली|पहले\s+का|पिछले\s+महीने",
                        _re.IGNORECASE)
_DUE_MARK = _re.compile(r"\b(baaki|baki|bakaya|udhaar|udhar)\b"
                        r"|\b(dene|dena|deni|lene|lena|leni|chukane|chukana|chukani)\s+(hain|hai|he|h|baaki)\b"
                        r"|बाकी|उधार|देने\s+हैं|देनी\s+है|देना\s+है|लेने\s+हैं|चुकाने\s+हैं", _re.IGNORECASE)
_NOW_EVENT = _re.compile(r"\b(diye|diya|de\s+diye|de\s+diya|di|aaye|aayi|aaya|mile|mila|bechi|becha|beche|kiya|kiye|"
                         r"liye|liya|chukaye|chukaya|chuka\s+diye|bhare|bhara|jama\s+kar\w*|pakdaye|pakdaya|"
                         r"de\s+ga\w*|le\s+ga\w*|aa\s+ga\w*|bhej\w*|daale|dale|daala|dala|daal\s+di\w*|nipta\w*)\b"
                         r"|दिए|दिया|आए|आया|मिले|बेची|किया|लिए|चुकाए|चुकाया|डाले|डाल\s+दिए", _re.IGNORECASE)
_MONEY_ONLY_TOOLS = {ToolName.RECORD_EMPLOYEE_TRANSACTION, ToolName.RECORD_SALE_PAYMENT,
                     ToolName.RECORD_SUPPLIER_PAYMENT, ToolName.RECORD_EXPENSE_PAYMENT,
                     ToolName.RECORD_OPENING_BALANCE}


_BUY_VERB = _re.compile(r"\b(li|liya|liye|le\s+li|le\s+liya|le\s+liye|kharida|kharidi|kharide|khareeda|khareedi|"
                        r"kharid\s+li\w*|khareed\s+li\w*|bought)\b|ली|लिया|खरीदा|खरीदी", _re.IGNORECASE)
_ASSET_WORD = _re.compile(r"\b(machine|machin|generator|genset|tractor|trolley|trolly|jcb|gaadi|gadi|truck|tempo|bike|"
                          r"scooter|motorcycle|dumper|cutter|mixer|pump|crane|compressor|car)\b"
                          r"|मशीन|जनरेटर|ट्रैक्टर|ट्रॉली|गाड़ी|ट्रक|बाइक|डंपर|कटर|मिक्सर|पंप", _re.IGNORECASE)
_PROPERTY_WORD = _re.compile(r"\b(haveli|kothi|makaan|makan|building|plot|dharamshala|property|bangla)\b"
                             r"|हवेली|कोठी|मकान|बिल्डिंग|प्लॉट|धर्मशाला", _re.IGNORECASE)
_PAY_WORD = _re.compile(r"\b(diye|diya|de\s+diye|de\s+diya|kiye|kiya|online|bheje|bheja|pakdaye|pakda\w*|chuka\w*|"
                        r"bayana|advance)\b|दिए|दिया|भेजे|चुका|बयाना", _re.IGNORECASE)
_ASSET_NOT = _re.compile(r"\b(theek|thik|repair|marammat|servicing|service|tel|diesel|petrol|kiraya|kiraye|kiraaya|"
                         r"bhada|bhaada|chali|chalayi|tyre|tayar|puncture|pankchar|bharwaya|dalwaya)\b"
                         r"|ठीक|मरम्मत|सर्विस|तेल|डीज़ल|डीजल|किराया|टायर", _re.IGNORECASE)


def _max_amount(text):
    t = _re.sub(r"\d{4}-\d{2}-\d{2}|\b\d{10}\b", " ", text or "")
    nums = [float(n.replace(",", "")) for n in _re.findall(r"\d[\d,]*(?:\.\d+)?", t)]
    return max(nums) if nums else 0


_PROFILE_TXT = _re.compile(r"(?<!\d)\d{10}(?!\d)|\b(pata|address)\b|पता",
                           _re.IGNORECASE)
_PROFILE_DEAL = _re.compile(r"\b(diye|diya|aaye|aaya|aayi|mile|mila|becha|bechi|li|liya|liye|bheji|kaam\s+kiya|kharid\w*)\b",
                            _re.IGNORECASE)


def _sanitize_decision(result: ToolDecisionResult, group, available_tools=None) -> ToolDecisionResult:
    """
    LLM ka jawaab check — galat action number pe aage crash na ho.
      - group_id hamesha wahi jo group ka hai
      - action number group ke actions ke andar ho
          * group mein sirf 1 action → galat number ko 0 maan lo (galti saaf hai)
          * kai actions → us decision ko chhod do (andaza nahi) + warning
    """
    n = len(group.actions)
    if result.group_id != group.group_id:
        print(f"⚠️ TOOL DECISION: LLM ne group_id '{result.group_id}' diya, sahi '{group.group_id}' — theek kiya")
        result.group_id = group.group_id
    kept = []
    for d in result.action_decisions:
        if 0 <= d.action_index < n:
            kept.append(d)
        elif n == 1:
            print(f"⚠️ TOOL DECISION: action_index {d.action_index} galat (group mein 1 action) — 0 maana")
            d.action_index = 0
            kept.append(d)
        else:
            print(f"⚠️ TOOL DECISION: action_index {d.action_index} galat (group {group.group_id} mein "
                  f"{n} actions) — ye decision chhod diya: {[t.value for t in d.selected_tools]}")
    # Ek hi action ke do decision ("action 0: []" + "action 0: [tool]") → ek; warna dobara-poochho
    # wala code dono ko bhar deta tha aur entry DO BAAR banti thi.
    merged = {}
    for d in kept:
        if d.action_index in merged:
            first = merged[d.action_index]
            extra = [t for t in d.selected_tools if t not in first.selected_tools]
            print(f"⚠️ TOOL DECISION: action {d.action_index} ke do decision aaye — ek kiya "
                  f"({[t.value for t in first.selected_tools]} + {[t.value for t in d.selected_tools]})")
            first.selected_tools = list(first.selected_tools) + extra
        else:
            merged[d.action_index] = d
    kept = list(merged.values())
    for d in kept:                      # ek action pe ek tool ek hi baar
        uniq = list(dict.fromkeys(d.selected_tools))
        if len(uniq) != len(d.selected_tools):
            print(f"⚠️ TOOL DECISION: action {d.action_index} mein ek hi tool do baar — ek rakha "
                  f"({[t.value for t in d.selected_tools]})")
            d.selected_tools = uniq
    if available_tools is not None:
        allowed = set(available_tools)
        for d in kept:
            bad = [t for t in d.selected_tools if t not in allowed]
            if bad:
                print(f"⚠️ TOOL DECISION: {[t.value for t in bad]} is group ke liye allowed nahi — hataya")
                d.selected_tools = [t for t in d.selected_tools if t in allowed]
    for d in kept:
        text = group.actions[d.action_index].text
        if (ToolName.RECORD_EMPLOYEE_TRANSACTION in d.selected_tools and presence_only(text)
                and (available_tools is None or ToolName.RECORD_ATTENDANCE in available_tools)):
            print(f"🔀 TOOL DECISION: '{text}' sirf maujoodgi hai — kaam ki jagah haazri")
            d.selected_tools = [t for t in d.selected_tools if t != ToolName.RECORD_EMPLOYEE_TRANSACTION]
            if ToolName.RECORD_ATTENDANCE not in d.selected_tools:
                d.selected_tools.append(ToolName.RECORD_ATTENDANCE)
        if (ToolName.RECORD_ATTENDANCE in d.selected_tools
                and ToolName.RECORD_EMPLOYEE_TRANSACTION in d.selected_tools
                and overtime(text) and not no_amount_no_task(text)):
            print(f"🔀 TOOL DECISION: '{text}' overtime ka kaam hai — haazri ka tool hataya")
            d.selected_tools = [t for t in d.selected_tools if t != ToolName.RECORD_ATTENDANCE]
        if (ToolName.RECORD_ATTENDANCE in d.selected_tools
                and ToolName.RECORD_EMPLOYEE_TRANSACTION in d.selected_tools
                and no_amount_no_task(text)):
            print(f"🔀 TOOL DECISION: '{text}' mein na amount na task — sirf haazri, kaam ka tool hataya")
            d.selected_tools = [t for t in d.selected_tools if t != ToolName.RECORD_EMPLOYEE_TRANSACTION]
        _sale_rules(d, text, available_tools)
        _expense_rules(d, text, available_tools)
        # "Aaj chai ke 120 lage" — bina party ka kharcha; LLM ne work_log chuna (kaam / mazdoor ka koi shabd nahi)
        from expense_rules import EXPENSE_WORD, expense_paid
        _EXP, _EPAY = ToolName.RECORD_EXPENSE, ToolName.RECORD_EXPENSE_PAYMENT
        if (group.record_type == RecordType.STANDALONE_TRANSACTION
                and d.selected_tools and set(d.selected_tools) <= {ToolName.RECORD_WORK_LOG}
                and EXPENSE_WORD.search(text) and _re.search(r"\d", text) and not _LABOUR_WORK.search(text)
                and (available_tools is None or _EXP in available_tools)):
            d.selected_tools = [_EXP] + ([_EPAY] if expense_paid(text) and (
                available_tools is None or _EPAY in available_tools) else [])
            print(f"🧾 TOOL DECISION: '{text}' kharcha hai, kaam nahi — {[t.value for t in d.selected_tools]} (work_log hataya)")
        if (not d.selected_tools and group.record_type == RecordType.STANDALONE_TRANSACTION
                and _BILL_WORD.search(text) and _LATER_PAY.search(text) and _re.search(r"\d", text)
                and (available_tools is None or _EXP in available_tools)):
            print(f"🧾 TOOL DECISION: '{text}' kiraya / bill bana, paisa baad mein — sirf record_expense")
            d.selected_tools = [_EXP]
        # "Rajbir ka mobile 94160…, Bhiwani bus adde ke paas dukaan hai" — aadmi ki profile, LLM ne tool nahi chuna
        if (not d.selected_tools and group.record_type == RecordType.NEED_PERSON and _PROFILE_TXT.search(text)
                and not _PROFILE_DEAL.search(text)):
            manage = [t for t in (ToolName.MANAGE_EMPLOYEE, ToolName.MANAGE_CUSTOMER, ToolName.MANAGE_SUPPLIER)
                      if available_tools is not None and t in available_tools]
            if len(manage) == 1:
                print(f"📇 TOOL DECISION: '{text}' sirf profile (phone / pata) — {manage[0].value}")
                d.selected_tools = manage
        # "Sohan ki pichhle mahine ki 1800 dihadi abhi deni hai" / "Purane hisab ke 15000 Suresh Traders ko chukane hain"
        #  — purana baaki, abhi kuch hua nahi → opening balance (payment / kuch nahi galat tha)
        _OPEN = ToolName.RECORD_OPENING_BALANCE
        if (_OLD_MARK.search(text) and _DUE_MARK.search(text) and _re.search(r"\d", text)
                and not _NOW_EVENT.search(text)
                and (available_tools is None or _OPEN in available_tools)
                and set(d.selected_tools) <= _MONEY_ONLY_TOOLS and d.selected_tools != [_OPEN]):
            print(f"📒 TOOL DECISION: '{text}' purana baaki hai, abhi kuch hua nahi — record_opening_balance "
                  f"(pehle: {[t.value for t in d.selected_tools]})")
            d.selected_tools = [_OPEN]
        # "Naya generator 45000 ka liya" / "Purana tractor trolley 1.2 lakh mein liya Bhupi se" — badi cheez KHAREEDI
        #  (kharid), dukaan ka kharcha nahi. "jagbeer ki haveli ke 1.5 lac online kiye" — property ki payment.
        _PUR, _PPAY = ToolName.RECORD_PURCHASE, ToolName.RECORD_PURCHASE_PAYMENT
        if (d.selected_tools and set(d.selected_tools) <= {ToolName.RECORD_EXPENSE, ToolName.RECORD_EXPENSE_PAYMENT}
                and _max_amount(text) >= 10000 and not _ASSET_NOT.search(text)):
            home = _re.search(r"\b(ghar|ghr)\b|घर", text, _re.IGNORECASE)
            if (_BUY_VERB.search(text) and (_ASSET_WORD.search(text) or _PROPERTY_WORD.search(text)) and not home
                    and (available_tools is None or _PUR in available_tools)):
                print(f"🏗️ TOOL DECISION: '{text}' badi cheez / property khareedi — record_purchase "
                      f"(pehle: {[t.value for t in d.selected_tools]})")
                d.selected_tools = [_PUR]
            elif (_PROPERTY_WORD.search(text) and _PAY_WORD.search(text) and not _BUY_VERB.search(text)
                    and (available_tools is None or _PPAY in available_tools)):
                print(f"🏗️ TOOL DECISION: '{text}' property ki payment — record_purchase_payment "
                      f"(pehle: {[t.value for t in d.selected_tools]})")
                d.selected_tools = [_PPAY]
        # "Suresh Traders ka aadmi unko 4000 pakda gaya" — party ke aadmi ne paisa diya = party ka payment
        if not d.selected_tools and _AGENT_PAID.search(text) and _re.search(r"\d", text) and (
                available_tools is None or ToolName.RECORD_SALE_PAYMENT in available_tools):
            print(f"💵 TOOL DECISION: '{text}' party ke aadmi ne paisa diya — record_sale_payment")
            d.selected_tools = [ToolName.RECORD_SALE_PAYMENT]
        # "Gudam mein 25 eent tooti mili" / "aaj shop pe 5 kam nikle" — stock wahin badla → record_adjustment
        #  (work_log / movement / kuch nahi chuna ho tab)
        from stock_rules import stock_sign
        _ADJ, _WORK, _MOV = ToolName.RECORD_ADJUSTMENT, ToolName.RECORD_WORK_LOG, ToolName.RECORD_MATERIAL_MOVEMENT
        if (stock_sign(text) is not None and _re.search(r"\d", text)
                and (available_tools is None or _ADJ in available_tools)
                and set(d.selected_tools) <= {_WORK, _MOV} and set(d.selected_tools) != {_MOV}
                and not _not_happened(text)):
            print(f"📦 TOOL DECISION: '{text}' stock wahin toota/kam-zyada nikla — record_adjustment "
                  f"(pehle: {[t.value for t in d.selected_tools]})")
            d.selected_tools = [_ADJ]
        # "Kal 200 eent gudam se dukaan bhejni hai" / "maal baad mein gudam aayega" — maal abhi hila nahi (plan)
        _STOCK_TOOLS = {ToolName.RECORD_MATERIAL_MOVEMENT, ToolName.RECORD_ADJUSTMENT, ToolName.RECORD_WORK_LOG}
        if set(d.selected_tools) & _STOCK_TOOLS and _MOVE_PLAN.search(text):
            print(f"🚫 TOOL DECISION: '{text}' maal abhi hila nahi (aage ka plan) — stock entry nahi")
            d.selected_tools = [t for t in d.selected_tools if t not in _STOCK_TOOLS]
        # "Sohan ki hazri Rana ji ki kothi ke kaam pe laga do" — employee + hazri ka shabd, koi tool nahi → haazri
        if not d.selected_tools and _HAZRI.search(text) and available_tools is not None \
                and ToolName.RECORD_ATTENDANCE in available_tools and not _not_happened(text):
            print(f"🗓️ TOOL DECISION: '{text}' haazri ki baat, LLM ne tool nahi chuna — record_attendance")
            d.selected_tools = [ToolName.RECORD_ATTENDANCE]
        # "Malik sahab ki dukaan ka kaam khatam" — sirf khabar hai ki kaam poora hua, koi naya kaam / labour nahi
        if ToolName.RECORD_WORK_LOG in d.selected_tools and _WORK_DONE_ONLY.search(text) \
                and not _re.search(r"\d|labour|mazdoor|mistri|बेलदार|लेबर", text, _re.IGNORECASE):
            print(f"🚫 TOOL DECISION: '{text}' sirf kaam khatam hone ki khabar — work log nahi")
            d.selected_tools = [t for t in d.selected_tools if t != ToolName.RECORD_WORK_LOG]
        # "Kal Mummy ko 2000 dene hain" — paisa dena BAAKI hai (plan), abhi diya nahi → paise wali entry nahi.
        # (maal wali baat — "18000 lene hain" udhaar bikri — aur bill/kharcha waise hi rehte hain)
        if d.selected_tools and _PLAN_ONLY.search(text):
            from sale_rules import has_goods
            money_only = {ToolName.RECORD_FAMILY_TRANSACTION, ToolName.RECORD_EMPLOYEE_TRANSACTION,
                          ToolName.RECORD_SALE_PAYMENT, ToolName.RECORD_SUPPLIER_PAYMENT,
                          ToolName.RECORD_EXPENSE_PAYMENT}
            drop = [t for t in d.selected_tools if t in money_only]
            if drop and not has_goods(text):
                print(f"🚫 TOOL DECISION: '{text}' paisa abhi dena baaki hai (plan) — entry nahi "
                      f"(hataya: {[t.value for t in drop]})")
                d.selected_tools = [t for t in d.selected_tools if t not in money_only]
        if d.selected_tools and _not_happened(text):
            # profile ki baat mein future aata hi hai ("beldari karega") — wo tool rehne do
            # "kiraya / bill … baad mein denge" — bill ban chuka, sirf paisa baaki → expense rehne do (payment nahi)
            bill_later = bool(_BILL_WORD.search(text) and _LATER_PAY.search(text))
            keep = [t for t in d.selected_tools if t in _PROFILE_TOOLS or (bill_later and t == ToolName.RECORD_EXPENSE)]
            drop = [t for t in d.selected_tools if t not in keep]
            if drop:
                print(f"🚫 TOOL DECISION: '{text}' abhi hua nahi / sirf plan hai — koi entry nahi "
                      f"(hataya: {[t.value for t in drop]})")
            d.selected_tools = keep
    result.action_decisions = kept
    return result



_HAS_AMOUNT = _re.compile(r"\d")


def _money_without_tool(result: ToolDecisionResult, group) -> list:
    """Action jisme amount hai, 'nahi hua/plan' nahi hai, phir bhi koi tool nahi chuna."""
    out = []
    for d in result.action_decisions:
        text = group.actions[d.action_index].text
        if not d.selected_tools and _HAS_AMOUNT.search(strip_non_money(text)) \
                and not _not_happened(text):
            out.append(d.action_index)
    return out


def resolve_available_tools(
    record_type: RecordType,
    person_role: PersonRole | None,
    transaction_type: TransactionType | None,
) -> list[ToolName]:
    """
    Decides which tools are relevant for this Action Group,
    based on which branch it came from.
    """
    if record_type == RecordType.NEED_PERSON:
        if person_role is None:
            raise ValueError("NEED_PERSON group has no resolved person_role.")
        bundle = NEED_PERSON_BUNDLE.get(person_role)
        if bundle is None:
            raise ValueError(f"No tool bundle configured for person role '{person_role}'.")
        return bundle

    if record_type == RecordType.MATERIAL_MOVEMENT:
        if transaction_type is None:
            raise ValueError("MATERIAL_MOVEMENT group has no resolved transaction_type.")
        bundle = MATERIAL_MOVEMENT_BUNDLE.get(transaction_type)
        if bundle is None:
            raise ValueError(f"No tool bundle configured for transaction type '{transaction_type}'.")
        return bundle

    if record_type == RecordType.STANDALONE_TRANSACTION:
        return STANDALONE_BUNDLE

    raise ValueError(f"Unknown record_type: {record_type}")

def build_prompt(available_tools: list[ToolName]) -> str:
    """
    Assembles the final prompt: global start + global rules +
    only the sub-prompts for the tools actually available to
    this group + global end. This keeps the prompt small and
    focused, instead of always including all 12 tools' rules.
    """
    sub_prompts = [TOOL_PROMPT_MAP[tool] for tool in available_tools if tool in TOOL_PROMPT_MAP]
    return GLOBAL_START + GLOBAL_RULES + "\n".join(sub_prompts) + GLOBAL_END

async def tool_decision_node(state):
    """
    Tool Decision Node
    ------------------
    1. Read Action Groups (already classified: record_type,
       and — depending on branch — person_role or transaction_type).
    2. Resolve the correct tool bundle for each group.
    3. Build a focused prompt using only that bundle's sub-prompts.
    4. Ask the LLM to select tool(s) per action.
    5. Return structured ToolDecisionResult(s).
    """

    grouped_intent = state.get("grouped_intent")
    resolved_roles = state.get("resolved_person_roles") or {}
    transaction_results = state.get("transaction_classifier_results") or {}

    structured_llm = llm.with_structured_output(ToolDecisionResult)
    results = []

    for group in grouped_intent.groups:
        if group.record_type == RecordType.CORRECTION:
            continue   # correction ke tools nahi hote, subgraph khud handle karega

        print(f"\n=== TOOL DECISION DEBUG for {group.group_id} ===")
        print(f"record_type: {group.record_type}")
        print(f"resolved_roles dict: {resolved_roles}")
        print(f"transaction_results dict: {transaction_results}")
        from grouping_node import unresolved_reference
        if unresolved_reference(group):
            print(f"🚫 TOOL DECISION: {group.group_id} ('{group.identity_key}') — paisa kisko gaya pata nahi, "
                  f"entry nahi banegi; user ko jawab mein bataya jayega")
            results.append(ToolDecisionResult(group_id=group.group_id, action_decisions=[
                ActionToolDecision(action_index=i, selected_tools=[]) for i in range(len(group.actions))]))
            continue
        _txn = transaction_results.get(group.group_id)
        if (group.record_type == RecordType.MATERIAL_MOVEMENT and _txn is not None
                and _txn.transaction_type == TransactionType.UNRESOLVED):
            # Maal kahan se kahan gaya pata nahi → andaze ki stock entry (adjustment) KABHI nahi.
            print(f"🚫 TOOL DECISION: {group.group_id} — maal kahan se/kahan gaya pata nahi (Unresolved), "
                  f"koi entry nahi; user ko jawab mein bataya jayega")
            results.append(ToolDecisionResult(group_id=group.group_id, action_decisions=[
                ActionToolDecision(action_index=i, selected_tools=[]) for i in range(len(group.actions))]))
            continue
        person_role = resolved_roles.get(group.group_id)
        txn_result = transaction_results.get(group.group_id)
        transaction_type = txn_result.transaction_type if txn_result else None
        print(f"resolved person_role: {person_role}")
        print(f"resolved transaction_type: {transaction_type}")
        print("===============================================")

        available_tools = resolve_available_tools(
            record_type=group.record_type,
            person_role=person_role,
            transaction_type=transaction_type,
        )

        if (group.record_type == RecordType.STANDALONE_TRANSACTION
                and ToolName.RECORD_FAMILY_TRANSACTION in available_tools
                and not family_context(" ".join(a.text for a in group.actions))):
            available_tools = [t for t in available_tools if t != ToolName.RECORD_FAMILY_TRANSACTION]
            print("🔒 TOOL DECISION: ghar/family ka koi shabd nahi — family tool hataya")

        prompt = build_prompt(available_tools)

        tool_input = ToolDecisionInput(
            group_id=group.group_id,
            actions=group.actions,
            person_role=person_role,
            transaction_type=transaction_type,
            record_type=group.record_type,
            available_tools=available_tools,
        )

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=tool_input.model_dump_json(indent=2)),
        ]

        result = await structured_llm.ainvoke(messages)
        if not isinstance(result, ToolDecisionResult):
            raise ValueError("Tool Decision LLM returned an invalid response.")
        result = _sanitize_decision(result, group, available_tools)

        # Amount wala action bina tool ke chhoot gaya ("शर्मा जी se 5000 आए" → []) — ek baar dobara poochho
        missed = _money_without_tool(result, group)
        if missed:
            print(f"⚠️ TOOL DECISION: {group.group_id} ke action {missed} mein amount hai par koi tool nahi — dobara pooch rahe hain")
            listed = "\n".join(f"- action {i}: {group.actions[i].text}" for i in missed)
            retry = await structured_llm.ainvoke(messages + [HumanMessage(content=(
                "Your previous answer selected NO tool for these actions, but each one contains an "
                "amount and describes something that already happened:\n" + listed +
                "\nSelect the correct tool(s) for them from available_tools (for example, money "
                "received from a customer → record_sale_payment). Return the full decision for "
                "every action again."))])
            if isinstance(retry, ToolDecisionResult):
                retry = _sanitize_decision(retry, group, available_tools)
                fixed = {d.action_index: d for d in retry.action_decisions if d.selected_tools}
                for d in result.action_decisions:
                    if d.action_index in missed and d.action_index in fixed:
                        d.selected_tools = fixed[d.action_index].selected_tools
                still = _money_without_tool(result, group)
                if still and person_role == PersonRole.SUPPLIER \
                        and ToolName.RECORD_SUPPLIER_PAYMENT in available_tools:
                    from sale_rules import has_goods
                    for d in result.action_decisions:
                        text = group.actions[d.action_index].text
                        if (d.action_index in still and not has_goods(text)
                                and _GIVE_MONEY.search(text) and not _BILL.search(text)):
                            print(f"🔀 TOOL DECISION: '{text}' — supplier ko sirf paisa diya, LLM ne tool nahi "
                                  f"chuna — record_supplier_payment")
                            d.selected_tools = [ToolName.RECORD_SUPPLIER_PAYMENT]
                        elif (d.action_index in still and _BILL.search(text)
                                and ToolName.RECORD_SUPPLIER_TRANSACTION in available_tools):
                            # "Krishna bhatte ka 14000 ka bill aaya" — supplier ka bill = uski maal/hisaab entry
                            print(f"🔀 TOOL DECISION: '{text}' — supplier ka bill, LLM ne tool nahi chuna "
                                  f"— record_supplier_transaction")
                            d.selected_tools = [ToolName.RECORD_SUPPLIER_TRANSACTION]
                    still = _money_without_tool(result, group)
                if still and person_role == PersonRole.PROPERTY_OWNER:
                    # "Saini ji ko 30000 bheje" — property wale ko paisa = purchase payment; "… 2 lakh mein li" = sauda
                    for d in result.action_decisions:
                        text = group.actions[d.action_index].text
                        if d.action_index not in still:
                            continue
                        if _GIVE_MONEY.search(text) and ToolName.RECORD_PURCHASE_PAYMENT in available_tools:
                            print(f"🔀 TOOL DECISION: '{text}' — property wale ko paisa diya, LLM ne tool nahi chuna "
                                  f"— record_purchase_payment")
                            d.selected_tools = [ToolName.RECORD_PURCHASE_PAYMENT]
                        elif _DEAL_DONE.search(text) and ToolName.RECORD_PURCHASE in available_tools:
                            print(f"🔀 TOOL DECISION: '{text}' — property ka sauda, LLM ne tool nahi chuna — record_purchase")
                            d.selected_tools = [ToolName.RECORD_PURCHASE]
                    still = _money_without_tool(result, group)
                if still:
                    print(f"⚠️ TOOL DECISION: action {still} ab bhi bina tool — user ko jawab mein bataya jayega")
        print(f"\n=== TOOL DECISION RESULT for {group.group_id} ===")
        for d in result.action_decisions:
            print(f"  action {d.action_index}: {[t.value for t in d.selected_tools]}")
        print("===============================================")
        results.append(result)

    return {"tool_decision_results": results}



