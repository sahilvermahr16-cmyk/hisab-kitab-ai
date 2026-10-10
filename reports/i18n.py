# reports/i18n.py
"""
Report ki teen bhashayein:  "hi" (हिंदी) | "hg" (Hinglish) | "en" (English)

1. LABELS      — report ke saare fixed shabd (column, heading, notes). Har key = (hi, hg, en).
2. FIXED_VALUES — DB mein baar-baar aane wale chhote shabd (unit, mode, role, category...)
                  bina LLM ke translate.
3. translate_values() — baaki free-text (item, note, naam, jagah) ek LLM call mein,
                  translation_cache table mein save — agli baar LLM nahi lagta.
                  Hinglish report ko translation ki zaroorat hi nahi (data Hinglish mein hai).
"""
LANGS = ("hi", "hg", "en")

LABELS = {
    # ---------------- common
    "period": ("अवधि", "Period", "Period"),
    "period_fmt": ("{a} से {b}", "{a} se {b}", "{a} to {b}"),
    "page": ("पृष्ठ", "Page", "Page"),
    "footer": ("हिसाब-किताब", "Hisab-Kitab", "Hisab-Kitab"),
    "generated": ("बनाया", "Bani", "Generated"),
    "no": ("क्र.", "#", "#"),
    "date": ("तारीख", "Date", "Date"),
    "total": ("कुल", "TOTAL", "TOTAL"),
    "note": ("टिप्पणी", "Note", "Note"),
    "amount": ("रकम", "Amount", "Amount"),
    "phone": ("फ़ोन", "Phone", "Phone"),
    "address": ("पता", "Address", "Address"),
    "type": ("किस्म", "Type", "Type"),
    "mode": ("तरीका", "Mode", "Mode"),
    "provider": ("ऐप", "App", "Provider"),
    "item": ("माल", "Item", "Item"),
    "qty": ("मात्रा", "Qty", "Qty"),
    "unit": ("इकाई", "Unit", "Unit"),
    "rate": ("भाव", "Rate", "Rate"),
    "bill": ("बिल नं.", "Bill No.", "Bill No."),
    "against_bill": ("किस बिल का", "Kis Bill ka", "Against Bill"),
    "driver": ("ड्राइवर", "Driver", "Driver"),
    "dest": ("कहाँ पहुँचा", "Kahan Pahuncha", "Destination"),
    "src": ("कहाँ से", "Kahan Se", "From"),
    "to": ("कहाँ गया", "Kahan Gaya", "To"),
    "vch": ("वाउचर", "Vch No.", "Vch No."),
    "balance": ("बाकी", "Balance", "Balance"),
    "open_bal": ("पिछला बाकी", "Pichla Baaki", "Opening Balance"),
    "close_bal": ("आख़िरी बाकी", "Closing Baaki", "Closing Balance"),
    "lena": ("लेना", "Lena", "Dr"),
    "dena": ("देना", "Dena", "Cr"),
    "nil": ("कुछ नहीं", "Nil", "Nil"),
    "party": ("पार्टी", "Party", "Party"),
    "group": ("समूह", "Group", "Group"),
    "particulars": ("विवरण", "Particulars", "Particulars"),
    "desc": ("विवरण", "Description", "Description"),
    "location": ("जगह", "Location", "Location"),
    "category": ("मद", "Category", "Category"),
    "share": ("हिस्सा", "Share", "Share"),
    "month": ("महीना", "Mahina", "Month"),
    "partial": ("(अधूरा)", "(adhoora)", "(partial)"),
    "index": ("इस रिपोर्ट में", "Is report mein", "Contents"),
    "empty_last_month": ("इस आख़िरी महीने में कोई एंट्री नहीं है।", "Is aakhri mahine mein koi entry nahi hai.",
                         "No entries in this last month."),
    "no_entries": ("इस अवधि में कोई एंट्री नहीं।", "Is period mein koi entry nahi.", "No entries in this period."),
    "amount_missing": ("(रकम नहीं लिखी)", "(amount nahi likha)", "(amount not recorded)"),

    # ---------------- overall
    "overall": ("पूरे कारोबार की रिपोर्ट", "Poore Business ki Report", "Overall Business Report"),
    "overall_order": ("क्रम: सप्लायर → कर्मचारी → खरीद → खर्च → ग्राहक बिक्री → परिवार का खर्च → कुल हिसाब",
                      "Order: Supplier → Employee → Purchase → Expense → Customer Sale → Family Kharcha → Overall Balance",
                      "Order: Suppliers → Employees → Purchases → Expenses → Sales → Family Drawings → Overall Balance"),
    "A": ("क. सप्लायर", "A. Supplier", "A. Suppliers"),
    "A1": ("क-1 · माल आया", "A-1 · Maal Aaya", "A-1 · Goods Received"),
    "A2": ("क-2 · पैसा दिया", "A-2 · Payment Diya", "A-2 · Payments Made"),
    "A3": ("क-3 · सप्लायर-वार सार", "A-3 · Supplier-wise Summary", "A-3 · Supplier-wise Summary"),
    "B": ("ख. कर्मचारी", "B. Employee", "B. Employees"),
    "B1": ("ख-1 · काम और मज़दूरी (एक दिन की सारी एंट्री एक लाइन में)",
           "B-1 · Kaam aur Payment (ek din ki saari entries ek row mein)",
           "B-1 · Work and Wages (same-day entries combined)"),
    "B2": ("ख-2 · कर्मचारी-वार सार", "B-2 · Employee-wise Summary", "B-2 · Employee-wise Summary"),
    "C": ("ग. खरीद", "C. Purchase", "C. Purchases"),
    "C_old": ("ग-1 · पुरानी खरीद की पेमेंट (इस अवधि में दी)", "C-1 · Purani Kharid ki Payment (is period mein di)",
              "C-1 · Payments Against Earlier Purchases"),
    "D": ("घ. खर्च", "D. Expense", "D. Expenses"),
    "D1": ("घ-1 · मद-वार खर्च", "D-1 · Category-wise Kharch", "D-1 · Category-wise Expenses"),
    "D_old": ("घ-2 · पुराने खर्च की पेमेंट", "D-2 · Purane Kharch ki Payment", "D-2 · Payments Against Earlier Expenses"),
    "E": ("ङ. ग्राहक बिक्री", "E. Customer Sale", "E. Sales"),
    "E1": ("ङ-1 · माल बेचा", "E-1 · Maal Becha", "E-1 · Goods Sold"),
    "E2": ("ङ-2 · पैसा आया", "E-2 · Paisa Aaya", "E-2 · Payments Received"),
    "E3": ("ङ-3 · ग्राहक-वार सार", "E-3 · Customer-wise Summary", "E-3 · Customer-wise Summary"),
    "FAM": ("च. परिवार का खर्च", "F. Family Kharcha", "F. Family Drawings"),
    "FAM1": ("च-1 · घर गया / गल्ले में आया", "F-1 · Ghar Gaya / Galle mein Aaya", "F-1 · Taken for Home / Put Back"),
    "FAM2": ("च-2 · सदस्य-वार सार", "F-2 · Member-wise Summary", "F-2 · Member-wise Summary"),
    "F": ("छ. कुल हिसाब", "G. Overall Balance", "G. Overall Balance"),
    "F1": ("छ-1 · मद-वार स्थिति (इस अवधि में)", "G-1 · Head-wise Position (is period mein)", "G-1 · Head-wise Position (this period)"),
    "F2": ("छ-2 · नकद की स्थिति", "G-2 · Cash Position", "G-2 · Cash Position"),

    # family
    "fam_entries": ("घर गया / गल्ले में आया", "Ghar Gaya / Galle mein Aaya", "Taken for Home / Put Back"),
    "fam_members": ("सदस्य-वार सार", "Member-wise Summary", "Member-wise Summary"),
    "member": ("सदस्य", "Member", "Member"),
    "relation": ("रिश्ता", "Rishta", "Relation"),
    "purpose": ("किसलिए", "Kisliye", "Purpose"),
    "fam_diya": ("घर को दिया (−)", "Ghar ko Diya (−)", "Taken for Home (−)"),
    "fam_liya": ("गल्ले में आया (+)", "Galle mein Aaya (+)", "Put Back (+)"),
    "fam_net": ("कुल घर गया", "Net Ghar Gaya", "Net Drawings"),
    "h_family": ("परिवार का खर्च", "Family Kharcha", "Family Drawings"),
    "family_title": ("परिवार का खर्च — घर का हिसाब", "Family Kharcha — Ghar ka Hisab", "Family Drawings Statement"),
    "family_all": ("पूरा परिवार", "Poori Family", "All Family Members"),
    "m_family": ("घर गया", "Ghar Gaya", "Family"),
    "note_family": ("यह उधार नहीं है — सिर्फ़ गल्ले से घर गया / घर से गल्ले में आया पैसा। यह 'किसको देना / किससे लेना' में नहीं जुड़ता।",
                    "Ye udhaar nahi hai — sirf galle se ghar gaya / ghar se galle mein aaya paisa. Ye 'kisko dena / kisse lena' mein nahi judta.",
                    "Not a loan — only money taken from the business for the family, or put back. Not included in payables / receivables."),

    # supplier
    "supplier": ("सप्लायर", "Supplier", "Supplier"),
    "total_maal": ("कुल माल आया", "Total Maal Aaya", "Total Goods Received"),
    "total_paid": ("कुल पैसा दिया", "Total Payment Diya", "Total Paid"),
    "maal_in": ("माल आया (+)", "Maal Aaya (+)", "Goods In (+)"),
    "paid_minus": ("दिया (−)", "Diya (−)", "Paid (−)"),
    "closing_dena": ("अब बाकी", "Ab Baaki", "Closing Balance"),

    # employee
    "employee": ("कर्मचारी", "Employee", "Employee"),
    "role": ("काम", "Role", "Role"),
    "work_amt": ("काम (₹)", "Kaam (₹)", "Work (₹)"),
    "work_detail": ("काम का ब्योरा", "Kaam ka Detail", "Work Detail"),
    "paid_amt": ("लिया (₹)", "Liya (₹)", "Paid (₹)"),
    "breakdown": ("ब्योरा", "Breakdown", "Breakdown"),
    "notes": ("टिप्पणी", "Notes", "Notes"),
    "pay_days": ("भुगतान के दिन", "Payment Days", "Payment Days"),
    "work_plus": ("काम (देना +)", "Kaam (dena +)", "Work (payable +)"),
    "paid_minus_emp": ("लिया (−)", "Liya (−)", "Paid (−)"),

    # purchase / expense
    "seller": ("बेचने वाला", "Seller", "Seller"),
    "tot": ("कुल", "Total", "Total"),
    "paid": ("दिया", "Paid", "Paid"),
    "baaki": ("बाकी", "Baaki", "Balance"),
    "pay_detail": ("भुगतान का ब्योरा", "Payment Detail", "Payment Detail"),

    # customer
    "customer": ("ग्राहक", "Customer", "Customer"),
    "total_sale": ("कुल बिक्री", "Total Sale", "Total Sales"),
    "total_rec": ("कुल पैसा आया", "Total Paisa Aaya", "Total Received"),
    "opening_udhaar": ("पिछला बाकी", "Pichla Baaki", "Opening Balance"),
    "sale_plus": ("बिक्री (+)", "Sale (+)", "Sales (+)"),
    "rec_minus": ("आया (−)", "Aaya (−)", "Received (−)"),

    # overall balance
    "head": ("मद", "Head", "Head"),
    "bill_value": ("कुल कारोबार", "Kul Business", "Bill Value"),
    "gaya": ("पैसा गया (−)", "Paisa Gaya (−)", "Paid Out (−)"),
    "aaya": ("पैसा आया (+)", "Paisa Aaya (+)", "Received (+)"),
    "h_sup": ("सप्लायर (माल आया)", "Supplier (Maal Aaya)", "Suppliers (Goods In)"),
    "h_emp": ("कर्मचारी (काम / मज़दूरी)", "Employee (Kaam / Payment)", "Employees (Work / Wages)"),
    "h_pur": ("खरीद", "Purchase", "Purchases"),
    "h_exp": ("खर्च", "Expense", "Expenses"),
    "h_sale": ("ग्राहक बिक्री", "Customer Sale", "Sales"),
    "cash_open": ("शुरुआती नकद", "Opening Cash", "Opening Cash"),
    "cash_in": ("(+) कुल पैसा आया", "(+) Kul Paisa Aaya", "(+) Total Received"),
    "cash_out": ("(−) कुल पैसा गया", "(−) Kul Paisa Gaya", "(−) Total Paid"),
    "cash_close": ("आख़िरी नकद", "Closing Cash", "Closing Cash"),

    # ledgers
    "sup_ledger": ("सप्लायर खाता", "Supplier Khata", "Supplier Ledger Account"),
    "cus_ledger": ("ग्राहक खाता", "Customer Khata", "Customer Ledger Account"),
    "emp_ledger": ("कर्मचारी खाता", "Employee Khata", "Employee Ledger Account"),
    "g_cred": ("लेनदार (जिसे देना है)", "Creditor (jisko dena hai)", "Sundry Creditor"),
    "g_debt": ("देनदार (जिससे लेना है)", "Debtor (jisse lena hai)", "Sundry Debtor"),
    "g_emp": ("कर्मचारी", "Employee", "Employee"),
    "vtype": ("किस्म", "Type", "Vch Type"),
    "v_maal_in": ("माल आया", "Maal Aaya", "Goods In"),
    "v_payment_out": ("पैसा दिया", "Payment Diya", "Payment"),
    "v_sale": ("बिक्री", "Sale", "Sale"),
    "v_payment_in": ("पैसा आया", "Paisa Aaya", "Receipt"),
    "v_opening": ("पुराना बाकी (शुरुआती)", "Purana Baaki (opening)", "Opening Entry"),
    "dr_sup": ("नामे (दिया)", "Debit (Diya)", "Debit (Paid)"),
    "cr_sup": ("जमा (माल आया)", "Credit (Maal Aaya)", "Credit (Goods In)"),
    "dr_cus": ("नामे (माल गया)", "Debit (Maal Gaya)", "Debit (Goods Out)"),
    "cr_cus": ("जमा (पैसा आया)", "Credit (Paisa Aaya)", "Credit (Received)"),
    "dr_emp": ("नामे (लिया)", "Debit (Liya)", "Debit (Paid)"),
    "cr_emp": ("जमा (काम किया)", "Credit (Kaam)", "Credit (Work)"),
    "sold": ("बिक्री", "Sale", "Sales"),
    "received": ("आया", "Aaya", "Received"),
    "total_work": ("कुल काम", "Kul Kaam", "Total Work"),
    "total_paid_emp": ("कुल लिया", "Kul Liya", "Total Paid"),
    "note_sup": ("'देना' = हमें सप्लायर को पैसा देना है। 'लेना' = सप्लायर ने हमसे ज़्यादा पैसा ले रखा है।",
                 "'Dena' = humein supplier ko paisa dena hai. 'Lena' = supplier ne zyada paisa le rakha hai.",
                 "Cr = payable to the supplier. Dr = supplier has been paid in advance."),
    "note_cus": ("'लेना' = ग्राहक से हमें पैसा लेना है (उधार)।",
                 "'Lena' = customer se humein paisa lena hai (udhaar).",
                 "Dr = receivable from the customer."),
    "note_emp": ("'देना' = कर्मचारी की मज़दूरी बाकी है। 'लेना' = कर्मचारी ने काम से ज़्यादा पैसा (एडवांस) ले रखा है।",
                 "'Dena' = mazdoori baaki hai. 'Lena' = kaam se zyada paisa (advance) le rakha hai.",
                 "Cr = wages payable. Dr = advance taken in excess of work done."),

    # registers
    "pur_register": ("खरीद रजिस्टर", "Purchase Register", "Purchase Register"),
    "exp_register": ("खर्च रजिस्टर", "Expense Register", "Expense Register"),
    "worklog": ("काम का रजिस्टर", "Work Log — Kaam ka Register", "Work Log — Business Activity Register"),
    "worklog_sub": ("एक दिन + एक जगह की सारी एंट्री एक लाइन में", "Ek din + ek location ki saari entries ek row mein",
                    "Same day + same location entries combined"),
    "loc_type": ("जगह की किस्म", "Location Type", "Location Type"),
    "entries": ("एंट्री", "Entries", "Entries"),
    "labour": ("कुल मज़दूर", "Kul Majdoor", "Total Labour"),
    "work": ("काम (मज़दूर)", "Kaam (majdoor)", "Work (labour)"),
    "mm": ("माल की आवाजाही का रजिस्टर", "Material Movement Register", "Material Movement Register"),
    "from_type": ("कहाँ से (किस्म)", "From Type", "From Type"),
    "to_type": ("कहाँ (किस्म)", "To Type", "To Type"),
    "mtype": ("आवाजाही की किस्म", "Movement Type", "Movement Type"),
    "reason": ("कारण", "Reason", "Reason"),
    "cashbook": ("रोकड़ बही — नकद का हिसाब", "Cash Book — Cash ka Hisab", "Cash Book — Business Statement"),
    "source": ("स्रोत", "Source", "Source"),
    "in_": ("आया (+)", "Aaya (+)", "In (+)"),
    "out": ("गया (−)", "Gaya (−)", "Out (−)"),
    "note_cash": ("स्रोत कॉलम से हर नकद एंट्री को उसके असली वाउचर तक ढूँढा जा सकता है।",
                  "Source column se har cash entry ko uske original voucher tak trace kar sakte ho.",
                  "The Source column traces each cash entry back to its original voucher."),

    # period (> 1 mahina)
    "period_note": ("1 महीने से लम्बी अवधि: हर महीने का सार, और सिर्फ़ आख़िरी महीने की पूरी डिटेल।",
                    "1 mahine se lambi duration: har mahine ka summary, aur sirf aakhri mahine ki poori detail.",
                    "Period longer than one month: monthly summary, with full detail for the last month only."),
    "month_summary": ("महीने-वार सार", "Mahine-wise Summary", "Month-wise Summary"),
    "party_summary": ("पार्टी-वार सार (पूरी अवधि)", "Party-wise Summary (poora period)", "Party-wise Summary (whole period)"),
    "last_month_detail": ("आख़िरी महीने की पूरी डिटेल", "Aakhri Mahine ki Poori Detail", "Full Detail — Last Month"),
    "m_maal": ("माल आया", "Maal Aaya", "Goods In"),
    "m_sup_paid": ("सप्लायर को दिया", "Supplier ko Diya", "Paid to Suppliers"),
    "m_emp": ("मज़दूरी दी", "Mazdoori Di", "Wages Paid"),
    "m_pur": ("खरीद", "Kharid", "Purchases"),
    "m_exp": ("खर्च", "Kharch", "Expenses"),
    "m_sale": ("बिक्री", "Bikri", "Sales"),
    "m_rec": ("पैसा आया", "Paisa Aaya", "Received"),
    "m_cash": ("आख़िरी नकद", "Closing Cash", "Closing Cash"),
    "m_bill": ("बिल", "Bill", "Bill"),
    "m_paid": ("दिया", "Diya", "Paid"),

    # final hisab
    "final": ("अंतिम हिसाब — किसको देना है, किससे लेना है", "Final Hisab — Kisko Dena Hai, Kisse Lena Hai",
              "Final Summary — What We Owe and What We Are Owed"),
    "as_of": ("{d} तक", "{d} tak", "as of {d}"),
    "give_head": ("हमें पैसे देने हैं", "Humein Paise DENE Hain", "Amounts We Have to PAY"),
    "take_head": ("हमें पैसे लेने हैं", "Humein Paise LENE Hain", "Amounts We Have to RECEIVE"),
    "who": ("किसको / किससे", "Kisko / Kisse", "Party"),
    "why": ("किस बात का", "Kis cheez ka", "Towards"),
    "total_give": ("कुल देना", "Kul Dena", "Total Payable"),
    "total_take": ("कुल लेना", "Kul Lena", "Total Receivable"),
    "nothing": ("कुछ नहीं", "Kuch nahi", "Nothing"),
    "r_supplier_balance": ("माल का बाकी पैसा", "Maal ka baaki paisa", "Balance for goods received"),
    "r_supplier_advance": ("सप्लायर को ज़्यादा दिया (एडवांस)", "Supplier ko zyada diya (advance)", "Advance paid to supplier"),
    "r_employee_wages_due": ("मज़दूरी बाकी", "Mazdoori baaki", "Wages payable"),
    "r_employee_advance": ("एडवांस लिया हुआ", "Advance liya hua", "Advance taken"),
    "r_purchase_balance": ("खरीद का बाकी", "Kharid ka baaki", "Purchase balance"),
    "r_expense_balance": ("खर्च का बाकी", "Kharch ka baaki", "Expense balance"),
    "r_customer_udhaar": ("माल का उधार", "Maal ka udhaar", "Outstanding for goods sold"),
    "r_customer_advance": ("ग्राहक का एडवांस", "Customer ka advance", "Customer advance"),
    "cash_hand": ("हाथ में नकद", "Haath mein Cash", "Cash in Hand"),
    "conclusion": (
        "कुल मिलाकर: हमें <b>₹{give}</b> देने हैं और <b>₹{take}</b> लेने हैं। यानी {diff_line}। "
        "हाथ में नकद <b>{cash}</b> है — सारा लेना-देना निपटाने के बाद <b>₹{after}</b> {after_word}।",
        "Kul milake: humein <b>₹{give}</b> dene hain aur <b>₹{take}</b> lene hain. Matlab {diff_line}. "
        "Haath mein cash <b>{cash}</b> hai — saara lena-dena clear karne ke baad <b>₹{after}</b> {after_word}.",
        "In total, we have to pay <b>₹{give}</b> and receive <b>₹{take}</b> — {diff_line}. "
        "Cash in hand is <b>{cash}</b>; after settling everything, <b>₹{after}</b> {after_word}."),
    "diff_more_give": ("लेने से <b>₹{x}</b> ज़्यादा देना है", "lene se <b>₹{x}</b> zyada dena hai",
                       "we owe <b>₹{x}</b> more than we are owed"),
    "diff_more_take": ("देने से <b>₹{x}</b> ज़्यादा लेना है", "dene se <b>₹{x}</b> zyada lena hai",
                       "we are owed <b>₹{x}</b> more than we owe"),
    "diff_equal": ("लेना और देना बराबर है", "lena aur dena barabar hai", "payables and receivables are equal"),
    "after_left": ("बचेंगे", "bachenge", "will remain"),
    "after_short": ("कम पड़ेंगे", "kam padenge", "will be short"),
    "note_final": ("यह मुनाफ़ा/घाटा नहीं है — सिर्फ़ लेना-देना की स्थिति है (शुरू से आज तक)।",
                   "Ye profit/loss nahi hai — sirf lena-dena ki position hai (shuru se aaj tak).",
                   "This is not profit/loss — it shows outstanding payables and receivables (all time)."),
}

