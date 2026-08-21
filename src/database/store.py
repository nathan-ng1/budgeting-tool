import os
import sqlite3
from datetime import date
from pathlib import Path

from recurring.rules import RecurringRule, StoredRecurringRule
from transaction_log.categories import require_valid_type_category_pair
from transaction_log.entries import Candidate, ExistingRow, Transaction

REPO_ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    notes TEXT NOT NULL,
    frequency TEXT NOT NULL,
    interval INTEGER NOT NULL,
    day TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS category_budgets (
    category TEXT PRIMARY KEY,
    monthly_amount NUMERIC NOT NULL
);
"""


class RecurringRuleNotFound(LookupError):
    """No Recurring Transactions Config rule has the given id.

    Distinct from a ValueError over the rule's contents: the caller named a row
    that isn't there, rather than describing one badly.
    """


class TransactionNotFound(LookupError):
    """No Transaction has the given id.

    Distinct from a ValueError over the transaction's contents: the caller
    named a row that isn't there, rather than describing one badly.
    """


class LocalStore:
    """Live Transaction Log + Recurring Transactions Config store, backed by
    a local SQLite database.

    Mirrors FakeStore's shape (see tests/conftest.py).
    """

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def read_existing_rows(self) -> list[ExistingRow]:
        rows = self._connection.execute("SELECT date, amount, notes FROM transactions").fetchall()
        return [
            ExistingRow(date=date.fromisoformat(row_date), amount=amount, notes=notes)
            for row_date, amount, notes in rows
        ]

    def append_rows(self, candidates: list[Candidate]) -> None:
        if not candidates:
            return

        self._connection.executemany(
            "INSERT INTO transactions (date, amount, type, category, notes) VALUES (?, ?, ?, ?, ?)",
            [
                (c.date.isoformat(), round(abs(c.amount), 2), c.type, c.category, c.notes)
                for c in candidates
            ],
        )
        self._connection.commit()

    def read_transactions(self) -> list[Transaction]:
        rows = self._connection.execute(
            "SELECT id, date, amount, type, category, notes FROM transactions"
        ).fetchall()
        return [
            Transaction(
                id=row_id,
                date=date.fromisoformat(row_date),
                amount=amount,
                type=transaction_type,
                category=category,
                notes=notes,
            )
            for row_id, row_date, amount, transaction_type, category, notes in rows
        ]

    def create_transaction(self, candidate: Candidate) -> Transaction:
        # Candidate.__post_init__ already validated the (Type, Category) pair
        # and the non-zero Amount - there is no invalid Candidate to reject.
        cursor = self._connection.execute(
            "INSERT INTO transactions (date, amount, type, category, notes) VALUES (?, ?, ?, ?, ?)",
            (candidate.date.isoformat(), candidate.amount, candidate.type, candidate.category, candidate.notes),
        )
        self._connection.commit()
        return Transaction(
            id=cursor.lastrowid,
            date=candidate.date,
            amount=candidate.amount,
            type=candidate.type,
            category=candidate.category,
            notes=candidate.notes,
        )

    def update_transaction(self, transaction_id: int, candidate: Candidate) -> Transaction:
        cursor = self._connection.execute(
            "UPDATE transactions SET date = ?, amount = ?, type = ?, category = ?, notes = ? WHERE id = ?",
            (candidate.date.isoformat(), candidate.amount, candidate.type, candidate.category, candidate.notes, transaction_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise TransactionNotFound(f"No Transaction has id {transaction_id}")

        self._connection.commit()
        return Transaction(
            id=transaction_id,
            date=candidate.date,
            amount=candidate.amount,
            type=candidate.type,
            category=candidate.category,
            notes=candidate.notes,
        )

    def delete_transaction(self, transaction_id: int) -> None:
        cursor = self._connection.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise TransactionNotFound(f"No Transaction has id {transaction_id}")

        self._connection.commit()

    def append_recurring_rules(self, rules: list[RecurringRule]) -> None:
        if not rules:
            return

        self._connection.executemany(
            "INSERT INTO recurring_rules "
            "(amount, type, category, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [_as_columns(rule) for rule in rules],
        )
        self._connection.commit()

    def read_recurring_rules(self) -> list[RecurringRule]:
        rows = self._connection.execute(
            "SELECT amount, type, category, notes, frequency, interval, day, start_date, end_date "
            "FROM recurring_rules"
        ).fetchall()
        return [_as_rule(row) for row in rows]

    def read_stored_recurring_rules(self) -> list[StoredRecurringRule]:
        """Every rule with the id the Dashboard needs to edit or delete it.

        Ordered by id, so the CRUD screen lists rules in the order they were
        created rather than whatever order SQLite happens to return.
        """
        rows = self._connection.execute(
            "SELECT id, amount, type, category, notes, frequency, interval, day, start_date, end_date "
            "FROM recurring_rules ORDER BY id"
        ).fetchall()
        return [StoredRecurringRule(id=row[0], rule=_as_rule(row[1:])) for row in rows]

    def create_recurring_rule(self, rule: RecurringRule) -> StoredRecurringRule:
        _validate_pair(rule)

        cursor = self._connection.execute(
            "INSERT INTO recurring_rules "
            "(amount, type, category, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            _as_columns(rule),
        )
        self._connection.commit()
        return StoredRecurringRule(id=cursor.lastrowid, rule=rule)

    def update_recurring_rule(self, rule_id: int, rule: RecurringRule) -> StoredRecurringRule:
        _validate_pair(rule)

        cursor = self._connection.execute(
            "UPDATE recurring_rules SET "
            "amount = ?, type = ?, category = ?, notes = ?, frequency = ?, "
            "interval = ?, day = ?, start_date = ?, end_date = ? "
            "WHERE id = ?",
            (*_as_columns(rule), rule_id),
        )
        if cursor.rowcount == 0:
            # Nothing was written, so nothing needs undoing - but leave the
            # transaction clean for the next caller either way.
            self._connection.rollback()
            raise RecurringRuleNotFound(f"No Recurring Transactions Config rule has id {rule_id}")

        self._connection.commit()
        return StoredRecurringRule(id=rule_id, rule=rule)

    def delete_recurring_rule(self, rule_id: int) -> None:
        cursor = self._connection.execute("DELETE FROM recurring_rules WHERE id = ?", (rule_id,))
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise RecurringRuleNotFound(f"No Recurring Transactions Config rule has id {rule_id}")

        self._connection.commit()

    def read_category_budgets(self) -> dict[str, float]:
        rows = self._connection.execute("SELECT category, monthly_amount FROM category_budgets").fetchall()
        return {category: monthly_amount for category, monthly_amount in rows}

    def upsert_category_budget(self, category: str, monthly_amount: float) -> None:
        require_valid_type_category_pair("Expense", category)

        self._connection.execute(
            "INSERT INTO category_budgets (category, monthly_amount) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_amount = excluded.monthly_amount",
            (category, monthly_amount),
        )
        self._connection.commit()

    def delete_category_budget(self, category: str) -> None:
        self._connection.execute("DELETE FROM category_budgets WHERE category = ?", (category,))
        self._connection.commit()


def _validate_pair(rule: RecurringRule) -> None:
    """Reject a rule whose (Type, Category) pair isn't one this project allows.

    RecurringRule's own __post_init__ already vets the schedule (Frequency,
    Interval, Day against Start Date); the pair is the part it can't see.
    """
    require_valid_type_category_pair(rule.type, rule.category)


def _as_columns(rule: RecurringRule) -> tuple:
    return (
        rule.amount,
        rule.type,
        rule.category,
        rule.notes,
        rule.frequency,
        rule.interval,
        str(rule.day),
        rule.start_date.isoformat(),
        rule.end_date.isoformat() if rule.end_date is not None else None,
    )


def _as_rule(columns) -> RecurringRule:
    amount, transaction_type, category, notes, frequency, interval, day, start_date, end_date = columns
    return RecurringRule(
        amount=amount,
        type=transaction_type,
        category=category,
        notes=notes,
        frequency=frequency,
        # Day is stored as text either way - a weekday name for Weekly rules,
        # a day-of-month for Monthly ones.
        day=int(day) if frequency == "Monthly" else day,
        interval=interval,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date) if end_date is not None else None,
    )


def connect(database_path: Path | None = None) -> LocalStore:
    """Build a LocalStore against the local SQLite database.

    Reads DATABASE_PATH from the environment (loaded from a repo-root `.env`
    if present) when database_path isn't given explicitly. Creates the
    transactions/recurring_rules/category_budgets tables if they don't exist
    yet.
    """
    if database_path is None:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env")
        database_path = Path(os.environ["DATABASE_PATH"])

    database_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the Dashboard's local HTTP server runs its
    # request-handling loop on a different thread than the one that opens
    # this connection, but serves one request at a time - never concurrent.
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.executescript(SCHEMA)
    connection.commit()
    return LocalStore(connection=connection)
