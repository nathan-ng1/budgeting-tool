"""The Split savings allocation (Goals spec section 9).

Pure money maths: a total, in cents, divided across Goals by percentage, with
whatever is left of 100% as the remainder. Largest-remainder method, so the
rows always sum exactly to the total and the same inputs always give the same
rows. Whole cents (ints) and exact fractions throughout - no float drift.
"""

from fractions import Fraction

HUNDRED = Fraction(100)


def allocate(total_cents: int, percents: list[float]) -> tuple[list[int], int]:
    """The cents each Goal's percentage takes, in order, and the remainder's.

    Every share (the Goals and the remainder, which is 100% minus the Goals)
    is floored to the cent; the cents left over then go one each to the shares
    with the largest fractional parts, ties broken by position (the remainder
    last). Raises ValueError for a negative percentage or a sum above 100%.
    """
    exact = [Fraction(str(percent)) for percent in percents]
    if any(percent < 0 for percent in exact):
        raise ValueError("A percentage can't be negative")
    if sum(exact) > HUNDRED:
        raise ValueError("The percentages add up to more than 100%")

    shares = [total_cents * percent / HUNDRED for percent in [*exact, HUNDRED - sum(exact)]]
    cents = [int(share) for share in shares]  # floor: every share is non-negative

    leftover = total_cents - sum(cents)
    by_largest_fraction = sorted(range(len(shares)), key=lambda i: (-(shares[i] - cents[i]), i))
    for index in by_largest_fraction[:leftover]:
        cents[index] += 1

    return cents[:-1], cents[-1]
