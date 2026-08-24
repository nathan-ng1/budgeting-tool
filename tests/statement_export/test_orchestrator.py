from datetime import date
from pathlib import Path

from statement_export.orchestrator import run
from statement_export.pipeline import Archive
from statement_export.parser import RawTransaction


def make_transaction(**overrides):
    defaults = dict(date=date(2026, 8, 5), amount=-42.50, notes="Woolworths")
    defaults.update(overrides)
    return RawTransaction(**defaults)


def fail_if_called(transaction, reason):
    raise AssertionError("resolve_needs_review should not have been called")


def test_categorised_transactions_are_written_and_archived(
    fake_categoriser, fake_store, make_category_result, tmp_path: Path
):
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store()
    source = tmp_path / "ANZ_20260805.csv"
    source.write_text("irrelevant")
    processed_dir = tmp_path / "processed"

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction()],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        archive=Archive(source_path=source, processed_dir=processed_dir),
        resolve_needs_review=fail_if_called,
    )

    assert not result.aborted
    assert len(result.write_result.to_write) == 1
    assert result.write_result.to_write[0].type == "Expense"
    assert result.write_result.to_write[0].category == "Groceries"
    assert store.appended == result.write_result.to_write
    assert not source.exists()
    assert (processed_dir / "ANZ_20260805.csv").exists()


def test_deterministic_candidates_bypass_categorisation(fake_categoriser, fake_store, make_candidate):
    categoriser = fake_categoriser(results=[])
    store = fake_store()
    deterministic = [
        make_candidate(amount=-42.0, type="Expense", category="Beem Adjustment", notes="Beem in")
    ]

    result = run(
        deterministic_candidates=deterministic,
        to_categorise=[],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=fail_if_called,
    )

    assert categoriser.calls == []
    assert result.write_result.to_write == deterministic
    assert store.appended == deterministic


def test_needs_review_item_is_resolved_via_the_injected_resolver(
    fake_categoriser, fake_store, make_category_result
):
    categoriser = fake_categoriser(
        results=[make_category_result(needs_review=True, reason="not sure if this is a donation")]
    )
    store = fake_store()
    transaction = make_transaction(notes="Square Payment")

    def resolve(txn, reason):
        assert txn == transaction
        assert reason == "not sure if this is a donation"
        return ("Expense", "Donations & Giving")

    result = run(
        deterministic_candidates=[],
        to_categorise=[transaction],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=resolve,
    )

    assert not result.aborted
    assert result.write_result.to_write[0].type == "Expense"
    assert result.write_result.to_write[0].category == "Donations & Giving"


def test_malformed_categoriser_response_aborts_with_no_write_or_archive(
    fake_categoriser, fake_store, tmp_path: Path
):
    from categorisation.interface import MalformedResponseError

    categoriser = fake_categoriser(error=MalformedResponseError("bad output"))
    store = fake_store()
    source = tmp_path / "ANZ_20260805.csv"
    source.write_text("irrelevant")
    processed_dir = tmp_path / "processed"

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction()],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        archive=Archive(source_path=source, processed_dir=processed_dir),
        resolve_needs_review=fail_if_called,
    )

    assert result.aborted
    assert result.reason == "bad output"
    assert result.write_result is None
    assert store.appended == []
    assert source.exists()
    assert not (processed_dir / "ANZ_20260805.csv").exists()


def test_result_count_mismatch_aborts(fake_categoriser, fake_store):
    categoriser = fake_categoriser(results=[])  # zero results for one transaction
    store = fake_store()

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction()],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=fail_if_called,
    )

    assert result.aborted
    assert store.appended == []


def test_invalid_type_category_pair_from_resolver_aborts(fake_categoriser, fake_store, make_category_result):
    categoriser = fake_categoriser(results=[make_category_result(needs_review=True)])
    store = fake_store()

    def resolve(txn, reason):
        return ("Expense", "Salary")  # Salary is an Income Category, not an Expense one

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction()],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=resolve,
    )

    assert result.aborted
    assert store.appended == []


def test_dry_run_resolves_needs_review_but_skips_write_and_archive(
    fake_categoriser, fake_store, make_category_result, tmp_path: Path
):
    categoriser = fake_categoriser(results=[make_category_result(needs_review=True, reason="unsure")])
    store = fake_store()
    source = tmp_path / "ANZ_20260805.csv"
    source.write_text("irrelevant")
    processed_dir = tmp_path / "processed"
    resolver_calls = []

    def resolve(txn, reason):
        resolver_calls.append((txn, reason))
        return ("Expense", "Groceries")

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction()],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        archive=Archive(source_path=source, processed_dir=processed_dir),
        dry_run=True,
        resolve_needs_review=resolve,
    )

    assert not result.aborted
    assert len(resolver_calls) == 1
    assert len(result.write_result.to_write) == 1
    assert store.appended == []
    assert source.exists()
    assert not processed_dir.exists()


def test_already_logged_transaction_is_not_reappended(
    fake_categoriser, fake_store, make_category_result, make_existing_row
):
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(existing_rows=[make_existing_row(notes="Woolworths", amount=42.50)])

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction(notes="Woolworths", amount=-42.50)],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=fail_if_called,
    )

    assert result.write_result.to_write == []
    assert store.appended == []


def test_needs_review_resolver_returning_none_drops_the_transaction(
    fake_categoriser, fake_store, make_category_result
):
    # ADR-0016 - the resolver-returns-None "don't record this" escape hatch is
    # generic, not specific to a Bill Payment (positive-Amount card rows never
    # reach categorisation/Needs Review at all any more - they're dropped at
    # parse time).
    categoriser = fake_categoriser(
        results=[make_category_result(needs_review=True, reason="ambiguous transaction")]
    )
    store = fake_store()

    def resolve(txn, reason):
        return None  # user decided this transaction shouldn't be recorded

    result = run(
        deterministic_candidates=[],
        to_categorise=[make_transaction(notes="Square Payment")],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=resolve,
    )

    assert not result.aborted
    assert result.write_result.to_write == []
    assert store.appended == []


def test_due_recurring_transactions_are_merged_in(fake_categoriser, fake_store, make_rule):
    rule = make_rule(
        amount=5000.0,
        type="Income",
        category="Salary",
        notes="Employer Pty Ltd",
        frequency="Monthly",
        interval=1,
        day=5,
        start_date=date(2026, 8, 5),
    )
    categoriser = fake_categoriser(results=[])
    store = fake_store(recurring_rules=[rule])

    result = run(
        deterministic_candidates=[],
        to_categorise=[],
        categoriser=categoriser,
        store=store,
        through=date(2026, 8, 5),
        resolve_needs_review=fail_if_called,
    )

    assert not result.aborted
    assert len(result.write_result.to_write) == 1
    assert result.write_result.to_write[0].notes == "Employer Pty Ltd"
    assert categoriser.calls == []
