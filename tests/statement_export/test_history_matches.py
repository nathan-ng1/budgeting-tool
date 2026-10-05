"""History Matches and prompt examples (Issue #159, ADR-0026), tested through
statement_export.run.process_data_dir - what gets written, what the
categoriser is asked (and with which examples), what reaches Needs Review,
and the summary counts.
"""

from datetime import date, timedelta
from pathlib import Path

from categorisation.interface import MalformedResponseError
from statement_export.run import process_data_dir


def fail_if_called(transaction, reason):
    raise AssertionError("resolve_needs_review should not have been called")


class FailingCategoriser:
    def categorise(self, transactions, categories, examples=()):
        raise AssertionError("the categoriser should not have been called")


def write_export(tmp_path: Path, name: str, lines: list[str]) -> Path:
    data_dir = tmp_path / ".data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / name).write_text("".join(f"{line}\n" for line in lines))
    return data_dir


def history_row(make_transaction, notes, type="Expense", category="Transport", day=1, **overrides):
    return make_transaction(notes=notes, type=type, category=category, date=date(2026, 7, day), **overrides)


def test_card_transaction_matching_settled_history_is_written_without_backend_or_review(
    fake_store, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-4.20,TRANSPORTFORNSW OPAL      CHIPPENDALE"])
    store = fake_store(
        transactions=[
            history_row(make_transaction, "TRANSPORTFORNSW OPAL      CHIPPENDALE", day=1, id=1),
            history_row(make_transaction, "TRANSPORTFORNSW OPAL      CHIPPENDALE", day=2, id=2),
        ]
    )

    [(_, result)] = process_data_dir(
        data_dir=data_dir,
        categoriser=FailingCategoriser(),
        store=store,
        resolve_needs_review=fail_if_called,
    )

    assert not result.aborted
    [written] = store.appended
    assert (written.type, written.category, written.notes) == (
        "Expense",
        "Transport",
        "TRANSPORTFORNSW OPAL      CHIPPENDALE",
    )
    assert (data_dir / "processed" / "ANZ_20260805.csv").exists()


def test_store_number_case_and_spacing_variants_still_match(fake_store, make_transaction, tmp_path: Path):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-12.00,subwayclarencest25812 sydney"])
    store = fake_store(
        transactions=[
            history_row(make_transaction, "SUBWAYCLARENCEST25739     SYDNEY", category="Dining & Takeaway"),
        ]
    )

    [(_, result)] = process_data_dir(
        data_dir=data_dir, categoriser=FailingCategoriser(), store=store, resolve_needs_review=fail_if_called
    )

    [written] = result.write_result.to_write
    assert written.category == "Dining & Takeaway"


def test_differently_worded_notes_go_to_the_categoriser(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-30.00,Woolworths Metro (West Pennant Hills)"])
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(transactions=[history_row(make_transaction, "Woolworths (Carlingford)", category="Groceries")])

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    [call] = categoriser.calls
    assert [t.notes for t in call] == ["Woolworths Metro (West Pennant Hills)"]


def test_a_key_whose_history_disagrees_goes_to_the_categoriser(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-50.00,Gym"])
    categoriser = fake_categoriser(results=[make_category_result(category="Subscriptions")])
    store = fake_store(
        transactions=[
            history_row(make_transaction, "Gym", category="Subscriptions", day=1, id=1),
            history_row(make_transaction, "Gym", category="Health & Medical", day=2, id=2),
        ]
    )

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    [call] = categoriser.calls
    assert [t.notes for t in call] == ["Gym"]


def test_same_category_name_under_a_different_type_counts_as_disagreement(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-50.00,Mystery"])
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(
        transactions=[
            history_row(make_transaction, "Mystery", type="Expense", category="Groceries", id=1),
            history_row(make_transaction, "Mystery", type="Income", category="Groceries", id=2),
        ]
    )

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    assert len(categoriser.calls) == 1


def test_beem_adjustment_history_rows_create_neither_a_match_nor_a_conflict(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(
        tmp_path, "ANZ_20260805.csv", ["05/08/2026,-20.00,Dinner Club", "06/08/2026,-9.00,Coffee Spot"]
    )
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(
        transactions=[
            # Only a Beem Adjustment row -> no match.
            history_row(make_transaction, "Dinner Club", category="Beem Adjustment", amount=-20.0, id=1),
            # A settled row plus a Beem Adjustment row -> still a match.
            history_row(make_transaction, "Coffee Spot", category="Dining & Takeaway", id=2),
            history_row(make_transaction, "Coffee Spot", category="Beem Adjustment", amount=-9.0, id=3),
        ]
    )

    [(_, result)] = process_data_dir(
        data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called
    )

    [call] = categoriser.calls
    assert [t.notes for t in call] == ["Dinner Club"]
    coffee = next(c for c in result.write_result.to_write if c.notes == "Coffee Spot")
    assert coffee.category == "Dining & Takeaway"


def test_outgoing_beem_row_with_matching_history_still_goes_to_the_categoriser_with_examples(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "Beem_20260805.csv", ["05/08/2026,-15.00,pickleball"])
    categoriser = fake_categoriser(results=[make_category_result(category="Entertainment & Leisure")])
    store = fake_store(
        transactions=[history_row(make_transaction, "pickleball", category="Entertainment & Leisure")]
    )

    [(_, result)] = process_data_dir(
        data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called
    )

    [call] = categoriser.calls
    assert [t.notes for t in call] == ["pickleball"]
    assert result.history_match_count == 0
    [examples] = categoriser.examples
    assert [(e.notes_key, e.pairs) for e in examples] == [
        ("pickleball", (("Expense", "Entertainment & Leisure"),))
    ]


def test_empty_normalised_notes_never_match_or_become_examples(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-10.00,12345"])
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(transactions=[history_row(make_transaction, "999 000", category="Groceries")])

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    assert len(categoriser.calls) == 1
    assert categoriser.examples == [[]]


def test_a_settled_pair_no_longer_in_the_categories_table_is_not_a_match(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-10.00,Old Shop"])
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(transactions=[history_row(make_transaction, "Old Shop", category="Retired Category")])

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    assert len(categoriser.calls) == 1


def test_settled_savings_history_is_never_a_history_match(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    # Savings is manual-entry only (ADR-0022): never assigned from a
    # Statement Export, even by repeating a past categorisation.
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-100.00,Vanguard Invest"])
    categoriser = fake_categoriser(results=[make_category_result()])
    store = fake_store(
        transactions=[history_row(make_transaction, "Vanguard Invest", type="Savings", category="Investments")]
    )

    [(_, result)] = process_data_dir(
        data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called
    )

    [call] = categoriser.calls
    assert [t.notes for t in call] == ["Vanguard Invest"]
    assert result.history_match_count == 0


def test_a_file_of_only_history_matches_and_bill_payments_never_calls_the_categoriser(
    fake_store, make_transaction, tmp_path: Path
):
    data_dir = write_export(
        tmp_path,
        "ANZ_20260805.csv",
        ["05/08/2026,-4.20,OPAL 123", "06/08/2026,500.00,PAYMENT THANK YOU", "07/08/2026,-4.20,OPAL 456"],
    )
    store = fake_store(transactions=[history_row(make_transaction, "OPAL 999")])

    [(_, result)] = process_data_dir(
        data_dir=data_dir, categoriser=FailingCategoriser(), store=store, resolve_needs_review=fail_if_called
    )

    assert not result.aborted
    assert len(store.appended) == 2
    assert (result.history_match_count, result.backend_count, result.needs_review_count) == (2, 0, 0)


def test_history_matches_only_use_the_log_as_it_was_when_the_file_started(
    fake_categoriser, fake_store, make_category_result, tmp_path: Path
):
    # Two rows with the same key in one file and no prior history: neither is
    # a History Match, regardless of order - both go to the backend.
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-4.20,OPAL 1", "06/08/2026,-4.20,OPAL 2"])
    categoriser = fake_categoriser(results=[make_category_result(category="Transport")] * 2)

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=fake_store(), resolve_needs_review=fail_if_called)

    [call] = categoriser.calls
    assert len(call) == 2


def test_categoriser_receives_examples_capped_at_200_most_recent_excluding_beem_adjustment(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-10.00,Brand New Shop"])
    categoriser = fake_categoriser(results=[make_category_result()])
    history = [
        make_transaction(
            id=i,
            notes=f"Shop {chr(65 + i // 26)}{chr(65 + i % 26)}",
            category="Groceries",
            date=date(2026, 1, 1) + timedelta(days=i),
        )
        for i in range(250)
    ]
    history.append(
        make_transaction(id=999, notes="Beem thing", category="Beem Adjustment", amount=-5.0, date=date(2027, 1, 1))
    )
    store = fake_store(transactions=history)

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    [examples] = categoriser.examples
    keys = [e.notes_key for e in examples]
    assert len(keys) == 200
    assert "beem thing" not in keys
    # The 200 most recently seen keys: the oldest 50 (i < 50) are dropped.
    assert "shop ab" not in keys  # i = 1
    assert "shop jp" in keys  # i = 249


def test_a_disagreeing_key_appears_in_examples_with_every_pair(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-50.00,Gym"])
    categoriser = fake_categoriser(results=[make_category_result(category="Subscriptions")])
    store = fake_store(
        transactions=[
            history_row(make_transaction, "Gym", category="Subscriptions", day=1, id=1),
            history_row(make_transaction, "GYM", category="Health & Medical", day=2, id=2),
        ]
    )

    process_data_dir(data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called)

    [[example]] = categoriser.examples
    assert example.notes_key == "gym"
    assert set(example.pairs) == {("Expense", "Subscriptions"), ("Expense", "Health & Medical")}


def test_summary_counts_history_matches_backend_and_needs_review(
    fake_categoriser, fake_store, make_category_result, make_transaction, tmp_path: Path
):
    data_dir = write_export(
        tmp_path,
        "ANZ_20260805.csv",
        ["05/08/2026,-4.20,OPAL 1", "06/08/2026,-10.00,New Place", "07/08/2026,-11.00,Other Place"],
    )
    categoriser = fake_categoriser(
        results=[make_category_result(), make_category_result(needs_review=True, reason="unsure")]
    )
    store = fake_store(transactions=[history_row(make_transaction, "OPAL 2")])

    [(_, result)] = process_data_dir(
        data_dir=data_dir,
        categoriser=categoriser,
        store=store,
        resolve_needs_review=lambda transaction, reason: ("Expense", "Shopping & Retail"),
    )

    assert (result.history_match_count, result.backend_count, result.needs_review_count) == (1, 2, 1)


def test_dry_run_reports_the_same_history_matches_without_writing(fake_store, make_transaction, tmp_path: Path):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-4.20,OPAL 1"])
    store = fake_store(transactions=[history_row(make_transaction, "OPAL 2")])

    [(source, result)] = process_data_dir(
        data_dir=data_dir,
        categoriser=FailingCategoriser(),
        store=store,
        resolve_needs_review=fail_if_called,
        dry_run=True,
    )

    [would_write] = result.write_result.to_write
    assert would_write.category == "Transport"
    assert result.history_match_count == 1
    assert store.appended == []
    assert source.exists()


def test_a_malformed_backend_response_writes_no_history_matches_either(
    fake_categoriser, fake_store, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-4.20,OPAL 1", "06/08/2026,-9.00,New Place"])
    categoriser = fake_categoriser(error=MalformedResponseError("bad output"))
    store = fake_store(transactions=[history_row(make_transaction, "OPAL 2")])

    [(source, result)] = process_data_dir(
        data_dir=data_dir, categoriser=categoriser, store=store, resolve_needs_review=fail_if_called
    )

    assert result.aborted
    assert result.history_match_count == 1
    assert store.appended == []
    assert source.exists()


def test_a_history_match_already_in_the_log_is_deduped(
    fake_store, make_existing_row, make_transaction, tmp_path: Path
):
    data_dir = write_export(tmp_path, "ANZ_20260805.csv", ["05/08/2026,-4.20,OPAL 1"])
    store = fake_store(
        existing_rows=[make_existing_row(date=date(2026, 8, 5), amount=4.20, notes="OPAL 1")],
        transactions=[
            history_row(make_transaction, "OPAL 1", day=1, id=1),
            make_transaction(id=2, notes="OPAL 1", category="Transport", date=date(2026, 8, 5), amount=4.20),
        ],
    )

    [(_, result)] = process_data_dir(
        data_dir=data_dir, categoriser=FailingCategoriser(), store=store, resolve_needs_review=fail_if_called
    )

    assert result.write_result.to_write == []
    assert len(result.write_result.skipped) == 1
