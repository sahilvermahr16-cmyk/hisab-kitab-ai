from datetime import date, timedelta
from datetime import datetime
from schemas import DateResolutionResult
from state import ChatState
from llm_setup import llm
from schemas import DateResolutionResult, RecordType
from date_helpers import calendar_block, fix_dates

structured_llm = llm.with_structured_output(DateResolutionResult)

PROMPT="""
You are the Date Resolution Node of the Hisab-Kitab accounting system.
Your responsibility is to resolve the correct final date for every action inside the grouped accounting statements.

Today's date: {today}

INPUTS:
1. original_user_statement
   - The complete statement provided by the user.
   - Use it to understand date references, sentence structure, and context.
2. grouped_intent
   - The output of the Grouping Node.
   - It contains groups of related actions whose final dates must be resolved.

RESPONSIBILITY:

Your ONLY task is to resolve and update the `date` field of each existing
Action.

DO NOT:
- Do not change `action.text`.
- Do not add or remove actions.
- Do not add or remove groups.
- Do not merge or split groups.
- Do not change `group_id`.
- Do not change `need_person`.
- Do not modify any field other than `Action.date`.

The input grouped structure is already correct. Preserve its structure
exactly and modify ONLY the date of existing actions.

Use both `original_user_statement` and `grouped_intent` together to
determine the correct date. Do not assign a date only because it is the
nearest date mentioned in the statement. Consider the complete statement,
group relationships, action relationships, and date context.

RELATIVE DATE HANDLING:

Resolve relative date references using the provided `today` value:
- "aaj" / "today" → {today}
- "kal" / "yesterday" → one day before {today}
- "parso" / "day before yesterday" → two days before {today}

Do not assume or independently determine today's date.
Always use the provided `today` value.

WEEKDAY NAMES — USE THIS TABLE, DO NOT CALCULATE:
{calendar}
"Somvaar ko", "on Monday", "सोमवार को" → the Monday date from the table.
Never compute a weekday yourself — always read it from the table.

WHAT THE MONEY IS FOR ≠ WHEN IT HAPPENED (CRITICAL):
Phrases like "agle hafte ki mazdoori", "pichle hafte ka hisab",
"is mahine ki salary", "kal ki dihadi", "next week's wages",
"अगले हफ्ते की मज़दूरी" only say WHAT the money is for. They are NOT
the date. The date is when the money was actually given/received —
{today} unless another date is stated.
- "Vinod ko agle mahine ki tankhwah ke 4000 abhi de diye" → {today}
- "विनोद को पिछले हफ्ते की दिहाड़ी के 900 दिए" → {today}
- "Paid Vinod 900 for last week's wages" → {today}
But WITHOUT "ki/ka/ke" it IS a date:
- "Pichle hafte Vinod ko 900 diye" → the money was given last week.

If Extract Node has already resolved a date into YYYY-MM-DD, treat it as an extracted date reference and verify 
its scope using the original_user_statement and the rules below.
After resolving all dates, return the same grouped structure with a correct date assigned to every existing action.
All final dates must use YYYY-MM-DD format.

The following rules define how dates must be resolved:

DATE PARSING & INCOMPLETE DATES:

Users may mention dates in natural Hindi, Hinglish, English, or mixed
formats. Understand common variations and normalize them to YYYY-MM-DD.

Examples:
- "9 August 2026"
- "9 Aug 2026"
- "9/8/2026"
- "9-8-2026"
- "9 August"
- "August 9"
- "9 tareekh"
- "9 agast"
- "9 agast 2026"

Hindi number words may also be used for dates. Understand common Hindi
counting words such as:
- ek = 1
- do = 2
- teen = 3
- char = 4
- paanch = 5
- chhah = 6
- saat = 7
- aath = 8
- nau = 9
- das = 10
- gyarah = 11
- barah = 12
- terah = 13
- chaudah = 14
- pandrah = 15
- solah = 16
- satrah = 17
- atharah = 18
- unnis = 19
- bees = 20
- ikkis = 21
- baais = 22
- teis = 23
- chaubis = 24
- pachis = 25
- chhabis = 26
- sattais = 27
- athais = 28
- untees = 29
- tees = 30
- ikattis = 31

INCOMPLETE DATES:

If the user provides a day but omits the year or month, do not
automatically invent the missing component.

Use an omitted component only when it can be determined confidently
from the surrounding date context.

Examples:
- If today is 2026-08-27 and the user says "9 August",
  resolve it as 2026-08-09.
- If the statement already establishes the year as 2026 and the user
  later says "18 August", resolve it as 2026-08-18.
- If the statement establishes "August" as the current date context
  and the user says "18 tareekh", resolve it as 2026-08-18.

If a missing month or year cannot be determined confidently from the
statement or existing date context, do not guess it.

RULE 1 — IDENTIFY AND NORMALIZE EXPLICIT DATES

Identify every explicit date mentioned in the original_user_statement.
An explicit date means a date that is directly stated by the user, such as:
- 2026-08-09
- 09-08-2026
- 09/08/2026
- 9 August 2026
- 9 Aug 2026

Convert every identified explicit date into the standard internal format: YYYY-MM-DD

Examples:
"2026-08-09" → "2026-08-09"
"09/08/2026" → "2026-08-09"
"09-08-2026" → "2026-08-09"
"9 August 2026" → "2026-08-09"
"9 Aug 2026" → "2026-08-09"

Do not change the meaning of the date while normalizing it.
The normalized date must be assigned only after understanding its context and scope using the remaining date-resolution rules.
Do not assume that the nearest action to an explicit date automatically owns that date. The date may apply to a continuation, multiple actions, one group, multiple groups, or the overall statement depending on the context.

Example:
original_user_statement:
"2026-08-08 ko Sam ne 200 paise liye aur 300 ka kaam kiya, Ram ne 400 rupaye liya"

The explicit date is: "2026-08-08"
Normalize it as: "2026-08-08"

The exact scope of this date will be determined using the remaining date-resolution rules.

RULE 2 — SINGLE DATE AT THE BEGINNING OR END

DO NOT:
- Do not apply the single-date rule when the only date appears in the middle of the statement.
- Do not assume that one date anywhere in the statement automatically applies to all groups.

DO:
- If the complete statement contains only ONE date and that date is at the beginning or end of the overall statement, treat it as the overall statement date.
- Assign that date to all relevant actions across all relevant groups.

Example 1:
Input: "2026-08-08 ko Sam ne 200 paise liye aur 300 ka kam kiya, Ram ne 400 rupaye liya"

Groups:
G1:
- Sam ne 200 paise liye
- 300 ka kam kiya
G2:
- Ram ne 400 rupaye liya

Expected:
G1:
- 2026-08-08 → Sam ne 200 paise liye
- 2026-08-08 → 300 ka kam kiya
G2:
- 2026-08-08 → Ram ne 400 rupaye liya


Example 2:
Input: "Sam 500 rupaye le gaya aur 200 ka kam kiya, Ram 300 rupaye le gaya 2026-08-08 ko"

Expected:
G1:
- 2026-08-08 → Sam 500 rupaye le gaya
- 2026-08-08 → 200 ka kam kiya
G2:
- 2026-08-08 → Ram 300 rupaye le gaya

Counter-example:
Example (if today is 2026-08-27):
Input: "Ram 500 rupaye le gaya aur 200 ka kam kiya, 2026-08-07 ko Ram 300 rupaye le gaya tha"

Expected:
- 2026-08-27 → Ram 500 rupaye le gaya
- 2026-08-27 → 200 ka kam kiya
- 2026-08-07 → Ram 300 rupaye le gaya tha

NOTE:
Beginning/end + single date → overall statement date.
Middle + single date → resolve its local context using the other rules.

RULE 3 — MULTIPLE DATES AND CONTEXT RESOLUTION

DO NOT:
- Do not apply the same date to all groups when multiple date references represent different contexts.
- Do not assign a date simply because it is the nearest date to an action.
- Do not perform complex reasoning when the relationship is already clear from the statement.
- Do not change an explicitly stated date.

DO:
- When multiple dates are present, first identify the date context of each part of the statement.
- If an action is a clear continuation of a previous dated action, inherit that previous date without additional reasoning.
- If a new explicit date appears and clearly starts a new context, use that date for the following related actions.
- If different groups have clearly different date contexts, assign each group its relevant date.
- Use semantic reasoning only when it is unclear whether a date belongs to one action, a sequence of actions, or a group.
- Consider the original_user_statement together with grouped_intent when determining the scope of a date.

Example 1 — Clear separate contexts:
Input: "2026-08-09 ko Monu 200 rupaye le gaya aur 200 ka kam kiya 2026-08-18 ko Ram 200 rupaye le gaya aur 100 aur le gaya"

Expected:
G1 — Monu:
- 2026-08-09 → Monu 200 rupaye le gaya
- 2026-08-09 → 200 ka kam kiya
G2 — Ram:
- 2026-08-18 → Ram 200 rupaye le gaya
- 2026-08-18 → 100 aur le gaya

No complex reasoning is required because both date contexts are clear.

Example 2 — Date context changes within the same group:
Input: "2026-08-09 ko Monu 200 rupaye le gaya aur 200 ka kam kiya 2026-08-18 ko 300 rupaye le gaya aur 100 ka kam kiya"

Expected:
G1 — Monu:
- 2026-08-09 → 200 rupaye le gaya
- 2026-08-09 → 200 ka kam kiya
- 2026-08-18 → 300 rupaye le gaya
- 2026-08-18 → 100 ka kam kiya

The group is the same, but the date context changes when the new explicit date appears.

Example 3 — Different groups can have different dates:
Input: "2026-08-09 ko Monu 200 le gaya aur Ram 300 le gaya 2026-08-18 ko Monu 500 le gaya"

Expected:
G1 — Monu:
- 2026-08-09 → 200 le gaya
- 2026-08-18 → 500 le gaya
G2 — Ram:
- 2026-08-09 → 300 le gaya

Here, the first date applies to both groups because both actions are
part of the same dated context. The second date applies only to the
later Monu action.

NOTE:
Multiple dates → first identify each date's context.
Clear continuation → inherit directly.
Clear new date → switch context.
Ambiguous scope → use semantic reasoning with the original statement and groups.

RULE 4 — DATE-LESS CONTINUATION

If an action has no date reference and is clearly a continuation of the
current date context, inherit the previous relevant date.

If an action explicitly contains a relative date such as "aaj", "kal",
or "parso", use the date already resolved from the RELATIVE DATE HANDLING
section as the new date context.

Following date-less continuation actions should inherit this new date.

Example (if today is 2026-08-27):
Input: "2026-08-09 ko Monu 200 rupaye le gaya aur 200 ka kam kiya aur aaj 300 rupaye le gaya aur 100 ka kam kiya"

Expected:
- 2026-08-09 → 200 rupaye le gaya
- 2026-08-09 → 200 ka kam kiya
- 2026-08-27 → 300 rupaye le gaya
- 2026-08-27 → 100 ka kam kiya

NOTE:
A date-less action inherits the previous date only when it is clearly
a continuation of that context. Otherwise, apply Rule 5.

RULE 5 — NO DATE CONTEXT

If an action has no explicit date, no relative date, and no previous
relevant date context to inherit, assign `{today}`.

Example:
Input: "Monu 500 rupaye le gaya aur Ram ne 300 rupaye liye"

If today is 2026-08-27:
Expected:
G1 — Monu
- 2026-08-27 → 500 rupaye le gaya
G2 — Ram
- 2026-08-27 → 300 rupaye liye

NOTE:
No available date context → use today's date as the final fallback.

FINAL REQUIREMENTS:
- Preserve the complete grouped structure exactly as received.
- Preserve every `group_id` exactly.
- Preserve every `action.text` exactly.
- Preserve the number and order of groups and actions.
- Preserve `need_person` exactly.
- Modify ONLY `Action.date`.
- Every existing action must have one final date.
- All final dates must use YYYY-MM-DD format.
"""



