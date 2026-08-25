"""Translation between the Transactions tab's JSON shape and Transaction/
Candidate - see Issues #33 and #35.

Kept out of dashboard.server so the HTTP layer stays a router: what a
Transaction looks like on the wire is a question about the domain, not about
HTTP - mirrors dashboard.recurring.
"""

import csv
import io
from datetime import date

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

from transaction_log.categories import TYPE_ORDER, Category, assignable_categories_by_type
from transaction_log.entries import Candidate, Transaction

FIELDS = ("date", "amount", "type", "category", "notes")
CSV_HEADER = ("Date", "Amount", "Type", "Category", "Notes")

# How many pre-formatted data rows the Import template offers - generous
# enough for a normal import batch without the workbook growing unwieldy.
IMPORT_TEMPLATE_ROWS = 500

DATE_NUMBER_FORMAT = "YYYY-MM-DD"

_COLUMN_INSTRUCTIONS = (
    ("Date", "The Transaction's date.", "An Excel date, or unambiguous YYYY-MM-DD text."),
    ("Amount", "The Transaction's amount.", "A positive number."),
    ("Type", "Income, Expense, Debt, or Transfer.", "Choose from the dropdown."),
    (
        "Category",
        "The specific budget label for the Transaction.",
        "Choose from the dropdown - see the Type / Category table below for which "
        "Categories belong to which Type.",
    ),
    ("Notes", "A description of the Transaction (e.g. the merchant).", "Free text."),
)


def as_payload(transaction: Transaction) -> dict:
    return {
        "id": transaction.id,
        "date": transaction.date.isoformat(),
        "amount": transaction.amount,
        "type": transaction.type,
        "category": transaction.category,
        "notes": transaction.notes,
    }


def as_csv(transactions: list[Transaction]) -> bytes:
    """The Export panel's `.csv` (Issue #96) - the same 5 columns as the
    Transaction Log, header-only when `transactions` is empty, with no
    internal `id` since that's meaningless outside the Dashboard.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    for t in transactions:
        writer.writerow([t.date.isoformat(), t.amount, t.type, t.category, t.notes])
    return buffer.getvalue().encode("utf-8")


def as_import_template(categories: list[Category]) -> bytes:
    """The Import panel's `.xlsx` template (Issue #97) - generated fresh on
    every request from the live Category list, so it never goes stale as
    Categories are added, renamed, or removed via Category Management.
    Upload/preview/commit is a follow-on ticket - this only has to be
    correct and downloadable.
    """
    workbook = openpyxl.Workbook()

    sheet = workbook.active
    sheet.title = "Transactions"
    sheet.append(CSV_HEADER)

    assignable = assignable_categories_by_type(categories)
    type_names = list(TYPE_ORDER)
    category_names = sorted({name for names in assignable.values() for name in names})

    instructions = workbook.create_sheet("Instructions")
    _write_instructions(instructions, categories)

    # A hidden sheet holding the dropdown source lists - a flat (non-dependent)
    # list per column, per the AC, not a Type->Category cascade. Excel data
    # validation reads a list from a real range rather than an inline string,
    # which openpyxl's DataValidation also caps at 255 characters.
    lists_sheet = workbook.create_sheet("Lists")
    lists_sheet.sheet_state = "hidden"
    for row, type_name in enumerate(type_names, start=1):
        lists_sheet.cell(row=row, column=1, value=type_name)
    for row, category_name in enumerate(category_names, start=1):
        lists_sheet.cell(row=row, column=2, value=category_name)

    last_row = IMPORT_TEMPLATE_ROWS + 1

    type_validation = DataValidation(
        type="list", formula1=f"Lists!$A$1:$A${len(type_names)}", allow_blank=True
    )
    sheet.add_data_validation(type_validation)
    type_validation.add(f"C2:C{last_row}")

    if category_names:
        category_validation = DataValidation(
            type="list", formula1=f"Lists!$B$1:$B${len(category_names)}", allow_blank=True
        )
        sheet.add_data_validation(category_validation)
        category_validation.add(f"D2:D{last_row}")

    for row in range(2, last_row + 1):
        sheet.cell(row=row, column=1).number_format = DATE_NUMBER_FORMAT

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _write_instructions(sheet, categories: list[Category]) -> None:
    sheet.append(["Column", "What it means", "Data type / rules"])
    for name, meaning, rules in _COLUMN_INSTRUCTIONS:
        sheet.append([name, meaning, rules])

    sheet.append([])
    sheet.append(["Type", "Category"])
    for transaction_type, category_name in _type_category_rows(categories):
        sheet.append([transaction_type, category_name])


def _type_category_rows(categories: list[Category]) -> list[tuple[str, str]]:
    """(Type, Category) pairs for the Instructions sheet's table - every
    non-locked Category, Type-then-name ordered, built from the same live,
    locked-excluding list the Type/Category dropdowns use above so the table
    can never drift from what's actually selectable.
    """
    assignable = assignable_categories_by_type(categories)
    return [
        (transaction_type, category_name)
        for transaction_type in TYPE_ORDER
        for category_name in sorted(assignable.get(transaction_type, set()))
    ]


def from_payload(payload) -> Candidate:
    """The Candidate a request body describes.

    Raises ValueError - with a message naming what's wrong - for anything the
    caller could fix by sending a different body. Candidate's own
    __post_init__ raises the same way for a zero Amount or an invalid (Type,
    Category) pair, so the caller has one kind of error to handle.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one transaction")

    missing = [field for field in FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    return Candidate(
        date=_date(payload["date"], "date"),
        amount=_number(payload["amount"], "amount"),
        type=payload["type"],
        category=payload["category"],
        notes=payload["notes"],
    )


def _number(value, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a number, got {value!r}") from None


def _date(value, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a date as YYYY-MM-DD, got {value!r}") from None
