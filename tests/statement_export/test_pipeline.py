from datetime import date
from pathlib import Path

from statement_export.pipeline import Archive, run


def test_candidates_are_written_and_source_file_is_archived(
    make_candidate, fake_sheets_client, tmp_path: Path, recurring_config: Path
):
    client = fake_sheets_client()
    source = tmp_path / "ANZ_20260730.csv"
    source.write_text("irrelevant — pipeline doesn't re-read this file")
    processed_dir = tmp_path / "processed"
    candidates = [make_candidate(notes="Woolworths")]

    result = run(
        candidates=candidates,
        client=client,
        recurring_config_path=recurring_config,
        through=date(2026, 8, 5),
        archive=Archive(source_path=source, processed_dir=processed_dir),
    )

    assert result.to_write == candidates
    assert client.appended == candidates
    assert not source.exists()
    assert (processed_dir / "ANZ_20260730.csv").exists()


def test_already_logged_candidate_is_not_reappended(
    make_candidate, make_existing_row, fake_sheets_client, recurring_config: Path
):
    client = fake_sheets_client(existing_rows=[make_existing_row(notes="Woolworths")])
    candidate = make_candidate(notes="Woolworths")

    result = run(
        candidates=[candidate],
        client=client,
        recurring_config_path=recurring_config,
        through=date(2026, 8, 5),
    )

    assert result.to_write == []
    assert client.appended == []


def test_no_source_file_still_writes_due_recurring_transactions(
    fake_sheets_client, recurring_config: Path
):
    from openpyxl import load_workbook

    workbook = load_workbook(recurring_config)
    worksheet = workbook.active
    worksheet.append([5000.0, "Income", "Salary", "Employer Pty Ltd", "Monthly", 1, 5, date(2026, 8, 5), None])
    workbook.save(recurring_config)

    client = fake_sheets_client()

    result = run(
        candidates=[],
        client=client,
        recurring_config_path=recurring_config,
        through=date(2026, 8, 5),
    )

    assert len(result.to_write) == 1
    assert result.to_write[0].notes == "Employer Pty Ltd"
    assert client.appended == result.to_write


def test_no_source_path_given_does_not_touch_the_filesystem(
    make_candidate, fake_sheets_client, recurring_config: Path
):
    client = fake_sheets_client()

    result = run(
        candidates=[make_candidate()],
        client=client,
        recurring_config_path=recurring_config,
        through=date(2026, 8, 5),
    )

    assert len(result.to_write) == 1
