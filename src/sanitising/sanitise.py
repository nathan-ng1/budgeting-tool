import os


def _sanitise_anz(raw_rows: list[list[str]]) -> list[list[str]]:
    return list(raw_rows)


def _sanitise_beem(raw_rows: list[list[str]]) -> list[list[str]]:
    username = os.environ["BEEM_USERNAME"]

    header, *rows = raw_rows
    col = {name: index for index, name in enumerate(header)}

    sanitised = []
    for row in rows:
        if row[col["Type"]] != "PAYMENT":
            continue
        date_str = row[col["Date/Time"]].split(" ")[0]
        payer = row[col["Payer"]]
        amount = float(row[col["Amount"]].removeprefix("$"))
        message = row[col["Message"]]
        signed_amount = -amount if payer == username else amount
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
