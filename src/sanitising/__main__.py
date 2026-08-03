import os
from pathlib import Path

from dotenv import load_dotenv

from sanitising.run import sanitise_inbox

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / ".data"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    transactions_inbox = Path(os.environ["TRANSACTIONS_INBOX"])
    written = sanitise_inbox(transactions_inbox, DATA_DIR)
    for path in written:
        print(f"Sanitised -> {path}")


if __name__ == "__main__":
    main()
