from pathlib import Path

import pytest

from sanitising.run import sanitise_inbox

FIXTURE_BYTES = (
    b"30/07/2026,-4.95,KFC NORTHMEAD             NORTHMEAD\n"
    b"27/07/2026,-35.19,ANTHROPIC* CLAUDE SUB     ANTHROPIC.COM\n"
    b"13/07/2026,2143.68,PAYMENT - THANKYOU\n"
)


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    path = tmp_path / "inbox"
    path.mkdir()
    return path


@pytest.fixture
def data(tmp_path: Path) -> Path:
    path = tmp_path / "data"
    path.mkdir()
    return path


def test_anz_export_moves_from_inbox_to_data_unchanged(inbox: Path, data: Path):
    (inbox / "ANZ_20260730.csv").write_bytes(FIXTURE_BYTES)

    sanitise_inbox(inbox, data)

    assert not (inbox / "ANZ_20260730.csv").exists()
    assert (data / "ANZ_20260730.csv").read_bytes() == FIXTURE_BYTES


def test_empty_inbox_is_a_noop(inbox: Path, data: Path):
    written = sanitise_inbox(inbox, data)

    assert written == []
    assert list(data.iterdir()) == []


def test_unrecognised_issuer_leaves_source_file_in_place(inbox: Path, data: Path):
    (inbox / "CHASE_20260730.csv").write_bytes(FIXTURE_BYTES)

    with pytest.raises(ValueError):
        sanitise_inbox(inbox, data)

    assert (inbox / "CHASE_20260730.csv").exists()
    assert list(data.iterdir()) == []


def test_unrecognised_issuer_stops_processing_leaving_later_files_untouched(inbox: Path, data: Path):
    (inbox / "ANZ_20260101.csv").write_bytes(FIXTURE_BYTES)
    (inbox / "BAD_20260102.csv").write_bytes(FIXTURE_BYTES)
    (inbox / "CBA_20260103.csv").write_bytes(FIXTURE_BYTES)

    with pytest.raises(ValueError):
        sanitise_inbox(inbox, data)

    assert not (inbox / "ANZ_20260101.csv").exists()
    assert (data / "ANZ_20260101.csv").read_bytes() == FIXTURE_BYTES
    assert (inbox / "BAD_20260102.csv").exists()
    assert (inbox / "CBA_20260103.csv").exists()
    assert not (data / "CBA_20260103.csv").exists()


def test_creates_data_dir_if_missing(inbox: Path, tmp_path: Path):
    data = tmp_path / "data"
    (inbox / "ANZ_20260730.csv").write_bytes(FIXTURE_BYTES)

    sanitise_inbox(inbox, data)

    assert (data / "ANZ_20260730.csv").read_bytes() == FIXTURE_BYTES
