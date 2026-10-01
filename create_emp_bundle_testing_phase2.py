"""Create/update the Employee Bundle Tests workbook.

By default, an existing workbook and its existing sheet are preserved.  Run
with --overwrite to recreate only the "Employee Bundle Tests" sheet.
"""

from __future__ import annotations

import argparse
import json
from copy import copy
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


FILENAME = "emp_bundle_testing_phase2.xlsx"
SHEET_NAME = "Employee Bundle Tests"
HEADERS = [
    "Test No.",
    "Input Statement",
    "Actual Extract Output",
    "Expected Extract Output",
    "Extract Match?",
    "Actual Grouping Output",
    "Expected Grouping Output",
    "Grouping Match?",
    "Person Role (if applicable)",
    "Tool Selected",
    "Expected Tool",
    "Tool Match?",
    "Tool Arguments",
    "Execution Result",
    "Bug Found?",
    "Bug Description",
    "Fix Applied?",
    "Fix Description",
    "Retest Status",
    "Notes",
]

GREEN = PatternFill("solid", fgColor="C6EFCE")
RED = PatternFill("solid", fgColor="FFC7CE")
YELLOW = PatternFill("solid", fgColor="FFEB9C")
GREY = PatternFill("solid", fgColor="D9E1F2")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")


def output_path() -> Path:
    """Use Claude's output directory when available; otherwise use this folder."""
    claude_output = Path("/mnt/user-data/outputs")
    return (claude_output if claude_output.is_dir() else Path.cwd()) / FILENAME


def apply_layout(ws) -> None:
    for column, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=column, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        alignment = copy(cell.alignment)
        alignment.wrap_text = True
        alignment.vertical = "center"
        cell.alignment = alignment

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:T{max(ws.max_row, 2)}"
    widths = {
        1: 10, 2: 48, 3: 48, 4: 48, 5: 15, 6: 35, 7: 35, 8: 16,
        9: 30, 10: 34, 11: 34, 12: 14, 13: 42, 14: 20, 15: 14,
        16: 55, 17: 16, 18: 55, 19: 18, 20: 40,
    }
    for column, width in widths.items():
        ws.column_dimensions[get_column_letter(column)].width = width

    last_row = 1000
    for column in (5, 8, 12):
        rng = f"{get_column_letter(column)}2:{get_column_letter(column)}{last_row}"
        ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Yes"'], fill=GREEN))
        ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"No"'], fill=RED))
    ws.conditional_formatting.add("O2:O1000", CellIsRule(operator="equal", formula=['"Yes"'], fill=YELLOW))
    ws.conditional_formatting.add("S2:S1000", CellIsRule(operator="equal", formula=['"Pass"'], fill=GREEN))
    ws.conditional_formatting.add("S2:S1000", CellIsRule(operator="equal", formula=['"Fail"'], fill=RED))
    ws.conditional_formatting.add("S2:S1000", CellIsRule(operator="equal", formula=['"Not Retested"'], fill=GREY))


def format_data_rows(ws) -> None:
    ws.auto_filter.ref = f"A1:T{max(ws.max_row, 2)}"
    for row in range(2, ws.max_row + 1):
        ws.row_dimensions[row].height = 32
        for cell in ws[row]:
            alignment = copy(cell.alignment)
            alignment.wrap_text = True
            alignment.vertical = "top"
            cell.alignment = alignment


def seed_test_cases(ws) -> None:
    """Add the supplied examples only once (identified by Test No.)."""
    existing_test_numbers = {ws.cell(row=row, column=1).value for row in range(2, ws.max_row + 1)}
    cases = [
        [
            1,
            "Ram hamara employee hai, driver hai, phone 9876543210 hai",
            json.dumps(["Ram hamara employee hai, driver hai, phone 9876543210 hai"], ensure_ascii=False),
            "", "",
            'record_type=NEED_PERSON, identity_key="Ram"',
            "record_type=STANDALONE (role is already explicit)", "No",
            "", "manage_employee", "", "", "", "Success", "Yes",
            "Statement should have gone to STANDALONE because the role is already explicit.",
            "Pending", "", "Not Retested", "",
        ],
        [
            2,
            "Ram ne 500 ka kaam kiya",
            json.dumps(["Ram ne 500 ka kaam kiya"], ensure_ascii=False),
            json.dumps(["Ram ne 500 ka kaam kiya"], ensure_ascii=False), "Yes",
            'record_type=NEED_PERSON, identity_key="Ram"',
            'record_type=NEED_PERSON, identity_key="Ram"', "Yes",
            "Employee (confidence: 9.90)",
            "record_employee_transaction (work, amount=500)",
            "record_employee_transaction", "Yes",
            json.dumps({"type": "work", "amount": 500}, ensure_ascii=False),
            "Success", "No", "", "", "", "Not Retested", "",
        ],
    ]
    for case in cases:
        if case[0] not in existing_test_numbers:
            ws.append(case)


