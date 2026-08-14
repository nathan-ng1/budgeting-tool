from pathlib import Path

import pytest


@pytest.fixture
def recurring_config(tmp_path: Path) -> Path:
    import openpyxl

    from recurring.config import COLUMNS

    path = tmp_path / "recurring-transactions.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active.append(COLUMNS)
    workbook.save(path)
    return path
