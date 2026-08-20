import os
import sqlite3
from datetime import date
from pathlib import Path

from recurring.rules import RecurringRule
from transaction_log.categories import is_valid_type_category_pair
from transaction_log.entries import Candidate, ExistingRow

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

    def append_recurring_rules(self, rules: list[RecurringRule]) -> None:
        if not rules:
            return

        self._connection.executemany(
            "INSERT INTO recurring_rules "
            "(amount, type, category, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    r.amount,
                    r.type,
                    r.category,
                    r.notes,
                    r.frequency,
                    r.interval,
                    str(r.day),
                    r.start_date.isoformat(),
                    r.end_date.isoformat() if r.end_date is not None else None,
                )
                for r in rules
            ],
        )
        self._connection.commit()

    def read_recurring_rules(self) -> list[RecurringRule]:
        rows = self._connection.execute(
            "SELECT amount, type, category, notes, frequency, interval, day, start_date, end_date "
            "FROM recurring_rules"
        ).fetchall()

        rules = []
        for amount, transaction_type, category, notes, frequency, interval, day, start_date, end_date in rows:
            rules.append(
                RecurringRule(
                    amount=amount,
                    type=transaction_type,
                    category=category,
                    notes=notes,
                    frequency=frequency,
                    interval=interval,
                    day=int(day) if frequency == "Monthly" else day,
                    start_date=date.fromisoformat(start_date),
                    end_date=date.fromisoformat(end_date) if end_date is not None else None,
                )
            )
        return rules

    def read_category_budgets(self) -> dict[str, float]:
        rows = self._connection.execute("SELECT category, monthly_amount FROM category_budgets").fetchall()
        return {category: monthly_amount for category, monthly_amount in rows}

    def upsert_category_budget(self, category: str, monthly_amount: float) -> None:
        if not is_valid_type_category_pair("Expense", category):
            raise ValueError(f"Category {category!r} is not a valid Expense Category")

        self._connection.execute(
            "INSERT INTO category_budgets (category, monthly_amount) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_amount = excluded.monthly_amount",
            (category, monthly_amount),
        )
        self._connection.commit()

    def delete_category_budget(self, category: str) -> None:
        self._connection.execute("DELETE FROM category_budgets WHERE category = ?", (category,))
        self._connection.commit()


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
    connection = sqlite3.connect(database_path)
    connection.executescript(SCHEMA)
    connection.commit()
    return LocalStore(connection=connection)
