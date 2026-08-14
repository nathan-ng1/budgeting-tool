from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from categorisation.interface import Categoriser, MalformedResponseError
from statement_export import pipeline
from statement_export.parser import RawTransaction
from statement_export.pipeline import Archive
from transaction_log.categories import SUB_CATEGORIES_BY_CATEGORY
from transaction_log.entries import Candidate, WriteResult

NeedsReviewResolver = Callable[[RawTransaction, str | None], tuple[str, str]]


@dataclass(frozen=True)
class OrchestrationResult:
    write_result: WriteResult | None
    aborted: bool
    reason: str | None = None


def run(
    deterministic_candidates: list[Candidate],
    to_categorise: list[RawTransaction],
    categoriser: Categoriser,
    client,
    recurring_config_path: Path,
    through: date,
    resolve_needs_review: NeedsReviewResolver,
    archive: Archive | None = None,
    dry_run: bool = False,
) -> OrchestrationResult:
    categorised, abort_reason = _categorise(to_categorise, categoriser, resolve_needs_review)
    if abort_reason is not None:
        return OrchestrationResult(write_result=None, aborted=True, reason=abort_reason)

    result = pipeline.run(
        candidates=deterministic_candidates + categorised,
        client=client,
        recurring_config_path=recurring_config_path,
        through=through,
        archive=archive,
        dry_run=dry_run,
    )
    return OrchestrationResult(write_result=result, aborted=False)


def _categorise(
    to_categorise: list[RawTransaction],
    categoriser: Categoriser,
    resolve_needs_review: NeedsReviewResolver,
) -> tuple[list[Candidate], str | None]:
    if not to_categorise:
        return [], None

    try:
        batch = categoriser.categorise(to_categorise, SUB_CATEGORIES_BY_CATEGORY)
    except MalformedResponseError as exc:
        return [], str(exc)

    if len(batch.results) != len(to_categorise):
        return [], f"Expected {len(to_categorise)} categorisation results, got {len(batch.results)}"

    candidates = []
    for transaction, result in zip(to_categorise, batch.results):
        category, sub_category = result.category, result.sub_category
        if result.needs_review:
            category, sub_category = resolve_needs_review(transaction, result.reason)
        try:
            candidates.append(
                Candidate(
                    date=transaction.date,
                    amount=transaction.amount,
                    category=category,
                    sub_category=sub_category,
                    notes=transaction.notes,
                )
            )
        except ValueError as exc:
            return [], str(exc)

    return candidates, None
