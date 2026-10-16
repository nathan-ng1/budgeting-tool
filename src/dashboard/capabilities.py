"""Which Collaborator-only features this build ships (spec #236, decision S14).

The Retail Edition leaves the Collaborator-only packages out, so a feature is
present exactly when the package behind it can be found. The frontend asks for
this rather than checking an edition name, so adding a package to a build later
turns its feature on with no frontend change (ADR-0033).

Detection never imports the package: shared code must not import a
Collaborator-only one, and finding a spec is enough to know it ships.
"""

from importlib.util import find_spec

# Capability name (what the frontend reads) -> the package that provides it.
FEATURE_PACKAGES = {
    "budget_suggestion": "budget_suggestions",
    "statement_export": "statement_export",
}


def _ships(package: str) -> bool:
    try:
        return find_spec(package) is not None
    except (ImportError, ValueError):
        # An import hook that refuses the package (the Retail-shaped test) or a
        # half-removed one both mean it is not there to use.
        return False


def detect() -> dict[str, bool]:
    return {feature: _ships(package) for feature, package in FEATURE_PACKAGES.items()}
