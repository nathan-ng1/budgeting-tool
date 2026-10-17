"""The release build carries the Version its tag names (spec #236; Issue #252)."""

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
