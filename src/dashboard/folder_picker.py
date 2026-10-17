"""The native folder picker behind Settings' "Change location..." (ADR-0030).

The dialog runs in a short-lived child process: macOS only allows Tk dialogs on
a process's main thread, and the Dashboard server handles each request on its
own thread. The server takes `pick_folder` as an injectable part so tests (and
headless machines) never open a real dialog.

A compiled build (Issue #252) has no `python -m` to start the child with, so it
starts its own executable again with `FOLDER_PICKER_FLAG`, which `retail_app`
hands to `run_child`.
"""

import subprocess
import sys

FOLDER_PICKER_FLAG = "--pick-folder"
# With this the child proves the dialog toolkit loads, then exits without showing
# a dialog - what the build's smoke test uses.
CHECK_FLAG = "--check"


def command(*, compiled: bool, executable: str | None = None) -> list[str]:
    if compiled:
        # Nuitka's `sys.executable` is a path beside the app that doesn't exist;
        # `sys.argv[0]` is the app's own executable.
        return [executable or sys.argv[0], FOLDER_PICKER_FLAG]
    return [executable or sys.executable, "-m", "dashboard.folder_picker"]


# Nuitka defines `__compiled__` in every module it compiles.
COMMAND = command(compiled="__compiled__" in globals())
# Long enough to browse around, short enough that a dialog hidden behind
# another window can't hang the request for ever.
TIMEOUT_SECONDS = 300


class FolderPickerError(Exception):
    """The dialog could not be shown (e.g. no display or no Tk)."""


def pick_folder(timeout: float = TIMEOUT_SECONDS, extra_args: tuple[str, ...] = ()) -> str | None:
    """The folder the user chose, or None if they cancelled. Raises
    FolderPickerError if the dialog can't be shown or isn't closed in time."""
    try:
        result = subprocess.run([*COMMAND, *extra_args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as cause:
        raise FolderPickerError("The folder picker timed out - it may be hidden behind another window. Try again.") from cause
    except OSError as cause:
        raise FolderPickerError(f"Could not open the folder picker: {cause}") from cause
    if result.returncode != 0:
        raise FolderPickerError(result.stderr.strip() or "Could not open the folder picker")
    chosen = result.stdout.strip()
    return chosen or None


def run_child(args: list[str]) -> None:
    _ask(check=CHECK_FLAG in args)


def _ask(*, check: bool = False) -> None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    if check:
        root.destroy()
        print("ok")
        return
    root.attributes("-topmost", True)
    chosen = filedialog.askdirectory(title="Choose a folder for the Database")
    root.destroy()
    print(chosen or "")


if __name__ == "__main__":
    run_child(sys.argv[1:])
