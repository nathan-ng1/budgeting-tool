"""The compiled app is one executable: the launcher, or the folder picker's own
process when started with its flag (Issue #252)."""

import sys
import types

import pytest

import retail_app
from dashboard import folder_picker


def test_the_picker_flag_runs_the_folder_picker_and_not_the_launcher(monkeypatch):
    picked = []
    monkeypatch.setattr(folder_picker, "run_child", picked.append)
    monkeypatch.setitem(sys.modules, "launcher.launch", types.SimpleNamespace(main=lambda: pytest.fail("launched")))

    retail_app.main([folder_picker.FOLDER_PICKER_FLAG, folder_picker.CHECK_FLAG])

    assert picked == [[folder_picker.CHECK_FLAG]]


def test_anything_else_runs_the_launcher(monkeypatch):
    launched = []
    monkeypatch.setattr(folder_picker, "run_child", lambda args: pytest.fail("picked"))
    monkeypatch.setitem(sys.modules, "launcher.launch", types.SimpleNamespace(main=lambda: launched.append(True)))

    retail_app.main([])

    assert launched == [True]


def test_the_check_flag_starts_the_picker_process_the_way_the_app_does(monkeypatch, capsys):
    asked = []

    def pick_folder(extra_args=()):
        asked.append(extra_args)
        return "ok"

    monkeypatch.setattr(folder_picker, "pick_folder", pick_folder)
    monkeypatch.setitem(sys.modules, "launcher.launch", types.SimpleNamespace(main=lambda: pytest.fail("launched")))

    retail_app.main([retail_app.CHECK_FOLDER_PICKER_FLAG])

    assert asked == [(folder_picker.CHECK_FLAG,)]
    assert capsys.readouterr().out.strip() == "ok"
