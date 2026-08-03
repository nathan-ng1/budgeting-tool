import csv
import re
from pathlib import Path

from sanitising.sanitise import sanitise

STATEMENT_EXPORT_PATTERN = re.compile(r"^(?P<issuer>[A-Za-z]+)_\d{8}\.csv$")


def sanitise_inbox(inbox_dir: Path, data_dir: Path) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for source in sorted(inbox_dir.glob("*.csv")):
        match = STATEMENT_EXPORT_PATTERN.match(source.name)
        if not match:
            raise ValueError(
                f"'{source.name}' doesn't match the Statement Export filename "
                "convention '{Issuer}_{yyyymmdd}.csv'"
            )
        issuer = match.group("issuer")

        raw_bytes = source.read_bytes()
        raw_rows = list(csv.reader(raw_bytes.decode("utf-8-sig").splitlines()))

        sanitised_rows = sanitise(raw_rows, issuer)

        dest = data_dir / source.name
        if sanitised_rows == raw_rows:
            # Byte-identical move for the (typical) case where sanitising
            # didn't change anything — re-serialising via csv.writer would
            # silently rewrite line endings/quoting even when unchanged.
            dest.write_bytes(raw_bytes)
        else:
            with open(dest, "w", newline="") as f:
                csv.writer(f).writerows(sanitised_rows)

        source.unlink()
        written.append(dest)

    return written
