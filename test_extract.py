import asyncio

from extract_node import extract_node

state = {
    "messages": [
        type(
            "msg",
            (),
            {
                "content":
                "Kitanu ne ek chakr eent utara, 500 ki dadhi bani."
            }
        )
    ]
}

result = asyncio.run(
    extract_node(state)
)

print(result["extracted_intent"])

# import asyncio
# from extract_node import extract_node

# test_cases = [

#     # =====================================================
#     # CATEGORY 1 : NO PERSON
#     # =====================================================

#     "3 labour lagi thi.",
#     "Hasi Gate par 2500 eent utari.",

#     # =====================================================
#     # CATEGORY 2 : ONE PERSON + ONE ACTION
#     # =====================================================

#     "Ram ko 500 diye.",
#     "Sandeep ne 700 ka kaam kiya.",

#     # =====================================================
#     # CATEGORY 3 : ONE PERSON + MULTIPLE ACTIONS
#     # =====================================================

#     "Ram ne 400 ka kaam kiya, 200 rupaye le gaya aur aaj pura din aaya.",

#     "Kitanu ne ek chakr eent utara, 500 ki dadhi bani aur uska hisab bata.",

#     # =====================================================
#     # CATEGORY 4 : MULTIPLE PERSONS + INDEPENDENT ACTIONS
#     # =====================================================

#     "Ram ko 400 diye aur Sandeep ne 500 ka kaam kiya.",

#     "Mohan ko 300 diye aur Ram ka hisab bata.",

#     # =====================================================
#     # CATEGORY 5 : MULTIPLE PERSONS + ONE SHARED BUSINESS EVENT
#     # (Should remain ONE action)
#     # =====================================================

#     "SBI bhatte se 2500 eent aayi, Kitanu driver tha, Hasi Gate par 18000 mein utari.",

#     "Gupta bhatte se 1500 eent aayi gudam mein, Veer driver tha 7200 mein.",

#     # =====================================================
#     # CATEGORY 6 : PROPERTY / DEAL
#     # =====================================================

#     "Aaj Ram ji se deal hui purana ghar todne ki 2 lakh mein, 1 lakh advance diye aur 2 din baad kaam start hoga.",

#     "Lela Ram se deal hui 3 lakh mein, 50 hazar advance diye.",

#     # =====================================================
#     # CATEGORY 7 : ACCOUNT QUERY
#     # =====================================================

#     "Ram ka hisab bata.",

#     "Kitanu ka poora hisab bata.",

#     # =====================================================
#     # CATEGORY 8 : PRONOUN RESOLUTION
#     # =====================================================

#     "Ram ne 500 ka kaam kiya. Usko 200 diye. Uska hisab bata.",

#     "Kitanu ne driving ki aur 400 ka kaam kiya, fir 500 rupaye liye.",

# ]

# async def run_test(statement):
#     state = {
#         "messages": [
#             type(
#                 "msg",
#                 (),
#                 {
#                     "content": statement
#                 }
#             )
#         ]
#     }

#     result = await extract_node(state)

#     print("=" * 100)
#     print("INPUT :")
#     print(statement)

#     print("\nOUTPUT :")
#     print(result["extracted_intent"])
#     print("=" * 100)
#     print()


# async def main():
#     for statement in test_cases:
#         await run_test(statement)


# if __name__ == "__main__":
#     asyncio.run(main())