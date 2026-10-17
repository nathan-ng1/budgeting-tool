"""The CI smoke test for a built Retail app (Issue #252, decision S11).

Launches the built executable against a throwaway Database and data folder,
waits for the Dashboard to answer, and fails unless:

- the capabilities endpoint reports every Collaborator-only feature absent;
- the Version it reports is the one being built, and its Version History has no
  Collaborator-only items;
- a request that needs the bundled spreadsheet library works;
- the app can start the folder picker's process and that process can load its
  dialog toolkit (without showing a dialog, which a CI machine can't answer);
- Quit stops the app.

It speaks to the app only over HTTP, the data folder and the command line, as a
Buyer's machine would, so it works on the compiled build and, for the tests, on
a source checkout started the same way.
"""

import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from database import location
from launcher.launch import INSTANCE_FILE_NAME, read_instance
from retail_app import CHECK_FOLDER_PICKER_FLAG

COLLABORATOR_ONLY_GROUP = "Collaborator Edition only"
STARTUP_TIMEOUT_SECONDS = 90
QUIT_TIMEOUT_SECONDS = 15
PICKER_TIMEOUT_SECONDS = 60


class SmokeFailure(Exception):
    pass


def sandbox_environment(workdir: Path, base: Mapping[str, str] | None = None) -> tuple[dict[str, str], Path]:
    """The environment to run the app in, and the data folder it will use: every
    place it could write (Database, per-user folders) is under `workdir`."""
    home = workdir / "home"
    home.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ if base is None else base)
    environment.update(
        HOME=str(home),
        USERPROFILE=str(home),
        LOCALAPPDATA=str(home / "AppData" / "Local"),
        XDG_DATA_HOME=str(home / ".local" / "share"),
        DATABASE_PATH=str(workdir / "smoke.db"),
        # The launcher opens the browser; a command that does nothing stands in for it
        # (forward slashes, because `webbrowser` splits this like a POSIX shell would).
        BROWSER=f'"{Path(sys.executable).as_posix()}" -c pass %s',
    )
    return environment, location.default_data_folder(environ=environment, home=home)


def absent_capabilities(capabilities: object) -> list[str]:
    """What is wrong with a capabilities answer for a Retail build: an empty list
    if it names at least one feature and reports none of them present."""
    if not isinstance(capabilities, dict) or not capabilities:
        return [f"expected a non-empty object of features, got {capabilities!r}"]
    return [f"{name} is present" for name, present in capabilities.items() if present is not False]


def run_smoke(
    command: list[str],
    *,
    workdir: Path,
    expected_version: str | None = None,
    check_folder_picker: bool = True,
    startup_timeout: float = STARTUP_TIMEOUT_SECONDS,
    environment_overrides: Mapping[str, str] | None = None,
) -> None:
    """Raises SmokeFailure naming the first thing that is wrong."""
    environment, data_folder = sandbox_environment(workdir)
    environment.update(environment_overrides or {})
    process = subprocess.Popen(
        command, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        port = _wait_for_port(process, data_folder, startup_timeout)
        _check_capabilities(port)
        _check_version(port, expected_version)
        _check_spreadsheet_library(port)
        if check_folder_picker:
            _check_folder_picker(command, environment)
        _quit(process, port)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _wait_for_port(process: subprocess.Popen, data_folder: Path, timeout: float) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SmokeFailure(f"The app exited with code {process.returncode} before it started serving")
        port = read_instance(data_folder)
        if port is not None:
            try:
                _request(port, "/api/capabilities", timeout=2)
                return port
            except (OSError, URLError):
                pass
        time.sleep(0.5)
    raise SmokeFailure(f"The app did not start serving within {timeout:g} seconds (looked for {data_folder / INSTANCE_FILE_NAME})")


def _request(port: int, path: str, *, method: str = "GET", timeout: float = 10) -> tuple[int, bytes]:
    request = Request(f"http://127.0.0.1:{port}{path}", method=method, data=b"{}" if method == "POST" else None)
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def _check_capabilities(port: int) -> None:
    status, body = _request(port, "/api/capabilities")
    if status != 200:
        raise SmokeFailure(f"Capabilities answered {status}")
    problems = absent_capabilities(json.loads(body))
    if problems:
        raise SmokeFailure("Collaborator-only features are in the build: " + "; ".join(problems))


def _check_version(port: int, expected_version: str | None) -> None:
    _, body = _request(port, "/api/version")
    info = json.loads(body)
    if expected_version is not None and info.get("version") != expected_version:
        raise SmokeFailure(f"The app reports Version {info.get('version')!r}, expected {expected_version!r}")
    history = info.get("history")
    if not history:
        raise SmokeFailure("The app has no Version History")
    if any(group["title"].lower() == COLLABORATOR_ONLY_GROUP.lower() for entry in history for group in entry["groups"]):
        raise SmokeFailure("The Version History contains Collaborator-only items")


def _check_spreadsheet_library(port: int) -> None:
    status, body = _request(port, "/api/transactions/import-template")
    # A spreadsheet file is a zip archive.
    if status != 200 or not body.startswith(b"PK"):
        raise SmokeFailure("The import template could not be built, so the spreadsheet library is missing or broken")


def _check_folder_picker(command: list[str], environment: dict[str, str]) -> None:
    try:
        result = subprocess.run(
            [*command, CHECK_FOLDER_PICKER_FLAG],
            env=environment,
            capture_output=True,
            text=True,
            timeout=PICKER_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as cause:
        raise SmokeFailure("The folder picker's process did not finish") from cause
    if result.returncode != 0 or result.stdout.strip() != "ok":
        raise SmokeFailure(
            f"The folder picker's process failed (exit {result.returncode}): {(result.stderr or result.stdout).strip()}"
        )


def _quit(process: subprocess.Popen, port: int) -> None:
    status, _ = _request(port, "/api/quit", method="POST")
    if status != 200:
        raise SmokeFailure(f"Quit answered {status}")
    try:
        process.wait(QUIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as cause:
        raise SmokeFailure(f"The app was still running {QUIT_TIMEOUT_SECONDS} seconds after Quit") from cause