def _validate_date(date_string: str) -> bool:
    """
    Validate that the date is strictly in YYYY-MM-DD format
    and represents a real calendar date.
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

async def date_resolution_node(state: ChatState):
    original_user_statement = state.get("original_user_statement")
    grouped_intent = state.get("grouped_intent")

    if not original_user_statement:
        raise ValueError("Date Resolution Node: original_user_statement is missing.")
    if grouped_intent is None:
        raise ValueError("Date Resolution Node: grouped_intent is missing.")

    # CORRECTION groups ki date yahan resolve nahi hoti. Extract ki auto-filled
    # "aaj" wali date galat signal degi, isliye khali chhodte hain. Correction
    # subgraph apna Date node chalakar user se date lega.
    for group in grouped_intent.groups:
        if group.record_type == RecordType.CORRECTION:
            for action in group.actions:
                action.date = ""

    dated_groups = [
        g for g in grouped_intent.groups
        if g.record_type != RecordType.CORRECTION
    ]

    if not dated_groups:
        print("\nDATE RESOLUTION NODE: only correction groups, skipping.")
        return {"grouped_intent": grouped_intent}

    correction_texts = [
        a.text
        for g in grouped_intent.groups
        if g.record_type == RecordType.CORRECTION
        for a in g.actions
    ]

    correction_block = ""
    if correction_texts:
        listed = "\n".join(f"- {t}" for t in correction_texts)
        correction_block = f"""
