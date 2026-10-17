"""The Retail build is an explicit allowlist (spec #236, S11; Issue #252)."""

from pathlib import Path

import pytest

from retail_build import plan

SRC = Path(__file__).resolve().parents[2] / "src"
SRC_ARGS = Path("/repo/src")


def build_args(**overrides):
    kwargs = {"src": SRC_ARGS, "output_dir": Path("/out"), "version": "0.6.0"}
    kwargs.update(overrides)
    return plan.nuitka_args(**kwargs)


def test_every_top_level_package_is_either_shipped_collaborator_only_or_tooling():
    # A package added to src/ must be decided on, not shipped (or left out) by default.
    present = {
        entry.stem if entry.suffix == ".py" else entry.name
        for entry in SRC.iterdir()
        if (entry.is_dir() and (entry / "__init__.py").exists()) or entry.suffix == ".py"
    }
    decided = set(plan.SHARED_PACKAGES) | set(plan.COLLABORATOR_ONLY_PACKAGES) | set(plan.BUILD_TOOLING)
    decided.add(Path(plan.MAIN_SCRIPT_NAME).stem)

    assert present == decided


def test_no_package_is_both_shipped_and_collaborator_only():
    assert not set(plan.SHARED_PACKAGES) & set(plan.COLLABORATOR_ONLY_PACKAGES)


def test_the_build_includes_each_shared_package_and_no_collaborator_only_one():
    args = build_args()

    included = {arg.split("=", 1)[1] for arg in args if arg.startswith("--include-package=")}
    assert included == set(plan.SHARED_PACKAGES)
    refused = {arg.split("=", 1)[1] for arg in args if arg.startswith("--nofollow-import-to=")}
    assert refused == set(plan.COLLABORATOR_ONLY_PACKAGES)


def test_the_build_is_standalone_not_onefile_with_the_frontend_and_build_info_bundled():
    args = build_args()

    assert "--standalone" in args
    assert not any("onefile" in arg for arg in args)
    assert f"--include-data-dir={SRC_ARGS / 'dashboard' / 'static'}=dashboard/static" in args
    assert f"--include-data-files={SRC_ARGS / 'dashboard' / 'build_info.json'}=dashboard/build_info.json" in args
    assert "--enable-plugin=tk-inter" in args
    assert args[-1] == str(SRC_ARGS / "retail_app.py")


def test_the_windows_build_has_no_console_window_and_carries_the_version():
    args = build_args(platform="win32")

    assert "--windows-console-mode=disable" in args
    assert "--product-version=0.6.0.0" in args


def test_other_platforms_get_no_windows_options():
    assert not [arg for arg in build_args(platform="darwin") if arg.startswith("--windows-")]


def test_a_report_is_requested_only_when_asked_for():
    assert not [arg for arg in build_args() if arg.startswith("--report")]
    assert f"--report={Path('/out/report.xml')}" in build_args(report=Path("/out/report.xml"))


def test_the_windows_executable_sits_in_the_standalone_folder():
    assert plan.executable_path(Path("/out"), "win32") == Path("/out/retail_app.dist/BudgetingTool.exe")
    assert plan.executable_path(Path("/out"), "darwin") == Path("/out/retail_app.dist/BudgetingTool")


@pytest.mark.parametrize("version", ["dev", "1.2", ""])
def test_a_version_that_is_not_three_numbers_is_refused(version):
    with pytest.raises(ValueError):
        plan.windows_version(version)
