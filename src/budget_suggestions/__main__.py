import logging
from pathlib import Path

from dotenv import load_dotenv

from advisor import factory
from budget_suggestions.run import generate_budget_suggestion
from database import store as database_store

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

    load_dotenv(REPO_ROOT / ".env")

    write_up = generate_budget_suggestion(store=database_store.connect(), advisor=factory.connect())

    print("Budget Suggestion regenerated:\n")
    print(write_up)


if __name__ == "__main__":
    main()