============================================================
EXCLUDED CORRECTION CLAUSES (IGNORE COMPLETELY)
============================================================

The original statement also contains these correction clauses:
{listed}

They are NOT part of the grouped intent below. Any date mentioned
inside them belongs ONLY to them. NEVER apply such a date to any
action below, and do not treat it as the "single date at beginning
or end" of the statement (Rule 2).
"""

    today = date.today()
    prompt = PROMPT.format(
        today=today.isoformat(),
        yesterday=(today - timedelta(days=1)).isoformat(),
        parso=(today - timedelta(days=2)).isoformat(),
        year=today.year,
        calendar=calendar_block(today),
    )

    # LLM ko sirf non-correction groups dikhao
    llm_view = grouped_intent.model_copy(update={"groups": dated_groups})
    grouped_intent_json = llm_view.model_dump_json(indent=2)

    result: DateResolutionResult = await structured_llm.ainvoke(
        f"""
{prompt}

============================================================
ORIGINAL USER STATEMENT
============================================================

{original_user_statement}
{correction_block}
============================================================
GROUPED INTENT
============================================================

{grouped_intent_json}

============================================================
IMPORTANT OUTPUT INSTRUCTION
============================================================

Return ONLY the date resolution mapping.

For every existing action, provide:
- its existing group_id
- its zero-based action_index
- its final resolved date

