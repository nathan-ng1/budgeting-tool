import os
from datetime import datetime


def _sanitise_anz(raw_rows: list[list[str]]) -> list[list[str]]:
    return list(raw_rows)


def _sanitise_nab(raw_rows: list[list[str]]) -> list[list[str]]:
    header, *rows = raw_rows
    col = {name: index for index, name in enumerate(header)}

    sanitised = []
    for row in rows:
        date = datetime.strptime(row[col["Date"]], "%d-%b-%y")
        amount = str(float(row[col["Amount"]]))
        notes = row[col["Merchant Name"]] or row[col["Transaction Details"]]
        sanitised.append([date.strftime("%d/%m/%Y"), amount, notes])
    return sanitised


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
    "NAB": _sanitise_nab,
}


def sanitise(raw_rows: list[list[str]], issuer: str) -> list[list[str]]:
    try:
        handler = ISSUER_HANDLERS[issuer]
    except KeyError:
        raise ValueError(f"No sanitising handler registered for issuer '{issuer}'")
    return handler(raw_rows)
