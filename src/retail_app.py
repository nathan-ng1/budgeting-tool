"""The compiled Retail build's entry point: what a Buyer's double-click runs.

It is the whole app in one executable. The folder picker needs a process of its
own (see `dashboard.folder_picker`), and a compiled app has no `python -m` to
start one with, so the executable starts itself again with the picker's flag.
Anything else is the launcher.
"""

import sys

# Starts the folder picker's process the way the app really does and prints what
# it answers, without showing a dialog: the build's smoke test uses it.
CHECK_FOLDER_PICKER_FLAG = "--check-folder-picker"


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    # Checked before importing the launcher: the picker's process should start
    # fast and doesn't need the Dashboard.
    from dashboard import folder_picker

    if argv and argv[0] == folder_picker.FOLDER_PICKER_FLAG:
        folder_picker.run_child(argv[1:])
        return

    if argv and argv[0] == CHECK_FOLDER_PICKER_FLAG:
        print(folder_picker.pick_folder(extra_args=(folder_picker.CHECK_FLAG,)))
        return

    from launcher.launch import main as launch

    launch()


if __name__ == "__main__":
    main()
