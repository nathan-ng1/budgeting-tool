from calendar import monthrange
from dataclasses import dataclass
from datetime import date

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class RecurringRule:
    amount: float
    category: str
    sub_category: str
    notes: str
    frequency: str
    interval: int
    day: int | str
    start_date: date
    end_date: date | None = None

    def __post_init__(self):
        if self.frequency not in ("Weekly", "Monthly"):
            raise ValueError(f"Frequency must be 'Weekly' or 'Monthly', got {self.frequency!r}")
        if self.interval < 1:
            raise ValueError(f"Interval must be >= 1, got {self.interval!r}")

        if self.frequency == "Weekly":
            if self.day not in WEEKDAY_NAMES:
                raise ValueError(f"Day must be a weekday name for a Weekly rule, got {self.day!r}")
            start_weekday = WEEKDAY_NAMES[self.start_date.weekday()]
            if start_weekday != self.day:
                raise ValueError(
                    f"Start Date {self.start_date} is a {start_weekday}, but Day says {self.day!r}"
                )
        else:
            if not isinstance(self.day, int) or not (1 <= self.day <= 31):
                raise ValueError(f"Day must be an integer between 1 and 31 for a Monthly rule, got {self.day!r}")
            last_day_of_start_month = monthrange(self.start_date.year, self.start_date.month)[1]
            expected_start_day = min(self.day, last_day_of_start_month)
            if self.start_date.day != expected_start_day:
                raise ValueError(
                    f"Start Date {self.start_date} doesn't fall on Day {self.day!r} "
                    f"(expected day {expected_start_day} for that month)"
                )

        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError(f"End Date {self.end_date} can't be before Start Date {self.start_date}")


@dataclass(frozen=True)
class Occurrence:
    date: date
    amount: float
    category: str
    sub_category: str
    notes: str
