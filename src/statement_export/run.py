import re
from datetime import date
from pathlib import Path

from beem import parser as beem_parser
from categorisation.interface import Categoriser
from statement_export import parser as statement_export_parser
from statement_export.orchestrator import NeedsReviewResolver, OrchestrationResult
from statement_export.orchestrator import run as orchestrate
from statement_export.pipeline import Archive

STATEMENT_EXPORT_PATTERN = re.compile(r"^(?P<issuer>[A-Za-z]+)_\d{8}\.csv$")


def process_data_dir(
    data_dir: Path,
    categoriser: Categoriser,
    client,
    recurring_config_path: Path,
    resolve_needs_review: NeedsReviewResolver,
    dry_run: bool = False,
) -> list[tuple[Path, OrchestrationResult]]:
    processed_dir = data_dir / "processed"
    results = []

    for source in sorted(data_dir.glob("*.csv")):
        match = STATEMENT_EXPORT_PATTERN.match(source.name)
        if not match:
            raise ValueError(
                f"'{source.name}' doesn't match the Statement Export filename "
                "convention '{Issuer}_{yyyymmdd}.csv'"
            )

        if match.group("issuer") == "Beem":
            deterministic, to_categorise = beem_parser.categorise(beem_parser.parse(source))
        else:
            deterministic, to_categorise = [], statement_export_parser.parse(source)

        through_dates = [t.date for t in deterministic] + [t.date for t in to_categorise]
        through = max(through_dates) if through_dates else date.today()

        result = orchestrate(
            deterministic_candidates=deterministic,
            to_categorise=to_categorise,
            categoriser=categoriser,
            client=client,
            recurring_config_path=recurring_config_path,
            through=through,
            resolve_needs_review=resolve_needs_review,
            archive=Archive(source_path=source, processed_dir=processed_dir),
            dry_run=dry_run,
        )
        results.append((source, result))

    return results
