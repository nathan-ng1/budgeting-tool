"""The Split savings allocation (Goals spec section 9): a total in cents divided
by percentages with the largest-remainder method. Pure maths, no Database."""

import pytest

from goals.split import allocate


def test_a_partial_split_leaves_the_rest_as_the_remainder():
    goals, remainder = allocate(100_000, [50, 25])

    assert goals == [50_000, 25_000]
    assert remainder == 25_000


def test_exact_shares_need_no_rounding():
    goals, remainder = allocate(100, [33.33, 33.33, 33.34])

    assert goals == [33, 33, 34]
    assert remainder == 0


def test_leftover_cents_go_to_the_largest_fractional_parts_and_rows_sum_to_the_total():
    # 1001c at 33.33% = 333.633c each (floor 333); the remainder's 0.01% is
    # 0.1001c. Two cents are left over: the first two equal .633 parts win
    # on the tie, in order; the smaller .1001 remainder gets none.
    goals, remainder = allocate(1_001, [33.33, 33.33, 33.33])

    assert goals == [334, 334, 333]
    assert remainder == 0
    assert sum(goals) + remainder == 1_001


def test_the_remainder_competes_for_leftover_cents_like_a_goal():
    # 10c at 33%: 3.3c each, remainder 34% = 3.4c. Floors 3+3+3 = 9, one cent
    # left, and the remainder's .4 is the largest fraction.
    goals, remainder = allocate(10, [33, 33])

    assert goals == [3, 3]
    assert remainder == 4


def test_the_same_inputs_always_give_the_same_rows():
    first = allocate(12_345, [10, 20, 30])

    assert all(allocate(12_345, [10, 20, 30]) == first for _ in range(5))


def test_exactly_one_hundred_percent_leaves_no_remainder():
    goals, remainder = allocate(999, [60, 40])

    assert remainder == 0
    assert sum(goals) == 999


def test_a_tiny_share_can_round_to_zero_cents():
    goals, remainder = allocate(10, [1, 99])

    assert goals == [0, 10]
    assert remainder == 0


def test_more_than_one_hundred_percent_is_refused():
    with pytest.raises(ValueError, match="100"):
        allocate(1_000, [60, 40.01])


def test_a_negative_percentage_is_refused():
    with pytest.raises(ValueError, match="negative"):
        allocate(1_000, [-5, 10])
