# ==========================================================
# TEST CASES - BLOCK 1 (TC-01 to TC-15)
# ==========================================================

TEST_CASES = [

    ("TC-01 Employee Work",
     "Ram ne 500 rupaye ka kaam kiya.",
     [True]),

    ("TC-02 Employee Payment",
     "Ram ko 300 rupaye diye.",
     [True]),

    ("TC-03 Employee Attendance",
     "Ram aaj kaam par aaya.",
     [True]),

    ("TC-04 Employee Account",
     "Ram ka hisab bata.",
     [True]),

    ("TC-05 Employee Advance",
     "Mohan ko advance diya.",
     [True]),

    ("TC-06 Employee Overtime",
     "Amit ko overtime ka paisa do.",
     [True]),

    ("TC-07 Customer Sale",
     "Sharma ji ko 1000 eent di.",
     [True]),

    ("TC-08 Customer Payment",
     "Verma ji se payment receive hui.",
     [True]),

    ("TC-09 Customer Account",
     "Anil ka hisab dikhao.",
     [True]),

    ("TC-10 Supplier Purchase",
     "Gupta bhatte se 5000 eent mangwayi.",
     [True]),

    ("TC-11 Supplier Payment",
     "Supplier Mohan ko payment kiya.",
     [True]),

    ("TC-12 Supplier Account",
     "Gupta Traders ka hisab bata.",
     [True]),

    ("TC-13 Purchase Deal",
     "Lala ji se cement ki deal hui.",
     [True]),

    ("TC-14 Rate Final",
     "Gupta ji se rate fix hua.",
     [True]),

    ("TC-15 Office Rent",
     "Office ka kiraya diya.",
     [False]),

]

# ==========================================================
# TEST CASES - BLOCK 2 (TC-16 to TC-30)
# ==========================================================

TEST_CASES += [

    ("TC-16 Electricity",
     "Bijli ka bill bhar diya.",
     [False]),

    ("TC-17 Water Bill",
     "Pani ka bill diya.",
     [False]),

    ("TC-18 Internet",
     "Internet recharge karwaya.",
     [False]),

    ("TC-19 Stationery",
     "Stationery kharidi.",
     [False]),

    ("TC-20 Generator",
     "Generator ki servicing karayi.",
     [False]),

    ("TC-21 Tractor",
     "Tractor ki servicing karayi.",
     [False]),

    ("TC-22 AC Repair",
     "Office ka AC theek karwaya.",
     [False]),

    ("TC-23 Diesel",
     "Diesel bharwaya.",
     [False]),

    ("TC-24 Petrol",
     "Petrol bharwaya.",
     [False]),

    ("TC-25 Tea Expense",
     "Chai pani ka kharcha hua.",
     [False]),

    ("TC-26 Stock Damage",
     "Gudam me 200 eent toot gayi.",
     [False]),

    ("TC-27 Cement Damage",
     "50 cement ki bori kharab ho gayi.",
     [False]),

    ("TC-28 Inventory",
     "Inventory count complete hua.",
     [False]),

    ("TC-29 Employee Full Record",
     "Ram ne 500 rupaye ka kaam kiya. Ram ko 300 rupaye diye. Ram ka hisab bata.",
     [True]),

    ("TC-30 Employee + Office Expense",
     "Ram ne 500 rupaye ka kaam kiya. Office ka kiraya diya.",
     [True, False]),

]

# ==========================================================
# TEST CASES - BLOCK 3 (TC-31 to TC-45)
# ==========================================================

