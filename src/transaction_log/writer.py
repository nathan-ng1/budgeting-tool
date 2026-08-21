from datetime import date

from recurring.rules import Occurrence, RecurringRule
from recurring.schedule import expand
from transaction_log.entries import Candidate, ExistingRow, WriteResult


def resolve_writes(
    candidates: list[Candidate],
    existing_rows: list[ExistingRow],
    recurring_rules: list[RecurringRule] | None = None,
    through: date | None = None,
) -> WriteResult:
    combined = list(candidates)
    if recurring_rules:
        due_through = through if through is not None else date.today()
        for rule in recurring_rules:
            combined.extend(_as_candidates(expand(rule, due_through)))

    existing_keys = {_key(row) for row in existing_rows}

    to_write = []
    skipped = []
    for entry in combined:
        if _key(entry) in existing_keys:
            skipped.append(entry)
        else:
            to_write.append(entry)

    return WriteResult(to_write=to_write, skipped=skipped)


def _as_candidates(occurrences: list[Occurrence]) -> list[Candidate]:
    return [
        Candidate(
            date=occurrence.date,
            amount=occurrence.amount,
            type=occurrence.type,
            category=occurrence.category,
            notes=occurrence.notes,
        )
        for occurrence in occurrences
    ]


def _key(entry: Candidate | ExistingRow) -> tuple:
    # Candidate.amount may still carry the source Statement Export's sign;
    # ExistingRow.amount is always positive (what's actually in the log) — so
    # dedupe on magnitude, matching how the writer normalises on write.
    return (entry.date, round(abs(entry.amount), 2), entry.notes)
