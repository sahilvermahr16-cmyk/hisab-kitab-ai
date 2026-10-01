import asyncio
from langchain_core.messages import HumanMessage
from extract_node import extract_node
from grouping_node import grouping_node
from need_person_node import need_person_node
from person_role_classification_node import person_role_classification_node

TEST_CASES = [
    # =====================================================
    # EMPLOYEE
    # =====================================================
    # "Ram ne 500 rupaye ka kaam kiya.",
    # "Mohan ne diwar todi.",
    # "Satpal ne driving ki.",
    # "Kitanu ne eent bhari or 200 rupe diye",
    # "Ram ko salary di.",
    # =====================================================
    # CUSTOMER
    # =====================================================
    # "Ram ne 500 eent kharidi.",
    # "Ram ne order diya.",
    # "Ram ko maal diya.",
    # "Ram ko saman becha.",
    # "Ram ne cement kharida.",
    # =====================================================
    # SUPPLIER
    # =====================================================
    # "Gupta se 500 eent li.",
    # "Ram ne cement supply ki.",
    # "Ram se maal liya.",
    # "Ram ne material bheja.",
    # "Ram se product kharida.",
    # =====================================================
    # PROPERTY OWNER
    # =====================================================
    # "Ramfal ji se ghar todne ki deal final hui.",
    # "Ram ki building todne ka contract mila.",
    # "Ram ki site Hansi Gate par hai.",
    # "Ramfal ji ka hisab pura ho gaya. Site Dinod Gate.",
    # "Ram ke plot par kaam kiya.",
    # =====================================================
    # FAMILY MEMBER
    # =====================================================
    # "Meri wife ko 5000 diye.",
    # "Bete ko pocket money di.",
    # "Beti ne paise liye.",
    # "Meri patni ko ghar kharch diya.",
    # "Mere husband ko paise diye.",
    # =====================================================
    # AMBIGUOUS
    # =====================================================
    "Ram ko 500 diye.",
    "Ram ka hisab bata.",
    "Ram ko advance diya.",
    "Ram ko payment ki.",
    "Ram se paise liye.",
]

async def run_test(statement):
    state = {
        "messages": [
            HumanMessage(content=statement)
        ]
    }
    extract_result = await extract_node(state)
    state.update(extract_result)
    grouping_result = await grouping_node(state)
    state.update(grouping_result)
    need_person_result = await need_person_node(state)
    state.update(need_person_result)
    person_result = await person_role_classification_node(state)
    state.update(person_result)
    print("\n" + "=" * 100)
    print("STATEMENT")
    print("-" * 100)
    print(statement)
    print("\nEXTRACT")
    print("-" * 100)
    print(state["extracted_intent"].model_dump_json(indent=2))
    print("\nGROUPING")
    print("-" * 100)
    print(state["grouped_intent"].model_dump_json(indent=2))
    print("\nPERSON ROLE CLASSIFICATION")
    print("-" * 100)
    rankings = state.get("person_role_rankings", [])
    if not rankings:
        print("No person classification required.")
    else:
        for result in rankings:
            print(f"\nGroup ID         : {result.group_id}")
            print(f"Person           : {result.person}")
            print(f"Confidence Level : {result.confidence_level.value}")
            print("\nRanking")
            print("-" * 40)
            for role in result.ranking:
                print(f"{role.role.value:<25} : {role.confidence:.2f}")
    print("=" * 100)

async def main():
    for statement in TEST_CASES:
        try:
            await run_test(statement)
        except Exception as e:
            print("\n" + "=" * 100)
            print("STATEMENT")
            print("-" * 100)
            print(statement)
            print("\nERROR")
            print("-" * 100)
            print(e)

if __name__ == "__main__":
    asyncio.run(main())