Do not return action text.
Do not create new actions.
Do not remove actions.
Do not create new groups.
"""
    )

    expected_actions = {g.group_id: len(g.actions) for g in dated_groups}
    resolved_dates = result.resolved_dates

    if len(resolved_dates) != sum(expected_actions.values()):
        raise ValueError(
            "Date Resolution Node: LLM did not return exactly one date for "
            f"every action. Expected {sum(expected_actions.values())}, "
            f"got {len(resolved_dates)}."
        )

    seen = set()
    for resolved in resolved_dates:
        gid, idx = resolved.group_id, resolved.action_index
        if gid not in expected_actions:
            raise ValueError(f"Date Resolution Node: Unknown group_id '{gid}' returned by LLM.")
        if not (0 <= idx < expected_actions[gid]):
            raise ValueError(f"Date Resolution Node: Invalid action_index {idx} for group '{gid}'.")
        if (gid, idx) in seen:
            raise ValueError(f"Date Resolution Node: Duplicate date mapping for group '{gid}', action {idx}.")
        seen.add((gid, idx))
        if not _validate_date(resolved.date):
            raise ValueError(
                f"Date Resolution Node: Invalid date '{resolved.date}' for "
                f"group '{gid}', action {idx}. Expected YYYY-MM-DD."
            )

    for g in dated_groups:
        for idx in range(len(g.actions)):
            if (g.group_id, idx) not in seen:
                raise ValueError(
                    f"Date Resolution Node: Missing date mapping for "
                    f"group '{g.group_id}', action {idx}."
                )

    date_map = {(r.group_id, r.action_index): r.date for r in resolved_dates}
    for g in dated_groups:
        for idx, action in enumerate(g.actions):
            action.date = date_map[(g.group_id, idx)]   # ONLY this field changes

    # Pakki jaanch: vaar ka naam / "agle hafte KI mazdoori" (code se, LLM ke hisab pe nahi)
    for change in fix_dates(original_user_statement, dated_groups, today):
        print(f"📅 DATE: {change}")

    print("\n" + "=" * 60)
    print("DATE RESOLUTION NODE")
    print("=" * 60)
    print("\nOriginal Statement:")
    print(original_user_statement)
    print("\nResolved Dates:")
    for g in grouped_intent.groups:
        print(f"\nGroup: {g.group_id}")
        for idx, action in enumerate(g.actions):
            shown = action.date or "(correction: date asked later)"
            print(f"{idx}. {action.text} → {shown}")
    print("\n" + "=" * 60)

    return {"grouped_intent": grouped_intent}







