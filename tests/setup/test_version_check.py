from setup.version_check import check_update_available


def test_equal_versions_report_no_update():
    result = check_update_available("0.3.0", "v0.3.0")

    assert result.update_available is False
    assert result.latest_version == "0.3.0"


def test_remote_ahead_reports_update_available():
    result = check_update_available("0.3.0", "v0.4.0")

    assert result.update_available is True
    assert result.latest_version == "0.4.0"


def test_local_ahead_of_latest_tag_reports_no_update():
    # e.g. a dev checkout running work not yet released.
    result = check_update_available("0.5.0-dev", "v0.4.0")

    assert result.update_available is False


def test_missing_tag_reports_no_update():
    result = check_update_available("0.3.0", None)

    assert result.update_available is False
    assert result.latest_version is None


def test_malformed_tag_reports_no_update():
    result = check_update_available("0.3.0", "not-a-version")

    assert result.update_available is False
    assert result.latest_version is None


def test_malformed_local_version_still_reports_the_latest_version():
    result = check_update_available("not-a-version", "v0.4.0")

    assert result.update_available is False
    assert result.latest_version == "0.4.0"


def test_tag_without_leading_v_is_still_parsed():
    result = check_update_available("0.3.0", "0.4.0")

    assert result.update_available is True
    assert result.latest_version == "0.4.0"
