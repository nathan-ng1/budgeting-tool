import logging
from dataclasses import dataclass
from datetime import date
from typing import Callable

from categorisation.history import Example, prompt_examples, split_history_matches
from categorisation.interface import Categoriser, MalformedResponseError
from statement_export import pipeline
from statement_export.parser import RawTransaction
from statement_export.pipeline import Archive
from transaction_log.categories import Category
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
    # How the file's Transactions were categorised (ADR-0026): straight from
    # the Transaction Log, sent to the backend, and - of those - flagged
    # Needs Review.
    history_match_count: int = 0
    backend_count: int = 0
    needs_review_count: int = 0


def run(
    deterministic_candidates: list[Candidate],
    to_categorise: list[RawTransaction],
    categoriser: Categoriser,
    store,
    through: date,
    resolve_needs_review: NeedsReviewResolver,
    archive: Archive | None = None,
    dry_run: bool = False,
    use_history_matches: bool = False,
) -> OrchestrationResult:
    # Read once, before anything is categorised, so a History Match never
    # depends on the order of rows within this same file.
    history = store.read_transactions()
    categories = store.read_categories()

    history_matches: list[Candidate] = []
    if use_history_matches:
        history_matches, to_categorise = split_history_matches(to_categorise, history, categories)
        if history_matches:
            logger.info("%d transaction(s) matched past categorisations", len(history_matches))

    counts = dict(history_match_count=len(history_matches), backend_count=len(to_categorise))
    categorised, needs_review_count, abort_reason = _categorise(
        to_categorise, categoriser, categories, prompt_examples(history), resolve_needs_review
    )
    if abort_reason is not None:
        return OrchestrationResult(
            write_result=None, aborted=True, reason=abort_reason, needs_review_count=needs_review_count, **counts
        )

    result = pipeline.run(
        candidates=deterministic_candidates + history_matches + categorised,
        store=store,
        through=through,
        archive=archive,
        dry_run=dry_run,
    )
    return OrchestrationResult(write_result=result, aborted=False, needs_review_count=needs_review_count, **counts)


def _categorise(
    to_categorise: list[RawTransaction],
    categoriser: Categoriser,
    categories: list[Category],
    examples: list[Example],
    resolve_needs_review: NeedsReviewResolver,
) -> tuple[list[Candidate], int, str | None]:
    """Returns (candidates, Needs Review count, abort reason or None)."""
    if not to_categorise:
        return [], 0, None

    logger.info("Categorising %d transaction(s)...", len(to_categorise))
    try:
        batch = categoriser.categorise(to_categorise, categories, examples)
    except MalformedResponseError as exc:
        return [], 0, str(exc)

    # Sourced from the live categories table (Issue #91), not the hardcoded
    # CATEGORIES_BY_TYPE dict - Candidate itself no longer validates its own
    # (Type, Category) pair, since only the store knows what's currently
    # valid, so this is the one place that check has to happen for a pair a
    # Needs Review resolution hands back.
    valid_pairs = {(c.type, c.name) for c in categories}

    if len(batch.results) != len(to_categorise):
        return [], 0, f"Expected {len(to_categorise)} categorisation results, got {len(batch.results)}"

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

        if (transaction_type, category) not in valid_pairs:
            return [], needs_review_count, f"Category {category!r} is not a valid {transaction_type} Category"

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
            return [], needs_review_count, str(exc)

    return candidates, needs_review_count, None
