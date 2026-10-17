"""The CI smoke test launches the built app and fails the build on a bad bundle
(Issue #252). Here it launches a source checkout the same way - a child
process, with only HTTP and the command line between them - and checks that it
passes a Retail-shaped app and catches each way a build can be wrong."""

import json
import sys
import webbrowser
from pathlib import Path

import pytest

from database import location
from retail_build import smoke
from retail_build.plan import COLLABORATOR_ONLY_PACKAGES
from retail_build.smoke import SmokeFailure, run_smoke

REAL_DEFAULT_DATA_FOLDER = location.default_data_folder
SRC = Path(__file__).resolve().parents[2] / "src"

# The app as the compiled build runs it, minus the compile: `retail_app.main`
# with the browser silenced and the baked-in Version pointed at `build_info`.
APP_SCRIPT = """
import sys, webbrowser
from pathlib import Path

sys.path.insert(0, {src!r})
{block}
webbrowser.open = lambda url: None
import dashboard.build_info
dashboard.build_info.BUILD_INFO_PATH = Path({build_info!r})
import retail_app
retail_app.main()
"""

BLOCK = f"""
BLOCKED = {COLLABORATOR_ONLY_PACKAGES!r}


class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(name)
        return None


sys.meta_path.insert(0, Blocker())
"""


def version_entry(*, groups=()):
    return {"version": "9.9.9", "date": "2026-10-17", "entries": ["Something new"], "groups": list(groups)}


@pytest.fixture
def build_info(tmp_path):
    def write(history=None, version="9.9.9"):
        path = tmp_path / "build_info.json"
        path.write_text(json.dumps({"version": version, "history": [version_entry()] if history is None else history}))
        return path

    return write


def run(command, workdir, **kwargs):
    # The picker's process is `python -m dashboard.folder_picker`, which needs src on the path.
    return run_smoke(command, workdir=workdir, environment_overrides={"PYTHONPATH": str(SRC)}, **kwargs)


def app(build_info_path, *, retail_shaped=True) -> list[str]:
    script = APP_SCRIPT.format(src=str(SRC), block=BLOCK if retail_shaped else "", build_info=str(build_info_path))
    return [sys.executable, "-c", script]


@pytest.fixture(autouse=True)
def real_data_folder(monkeypatch):
    # The suite points the data folder at a temporary one in this process; the app
    # runs in another, where the smoke test has to look for the folder it really uses.
    monkeypatch.setattr(location, "default_data_folder", REAL_DEFAULT_DATA_FOLDER)


def tk_is_usable() -> bool:
    try:
        import tkinter

        tkinter.Tk().destroy()
    except Exception:
        return False
    return True


def test_a_retail_shaped_app_passes(tmp_path, build_info):
    run(app(build_info()), workdir=tmp_path, expected_version="9.9.9", check_folder_picker=False)


@pytest.mark.skipif(not tk_is_usable(), reason="no display to open a window on")
def test_a_retail_shaped_app_passes_with_the_folder_picker_check(tmp_path, build_info):
    run(app(build_info()), workdir=tmp_path, expected_version="9.9.9")


def test_an_app_with_collaborator_only_features_fails(tmp_path, build_info):
    with pytest.raises(SmokeFailure, match="Collaborator-only features are in the build"):
        run(app(build_info(), retail_shaped=False), workdir=tmp_path, check_folder_picker=False)


def test_an_app_that_exits_before_serving_fails(tmp_path):
    with pytest.raises(SmokeFailure, match="exited with code 3"):
        run([sys.executable, "-c", "raise SystemExit(3)"], workdir=tmp_path, check_folder_picker=False)


def test_an_app_that_never_serves_fails_after_the_timeout(tmp_path):
    with pytest.raises(SmokeFailure, match="did not start serving"):
        run_smoke(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            workdir=tmp_path,
            check_folder_picker=False,
            startup_timeout=1,
        )


def test_a_different_version_fails(tmp_path, build_info):
    with pytest.raises(SmokeFailure, match="expected '1.0.0'"):
        run(app(build_info()), workdir=tmp_path, expected_version="1.0.0", check_folder_picker=False)


def test_a_version_history_with_collaborator_only_items_fails(tmp_path, build_info):
    leaky = [version_entry(groups=[{"title": "Collaborator Edition only", "entries": ["Pipeline change"]}])]

    with pytest.raises(SmokeFailure, match="Collaborator-only items"):
        run(app(build_info(leaky)), workdir=tmp_path, check_folder_picker=False)


def test_the_app_is_given_a_browser_that_does_nothing(tmp_path):
    environment, _ = smoke.sandbox_environment(tmp_path, base={})

    # webbrowser reads this to choose the browser the launcher opens.
    assert webbrowser.get(environment["BROWSER"]).open("http://127.0.0.1:1/") is True


def test_the_app_is_run_against_a_throwaway_database_and_data_folder(tmp_path, build_info):
    run(app(build_info()), workdir=tmp_path, check_folder_picker=False)

    assert (tmp_path / "smoke.db").exists()
    assert not (tmp_path / "home" / "AppData" / "Local" / "Budgeting Tool" / "instance.json").exists()


@pytest.mark.parametrize(
    ("capabilities", "problems"),
    [
        ({"statement_export": False, "budget_suggestion": False}, []),
        ({"statement_export": False, "budget_suggestion": True}, ["budget_suggestion is present"]),
        ({}, ["expected a non-empty object of features, got {}"]),
        (None, ["expected a non-empty object of features, got None"]),
        ({"statement_export": "no"}, ["statement_export is present"]),
    ],
)
def test_only_a_non_empty_list_of_absent_features_is_a_retail_build(capabilities, problems):
    assert smoke.absent_capabilities(capabilities) == problems
