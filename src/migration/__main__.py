from pathlib import Path

from dotenv import load_dotenv

from database import store as database_store
from migration.run import migrate

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSACTION_LOG_CSV = REPO_ROOT / ".data" / "migration" / "transaction_log_export.csv"
RECURRING_CONFIG_XLSX = REPO_ROOT / "config" / "recurring-transactions.xlsx"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")

    if not TRANSACTION_LOG_CSV.exists():
        raise SystemExit(
            f"No historical Transaction Log export found at {TRANSACTION_LOG_CSV} - "
            "export the live Google Sheet's Transaction Log to that path first."
        )

    result = migrate(
        transaction_log_csv=TRANSACTION_LOG_CSV,
        recurring_config_xlsx=RECURRING_CONFIG_XLSX,
        store=database_store.connect(),
    )

    print(f"Transactions: wrote {len(result.transactions_written)}, skipped {len(result.transactions_skipped)} (already present)")
    print(f"Recurring rules: wrote {len(result.recurring_rules_written)}, skipped {len(result.recurring_rules_skipped)} (already present)")


if __name__ == "__main__":
    main()
