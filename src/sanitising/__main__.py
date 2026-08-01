from pathlib import Path

from sanitising.run import run

TRANSACTIONS_INBOX = Path(r"D:\natha\Documents\Transactions")
DATA_DIR = Path(__file__).resolve().parents[2] / ".data"


def main() -> None:
    written = run(TRANSACTIONS_INBOX, DATA_DIR)
    for path in written:
        print(f"Sanitised -> {path}")


if __name__ == "__main__":
    main()
