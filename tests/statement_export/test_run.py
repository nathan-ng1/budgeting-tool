from datetime import date
from pathlib import Path

import pytest

from categorisation.interface import MalformedResponseError
from statement_export.run import process_data_dir


def fail_if_called(transaction, reason):
    raise AssertionError("resolve_needs_review should not have been called")


def test_card_export_is_categorised_written_and_archived(
    fake_categoriser, fake_sheets_client, make_category_result, tmp_path: Path, recurring_config: Path
):
    data_dir = tmp_path / ".data"
    data_dir.mkdir()
    (data_dir / "ANZ_20260805.csv").write_text("05/08/2026,-42.50,Woolworths\n")

    categoriser = fake_categoriser(results=[make_category_result()])
    client = fake_sheets_client()

    results = process_data_dir(
        data_dir=data_dir,
        categoriser=categoriser,
        client=client,
        recurring_config_path=recurring_config,
        resolve_needs_review=fail_if_called,
    )

    [(source, result)] = results
    assert source.name == "ANZ_20260805.csv"
    assert not result.aborted
    assert len(result.write_result.to_write) == 1
    assert client.appended == result.write_result.to_write
    assert not source.exists()
    assert (data_dir / "processed" / "ANZ_20260805.csv").exists()


def test_beem_report_splits_deterministic_income_from_categorised_outgoings(
    fake_categoriser, fake_sheets_client, make_category_result, tmp_path: Path, recurring_config: Path
):
    data_dir = tmp_path / ".data"
    data_dir.mkdir()
    (data_dir / "Beem_20260805.csv").write_text(
        "05/08/2026,15.00,From Alex\n06/08/2026,-9.00,Coffee split\n"
    )

    categoriser = fake_categoriser(results=[make_category_result(category="Expenses", sub_category="Dining & Takeaway")])
    client = fake_sheets_client()

    results = process_data_dir(
        data_dir=data_dir,
        categoriser=categoriser,
        client=client,
        recurring_config_path=recurring_config,
        resolve_needs_review=fail_if_called,
    )

    [(_, result)] = results
    assert not result.aborted
    written = result.write_result.to_write
    assert len(written) == 2
    income = next(c for c in written if c.notes == "From Alex")
    assert (income.category, income.sub_category) == ("Income", "Beem Adjustment")
    outgoing = next(c for c in written if c.notes == "Coffee split")
    assert (outgoing.category, outgoing.sub_category) == ("Expenses", "Dining & Takeaway")
    [categorised_call] = categoriser.calls
    assert [t.notes for t in categorised_call] == ["Coffee split"]


def test_one_files_malformed_response_aborts_only_that_file(
    fake_categoriser, fake_sheets_client, make_category_result, tmp_path: Path, recurring_config: Path
):
    data_dir = tmp_path / ".data"
    data_dir.mkdir()
    (data_dir / "ANZ_20260805.csv").write_text("05/08/2026,-42.50,Woolworths\n")
    (data_dir / "NAB_20260805.csv").write_text("05/08/2026,-10.00,Coles\n")

    class RoutingCategoriser:
        def categorise(self, transactions, category_list):
            if transactions[0].notes == "Woolworths":
                raise MalformedResponseError("bad output")
            return fake_categoriser(results=[make_category_result()]).categorise(transactions, category_list)

    client = fake_sheets_client()

    results = process_data_dir(
        data_dir=data_dir,
        categoriser=RoutingCategoriser(),
        client=client,
        recurring_config_path=recurring_config,
        resolve_needs_review=fail_if_called,
    )

    by_name = {source.name: result for source, result in results}
    assert by_name["ANZ_20260805.csv"].aborted
    assert not by_name["NAB_20260805.csv"].aborted
    assert (data_dir / "ANZ_20260805.csv").exists()
    assert not (data_dir / "NAB_20260805.csv").exists()
    assert (data_dir / "processed" / "NAB_20260805.csv").exists()


def test_unrecognised_filename_raises(fake_categoriser, fake_sheets_client, tmp_path: Path, recurring_config: Path):
    data_dir = tmp_path / ".data"
    data_dir.mkdir()
    (data_dir / "not-a-statement-export.csv").write_text("irrelevant")

    with pytest.raises(ValueError):
        process_data_dir(
            data_dir=data_dir,
            categoriser=fake_categoriser(results=[]),
            client=fake_sheets_client(),
            recurring_config_path=recurring_config,
            resolve_needs_review=fail_if_called,
        )


def test_dry_run_does_not_write_or_archive(
    fake_categoriser, fake_sheets_client, make_category_result, tmp_path: Path, recurring_config: Path
):
    data_dir = tmp_path / ".data"
    data_dir.mkdir()
    (data_dir / "ANZ_20260805.csv").write_text("05/08/2026,-42.50,Woolworths\n")

    categoriser = fake_categoriser(results=[make_category_result()])
    client = fake_sheets_client()

    results = process_data_dir(
        data_dir=data_dir,
        categoriser=categoriser,
        client=client,
        recurring_config_path=recurring_config,
        resolve_needs_review=fail_if_called,
        dry_run=True,
    )

    [(source, result)] = results
    assert not result.aborted
    assert len(result.write_result.to_write) == 1
    assert client.appended == []
    assert source.exists()
    assert not (data_dir / "processed").exists()


def test_no_files_returns_empty_list(fake_categoriser, fake_sheets_client, tmp_path: Path, recurring_config: Path):
    data_dir = tmp_path / ".data"
    data_dir.mkdir()

    results = process_data_dir(
        data_dir=data_dir,
        categoriser=fake_categoriser(results=[]),
        client=fake_sheets_client(),
        recurring_config_path=recurring_config,
        resolve_needs_review=fail_if_called,
    )

    assert results == []
