import csv
from pathlib import Path

from sanitising import __main__ as sanitising_main

BEEM_FIXTURE = (
    "Date/Time,Type,Reference,Amount,Payer,Recipient,Message\n"
    "30/07/2026 10:00,PAYMENT,REF001,$15.50,nathan_ng,jane_doe,mahjong + coke\n"
)


def test_main_reads_beem_username_from_dotenv_file(monkeypatch, tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    data_dir = tmp_path / "data"
    (tmp_path / ".env").write_text(
        f"BEEM_USERNAME=nathan_ng\nTRANSACTIONS_INBOX={inbox}\n"
    )
    (inbox / "Beem_20260730.csv").write_text(BEEM_FIXTURE)

    monkeypatch.delenv("BEEM_USERNAME", raising=False)
    monkeypatch.delenv("TRANSACTIONS_INBOX", raising=False)
    monkeypatch.setattr(sanitising_main, "DATA_DIR", data_dir)
    monkeypatch.setattr(sanitising_main, "REPO_ROOT", tmp_path)

    try:
        sanitising_main.main()

        with open(data_dir / "Beem_20260730.csv", newline="") as f:
            rows = list(csv.reader(f))
        assert rows == [["30/07/2026", "-15.5", "mahjong + coke"]]
    finally:
        # load_dotenv() writes straight to os.environ, bypassing monkeypatch's
        # tracking, so its own teardown won't undo this — clean up explicitly
        # or these leak into the rest of the test session.
        monkeypatch.delenv("BEEM_USERNAME", raising=False)
        monkeypatch.delenv("TRANSACTIONS_INBOX", raising=False)
