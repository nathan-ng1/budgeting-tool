from dataclasses import dataclass

# The per-person settings setup.bat is able to write, per issue #116 -
# TRANSACTIONS_INBOX and DATABASE_PATH are always required; CATEGORISER_BACKEND
# is only required on the AI path (the caller decides whether to pass it).
REQUIRED_KEYS = ("TRANSACTIONS_INBOX", "DATABASE_PATH")


@dataclass(frozen=True)
class MergeResult:
    content: str
    missing_required: list[str]


def merge_env(existing_content: str, values: dict[str, str], required_keys: tuple[str, ...] = REQUIRED_KEYS) -> MergeResult:
    """Merge `values` into `existing_content` (a `.env` or `.env.example`'s text).

    A key already present as `KEY=...` is overwritten in place, preserving
    every other line (comments, blank lines, untouched keys) verbatim and in
    order - this is what lets a Dashboard-only user re-run setup.bat to add
    the AI path later without clobbering their existing TRANSACTIONS_INBOX/
    DATABASE_PATH (issue #116, user story 13). A key in `values` that isn't
    already present is appended as a new line.

    `missing_required` lists which of `required_keys` are still unset (absent,
    or set to a blank value) once the merge is applied.
    """
    lines = existing_content.splitlines()
    merged_lines: list[str] = []
    seen: set[str] = set()

    for line in lines:
        key = _key_of(line)
        if key is not None and key in values:
            merged_lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            merged_lines.append(line)
            if key is not None:
                seen.add(key)

    for key, value in values.items():
        if key not in seen:
            merged_lines.append(f"{key}={value}")
            seen.add(key)

    content = "\n".join(merged_lines)
    if merged_lines:
        content += "\n"

    final_values = _parse(merged_lines)
    missing_required = [key for key in required_keys if not final_values.get(key)]

    return MergeResult(content=content, missing_required=missing_required)


def _key_of(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        return None
    key, _, _ = line.partition("=")
    return key.strip()


def _parse(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        key = _key_of(line)
        if key is None:
            continue
        _, _, value = line.partition("=")
        values[key] = value.strip()
    return values
