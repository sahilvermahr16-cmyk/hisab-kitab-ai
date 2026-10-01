from langchain_core.messages import HumanMessage

from state import ChatState

from extract_node import extract_node
from grouping_node import grouping_node
from need_person_node import need_person_node
from person_role_classification_node import (
    person_role_classification_node,
)
from person_role_hitl_node import person_role_hitl_node
from tool_decision_node import tool_decision_node


TEST_QUERY = "Ram ko 500 diye"


async def main():
    state = ChatState(
        messages=[
            HumanMessage(content=TEST_QUERY)
        ]
    )
    state.update(await extract_node(state))
    state.update(await grouping_node(state))
    state.update(await need_person_node(state))
    state.update(await person_role_classification_node(state))
    state.update(await person_role_hitl_node(state))
    state.update(await tool_decision_node(state))
    print("\n")
    print("=" * 80)
    print("FINAL TOOL DECISION")
    print("=" * 80)
    for result in state["tool_decision_results"]:
        print(f"\nGroup : {result.group_id}")
        print("Selected Tools")
        for tool in result.selected_tools:
            print(f"- {tool.value}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())