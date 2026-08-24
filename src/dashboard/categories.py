"""Translation between Category Management's JSON shape and Category - see
Issue #91.

Kept out of dashboard.server so the HTTP layer stays a router: what a
Category looks like on the wire is a question about the domain, not about
HTTP. Mirrors dashboard.recurring's as_payload/from_payload split.
"""

from transaction_log.categories import Category


def as_payload(category: Category) -> dict:
    return {
        "id": category.id,
        "type": category.type,
        "name": category.name,
        "emoji": category.emoji,
        "locked": category.locked,
    }


def create_from_payload(payload) -> tuple[str, str, str | None]:
    """The (type, name, emoji) triple a create request body describes."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one Category")

    missing = [field for field in ("type", "name") if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    return _type(payload["type"]), _name(payload["name"]), _emoji(payload.get("emoji"))


def update_from_payload(payload) -> tuple[str, str | None]:
    """The (name, emoji) pair an update request body describes.

    No Type field: a Category's Type is fixed at creation (Issue #89's
    Implementation Decisions), so a PUT body never carries one.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one Category")

    if "name" not in payload:
        raise ValueError("Missing required field: name")

    return _name(payload["name"]), _emoji(payload.get("emoji"))


def _type(value) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Field 'type' must be a string, got {value!r}")
    return value


def _name(value) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Field 'name' must be a string, got {value!r}")
    return value


def _emoji(value) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"Field 'emoji' must be a string, got {value!r}")
    return value
