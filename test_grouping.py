import asyncio

from extract_node import extract_node
from grouping_node import grouping_node

test_cases = [

    # =====================================================
    # MULTI-STATEMENT TESTS
    # =====================================================

    """
    Ram ne 600 ka kaam kiya.
    Usko 300 rupaye diye.
    Uska hisab bata.

    SBI bhatte se 3000 eent aayi.
    Driver Kitanu tha.
    Hasi Gate par utari.

    Office ka kiraya diya.

    Sandeep ne aaj pura din kaam kiya.
    Sandeep ko 500 diye.

    Shyam se purana makan todne ki deal hui.
    5 lakh mein deal final hui.
    1 lakh advance diya.
    """,

    """
    Gupta bhatte se 2500 eent aayi.
    Driver Veer tha.
    Godown mein utari.

    Ram ne 500 ka kaam kiya.
    Ram ko 200 diye.

    Mohan ka hisab bata.

    Generator ki servicing karayi.

    Lala ji se 2 lakh ki deal hui.
    50000 advance diya.
    """,

    """
    Kitanu ne driving ki.
    700 ka kaam kiya.
    300 rupaye liye.

    SBI bhatte se 1800 eent aayi.
    Driver Sonu tha.
    Sector 12 mein utari.

    Office ka bijli bill diya.

    Sandeep ne aaj kaam kiya.
    Usko 400 diye.
    """
]


async def run_test(statement):

    extract_state = {
        "messages": [
            type(
                "msg",
                (),
                {
                    "content": statement
                }
            )
        ]
    }

    extract_result = await extract_node(extract_state)

    grouping_state = {
        "extracted_intent": extract_result["extracted_intent"]
    }

    grouping_result = await grouping_node(grouping_state)

    print("=" * 100)
    print("INPUT:")
    print(statement)

    print("\nEXTRACT OUTPUT:")
    print(extract_result["extracted_intent"])

    print("\nGROUPING OUTPUT:")
    print(grouping_result["grouped_intent"])

    print("=" * 100)
    print()


async def main():
    for statement in test_cases:
        await run_test(statement)


if __name__ == "__main__":
    asyncio.run(main())