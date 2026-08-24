import logging
from dataclasses import dataclass
from datetime import date
from typing import Callable

from categorisation.interface import Categoriser, MalformedResponseError
from statement_export import pipeline
from statement_export.parser import RawTransaction
from statement_export.pipeline import Archive
from transaction_log.entries import Candidate, WriteResult

logger = logging.getLogger(__name__)

# Resolves a Needs Review transaction to a (Type, Category) pair, or None if the
# user decides it shouldn't be recorded at all.
NeedsReviewResolver = Callable[[RawTransaction, str | None], tuple[str, str] | None]


@dataclass(frozen=True)
class OrchestrationResult:
    write_result: WriteResult | None
    aborted: bool
    reason: str | None = None


def run(
    deterministic_candidates: list[Candidate],
    to_categorise: list[RawTransaction],
    categoriser: Categoriser,
    store,
    through: date,
    resolve_needs_review: NeedsReviewResolver,
    archive: Archive | None = None,
    dry_run: bool = False,
) -> OrchestrationResult:
    categorised, abort_reason = _categorise(to_categorise, categoriser, store, resolve_needs_review)
    if abort_reason is not None:
        return OrchestrationResult(write_result=None, aborted=True, reason=abort_reason)

    result = pipeline.run(
        candidates=deterministic_candidates + categorised,
        store=store,
        through=through,
        archive=archive,
        dry_run=dry_run,
    )
    return OrchestrationResult(write_result=result, aborted=False)


def _categorise(
    to_categorise: list[RawTransaction],
    categoriser: Categoriser,
    store,
    resolve_needs_review: NeedsReviewResolver,
) -> tuple[list[Candidate], str | None]:
    if not to_categorise:
        return [], None

    logger.info("Categorising %d transaction(s)...", len(to_categorise))
    try:
        batch = categoriser.categorise(to_categorise, store.read_categories())
    except MalformedResponseError as exc:
        return [], str(exc)

    if len(batch.results) != len(to_categorise):
        return [], f"Expected {len(to_categorise)} categorisation results, got {len(batch.results)}"

    needs_review_count = sum(1 for result in batch.results if result.needs_review)
    if needs_review_count:
        logger.info("%d transaction(s) flagged Needs Review", needs_review_count)

    candidates = []
    for transaction, result in zip(to_categorise, batch.results):
        if result.needs_review:
            resolution = resolve_needs_review(transaction, result.reason)
            if resolution is None:
                continue  # resolved as not-to-be-recorded — drop, never written
            transaction_type, category = resolution
        else:
            transaction_type, category = result.type, result.category
        try:
            candidates.append(
                Candidate(
                    date=transaction.date,
                    amount=transaction.amount,
                    type=transaction_type,
                    category=category,
                    notes=transaction.notes,
                )
            )
        except ValueError as exc:
            return [], str(exc)

    return candidates, None
