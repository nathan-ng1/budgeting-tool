import os


def _sanitise_anz(raw_rows: list[list[str]]) -> list[list[str]]:
    return list(raw_rows)


def _sanitise_beem(raw_rows: list[list[str]]) -> list[list[str]]:
    username = os.environ["BEEM_USERNAME"]

    sanitised = []
    for date_str, row_type, payer, _recipient, amount, _reference, message in raw_rows[1:]:
        if row_type != "PAYMENT":
            continue
        signed_amount = -float(amount) if payer == username else float(amount)
        sanitised.append([date_str, str(signed_amount), message])
    return sanitised


ISSUER_HANDLERS = {
    "ANZ": _sanitise_anz,
    "Beem": _sanitise_beem,
}


def sanitise(raw_rows: list[list[str]], issuer: str) -> list[list[str]]:
    try:
        handler = ISSUER_HANDLERS[issuer]
    except KeyError:
        raise ValueError(f"No sanitising handler registered for issuer '{issuer}'")
    return handler(raw_rows)
