# Manual checks

## Milestone 5: clipboard, selection, undo, and persistence

**Environment:** Ubuntu 24.04.4 LTS, GNOME Shell 46.0, `XDG_SESSION_TYPE=x11`,
`DISPLAY=:0`, GTK 3.24. The live integration check was run with:
`PYTHONPATH=src NO_AT_BRIDGE=1 /usr/bin/python3 tools/milestone5_gtk_check.py`.

The script opened two real GTK editor windows and exercised selection copy in
one window and paste/commit in the other. It confirmed the selected 5×5 image
was available on `CLIPBOARD`, and used `xclip` as a separate X11 client to
export Shooty's PNG clipboard image and import a PNG owned by `xclip`. It
opened the GTK Save chooser, wrote and reopened the resulting file with
Pillow, and checked that the document became clean. It also drove the dirty
close dialog through Cancel, Discard, and Save; Cancel kept the window and
dirty state, while Discard and Save closed it. The script passed.

The overwrite-confirmation option is enabled on the GTK Save chooser, but the
confirmation prompt itself was not manually exercised. The GTK integration
script activates controls and answers dialogs programmatically; physical
mouse operation of selection/paste movement and visual review of the chooser
remain unchecked. Automated document tests cover selection bounds and pixels,
floating paste movement/commit/cancel, per-document isolation, undo branches,
saved revisions, and clipboard/store failures.

## Milestone 4: editor operations and drawing tools

**Environment:** Ubuntu 24.04.4 LTS, GNOME Shell 46.0, `XDG_SESSION_TYPE=x11`,
`DISPLAY=:0`.

**GTK editor interaction check:** Ran
`PYTHONPATH=src NO_AT_BRIDGE=1 /usr/bin/python3 tools/editor_gtk_check.py` on
the live GNOME desktop. It passed. The script created a real GTK editor
window, dispatched GDK canvas button/motion events, activated the actual
toolbar widgets, and asserted document pixels/history. It checked pen, line,
arrow, rectangle, circle, ellipse, preview without pixel changes, one commit
on release, zero-length arrow no-op, text dialog commit, primary and secondary
color controls, secondary None, eyedropper into the secondary slot, both
flips, both rotations, and Fit/100% controls. A 2400×1600 editor launch also
rendered at fit zoom 0.45. I visually inspected a live desktop screenshot of
the toolbar and sample canvas after splitting tools and settings into two
rows; all controls were visible without horizontal scrolling.

Also injected an XTEST mouse drag into the visible editor through the X11
server (press at desktop `(150, 180)`, drag/release at `(230, 240)`). The
document recorded one operation and its nontransparent pixel bounds were
`(84, 35, 166, 97)`, matching the drag after conversion to image coordinates.
This verified the X11 pointer-to-canvas path and release commit on the real
GNOME session.

The broad interaction check uses synthesized GDK events for repeatability;
the pen drag above used actual XTEST pointer input. A physical-mouse check of
the visible tool palette and native color/font chooser dialogs remains.

**Headless checks:** `uv run --python 3.12 --with pytest python -m pytest -q
tests/test_editor.py` passed (6 tests), and the full suite passed (43 tests).
The tests cover transform dimensions/pixels, shape pixels, preview isolation,
one release commit, arrow direction/head and zero-length behavior, text
background/transparency, color sampling, and per-document isolation.

**Still unchecked:** Hands-on physical-mouse checks of every drawing tool and
opening the native GTK color/font chooser dialogs remain. Automated GTK
callback checks cover these operations, and XTEST verified a real pointer
drag for the pen; they do not confirm physical-mouse feel or chooser behavior.

## Milestone 3: selection overlay and first editor window

**Environment:** Ubuntu 24.04.4 LTS, GNOME Shell 46.0,
`XDG_SESSION_TYPE=x11`, `DISPLAY=:0`; GTK 3 and PyGObject load successfully.
Launching `PYTHONPATH=src /usr/bin/python3 -m shooty capture` constructed a
3840x2160 X11 window titled “Select a region” (confirmed with
`xwininfo -root -tree`) at `3840x2160+0+0`. XTEST sent a reverse-direction
drag from `(700, 500)` to `(150, 120)` and Enter; the selection opened a
Shooty editor window. A second independent `shooty capture` invocation while
the first editor remained open produced a second editor. `xwininfo` reported
two Shooty windows, with outer sizes `602x510` and `402x380` respectively.
Both test processes were closed afterward. This exercised GNOME X11 capture,
overlay input, editor dispatch, and repeated invocations without saving an
image file.

