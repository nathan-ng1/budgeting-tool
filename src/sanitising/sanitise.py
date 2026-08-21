import os
from datetime import datetime


def _sanitise_anz(raw_rows: list[list[str]]) -> list[list[str]]:
    # A real ANZ export pads each row with trailing empty columns after
    # Date/Amount/Notes (reserved for fields ANZ leaves blank in this
    # download), and ends with a blank trailing line - drop both so
    # downstream parsing sees exactly 3 columns per row.
    return [row[:3] for row in raw_rows if row]


def _sanitise_nab(raw_rows: list[list[str]]) -> list[list[str]]:
    header, *rows = raw_rows
    col = {name: index for index, name in enumerate(header)}

    sanitised = []
    for row in rows:
        # NAB's own exports use dashes ("27-Jul-26"), but a straight CSV download
        # from their online banking uses spaces ("21 Aug 26") - normalise before
        # parsing so both forms of the same %d-%b-%y date land the same way.
        date = datetime.strptime(row[col["Date"]].replace("-", " "), "%d %b %y")
        amount = str(float(row[col["Amount"]]))
        notes = row[col["Merchant Name"]] or row[col["Transaction Details"]]
        sanitised.append([date.strftime("%d/%m/%Y"), amount, notes])
    return sanitised


_BEEM_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")


def _parse_beem_date(date_str: str) -> str:
    for fmt in _BEEM_DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(f"Unrecognised Beem date format: {date_str!r}")


def _sanitise_beem(raw_rows: list[list[str]]) -> list[list[str]]:
    username = os.environ["BEEM_USERNAME"]

    header, *rows = raw_rows
    col = {name: index for index, name in enumerate(header)}

    sanitised = []
    for row in rows:
        if row[col["Type"]] != "PAYMENT":
            continue
        # A Beem Report's Date/Time column shows up as either dd/mm/yyyy (the
        # sample fixture's format) or ISO yyyy-mm-dd (seen in a real export) -
        # normalise to dd/mm/yyyy, the same convention statement_export's
        # parser expects from every sanitised source.
        date_str = _parse_beem_date(row[col["Date/Time"]].split(" ")[0])
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
