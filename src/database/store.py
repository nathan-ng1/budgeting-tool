import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from goals.goal import ACTIVE, Goal, GoalDraft, GoalNotFound
from goals.links import require_valid_goal_link

from budget_suggestions.suggestion import BudgetSuggestion
from database.backup import backup_to
from recurring.rules import RecurringRule, StoredRecurringRule
from transaction_log.categories import CATEGORIES_BY_TYPE, TYPE_ORDER, Category, default_category_rows
from transaction_log.entries import Candidate, ExistingRow, Transaction

# The `settings` row recording the latest Backup (Issue #197).
LAST_BACKED_UP_KEY = "last_backed_up"

REPO_ROOT = Path(__file__).resolve().parents[2]

# `categories` is additive (CREATE TABLE IF NOT EXISTS), same as every other
# table here. `transactions`/`recurring_rules`/`category_budgets` are written
# below with their end-state `category_id` FK column already in place - see
# Issue #90's "Foreign-key migration" decision: on a brand new database (every
# test, every fresh install) CREATE TABLE IF NOT EXISTS builds the target
# schema directly, while an existing pre-#90 database (still `category` TEXT)
# needs `migration.categories_table.migrate` run once to add `category_id`,
# backfill it, and drop the old TEXT column before this code can read it -
# `python -m migration` does that as part of the update process (ADR-0025).
SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    emoji TEXT,
    locked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    notes TEXT NOT NULL,
    -- The Goal a Contribution (Category Goals) belongs to; NULL for every other
    -- row. Not enforced by SQLite - the store checks it (ADR-0031). An existing
    -- file gets the column from migration.add_goals, not from here.
    goal_id INTEGER REFERENCES goals(id)
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    notes TEXT NOT NULL,
    frequency TEXT NOT NULL,
    interval INTEGER NOT NULL,
    day TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS category_budgets (
    category_id INTEGER NOT NULL REFERENCES categories(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC NOT NULL,
    PRIMARY KEY (category_id, year, month)
);

CREATE TABLE IF NOT EXISTS budget_suggestion (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    write_up TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

-- Goals (ADR-0031): the user's own fields plus a lifecycle state. Status, saved
-- amount and pace are derived, never stored.
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    target_amount REAL NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active'
);

-- Localisation settings (ADR-0027): only what has been saved. A setting with
-- no row reads as its default, which dashboard.settings owns.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
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


class CategoryNotFound(LookupError):
    """No Category has the given id."""


class CategoryLocked(ValueError):
    """A locked Category (see LOCKED_CATEGORIES; Beem Adjustment - ADR-0015 - is one) can't be
    renamed or deleted, no matter what the caller sends - the UI hiding the
    edit/delete controls is a courtesy, not the enforcement point (Issue #89).
    """


class CategoryInUse(ValueError):
    """A Category still referenced by a Transaction or Recurring Rule can't
    be deleted - delete is blocked, not cascading (Issue #89). Category
    Budgets don't count: they're deleted with the Category (Issue #162).
    """


def category_in_use_message(name: str, transactions: int, rules: int) -> str:
    """Name each cause blocking a Category delete, so the Dashboard says
    what to re-categorise first rather than an opaque record count.
    """
    causes = []
    if transactions:
        causes.append(f"{transactions} Transaction{'s' if transactions != 1 else ''}")
    if rules:
        causes.append(f"{rules} Recurring Transactions Config rule{'s' if rules != 1 else ''}")
    return f"Category {name!r} is used by {' and '.join(causes)} and cannot be deleted"


class LocalStore:
    """Live Transaction Log + Recurring Transactions Config store, backed by
    a local SQLite database.

    Mirrors FakeStore's shape (see tests/conftest.py).
    """

    def __init__(self, connection: sqlite3.Connection, database_path: Path | None = None):
        self._connection = connection
        # Where the Database file lives, for Settings to show (ADR-0030). None
        # for a store built straight from a connection, e.g. in a unit test.
        self.path = database_path

    def close(self) -> None:
        """Release the Database file, so it can be moved or deleted -
        Windows won't let an open SQLite file go (ADR-0030)."""
        self._connection.close()

    def pending_migration_names(self) -> list[str]:
        """The registered one-off migrations this Database has not had yet
        (ADR-0025). Read-only: the Dashboard checks this at startup and
        refuses to run while any are pending."""
        # Imported here, not at module level: the migrations import this module.
        from migration.registry import MIGRATIONS
        from migration.runner import pending

        return [migration.name for migration in pending(self._connection, MIGRATIONS)]

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
            "INSERT INTO transactions (date, amount, type, category_id, notes) VALUES (?, ?, ?, ?, ?)",
            [
                (c.date.isoformat(), round(c.stored_amount, 2), c.type, self._category_id(c.category), c.notes)
                for c in candidates
            ],
        )
        self._connection.commit()

    def read_transactions(self) -> list[Transaction]:
        rows = self._connection.execute(
            "SELECT t.id, t.date, t.amount, t.type, c.name, t.notes, t.goal_id, g.title "
            "FROM transactions t JOIN categories c ON c.id = t.category_id "
            "LEFT JOIN goals g ON g.id = t.goal_id"
        ).fetchall()
        return [
            Transaction(
                id=row_id,
                date=date.fromisoformat(row_date),
                amount=amount,
                type=transaction_type,
                category=category,
                notes=notes,
                goal_id=goal_id,
                goal_title=goal_title,
            )
            for row_id, row_date, amount, transaction_type, category, notes, goal_id, goal_title in rows
        ]

    def create_transaction(self, candidate: Candidate) -> Transaction:
        # Candidate.__post_init__ only validated the non-zero Amount - the
        # (Type, Category) pair is checked here, against the live categories
        # table, so a Category added through Category Management is usable
        # immediately (Issue #91).
        self._require_valid_pair(candidate.type, candidate.category)
        self._require_valid_goal_link(candidate, current_goal_id=None)

        cursor = self._connection.execute(
            "INSERT INTO transactions (date, amount, type, category_id, notes, goal_id) VALUES (?, ?, ?, ?, ?, ?)",
            self._transaction_columns(candidate),
        )
        self._connection.commit()
        return _as_transaction(cursor.lastrowid, candidate)

    def update_transaction(self, transaction_id: int, candidate: Candidate) -> Transaction:
        self._require_valid_pair(candidate.type, candidate.category)
        self._require_valid_goal_link(candidate, current_goal_id=self._current_goal_id(transaction_id))

        cursor = self._connection.execute(
            "UPDATE transactions SET date = ?, amount = ?, type = ?, category_id = ?, notes = ?, goal_id = ? "
            "WHERE id = ?",
            (*self._transaction_columns(candidate), transaction_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise TransactionNotFound(f"No Transaction has id {transaction_id}")

        self._connection.commit()
        return _as_transaction(transaction_id, candidate)

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
            "(amount, type, category_id, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [self._as_columns(rule) for rule in rules],
        )
        self._connection.commit()

    def read_recurring_rules(self) -> list[RecurringRule]:
        rows = self._connection.execute(
            "SELECT r.amount, r.type, c.name, r.notes, r.frequency, r.interval, r.day, r.start_date, r.end_date "
            "FROM recurring_rules r JOIN categories c ON c.id = r.category_id"
        ).fetchall()
        return [_as_rule(row) for row in rows]

    def read_stored_recurring_rules(self) -> list[StoredRecurringRule]:
        """Every rule with the id the Dashboard needs to edit or delete it.

        Ordered by id, so the CRUD screen lists rules in the order they were
        created rather than whatever order SQLite happens to return.
        """
        rows = self._connection.execute(
            "SELECT r.id, r.amount, r.type, c.name, r.notes, r.frequency, r.interval, r.day, r.start_date, r.end_date "
            "FROM recurring_rules r JOIN categories c ON c.id = r.category_id ORDER BY r.id"
        ).fetchall()
        return [StoredRecurringRule(id=row[0], rule=_as_rule(row[1:])) for row in rows]

    def create_recurring_rule(self, rule: RecurringRule) -> StoredRecurringRule:
        self._require_valid_pair(rule.type, rule.category)

        cursor = self._connection.execute(
            "INSERT INTO recurring_rules "
            "(amount, type, category_id, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self._as_columns(rule),
        )
        self._connection.commit()
        return StoredRecurringRule(id=cursor.lastrowid, rule=rule)

    def update_recurring_rule(self, rule_id: int, rule: RecurringRule) -> StoredRecurringRule:
        self._require_valid_pair(rule.type, rule.category)

        cursor = self._connection.execute(
            "UPDATE recurring_rules SET "
            "amount = ?, type = ?, category_id = ?, notes = ?, frequency = ?, "
            "interval = ?, day = ?, start_date = ?, end_date = ? "
            "WHERE id = ?",
            (*self._as_columns(rule), rule_id),
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

    def read_category_budgets(self, year: int, month: int) -> dict[str, float]:
        """Every Category Budget set for one specific (year, month), keyed by
        Category. A Category with no Category Budget for this month is
        omitted - never reported as $0 (unset != $0).
        """
        rows = self._connection.execute(
            "SELECT c.name, cb.amount FROM category_budgets cb JOIN categories c ON c.id = cb.category_id "
            "WHERE cb.year = ? AND cb.month = ?",
            (year, month),
        ).fetchall()
        return {category: amount for category, amount in rows}

    def read_category_budgets_for_range(
        self, category: str, start_year: int, start_month: int, end_year: int, end_month: int
    ) -> dict[tuple[int, int], float]:
        """One Category's Category Budgets across an inclusive span of months,
        keyed by (year, month). A month with none set is omitted.
        """
        rows = self._connection.execute(
            "SELECT cb.year, cb.month, cb.amount FROM category_budgets cb JOIN categories c ON c.id = cb.category_id "
            "WHERE c.name = ? AND (cb.year * 12 + cb.month) BETWEEN (? * 12 + ?) AND (? * 12 + ?)",
            (category, start_year, start_month, end_year, end_month),
        ).fetchall()
        return {(year, month): amount for year, month, amount in rows}

    def upsert_category_budget(
        self, transaction_type: str, category: str, year: int, month: int, amount: float
    ) -> None:
        self._require_valid_pair(transaction_type, category)

        self._connection.execute(
            "INSERT INTO category_budgets (category_id, year, month, amount) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(category_id, year, month) DO UPDATE SET amount = excluded.amount",
            (self._category_id(category), year, month, amount),
        )
        self._connection.commit()

    def delete_category_budget(self, category: str, year: int, month: int) -> None:
        category_id = self._category_id_or_none(category)
        if category_id is None:
            # Nothing could reference an unknown Category anyway - a no-op,
            # same as deleting a budget that was simply never set.
            return

        self._connection.execute(
            "DELETE FROM category_budgets WHERE category_id = ? AND year = ? AND month = ?",
            (category_id, year, month),
        )
        self._connection.commit()

    def read_goals(self) -> list[Goal]:
        """Every Goal in any state, oldest first."""
        rows = self._connection.execute(
            "SELECT id, title, description, target_amount, start_date, end_date, state FROM goals ORDER BY id"
        ).fetchall()
        return [_as_goal(row) for row in rows]

    def create_goal(self, draft: GoalDraft) -> Goal:
        self._require_unique_goal_title(draft.title, except_id=None)

        cursor = self._connection.execute(
            "INSERT INTO goals (title, description, target_amount, start_date, end_date, state) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                draft.title,
                draft.description,
                draft.target_amount,
                draft.start_date.isoformat(),
                draft.end_date.isoformat(),
                ACTIVE,
            ),
        )
        self._connection.commit()
        return self._goal(cursor.lastrowid)

    def update_goal(self, goal_id: int, draft: GoalDraft) -> Goal:
        """Replace a Goal's own fields. Its lifecycle state is left alone."""
        self._goal(goal_id)
        self._require_unique_goal_title(draft.title, except_id=goal_id)

        self._connection.execute(
            "UPDATE goals SET title = ?, description = ?, target_amount = ?, start_date = ?, end_date = ? "
            "WHERE id = ?",
            (
                draft.title,
                draft.description,
                draft.target_amount,
                draft.start_date.isoformat(),
                draft.end_date.isoformat(),
                goal_id,
            ),
        )
        self._connection.commit()
        return self._goal(goal_id)

    def read_goal(self, goal_id: int) -> Goal:
        """One Goal in any state, or GoalNotFound."""
        return self._goal(goal_id)

    def read_goal_savings(self) -> dict[int, float]:
        """Saved so far per Goal: the sum of every linked Contribution, of any
        date and whatever the Goal's state. A Goal with none is omitted."""
        rows = self._connection.execute(
            "SELECT goal_id, SUM(amount) FROM transactions WHERE goal_id IS NOT NULL GROUP BY goal_id"
        ).fetchall()
        return {goal_id: round(total, 2) for goal_id, total in rows}

    def _goal(self, goal_id: int) -> Goal:
        row = self._connection.execute(
            "SELECT id, title, description, target_amount, start_date, end_date, state FROM goals WHERE id = ?",
            (goal_id,),
        ).fetchone()
        if row is None:
            raise GoalNotFound(f"No Goal has id {goal_id}")
        return _as_goal(row)

    def _require_unique_goal_title(self, title: str, except_id: int | None) -> None:
        """A title is unique across every Goal, Past goals included, ignoring
        case and surrounding spaces. Folded in code with `casefold()`, not by
        a column constraint: SQLite's `lower()` and NOCASE fold ASCII only."""
        wanted = title.strip().casefold()
        for goal in self.read_goals():
            if goal.id != except_id and goal.title.strip().casefold() == wanted:
                raise ValueError(f"Another Goal already uses the title {goal.title!r} (Past goals count too)")

    def read_categories(self) -> list[Category]:
        """Every Category, sourced from the `categories` table (Issue #90) -
        the DB-backed replacement for the hardcoded CATEGORIES_BY_TYPE dict.
        """
        rows = self._connection.execute("SELECT id, type, name, emoji, locked FROM categories").fetchall()
        return [
            Category(id=row_id, type=row_type, name=name, emoji=emoji, locked=bool(locked))
            for row_id, row_type, name, emoji, locked in rows
        ]

    def create_category(self, transaction_type: str, name: str, emoji: str | None) -> Category:
        if transaction_type not in TYPE_ORDER:
            raise ValueError(f"{transaction_type!r} is not a valid Type")

        name = name.strip()
        if not name:
            raise ValueError("Category name must not be blank")
        if self._category_id_or_none(name) is not None:
            raise ValueError(f"Category {name!r} already exists")

        cursor = self._connection.execute(
            "INSERT INTO categories (type, name, emoji) VALUES (?, ?, ?)",
            (transaction_type, name, emoji),
        )
        self._connection.commit()
        return Category(id=cursor.lastrowid, type=transaction_type, name=name, emoji=emoji, locked=False)

    def update_category(self, category_id: int, name: str, emoji: str | None) -> Category:
        """Rename and/or change a Category's emoji - its Type is fixed at
        creation (Issue #89's Implementation Decisions), so nothing here can
        change it.
        """
        existing = self._category_or_none(category_id)
        if existing is None:
            raise CategoryNotFound(f"No Category has id {category_id}")
        if existing.locked:
            raise CategoryLocked(f"Category {existing.name!r} is locked and cannot be renamed")

        name = name.strip()
        if not name:
            raise ValueError("Category name must not be blank")
        colliding_id = self._category_id_or_none(name)
        if colliding_id is not None and colliding_id != category_id:
            raise ValueError(f"Category {name!r} already exists")

        self._connection.execute("UPDATE categories SET name = ?, emoji = ? WHERE id = ?", (name, emoji, category_id))
        self._connection.commit()
        return Category(id=category_id, type=existing.type, name=name, emoji=emoji, locked=False)

    def delete_category(self, category_id: int) -> None:
        existing = self._category_or_none(category_id)
        if existing is None:
            raise CategoryNotFound(f"No Category has id {category_id}")
        if existing.locked:
            raise CategoryLocked(f"Category {existing.name!r} is locked and cannot be deleted")

        transactions, rules = self._connection.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM transactions WHERE category_id = :id), "
            "(SELECT COUNT(*) FROM recurring_rules WHERE category_id = :id)",
            {"id": category_id},
        ).fetchone()
        if transactions or rules:
            raise CategoryInUse(category_in_use_message(existing.name, transactions, rules))

        # A Category Budget never keeps its Category alive (Issue #162) - it
        # goes with it, committed together. Foreign keys aren't enforced, so
        # nothing would remove these rows otherwise.
        self._connection.execute("DELETE FROM category_budgets WHERE category_id = ?", (category_id,))
        self._connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self._connection.commit()

    def _require_valid_pair(self, transaction_type: str, category: str) -> None:
        """Raise unless `category` exists and belongs to `transaction_type` -
        sourced from the live `categories` table (Issue #91), not the
        hardcoded CATEGORIES_BY_TYPE dict, so a Category added through
        Category Management is usable immediately, in this process and after
        a restart alike.
        """
        row = self._connection.execute("SELECT type FROM categories WHERE name = ?", (category,)).fetchone()
        if row is None or row[0] != transaction_type:
            raise ValueError(f"Category {category!r} is not a valid {transaction_type} Category")

    def _category_or_none(self, category_id: int) -> Category | None:
        row = self._connection.execute(
            "SELECT id, type, name, emoji, locked FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if row is None:
            return None
        row_id, row_type, name, emoji, locked = row
        return Category(id=row_id, type=row_type, name=name, emoji=emoji, locked=bool(locked))

    def _category_id(self, name: str) -> int:
        category_id = self._category_id_or_none(name)
        if category_id is None:
            raise ValueError(f"Category {name!r} does not exist")
        return category_id

    def _category_id_or_none(self, name: str) -> int | None:
        row = self._connection.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        return row[0] if row is not None else None

    def _require_valid_goal_link(self, candidate: Candidate, current_goal_id: int | None) -> None:
        """The Goal-link rules (goals.links) against the live `goals` table."""
        goal = None
        if candidate.goal_id is not None:
            try:
                goal = self._goal(candidate.goal_id)
            except GoalNotFound:
                pass
        require_valid_goal_link(candidate.category, candidate.goal_id, goal, current_goal_id)

    def _current_goal_id(self, transaction_id: int) -> int | None:
        row = self._connection.execute("SELECT goal_id FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if row is None:
            raise TransactionNotFound(f"No Transaction has id {transaction_id}")
        return row[0]

    def _transaction_columns(self, candidate: Candidate) -> tuple:
        return (
            candidate.date.isoformat(),
            candidate.amount,
            candidate.type,
            self._category_id(candidate.category),
            candidate.notes,
            candidate.goal_id,
        )

    def _as_columns(self, rule: RecurringRule) -> tuple:
        return (
            rule.amount,
            rule.type,
            self._category_id(rule.category),
            rule.notes,
            rule.frequency,
            rule.interval,
            str(rule.day),
            rule.start_date.isoformat(),
            rule.end_date.isoformat() if rule.end_date is not None else None,
        )

    def write_budget_suggestion(self, write_up: str, generated_at: datetime) -> None:
        """Replace the one standing Budget Suggestion outright (ADR-0014) -
        `budget_suggestion` is a single-row table (CHECK (id = 1)), not a
        history table, so this is always an overwrite, never an append.
        """
        self._connection.execute(
            "INSERT INTO budget_suggestion (id, write_up, generated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET write_up = excluded.write_up, generated_at = excluded.generated_at",
            (write_up, generated_at.isoformat()),
        )
        self._connection.commit()

    def read_budget_suggestion(self) -> BudgetSuggestion | None:
        """The current standing Budget Suggestion, or None if the script has
        never been run."""
        row = self._connection.execute(
            "SELECT write_up, generated_at FROM budget_suggestion WHERE id = 1"
        ).fetchone()
        if row is None:
            return None

        write_up, generated_at = row
        return BudgetSuggestion(write_up=write_up, generated_at=datetime.fromisoformat(generated_at))

    def backup_to(self, target_path: Path) -> None:
        """Write a consistent copy of the live Database to `target_path`
        (Issue #197)."""
        backup_to(self._connection, target_path)

    def count_data(self) -> dict[str, int]:
        """How much the user has put in the Database, for the delete flow's
        "what will be lost" list (Issue #201): rows in each user-owned table (Goals in any state),
        Categories beyond the predefined ones, and saved Display Settings
        (the `settings` row recording the latest Backup is not one)."""

        def count(table: str) -> int:
            return self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        predefined = {(kind, name) for kind, names in CATEGORIES_BY_TYPE.items() for name in names}
        categories = self._connection.execute("SELECT type, name FROM categories").fetchall()
        return {
            "transactions": count("transactions"),
            "recurring_rules": count("recurring_rules"),
            "category_budgets": count("category_budgets"),
            "goals": count("goals"),
            "custom_categories": sum(1 for row in categories if tuple(row) not in predefined),
            "display_settings": len(set(self.read_settings()) - {LAST_BACKED_UP_KEY}),
        }

    def read_last_backed_up(self) -> str | None:
        """When a Backup was last generated (ISO text), None if never.
        Kept in `settings` but apart from the user-facing settings payload."""
        return self.read_settings().get(LAST_BACKED_UP_KEY)

    def record_backup(self, when: str) -> None:
        self.write_settings({LAST_BACKED_UP_KEY: when})

    def read_settings(self) -> dict[str, str]:
        """The settings that have been saved, as text - a setting never saved
        is simply absent (its default is the caller's concern)."""
        return dict(self._connection.execute("SELECT key, value FROM settings").fetchall())

    def write_settings(self, updates: dict) -> None:
        """Upsert each given setting, all or none."""
        self._connection.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(key, str(value)) for key, value in updates.items()],
        )
        self._connection.commit()


