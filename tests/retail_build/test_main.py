"""The release build carries the Version its tag names (spec #236; Issue #252)."""

import os

import pytest

from retail_build import __main__ as retail_build_main


def test_a_tag_matching_the_project_version_is_accepted():
    retail_build_main.check_tag("v0.6.0", "0.6.0")


@pytest.mark.parametrize("tag", ["v0.6.1", "v0.5.0", "0.6.0.1", "release"])
def test_a_tag_that_names_another_version_is_refused(tag):
    with pytest.raises(SystemExit, match="does not match"):
        retail_build_main.check_tag(tag, "0.6.0")


def test_the_project_version_is_read_from_pyproject():
    assert retail_build_main.project_version().count(".") == 2


def touch(path, when):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")
    os.utime(path, (when, when))
    return path


def test_a_built_frontend_older_than_a_source_file_is_stale(tmp_path):
    built = touch(tmp_path / "static" / "index.html", 1000)
    touch(tmp_path / "frontend" / "src" / "App.jsx", 900)
    touch(tmp_path / "frontend" / "src" / "components" / "Quit.jsx", 2000)

    assert retail_build_main.frontend_is_stale(built, (tmp_path / "frontend" / "src",))


def test_a_built_frontend_newer_than_every_source_is_fresh(tmp_path):
    built = touch(tmp_path / "static" / "index.html", 3000)
    source = touch(tmp_path / "frontend" / "package.json", 2000)
    touch(tmp_path / "frontend" / "src" / "App.jsx", 1000)

    assert not retail_build_main.frontend_is_stale(built, (tmp_path / "frontend" / "src", source))
