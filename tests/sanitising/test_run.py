from pathlib import Path

import pytest

from sanitising.run import run

FIXTURE_CONTENT = (
    "30/07/2026,-4.95,KFC NORTHMEAD             NORTHMEAD\n"
    "27/07/2026,-35.19,ANTHROPIC* CLAUDE SUB     ANTHROPIC.COM\n"
    "13/07/2026,2143.68,PAYMENT - THANKYOU\n"
)


def test_anz_export_moves_from_inbox_to_data_unchanged(tmp_path: Path):
    inbox = tmp_path / "inbox"
    data = tmp_path / "data"
    inbox.mkdir()
    data.mkdir()
    (inbox / "ANZ_20260730.csv").write_text(FIXTURE_CONTENT)

    run(inbox, data)

    assert not (inbox / "ANZ_20260730.csv").exists()
    assert (data / "ANZ_20260730.csv").read_text() == FIXTURE_CONTENT


def test_empty_inbox_is_a_noop(tmp_path: Path):
    inbox = tmp_path / "inbox"
    data = tmp_path / "data"
    inbox.mkdir()
    data.mkdir()

    written = run(inbox, data)

    assert written == []
    assert list(data.iterdir()) == []


def test_unrecognised_issuer_leaves_source_file_in_place(tmp_path: Path):
    inbox = tmp_path / "inbox"
    data = tmp_path / "data"
    inbox.mkdir()
    data.mkdir()
    (inbox / "CHASE_20260730.csv").write_text(FIXTURE_CONTENT)

    with pytest.raises(ValueError):
        run(inbox, data)

    assert (inbox / "CHASE_20260730.csv").exists()
    assert list(data.iterdir()) == []
