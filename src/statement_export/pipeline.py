from dataclasses import dataclass
from datetime import date
from pathlib import Path

from transaction_log.entries import Candidate, WriteResult
from transaction_log.writer import resolve_writes


@dataclass(frozen=True)
class Archive:
    source_path: Path
    processed_dir: Path


def run(
    candidates: list[Candidate],
    store,
    through: date,
    archive: Archive | None = None,
    dry_run: bool = False,
) -> WriteResult:
    recurring_rules = store.read_recurring_rules()
    existing_rows = store.read_existing_rows()

    result = resolve_writes(
        candidates=candidates,
        existing_rows=existing_rows,
        recurring_rules=recurring_rules,
        through=through,
    )

    if dry_run:
        return result

    store.append_rows(result.to_write)

    if archive is not None:
        archive.processed_dir.mkdir(parents=True, exist_ok=True)
        archive.source_path.rename(archive.processed_dir / archive.source_path.name)

    return result
