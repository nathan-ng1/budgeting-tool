"""The native folder picker's child process (ADR-0030): a dialog that never
closes must not wait forever."""

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