MONTHS = {
    "hi": ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अग", "सित", "अक्टू", "नव", "दिस"],
    "hg": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
MONTHS_FULL = {
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर"],
    "hg": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

_IDX = {"hi": 0, "hg": 1, "en": 2}


def t(lang, key, **kw):
    s = LABELS[key][_IDX[lang]]
    return s.format(**kw) if kw else s


# ---------------------------------------------------------------- fixed values (no LLM)
FIXED_VALUES = {
    # modes / providers
    "cash": ("नकद", "Cash", "Cash"), "upi": ("UPI", "UPI", "UPI"), "bank": ("बैंक", "Bank", "Bank"),
    "phonepe": ("PhonePe", "PhonePe", "PhonePe"), "gpay": ("GPay", "GPay", "GPay"), "paytm": ("Paytm", "Paytm", "Paytm"),
    # units
    "pcs": ("नग", "pcs", "pcs"), "cft": ("घन फुट", "cft", "cft"), "kg": ("किलो", "kg", "kg"),
    "quintal": ("क्विंटल", "quintal", "quintal"), "trolley": ("ट्रॉली", "trolley", "trolley"),
    "truck": ("ट्रक", "truck", "truck"), "ton": ("टन", "ton", "ton"), "bore": ("बोरी", "bore", "bag"),
    # roles
    "driver": ("ड्राइवर", "Driver", "Driver"), "gudam_worker": ("गोदाम कर्मचारी", "Gudam Worker", "Warehouse Worker"),
    "shop_worker": ("दुकान कर्मचारी", "Shop Worker", "Shop Worker"), "tod_worker": ("तोड़ने वाला", "Tod Worker", "Demolition Worker"),
    # location types
    "storage": ("भंडार", "Storage", "Storage"), "site": ("साइट", "Site", "Site"),
    "gudam": ("गोदाम", "Gudam", "Warehouse"), "shop": ("दुकान", "Shop", "Shop"),
    # transaction types
    "work": ("काम", "Kaam", "Work"), "payment": ("मज़दूरी", "Payment", "Wages"), "advance": ("एडवांस", "Advance", "Advance"),
    # cash_ledger categories
    "salary": ("कर्मचारी को भुगतान", "Employee Payment", "Wages"),
    "sales_payment": ("बिक्री वसूली", "Sale Payment", "Sales Receipt"),
    "supplier_payment": ("सप्लायर को भुगतान", "Supplier Payment", "Supplier Payment"),
    "purchase_payment": ("खरीद भुगतान", "Purchase Payment", "Purchase Payment"),
    "expense_payment": ("खर्च भुगतान", "Expense Payment", "Expense Payment"),
    "opening_balance": ("शुरुआती बाकी", "Opening Balance", "Opening Balance"),
    "family": ("परिवार का खर्च", "Family Kharcha", "Family Drawings"),
    # family transaction types
    "kharcha": ("घर गया", "Ghar Gaya", "Taken for Home"), "jama": ("गल्ले में आया", "Galle mein Aaya", "Put Back"),
    # expense categories (tools.py docstring examples)
    "transport": ("ढुलाई", "Transport", "Transport"), "utility": ("बिजली-पानी", "Utility", "Utilities"),
    "maintenance": ("मरम्मत", "Maintenance", "Maintenance"), "misc": ("फुटकर", "Misc", "Miscellaneous"),
    # movement
    "internal": ("अंदरूनी", "Internal", "Internal"),
}


def fixed_value(lang, text):
    if text is None:
        return None
    v = FIXED_VALUES.get(str(text).strip().lower())
    return v[_IDX[lang]] if v else None


# ---------------------------------------------------------------- free-text translation
TRANSLATE_PROMPT = """You translate short labels from a family brick & timber salvage business
in Bhiwani, Haryana. The source text is Hinglish (Hindi written in Roman letters, mixed with English).

Target language: {target}

Rules:
- Person / business names: {name_rule}
- Keep numbers, bill numbers and codes exactly as they are.
- Keep it short — these go into table cells.
- Return exactly one translation per input, same order, same count.

Inputs:
{items}
"""


def translate_values(db, lang, texts, llm=None):
    """
    {source_text: translated_text} — sirf hi/en ke liye. Pehle FIXED_VALUES, fir
    translation_cache, aur jo bache unke liye EK LLM call (fir cache mein save).
    LLM fail ho to original text hi wapas — report kabhi nahi rukti.
    """
    from models import TranslationCache
    out = {}
    if lang == "hg":
        # Hinglish: data pehle se Hinglish — sirf fixed shabd saaf (cash → Cash, gudam_worker → Gudam Worker)
        return {x: (fixed_value("hg", x) or x) for x in texts if x}
    todo = []
    for x in {str(x) for x in texts if x}:
        f = fixed_value(lang, x)
        if f is not None:
            out[x] = f
        else:
            todo.append(x)
    if todo:
        for row in (db.query(TranslationCache)
                    .filter(TranslationCache.lang == lang, TranslationCache.source_text.in_(todo)).all()):
            out[row.source_text] = row.translated_text
        todo = [x for x in todo if x not in out]
    if todo and llm is not None:
        try:
            from pydantic import BaseModel

            class _Out(BaseModel):
                translations: list[str]

            prompt = TRANSLATE_PROMPT.format(
                target="Hindi in Devanagari script" if lang == "hi" else "simple English",
                name_rule=("write them in Devanagari (transliterate, do not translate meaning)"
                           if lang == "hi" else "keep them as they are, only fix capitalisation"),
                items="\n".join(f"{i + 1}. {x}" for i, x in enumerate(todo)),
            )
            res = llm.with_structured_output(_Out).invoke(prompt)
            if len(res.translations) == len(todo):
                for src, dst in zip(todo, res.translations):
                    dst = (dst or "").strip() or src
                    out[src] = dst
                    db.add(TranslationCache(source_text=src, lang=lang, translated_text=dst))
                db.commit()
        except Exception as e:  # noqa: BLE001 — translation kabhi report na roke
            db.rollback()
            print(f"⚠️ translation skip ({lang}): {e}")
    for x in todo:
        out.setdefault(x, x)
    return out
