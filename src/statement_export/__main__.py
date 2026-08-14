import sys
from pathlib import Path

from dotenv import load_dotenv

from categorisation import factory
from statement_export.run import process_data_dir
from statement_export.terminal_review import TerminalReviewer
from transaction_log import sheets_client

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / ".data"
RECURRING_CONFIG_PATH = REPO_ROOT / "config" / "recurring-transactions.xlsx"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    dry_run = "--dry-run" in sys.argv[1:]

    results = process_data_dir(
        data_dir=DATA_DIR,
        categoriser=factory.connect(),
        client=sheets_client.connect(),
        recurring_config_path=RECURRING_CONFIG_PATH,
        resolve_needs_review=TerminalReviewer(),
        dry_run=dry_run,
    )

    if not results:
        print("Nothing outstanding in .data\\ - nothing to process.")
        return

    any_aborted = False
    for source, result in results:
        if result.aborted:
            any_aborted = True
            print(f"Aborted processing {source.name}: {result.reason}")
            continue

        verb = "Would write" if dry_run else "Wrote"
        print(f"\n{verb} {len(result.write_result.to_write)} row(s) for {source.name}:")
        for candidate in result.write_result.to_write:
            print(f"  {candidate.date}  {candidate.amount:>10.2f}  {candidate.category} / {candidate.sub_category}  {candidate.notes}")
        if result.write_result.skipped:
            print(f"  ({len(result.write_result.skipped)} already logged, skipped)")

    if any_aborted:
        sys.exit(1)


if __name__ == "__main__":
    main()