To inspect the overlay safely on the GNOME desktop, I temporarily covered
the desktop with a fullscreen synthetic color grid, then launched capture and
used XTEST to create a `650x520` selection, move the pointer to exercise the
magnifier, and press Escape. I inspected the resulting X11 screenshot: the
overlay was above the fullscreen source window and showed the expected
dimmed outside, clear selected region, dashed border, `650 × 520 px` label,
pixel magnifier/readout, and adjacent Capture button. The screenshot contains
only the synthetic grid and is saved at
[GNOME overlay render](verification/milestone3-gnome-overlay.png). This check
also exposed and fixed stacking: the selector now requests fullscreen and
raises its X11 window after Mutter processes that request.

**GTK overlay rendering and interaction in Xvfb:** Reproducible smoke runs use
the system Python GTK/Pillow bindings, `python3-xlib`, `xvfb-run`, and XTEST:

```sh
xvfb-run -a --server-args='-screen 0 1000x700x24' env NO_AT_BRIDGE=1 PYTHONPATH=src /usr/bin/python3 tools/xvfb_overlay_check.py button
xvfb-run -a --server-args='-screen 0 1000x700x24' env NO_AT_BRIDGE=1 PYTHONPATH=src /usr/bin/python3 tools/xvfb_overlay_check.py enter
xvfb-run -a --server-args='-screen 0 1000x700x24' env NO_AT_BRIDGE=1 PYTHONPATH=src /usr/bin/python3 tools/xvfb_overlay_check.py escape
xvfb-run -a --server-args='-screen 0 1000x700x24' env NO_AT_BRIDGE=1 PYTHONPATH=src /usr/bin/python3 tools/xvfb_overlay_check.py inspect
```

All four runs passed. The button scenario checked all eight resize handles,
interior movement, all eight resize cursors plus move and crosshair cursors,
button placement stability while the pointer moved, button click dispatch,
exact crop dimensions/pixels, and editor creation. The Enter scenario checked
keyboard confirmation and crop pixels; Escape cancelled. The inspect scenario
saved a rendered overlay screenshot, visually checked here: [Xvfb overlay
render](verification/milestone3-xvfb-overlay.png). It shows the dimmed outside,
clear selection, dashed edge, pixel dimensions, magnifier crosshair and pixel
readout, and adjacent Capture button. The fake backend raises if any overlay
path attempts a second desktop capture.

**Still unchecked:** This GNOME session has one monitor, so negative origins,
mixed scale factors, monitor seams, and multi-monitor fullscreen stacking
remain unverified. Native CUA window controls were unavailable, so pointer
and keyboard input was sent with XTEST; the resulting GNOME screenshot was
visually inspected.

**Automated tests:** `uv run --python 3.12 --with pytest python -m pytest -q`
passed (37 tests). `python3 -m compileall -q src/shooty` and
`git diff --check` passed.

## Milestone 2: X11 desktop capture

**Environment:** Ubuntu 24.04.4 LTS, GNOME Shell 46.0, `XDG_SESSION_TYPE=x11`,
one 3840x2160 monitor at scale factor 1.

**Composed-content readback:** Ran `X11CaptureBackend.capture_desktop()` while
the browser, terminal, editor, chat client, GNOME top panel, and dock were
visible. It returned a 3840x2160 RGB snapshot and one monitor mapping with
logical and pixel bounds `(0, 0, 3840, 2160)`. Opened the saved result and
visually confirmed the visible windows and panels appeared at their screen
positions. A second check showed an undecorated GTK window filled with RGB
`(217, 31, 79)` at screen position `(120, 120)`; the snapshot pixel at
`(160, 160)` read `(217, 30, 79)`, confirming composed window pixels and
coordinate alignment.

**Failure reporting:** GNOME Shell's screenshot D-Bus method returned
`AccessDenied: Screenshot is not allowed (9)`. The adapter fell back to X11
root readback, which succeeded. Then forced that readback path to raise an
injected `OSError`; the adapter raised `CaptureError` with both the GNOME Shell
denial and X11 readback failure in its message. The user-facing capture
controller is not implemented until milestone 3, so dialog presentation is
not yet checkable.

