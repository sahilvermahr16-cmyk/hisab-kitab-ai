import asyncio
from extract_node import extract_node
from graph import llm_with_tools

state = {
    "messages": [
        type(
            "msg",
            (),
            {
                "content":
                "Kitanu ko 500 diye, Kitanu ka hisab bata"
            }
        )()
    ]
}

result = asyncio.run(
    extract_node(state)
)

for action in result["extracted_intent"].actions:

    print("\nACTION:", action.text)

    response = llm_with_tools.invoke(
        action.text
    )

    print(response.tool_calls)