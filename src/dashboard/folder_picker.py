"""The native folder picker behind Settings' "Change location..." (ADR-0030).

The dialog runs in a short-lived child process: macOS only allows Tk dialogs on
a process's main thread, and the Dashboard server handles each request on its
own thread. The server takes `pick_folder` as an injectable part so tests (and
headless machines) never open a real dialog.
"""

import subprocess
import sys


class FolderPickerError(Exception):
    """The dialog could not be shown (e.g. no display or no Tk)."""


def pick_folder() -> str | None:
    """The folder the user chose, or None if they cancelled."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "dashboard.folder_picker"],
            capture_output=True,
            text=True,
        )
    except OSError as cause:
        raise FolderPickerError(f"Could not open the folder picker: {cause}") from cause
    if result.returncode != 0:
        raise FolderPickerError(result.stderr.strip() or "Could not open the folder picker")
    chosen = result.stdout.strip()
    return chosen or None


def _ask() -> None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askdirectory(title="Choose a folder for the Database")
    root.destroy()
    print(chosen or "")


if __name__ == "__main__":
    _ask()
