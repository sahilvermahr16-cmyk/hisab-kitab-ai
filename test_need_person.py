import asyncio

from langchain_core.messages import HumanMessage

from extract_node import extract_node
from grouping_node import grouping_node
from need_person_node import need_person_node


# ==========================================================
# GROUPING TEST CASES
# ==========================================================

TEST_CASES = [

    # -------------------------------------------------
    # One Person - One Action
    # -------------------------------------------------

    ("TC-G01",
     "Ram ne 500 rupaye ka kaam kiya."),

    ("TC-G02",
     "Ram ko 300 rupaye diye."),

    ("TC-G03",
     "Ram ka hisab bata."),

    # -------------------------------------------------
    # Same Person - Multiple Actions
    # -------------------------------------------------

    ("TC-G04",
     "Ram ne 500 rupaye ka kaam kiya or 300 rupaye diye."),

    ("TC-G05",
     "Ram ne diwar todi or 500 diye. Ram ka hisab bata."),

    # -------------------------------------------------
    # Two Employees
    # -------------------------------------------------

    ("TC-G06",
     "Ram ne 500 ka kaam kiya. Mohan ne 700 ka kaam kiya."),

    ("TC-G07",
     "Ram ko 500 diye. Mohan ko 700 diye."),

    # -------------------------------------------------
    # Employee + Expense
    # -------------------------------------------------

    ("TC-G08",
     "Ram ne 500 ka kaam kiya. Office ka kiraya diya."),

    # -------------------------------------------------
    # Employee + Customer
    # -------------------------------------------------

    ("TC-G09",
     "Ram ne diwar todi. Sharma ji ko 1000 eent di."),

    # -------------------------------------------------
    # Mixed Business Conversation
    # -------------------------------------------------

    ("TC-G10",
     "Ram ne 500 ka kaam kiya. Office ka kiraya diya. Sharma ji ko 1000 eent di."),

]


# ==========================================================
# RUN TEST
# ==========================================================

async def run_test(name, statement):

    state = {
        "messages": [
            HumanMessage(content=statement)
        ]
    }

    # ---------------- Extract ----------------

    extract_result = await extract_node(state)
    state.update(extract_result)

    # ---------------- Grouping ----------------

    grouping_result = await grouping_node(state)
    state.update(grouping_result)

    # ---------------- Need Person ----------------

    need_person_result = await need_person_node(state)
    state.update(need_person_result)

    # ==================================================
    # PRINT
    # ==================================================


    for i, action in enumerate(state["extracted_intent"].actions, start=1):
        print(f"{i}. {action.text}")

    groups = state["grouped_intent"].groups

    for i, group in enumerate(groups, start=1):

        print(f"\nG{i}")

        for action in group.actions:
            print(f"   • {action.text}")

        print(f"\nNeed Person : {group.need_person}")

    print("\n" + "=" * 100)


# ==========================================================
# MAIN
# ==========================================================

async def main():

    for tc in TEST_CASES:

        try:

            await run_test(*tc)

        except Exception as e:

            print("\n")
            print("=" * 100)
            print(tc[0])
            print("=" * 100)

            print(f"Statement : {tc[1]}")
            print(f"\nERROR : {e}")


# ==========================================================
# ENTRY
# ==========================================================

if __name__ == "__main__":
    asyncio.run(main())