import logging
import re
from datetime import date
from pathlib import Path

from beem import parser as beem_parser
from categorisation.interface import Categoriser
from statement_export import parser as statement_export_parser
from statement_export.orchestrator import NeedsReviewResolver, OrchestrationResult
from statement_export.orchestrator import run as orchestrate
from statement_export.pipeline import Archive

logger = logging.getLogger(__name__)

STATEMENT_EXPORT_PATTERN = re.compile(r"^(?P<issuer>[A-Za-z]+)_\d{8}\.csv$")


def process_data_dir(
    data_dir: Path,
    categoriser: Categoriser,
    store,
    resolve_needs_review: NeedsReviewResolver,
    dry_run: bool = False,
) -> list[tuple[Path, OrchestrationResult]]:
    processed_dir = data_dir / "processed"
    sources = sorted(data_dir.glob("*.csv"))
    logger.info("Found %d outstanding file(s) in .data", len(sources))

    results = []

    for source in sources:
        match = STATEMENT_EXPORT_PATTERN.match(source.name)
        if not match:
            raise ValueError(
                f"'{source.name}' doesn't match the Statement Export filename "
                "convention '{Issuer}_{yyyymmdd}.csv'"
            )
        issuer = match.group("issuer")
        logger.info("Processing %s (issuer: %s)", source.name, issuer)

        if issuer == "Beem":
            deterministic, to_categorise = beem_parser.categorise(beem_parser.parse(source))
        else:
            deterministic, to_categorise = [], statement_export_parser.parse(source)
        logger.info(
            "%s: %d deterministic candidate(s), %d transaction(s) to categorise",
            source.name,
            len(deterministic),
            len(to_categorise),
        )

        through_dates = [t.date for t in deterministic] + [t.date for t in to_categorise]
        through = max(through_dates) if through_dates else date.today()

        result = orchestrate(
            deterministic_candidates=deterministic,
            to_categorise=to_categorise,
            categoriser=categoriser,
            store=store,
            through=through,
            resolve_needs_review=resolve_needs_review,
            archive=Archive(source_path=source, processed_dir=processed_dir),
            dry_run=dry_run,
        )
        if result.aborted:
            logger.info("%s: aborted - %s", source.name, result.reason)
        else:
            verb = "would write" if dry_run else "wrote"
            logger.info(
                "%s: %s %d row(s), %d already logged",
                source.name,
                verb,
                len(result.write_result.to_write),
                len(result.write_result.skipped),
            )
        results.append((source, result))

    return results
