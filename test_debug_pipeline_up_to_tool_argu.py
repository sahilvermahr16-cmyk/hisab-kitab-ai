import asyncio
import time
from copy import deepcopy
from pprint import pprint

from langchain_core.messages import HumanMessage

from state import ChatState

from extract_node import extract_node
from grouping_node import grouping_node
from need_person_node import need_person_node
from person_role_classification_node import person_role_classification_node
from person_role_hitl_node import person_role_hitl_node
from tool_decision_node import tool_decision_node
from tool_argument_extraction_node import tool_argument_extraction_node


LINE = "=" * 90
SUBLINE = "-" * 90


def header(title):
    print("\n")
    print(LINE)
    print(title)
    print(LINE)


def section(title):
    print("\n" + title)
    print(SUBLINE)


def print_state(state):
    pprint(state, sort_dicts=False)


async def execute_node(title, node, state):

    header(title)

    before_state = deepcopy(state)

    section("INPUT STATE")
    print_state(before_state)

    start = time.perf_counter()

    try:

        result = await node(state)

    except Exception as e:

        section("ERROR")
        print(type(e).__name__)
        print(e)

        section("STATE BEFORE FAILURE")
        print_state(state)

        raise

    end = time.perf_counter()

    section("NODE OUTPUT")
    pprint(result, sort_dicts=False)

    state.update(result)

    section("ADDED / UPDATED KEYS")

    before_keys = set(before_state.keys())
    after_keys = set(state.keys())

    added = sorted(after_keys - before_keys)

    updated = []

    for key in before_keys & after_keys:
        if before_state[key] != state[key]:
            updated.append(key)

    if added:
        print("\nAdded Keys")
        for key in added:
            print(f"  + {key}")

    if updated:
        print("\nUpdated Keys")
        for key in updated:
            print(f"  * {key}")

    if not added and not updated:
        print("No changes")

    section("UPDATED STATE")
    print_state(state)

    section("EXECUTION TIME")
    print(f"{end-start:.3f} sec")

    return state


async def main():

    statement = input("\nEnter Statement : ").strip()

    state = ChatState(
        messages=[
            HumanMessage(content=statement)
        ]
    )

    pipeline = [

        (
            "1. EXTRACTION NODE",
            extract_node,
        ),

        (
            "2. GROUPING NODE",
            grouping_node,
        ),

        (
            "3. NEED PERSON NODE",
            need_person_node,
        ),

        (
            "4. PERSON ROLE CLASSIFICATION NODE",
            person_role_classification_node,
        ),

        (
            "5. PERSON ROLE HITL NODE",
            person_role_hitl_node,
        ),

        (
            "6. TOOL DECISION NODE",
            tool_decision_node,
        ),

        (
            "7. TOOL ARGUMENT EXTRACTION NODE",
            tool_argument_extraction_node,
        ),

    ]

    total_start = time.perf_counter()

    try:

        for title, node in pipeline:

            await execute_node(
                title,
                node,
                state,
            )

    except Exception:

        print("\n")
        print(LINE)
        print("PIPELINE FAILED")
        print(LINE)
        return

    total_end = time.perf_counter()

    print("\n")
    print(LINE)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(LINE)

    print(f"\nTotal Execution Time : {total_end-total_start:.3f} sec")

    print("\nFinal State")
    print(SUBLINE)

    pprint(state, sort_dicts=False)


if __name__ == "__main__":
    asyncio.run(main())