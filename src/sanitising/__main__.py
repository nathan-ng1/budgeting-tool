from pathlib import Path

from dotenv import load_dotenv

from sanitising.run import sanitise_inbox

TRANSACTIONS_INBOX = Path(r"D:\natha\Documents\Transactions")
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / ".data"


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    written = sanitise_inbox(TRANSACTIONS_INBOX, DATA_DIR)
    for path in written:
        print(f"Sanitised -> {path}")


if __name__ == "__main__":
    main()