def update_detailed_results(ws) -> None:
    """Overwrite Test 1–3 with the reviewed Phase 2 results."""
    detail_headers = {"Expected Behavior": 21, "Actual Behavior": 22}
    for header, column in detail_headers.items():
        ws.cell(1, column, header)

    expected_1 = (
        'Ram ka role statement mein explicitly "employee hai" diya hai, isliye role ambiguity nahi hai. '
        'Ye STANDALONE_TRANSACTION treat hona chahiye aur Person-Role HITL ke bina seedha '
        'manage_employee tool call honi chahiye.'
    )
    actual_1 = (
        'Statement NEED_PERSON classify hua. Person-Role-Classification trigger hui; AI ne Employee '
        '(9.90 confidence) recommend kiya aur user ne confirm kiya. Uske baad manage_employee sahi call '
        'hui aur data successfully save hua.'
    )
    expected_2 = (
        'Employee-work statement with explicit amount. NEED_PERSON branch, high-confidence Employee '
        'recommendation, aur record_employee_transaction call with transaction_type=work, amount=500 expected hai.'
    )
    actual_2 = (
        'Bilkul expected ke mutabik: NEED_PERSON classify hua, AI ne Employee (9.90 confidence) recommend '
        'kiya, user ne confirm kiya, record_employee_transaction (work, amount=500) call hua aur DB mein save hua.'
    )
    expected_3 = (
        '"Diye" payment kisi bhi role ke saath ho sakta hai aur koi strong contextual role signal nahi hai. '
        'Person-Role-Classification ko low-confidence result dena chahiye aur system ko user se sabhi 5 roles '
        'options ke saath explicitly poochna chahiye.'
    )
    actual_3 = (
        'Bilkul expected ke mutabik: Family Member 2.50 confidence aur baaki roles 0.00 aaye. System ne '
        '5-option selection screen dikhayi; user ne Employee select kiya. record_employee_transaction '
        '(payment, amount=300) call hui aur CashLedger mein OUT-entry sahi bani.'
    )
    note_3 = (
        'Additional Note: PersonRole enum mein FAMILY_MEMBER role hai jiske liye NEED_PERSON_BUNDLE mein koi '
        'tool-bundle define nahi hai — agar user ye role select kare, system crash karega '
        '(ValueError: No tool bundle configured). Ye latent/potential bug abhi trigger nahi hua, lekin future '
        'test ke liye flag karne layak hai.'
    )
    rows = {
        2: [1, 'Ram hamara employee hai, driver hai, phone 9876543210 hai',
            '["Ram hamara employee hai, driver hai, phone 9876543210 hai"]',
            '["Ram hamara employee hai, driver hai, phone 9876543210 hai"]', 'Yes',
            'record_type=NEED_PERSON, identity_key="Ram"', 'record_type=STANDALONE_TRANSACTION', 'No',
            'Employee (confidence: 9.90; user confirmed)', 'manage_employee', 'manage_employee', 'Yes',
            '{"name": "Ram", "role": "driver", "phone": "9876543210"}',
            'Success — data saved to DB', 'Yes',
            'Grouping-node explicit-role statements ko NEED_PERSON maan raha hai, jabki inhe '
            'STANDALONE_TRANSACTION maana jana chahiye tha. Isse unnecessary Person-Role HITL step add hua, '
            'chahe final result correct aaya.',
            'No', '', 'Not Retested Yet', '', expected_1, actual_1],
        3: [2, 'Ram ne 500 ka kaam kiya', '["Ram ne 500 ka kaam kiya"]',
            '["Ram ne 500 ka kaam kiya"]', 'Yes',
            'record_type=NEED_PERSON, identity_key="Ram"', 'record_type=NEED_PERSON, identity_key="Ram"', 'Yes',
            'Employee (confidence: 9.90; user confirmed)', 'record_employee_transaction (work, amount=500)',
            'record_employee_transaction (transaction_type=work, amount=500)', 'Yes',
            '{"transaction_type": "work", "amount": 500}', 'Success — saved to DB', 'No', '', '', '', '',
            '', expected_2, actual_2],
        4: [3, 'Ram ko 300 diye', '["Ram ko 300 diye"]', '["Ram ko 300 diye"]', 'Yes',
            'record_type=NEED_PERSON, identity_key="Ram"', 'record_type=NEED_PERSON (role ambiguity expected)', 'Yes',
            'Family Member 2.50; all other roles 0.00; user selected Employee',
            'record_employee_transaction (payment, amount=300)',
            'record_employee_transaction (transaction_type=payment, amount=300)', 'Yes',
            '{"transaction_type": "payment", "amount": 300}',
            'Success — saved to DB; CashLedger OUT-entry created', 'No', '', '', '', '', note_3, expected_3, actual_3],
    }
    for row, values in rows.items():
        for column, value in enumerate(values, start=1):
            ws.cell(row, column, value)

    wide_columns = {2: 58, 16: 60, 21: 60, 22: 60}
    for column, width in wide_columns.items():
        ws.column_dimensions[get_column_letter(column)].width = width
    for column in range(1, 23):
        header = ws.cell(1, column)
        header.font = Font(bold=True, color="FFFFFF")
        header.fill = HEADER_FILL
        alignment = copy(header.alignment)
        alignment.wrap_text = True
        alignment.vertical = "center"
        header.alignment = alignment
    for row in range(2, 5):
        max_lines = 1
        for column in range(1, 23):
            cell = ws.cell(row, column)
            alignment = copy(cell.alignment)
            alignment.wrap_text = True
            alignment.vertical = "top"
            cell.alignment = alignment
            width = ws.column_dimensions[get_column_letter(column)].width or 15
            max_lines = max(max_lines, (len(str(cell.value or "")) // max(int(width), 1)) + 1)
        ws.row_dimensions[row].height = max(36, min(max_lines * 18, 180))

    # Explicit fills ensure the requested colours also show without depending on Excel recalculation.
    ws["O2"].fill = YELLOW
    ws["O3"].fill = PatternFill("solid", fgColor="FFFFFF")
    ws["O4"].fill = PatternFill("solid", fgColor="FFFFFF")
    ws["S2"].fill = GREY
    ws.auto_filter.ref = "A1:V4"


def add_tests_4_to_7(ws) -> None:
    """Append reviewed Tests 4–7 without modifying Tests 1–3."""
    cases = {
        5: [4, 'Satpal ne driving ki', '["Satpal ne driving ki"]', '["Satpal ne driving ki"]', 'Yes',
            'record_type=NEED_PERSON, identity_key="Satpal"',
            'record_type=NEED_PERSON, identity_key="Satpal"', 'Yes',
            'Employee (confidence: 9.80; user confirmed)', 'record_attendance (attendance="P", driving="P")',
            'record_attendance (attendance="P", driving="P")', 'Yes',
            '{"attendance": "P", "driving": "P"}', 'Success — saved to DB', 'No', '', '', '', '', '',
            'Driving alone should also set attendance to the same value. For full-day driving, attendance="P" '
            'and driving="P" are expected; record_attendance should be called.',
            'Bilkul expected ke mutabik: NEED_PERSON classify hua, AI ne Employee (9.80 confidence) recommend '
            'kiya, user ne confirm kiya, record_attendance (attendance="P", driving="P") call hui aur DB mein save hua.'],
        6: [5,
            'Aaj Suresh pura din aaya drivery ki usne 3 chakar mare (pehla attempt, Suresh naam se)',
            '["Aaj Suresh pura din aaya drivery ki", "usne 3 chakar mare"]',
            '["Aaj Suresh pura din aaya drivery ki", "usne 3 chakar mare"]', 'Yes',
            'record_type=NEED_PERSON, identity_key="Suresh", group_id="G1"',
            'Same person Suresh; both actions in group_id="G1"', 'Yes',
            'Employee (user selection required for missing amount)',
            'record_attendance; record_employee_transaction (corrupted after HITL update)',
            'record_attendance; record_employee_transaction', 'Yes',
            'Attendance result incorrectly gained amount; group_id values became "1" and "some_group_id"; '
            'both action_index values became 0.',
            'Argument-update result corrupted; unrelated attendance result was also re-processed', 'Yes',
            'tool_argument_update_node mein 3 combined bugs — (1) LLM ko poora ToolArgumentResult schema diya '
            'ja raha tha update ke liye, jisse LLM group_id/action_index/tool_name invent kar raha tha, (2) loop sabhi '
            'results ko re-process kar raha tha chahe missing-field ho ya nahi, jisse unrelated results corrupt ho rahe '
            'the, (3) RecordEmployeeTransactionArgs mein amount constraint gt=0 tha, jo amount=0 valid case ko reject karta tha.',
            'Yes', 'Updated only the missing-field arguments; preserved wrapper metadata and allowed amount=0.',
            'Not Retested Yet', '',
            'Two actions should split: full attendance/driving and employee work (3 trips, no rupee amount). Both '
            'must share person Suresh and group_id="G1", with action_index 0 and 1. Missing-field HITL applies '
            'only to employee-work; attendance stays untouched.',
            'Three bugs: attendance arguments received an invalid amount field; group_id values were corrupt ("1" '
            'and "some_group_id"); both action_index values were 0. Root cause was the update node regenerating '
            'whole ToolArgumentResult wrappers and re-processing every result.'],
        7: [6,
            'Aaj Mohan pura din aaya drivery ki usne 3 chakar mare (Test 6 ka retest, naye naam "Mohan" se taaki fresh employee-record bane)',
            '["Aaj Mohan pura din aaya drivery ki", "usne 3 chakar mare"]',
            '["Aaj Mohan pura din aaya drivery ki", "usne 3 chakar mare"]', 'Yes',
            'record_type=NEED_PERSON, identity_key="Mohan", group_id="G1"',
            'Both actions in group_id="G1" with action_index 0 and 1', 'Yes',
            'Employee (user selected)', 'record_attendance; record_employee_transaction (work, amount=0.0)',
            'record_attendance; record_employee_transaction', 'Yes',
            'record_attendance clean (no amount); both group_id="G1"; action_index 0 and 1; employee transaction amount=0.0.',
            'Success — amount=0.0 accepted; no validation error', 'No',
            'Test 5 fixes verified successfully in this retest.', 'Yes',
            'Only missing-field arguments are updated; wrapper metadata remains intact and amount=0 is valid.', 'Yes', '',
            'Same workflow as Test 5 retest: two correctly split actions, clean attendance arguments with no amount, '
            'group_id="G1" on both, and action_index values 0 and 1.',
            'All three fixes verified: attendance arguments had no amount, both results used group_id="G1", action '
            'indices were 0 and 1, and amount=0.0 was accepted without validation error.'],
        8: [7, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
            'Awaiting Test 7 details.', '', ''],
    }
    for row, values in cases.items():
        for column, value in enumerate(values, start=1):
            ws.cell(row, column, value)

    for row in range(5, 9):
        max_lines = 1
        for column in range(1, 23):
            cell = ws.cell(row, column)
            alignment = copy(cell.alignment)
            alignment.wrap_text = True
            alignment.vertical = "top"
            cell.alignment = alignment
            width = ws.column_dimensions[get_column_letter(column)].width or 15
            max_lines = max(max_lines, (len(str(cell.value or "")) // max(int(width), 1)) + 1)
        ws.row_dimensions[row].height = max(36, min(max_lines * 18, 220))

    for row in (5, 7, 8):
        ws.cell(row, 15).fill = PatternFill("solid", fgColor="FFFFFF")
    ws.cell(6, 15).fill = YELLOW
    ws.cell(6, 19).fill = GREY
    ws.cell(7, 19).fill = GREEN
    ws.auto_filter.ref = "A1:V8"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Recreate only the target sheet.")
    parser.add_argument("--update-results", action="store_true", help="Overwrite Test 1–3 with reviewed Phase 2 results.")
    parser.add_argument("--add-tests-4-7", action="store_true", help="Add Test 4–7 rows while preserving existing tests.")
    args = parser.parse_args()

    path = output_path()
    if path.exists():
        wb = load_workbook(path)
    else:
        wb = Workbook()
        wb.remove(wb.active)

    if SHEET_NAME in wb.sheetnames and args.overwrite:
        del wb[SHEET_NAME]
    new_sheet = SHEET_NAME not in wb.sheetnames
    ws = wb.create_sheet(SHEET_NAME) if new_sheet else wb[SHEET_NAME]

    # Do not alter an existing sheet: this makes normal re-runs non-destructive.
    if new_sheet:
        apply_layout(ws)
    seed_test_cases(ws)
    if new_sheet:
        format_data_rows(ws)
    if args.update_results:
        update_detailed_results(ws)
    if args.add_tests_4_7:
        add_tests_4_to_7(ws)
    wb.save(path)
    print(f"Workbook saved to: {path.resolve()}")


if __name__ == "__main__":
    main()
