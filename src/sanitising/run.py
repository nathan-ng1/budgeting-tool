import csv
import re
from pathlib import Path

from sanitising.sanitise import sanitise

STATEMENT_EXPORT_PATTERN = re.compile(r"^(?P<issuer>[A-Za-z]+)_\d{8}\.csv$")


def run(inbox_dir: Path, data_dir: Path) -> list[Path]:
    written = []
    for source in sorted(inbox_dir.glob("*.csv")):
        match = STATEMENT_EXPORT_PATTERN.match(source.name)
        if not match:
            raise ValueError(
                f"'{source.name}' doesn't match the Statement Export filename "
                "convention '{Issuer}_{yyyymmdd}.csv'"
            )
        issuer = match.group("issuer")

        with open(source, newline="") as f:
            raw_rows = list(csv.reader(f))

        sanitised_rows = sanitise(raw_rows, issuer)

        dest = data_dir / source.name
        with open(dest, "w", newline="") as f:
            csv.writer(f).writerows(sanitised_rows)

        source.unlink()
        written.append(dest)

    return written
