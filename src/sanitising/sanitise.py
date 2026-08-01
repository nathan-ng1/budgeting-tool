def _sanitise_anz(raw_rows: list[list[str]]) -> list[list[str]]:
    return list(raw_rows)


ISSUER_HANDLERS = {
    "ANZ": _sanitise_anz,
}


def sanitise(raw_rows: list[list[str]], issuer: str) -> list[list[str]]:
    try:
        handler = ISSUER_HANDLERS[issuer]
    except KeyError:
        raise ValueError(f"No sanitising handler registered for issuer '{issuer}'")
    return handler(raw_rows)
