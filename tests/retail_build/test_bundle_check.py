"""What is in a finished build, from Nuitka's report and the build folder (Issue #252)."""

from pathlib import Path

import pytest

from retail_build import bundle_check, plan


def write_report(path: Path, *modules: str) -> Path:
    body = "".join(f'<module name="{name}" kind="CompiledPythonModule"><module_usages /></module>' for name in modules)
    path.write_text(f"<nuitka-compilation-report>{body}</nuitka-compilation-report>", encoding="utf-8")
    return path


@pytest.fixture
def dist(tmp_path):
    folder = tmp_path / "retail_app.dist"
    (folder / plan.STATIC_DIR).mkdir(parents=True)
    (folder / plan.STATIC_DIR / "index.html").write_text("<html></html>")
    (folder / plan.BUILD_INFO_FILE).write_text("{}")
    return folder


def test_a_build_of_only_shared_packages_with_its_data_files_has_no_problems(tmp_path, dist):
    report = write_report(tmp_path / "report.xml", "__main__", "dashboard", "dashboard.server", "database.store", "sqlite3")

    assert bundle_check.problems(report, dist) == []


@pytest.mark.parametrize("module", ["statement_export", "categorisation.history", "beem.parser", "advisor", "sanitising.run"])
def test_a_compiled_in_collaborator_only_module_is_a_problem(tmp_path, dist, module):
    report = write_report(tmp_path / "report.xml", "dashboard", module)

    [problem] = bundle_check.problems(report, dist)

    assert module.split(".")[0] in problem
    assert "compiled in" in problem


def test_a_module_that_only_shares_a_prefix_with_a_collaborator_only_package_is_fine(tmp_path, dist):
    report = write_report(tmp_path / "report.xml", "dashboard", "advisory_notes", "beemer")

    assert bundle_check.problems(report, dist) == []


def test_a_collaborator_only_folder_in_the_build_is_a_problem(tmp_path, dist):
    (dist / "statement_export").mkdir()
    report = write_report(tmp_path / "report.xml", "dashboard")

    [problem] = bundle_check.problems(report, dist)

    assert "build folder" in problem


def test_a_missing_frontend_or_build_info_is_a_problem(tmp_path, dist):
    (dist / plan.STATIC_DIR / "index.html").unlink()
    (dist / plan.BUILD_INFO_FILE).unlink()
    report = write_report(tmp_path / "report.xml", "dashboard")

    assert len(bundle_check.problems(report, dist)) == 2


def test_a_report_with_no_modules_is_a_problem_not_a_pass(tmp_path, dist):
    report = write_report(tmp_path / "report.xml")

    assert "lists no modules" in bundle_check.problems(report, dist)[0]
