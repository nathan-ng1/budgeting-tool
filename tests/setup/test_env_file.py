from setup.env_file import merge_env


def test_merge_into_empty_content_writes_every_value():
    result = merge_env("", {"TRANSACTIONS_INBOX": r"C:\Transactions", "DATABASE_PATH": r"C:\budget.db"})

    assert result.content == "TRANSACTIONS_INBOX=C:\\Transactions\nDATABASE_PATH=C:\\budget.db\n"
    assert result.missing_required == []


def test_merge_overwrites_an_existing_key_in_place():
    existing = "TRANSACTIONS_INBOX=C:\\Old\nDATABASE_PATH=C:\\budget.db\n"

    result = merge_env(existing, {"TRANSACTIONS_INBOX": r"C:\New"})

    assert result.content == "TRANSACTIONS_INBOX=C:\\New\nDATABASE_PATH=C:\\budget.db\n"


def test_merge_preserves_untouched_keys_comments_and_blank_lines():
    existing = (
        "# per-person settings\n"
        "TRANSACTIONS_INBOX=C:\\Transactions\n"
        "\n"
        "BEEM_USERNAME=nathan\n"
    )

    result = merge_env(existing, {"DATABASE_PATH": r"C:\budget.db"})

    assert result.content == (
        "# per-person settings\n"
        "TRANSACTIONS_INBOX=C:\\Transactions\n"
        "\n"
        "BEEM_USERNAME=nathan\n"
        "DATABASE_PATH=C:\\budget.db\n"
    )


def test_merge_reports_required_keys_still_unset_after_merge():
    result = merge_env("", {"TRANSACTIONS_INBOX": r"C:\Transactions"})

    assert result.missing_required == ["DATABASE_PATH"]


def test_merge_treats_a_blank_value_as_still_unset():
    result = merge_env("", {"TRANSACTIONS_INBOX": r"C:\Transactions", "DATABASE_PATH": ""})

    assert result.missing_required == ["DATABASE_PATH"]


def test_merge_treats_existing_blank_key_as_unset_when_not_overridden():
    existing = "DATABASE_PATH=\n"

    result = merge_env(existing, {"TRANSACTIONS_INBOX": r"C:\Transactions"})

    assert result.missing_required == ["DATABASE_PATH"]


def test_merge_honours_a_custom_required_keys_set():
    result = merge_env(
        "",
        {"TRANSACTIONS_INBOX": r"C:\Transactions", "DATABASE_PATH": r"C:\budget.db", "CATEGORISER_BACKEND": "claude"},
        required_keys=("TRANSACTIONS_INBOX", "DATABASE_PATH", "CATEGORISER_BACKEND"),
    )

    assert result.missing_required == []


def test_merge_leaves_categoriser_backend_unset_on_the_dashboard_only_path():
    result = merge_env(
        "",
        {"TRANSACTIONS_INBOX": r"C:\Transactions", "DATABASE_PATH": r"C:\budget.db"},
        required_keys=("TRANSACTIONS_INBOX", "DATABASE_PATH", "CATEGORISER_BACKEND"),
    )

    assert result.missing_required == ["CATEGORISER_BACKEND"]
