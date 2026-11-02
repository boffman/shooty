# Shooty

Shooty is a Python screenshot annotation application targeting Ubuntu 24.04 GNOME on X11.

## Install from a release archive

Download and extract the versioned `shooty-*.tar.gz` release from [GitHub Releases](https://github.com/boffman/shooty/releases/latest), then run `./install.sh`. The installer writes only to your home directory; it does not use root or a Python package manager. The archive bundles Python, the application, and Pillow. A standard Ubuntu 24.04 GNOME desktop supplies GTK 3, its GObject Introspection typelibs, Cairo, and X11 libraries. Add `~/.local/bin` to `PATH` if `shooty` is not found. Run `shooty --help` or `shooty --version`. Remove with `./uninstall.sh` from the extracted archive.

After installation, Shooty appears in the Applications grid. Right-click it in the Ubuntu Dock and choose **Pin to Dash** to keep it there. To use a keyboard shortcut, open **Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts**, add a shortcut named “Shooty Capture” with command `shooty capture`, and assign **Shift+Alt+S**. If another app already uses that combination, choose a different unassigned shortcut. The shortcut starts capture without a resident process. To keep a top-bar indicator running, launch **Shooty → Start Top Bar Indicator** from its application menu (or run `shooty indicator`); its menu offers Capture and Quit. Indicator support depends on the desktop's Ayatana AppIndicator extension.

## Development

Use Python 3.10 or newer. Install pytest in a developer environment, then run `python -m pytest`. On Ubuntu 24.04, build a release archive with `./tools/build_release.sh` (uses `uv` for isolated build tooling). Launch the CLI with `PYTHONPATH=src python -m shooty --help`.

Run `shooty capture` to select a region from a frozen desktop snapshot. Drag
to create a selection, resize from its corners or sides, or move it from the
interior. Press Enter or click Capture to open the crop in an editor window;
press Escape to cancel. Each capture invocation opens its own selection
session and each confirmed image opens in a separate window. Wayland is not
supported.

The editor supports annotation, rectangular pixel selection, Ctrl+C/Ctrl+V
image clipboard transfer, movable floating pastes (Enter to commit, Escape to
cancel), Undo/Redo, and PNG saving. Each editor window has its own image and
history. Closing a changed image offers Save, Discard, or Cancel. Open an
existing image with `shooty open FILE`.