def _as_transaction(transaction_id: int, candidate: Candidate) -> Transaction:
    return Transaction(
        id=transaction_id,
        date=candidate.date,
        amount=candidate.amount,
        type=candidate.type,
        category=candidate.category,
        notes=candidate.notes,
        goal_id=candidate.goal_id,
    )


def _as_goal(columns) -> Goal:
    goal_id, title, description, target_amount, start_date, end_date, state = columns
    return Goal(
        id=goal_id,
        title=title,
        description=description,
        target_amount=target_amount,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        state=state,
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


def _seed_default_categories(connection: sqlite3.Connection) -> None:
    """One-off bootstrap of `categories` from CATEGORIES_BY_TYPE - only runs
    while the table is still empty (a brand new database: every test, every
    new install), so it needs no separate setup step - the locked ones
    (LOCKED_CATEGORIES, e.g. Beem Adjustment - ADR-0015) seeded locked. Deliberately *not* run on every connect(): a Category
    a user deletes via Category Management must stay deleted across Dashboard
    restarts, and this is the only thing that distinguishes "never created"
    from "deliberately deleted" - there's no tombstone, so re-running this
    once the table already has rows would silently undo a delete by name. A
    pre-#90 database that already has real Transaction/Recurring Rule/Category
    Budget rows still needs `migration.categories_table.migrate` run once to
    backfill their `category_id` from the old TEXT `category` column - that
    call also lands here with an empty, freshly-created `categories` table, so
    it still seeds normally. A future addition to CATEGORIES_BY_TYPE for
    existing installs is delivered via its own one-off migration script
    instead (see ADR-0022's rollout of Savings/Investments), registered in
    `migration.registry` so the update process runs it (ADR-0025), not by
    this function running again.
    """
    [(count,)] = connection.execute("SELECT COUNT(*) FROM categories")
    if count > 0:
        return

    connection.executemany(
        "INSERT INTO categories (type, name, emoji, locked) VALUES (?, ?, ?, ?)",
        [
            (transaction_type, name, emoji, 1 if locked else 0)
            for transaction_type, name, emoji, locked in default_category_rows()
        ],
    )
    connection.commit()


def resolve_database_path(database_path: Path | None = None) -> Path:
    """database_path if given, else DATABASE_PATH from the environment
    (loaded from a repo-root `.env` if present).
    """
    if database_path is not None:
        return database_path

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    return Path(os.environ["DATABASE_PATH"])


def open_connection(database_path: Path | None = None) -> sqlite3.Connection:
    """Open the local SQLite database - the public entry point for anything
    needing a raw connection rather than a LocalStore (`python -m migration`).

    Creates the categories/transactions/recurring_rules/category_budgets/
    budget_suggestion tables if they don't exist yet, and seeds `categories`
    with today's fixed Category list if it's empty. A brand new database -
    one with no `transactions` table yet - is built on the current schema
    directly, so every registered one-off migration is recorded as already
    applied there rather than ever run against it (Issue #152, ADR-0025).
    """
    database_path = resolve_database_path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the Dashboard's local HTTP server handles each
    # connection on its own thread, so this connection is used from threads
    # other than the one that opened it. A lock in dashboard.server serialises
    # the handlers, so access stays one request at a time - never concurrent.
    connection = sqlite3.connect(database_path, check_same_thread=False)
    is_new = (
        connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transactions'").fetchone()
        is None
    )
    if is_new:
        # Recorded before the schema is built, not after: if the process dies
        # in between, the next open still finds no `transactions` table and
        # treats the database as new again, rather than as an old install
        # every migration should run against. Imported here, not at module
        # level: the migrations themselves import from this module.
        from migration.registry import MIGRATIONS
        from migration.runner import mark_all_applied

        mark_all_applied(connection, MIGRATIONS)
    connection.executescript(SCHEMA)
    connection.commit()
    _seed_default_categories(connection)
    return connection


def connect(database_path: Path | None = None) -> LocalStore:
    """Build a LocalStore against the local SQLite database - see
    open_connection.
    """
    database_path = resolve_database_path(database_path).resolve()
    return LocalStore(connection=open_connection(database_path), database_path=database_path)
