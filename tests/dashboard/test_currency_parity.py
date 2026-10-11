"""The server's CURRENCY_IDS and the frontend's curated list must name the same
Display Currency entries (ADR-0027): a drift either lets the picker offer an
entry the server rejects, or the server accept one the picker cannot format."""

import re
from pathlib import Path

from dashboard.settings import CURRENCY_IDS, DEFAULTS

CURRENCIES_JS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "currencies.js"


def frontend_currency_ids() -> list[str]:
    return re.findall(r'\{\s*id:\s*"([^"]+)"', CURRENCIES_JS.read_text(encoding="utf-8"))


def test_frontend_and_server_offer_the_same_currency_ids():
    frontend = frontend_currency_ids()

    assert len(frontend) == len(set(frontend)), "currencies.js lists an id twice"
    assert set(frontend) == CURRENCY_IDS, (
        f"only in currencies.js: {sorted(set(frontend) - CURRENCY_IDS)}; "
        f"only in settings.py: {sorted(CURRENCY_IDS - set(frontend))}"
    )


def test_the_default_currency_is_an_available_entry():
    assert DEFAULTS["currency"] in CURRENCY_IDS
    assert DEFAULTS["currency"] in frontend_currency_ids()
