from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BudgetSuggestion:
    """The one standing Budget Suggestion write-up - regenerating it replaces
    whatever was stored before, no history kept (ADR-0014)."""

    write_up: str
    generated_at: datetime
