from langchain_core.messages import SystemMessage, HumanMessage

from llm_setup import llm
from schemas import NeedPerson

# ==========================================================
# Structured Output
# ==========================================================

structured_llm = llm.with_structured_output(NeedPerson)

# ==========================================================
# Prompt
# ==========================================================

NEED_PERSON_PROMPT = """
You are a Need Person Classification Engine.

You will receive ONE finalized Action Group.

The actions are already extracted and grouped.

Your ONLY responsibility is to determine whether executing this Action Group requires identifying a specific person from the business database.

═══════════════════════════════
ROLE
═══════════════════════════════

Return:

need_person = true

if execution requires identifying a person.

Return:

need_person = false

if execution does NOT require identifying any person.

═══════════════════════════════
IMPORTANT
═══════════════════════════════

Do NOT:

• Identify the person.
• Classify the person.
• Search the database.
• Guess missing information.
• Modify actions.
• Merge actions.
• Split actions.
• Decide operations.
• Decide tool execution.
• Explain your reasoning.

Only answer one question:

Does this Action Group require identifying a person?

═══════════════════════════════
RETURN TRUE
═══════════════════════════════

Return TRUE if execution depends on identifying a specific person.

Examples:

• Employee work
• Employee attendance
• Employee payment
• Employee account
• Customer transaction
• Supplier transaction
• Purchase / seller
• Driver when the driver represents a business person

═══════════════════════════════
RETURN FALSE
═══════════════════════════════

Return FALSE if execution does not require identifying any person.

Examples:

• Office rent
• Electricity bill
• Generator servicing
• Fuel expense
• Office expense
• Equipment maintenance
• Miscellaneous expense
• Stock adjustment without any person

═══════════════════════════════
OUTPUT
═══════════════════════════════

Return ONLY a valid NeedPerson object.
"""

# ==========================================================
# Node
# ==========================================================

async def need_person_node(state):

    grouped_intent = state["grouped_intent"]

    print("\n" + "=" * 60)
    print("NEED PERSON NODE")
    print("=" * 60)

    for group in grouped_intent.groups:

        actions_text = "\n".join(
            f"- {action.text}"
            for action in group.actions
        )

        print(f"\nProcessing {group.group_id}")
        print(actions_text)

        result = structured_llm.invoke(
            [
                SystemMessage(content=NEED_PERSON_PROMPT),
                HumanMessage(
                    content=f"""
Action Group

{actions_text}
"""
                ),
            ]
        )

        group.need_person = result.need_person

        print(f"Need Person : {result.need_person}")

    return {
        "grouped_intent": grouped_intent
    }