import asyncio
from langchain_core.messages import HumanMessage
from accounting_subgraph import accounting_subgraph

graph = accounting_subgraph.compile()

async def main():

    state = {
        "messages": [
            HumanMessage(
                content="Ram ko salary di."
            )
        ]
    }

    result = await graph.ainvoke(state)

    print("\n")
    print("=" * 80)
    print("FINAL STATE")
    print("=" * 80)

    for key, value in result.items():
        print(f"\n{key}")
        print(value)

if __name__ == "__main__":
    asyncio.run(main())