TEST_CASES += [

    ("TC-31 Customer + Electricity",
     "Sharma ji ko 1000 eent di. Bijli ka bill bhar diya.",
     [True, False]),

    ("TC-32 Supplier Delivery",
     "Gupta bhatte se 3000 eent aayi. Driver Kitanu tha. Gudam me utari.",
     [True]),

    ("TC-33 Purchase Deal",
     "Lela Ram se ghar todne ki deal hui. 3 lakh me. 1 lakh advance diya.",
     [True]),

    ("TC-34 Two Purchase Deals",
     "Lela Ram se deal hui 3 lakh me. Mohan se dusri deal hui 5 lakh me.",
     [True, True]),

    ("TC-35 Expense Batch",
     "Office ka kiraya diya. Bijli ka bill diya. Internet recharge karwaya.",
     [False, False, False]),

    ("TC-36 Employee + Customer",
     "Ram ne 500 ka kaam kiya. Sharma ji ko 2000 eent di.",
     [True, True]),

    ("TC-37 Stock + Employee",
     "Gudam me 200 eent toot gayi. Ram ne 500 rupaye ka kaam kiya.",
     [False, True]),

    ("TC-38 Mixed Conversation",
     "Ram ne 500 rupaye ka kaam kiya. Office ka kiraya diya. Sharma ji ko 1000 eent di. Diesel bharwaya.",
     [True, False, True, False]),

    ("TC-39 Two Employees",
     "Ram ne 500 ka kaam kiya. Mohan ne 700 ka kaam kiya.",
     [True, True]),

    ("TC-40 Employee + Supplier",
     "Ram ne diwar todi. Gupta bhatte se 2000 eent aayi.",
     [True, True]),

    ("TC-41 Expense + Payment",
     "Office ka kiraya diya. Ram ko 500 diye.",
     [False, True]),

    ("TC-42 Stock + Delivery",
     "Gudam me 200 eent toot gayi. Gupta se 1500 eent aayi.",
     [False, True]),

    ("TC-43 Delivery + Employee",
     "Gupta se 2500 eent aayi. Driver Kitanu tha. Ram ne 500 ka kaam kiya.",
     [True, True]),

    ("TC-44 Two Deliveries",
     "Gupta se 3000 eent aayi. SBI se 2500 eent aayi.",
     [True, True]),

    ("TC-45 Long Mixed",
     "Ram ne 500 ka kaam kiya. Office ka kiraya diya. Gupta se 3000 eent aayi. Driver Kitanu tha. Gudam me utari. Ram ko 300 diye.",
     [True, False, True, True]),

]

# ==========================================================
# EDGE CASES (TC-46 to TC-55)
# ==========================================================

TEST_CASES += [

    ("TC-46 Subject Inheritance",
     "Ram ne diwar todi. 500 rupaye ka kaam kiya.",
     [True]),

    ("TC-47 Delivery Continuation",
     "Gupta bhatte se 3000 eent aayi. Driver Kitanu tha. Gudam me utari. 300 rupaye bhada laga.",
     [True]),

    ("TC-48 Deal Continuation",
     "Ram ka ghar todne ki 3 lakh me baat hui. 1 lakh advance diya. Kam Monday se shuru hoga.",
     [True]),

    ("TC-49 Two Independent Deliveries",
     "Gupta se 3000 eent aayi. SBI se 2500 eent aayi. Driver Veer tha.",
     [True, True]),

    ("TC-50 Mixed Events",
     "Ram ne diwar todi. Sharma ji ko 1000 eent di. Office ka kiraya diya.",
     [True, True, False]),

    ("TC-51 Only Driver Info",
     "Driver Kitanu tha. Gudam me utari.",
     [True]),

    ("TC-52 Reverse Delivery",
     "Gudam me utari. Driver Kitanu tha. Gupta se 3000 eent aayi.",
     [True]),

    ("TC-53 Reverse Deal",
     "1 lakh advance diya. Ram ka ghar todne ki baat hui. Total 3 lakh.",
     [True]),

    ("TC-54 Long Employee Record",
     "Ram aaya. Ram ne diwar todi. Ram ko 500 diye. Ram ka hisab bata.",
     [True]),

    ("TC-55 Production Mixed",
     "Office ka kiraya diya. Gupta se 3000 eent aayi. Driver Kitanu tha. Gudam me utari. Ram ne 500 ka kaam kiya. Ram ko 300 diye.",
     [False, True, True]),

]