**Not checked:** The session has one monitor, so negative monitor origins,
mixed scale factors, monitor seams, and monitor-edge readback need verification
on a multi-monitor target desktop. This milestone does not provide an overlay;
the snapshot is taken before any Shooty overlay exists.

## Milestone 1 manual checks

## Release archive install smoke test

From an extracted release archive, as an ordinary user:

1. Run `./install.sh`.
2. Run `~/.local/bin/shooty --version` and confirm `shooty 0.1.0`.
3. Run `~/.local/bin/shooty --help` and confirm usage is printed without a display server.
4. Run `./uninstall.sh` and confirm `~/.local/bin/shooty` and the owned data directory are removed.

## Recorded archive smoke test

On the development host, extracted `dist/shooty-0.1.0.tar.gz` into a temporary directory and ran the sequence above with a fresh temporary `HOME`/`XDG_DATA_HOME` (without sudo or a Python package manager). Install printed its success message; `shooty --version` printed `shooty 0.1.0`; `shooty --help` exited successfully; repeat install succeeded; uninstall removed the launcher and owned data directory. This exercised filesystem isolation but used the current UID.

The original archive check used the current UID. The final milestone 6 archive was subsequently tested from a separate, newly created standard account (`shooty-smoke`) with no sudo access. The install, repeat install, version/help commands, opening a supplied PNG under Xvfb, and uninstall all passed. The test administrator created the account and launched the smoke commands as that user; no package manager was used by the test account.

After rebuilding the archive to include milestone 2, extracted it into a
temporary directory and used a temporary `HOME`/`XDG_DATA_HOME`. Install,
`shooty --help`, the installed backend capture `(3840, 2160)` with one monitor,
and uninstall all passed. This still used the current UID rather than a second
account.

Archive SHA-256 after adding milestone 2 capture code: `0db5c06b43d14be775d24bbccabe5e301cf4903e1b2233bd960d7d59be00698f`.

## Milestone 6: desktop integration and release candidate

**Environment:** Ubuntu 24.04.4 LTS, GNOME Shell 46.0, X11, GTK 3.24.

The final release archive is built on this Ubuntu 24.04 host with
`./tools/build_release.sh`. It contains the PyInstaller one-directory bundle
(Python runtime, application, and Pillow), root-free install and uninstall
scripts, a freedesktop launcher, SVG icon, and first-run README. GTK/GObject
Introspection typelibs, Cairo native libraries, and X11 are supplied by the
standard Ubuntu desktop. `desktop-file-validate packaging/shooty.desktop`
passed. The final archive passed fresh-account install, repeat install,
`shooty --version`, `shooty --help`, desktop-file validation, PNG editor launch
under Xvfb, and uninstall. The frozen capture overlay and frozen indicator
both remained running when launched on the live GNOME X11 session; their
processes were stopped after the smoke checks. The Ubuntu AppIndicators
extension was enabled. The live milestone 5 GTK check passed again and
exercised two simultaneously open editors, cross-window clipboard transfer,
PNG save, and dirty-close choices.

The complete automated suite passed with
`uv run --python 3.12 --with pytest python -m pytest -q` (51 tests).
Earlier recorded GNOME X11 checks for capture readback, overlay interaction,
and repeated independent capture invocations are documented under milestones
2 and 3 above.

Release candidate: `dist/shooty-0.1.0.tar.gz` (116 MB), SHA-256
`84c4904066a2b0ebc2889369cb02dcdc12b38027f570aa7ea3445e96edcb75e9`.
The checksum is also in `dist/shooty-0.1.0.tar.gz.sha256`. The full test
command `uv run --python 3.12 --with pytest python -m pytest -q` passed with
51 tests; `git diff --check` passed.

**Still requiring release sign-off:** There is no Git remote configured and
`boffman/shooty` does not exist on GitHub. GitHub CLI and REST repository
creation both returned HTTP 403, `Resource not accessible by personal access
token`, so no tagged release URL can be reported. I did not pin the launcher
through the Ubuntu Dock UI, physically
configure and press the suggested Shift+Alt+S custom shortcut, or visually
inspect the top-bar indicator menu. This session has one monitor, so negative
origins, mixed scale factors, seams, and multi-monitor stacking remain
unverified. Physical-mouse checks and the overwrite confirmation are also
still listed above. This archive is a tested release candidate; the release
and complete manual sign-off are not finished.
