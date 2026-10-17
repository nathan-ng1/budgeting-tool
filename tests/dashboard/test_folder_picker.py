"""The native folder picker's child process (ADR-0030): a dialog that never
closes must not wait forever."""

import subprocess
import sys

import pytest

from dashboard import folder_picker
from dashboard.folder_picker import FolderPickerError, pick_folder


def test_a_dialog_that_never_closes_gives_up_with_a_plain_error(monkeypatch):
    monkeypatch.setattr(folder_picker, "COMMAND", [sys.executable, "-c", "import time; time.sleep(60)"])

    with pytest.raises(FolderPickerError, match="timed out|didn't close|too long"):
        pick_folder(timeout=0.5)


def test_a_chosen_folder_is_returned_and_an_empty_answer_is_a_cancel(monkeypatch):
    monkeypatch.setattr(folder_picker, "COMMAND", [sys.executable, "-c", "print('C:/somewhere')"])
    assert pick_folder() == "C:/somewhere"

    monkeypatch.setattr(folder_picker, "COMMAND", [sys.executable, "-c", "print('')"])
    assert pick_folder() is None


def test_a_compiled_build_starts_its_own_executable_for_the_picker():
    # A compiled app has no `python -m` (Issue #252), so it re-runs itself with a flag.
    assert folder_picker.command(compiled=True, executable="C:/App/BudgetingTool.exe") == [
        "C:/App/BudgetingTool.exe",
        folder_picker.FOLDER_PICKER_FLAG,
    ]
    # Not `sys.executable`: in a compiled app that is a path that doesn't exist.
    assert folder_picker.command(compiled=True)[0] == sys.argv[0]
    assert folder_picker.command(compiled=False, executable="python") == ["python", "-m", "dashboard.folder_picker"]


def test_the_check_flag_loads_the_dialog_toolkit_without_showing_a_dialog():
    pytest.importorskip("tkinter")
    result = subprocess.run(
        [sys.executable, "-m", "dashboard.folder_picker", folder_picker.CHECK_FLAG],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0 and "display" in result.stderr.lower():
        pytest.skip("no display to open a window on")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_extra_arguments_are_passed_to_the_child(monkeypatch):
    monkeypatch.setattr(folder_picker, "COMMAND", [sys.executable, "-c", "import sys; print(sys.argv[1])"])

    assert pick_folder(extra_args=("--hello",)) == "--hello"
