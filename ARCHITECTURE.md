# Shooty architecture and implementation guide

This guide turns [PLAN.md](PLAN.md) into small coding tasks. Favor a working vertical slice over building every abstraction in advance. The first working slice is: launch `shooty capture`, select a rectangle, press Enter, and see an editor window with the exact selected pixels.

## Dependency direction

```text
CLI / Gtk.Application
  -> capture controller -> capture service -> CaptureBackend (X11 adapter)
                        -> selection model (pure Python)
                        -> overlay view (GTK/Cairo)
  -> editor window -> editor controller -> EditorDocument / tool operations (pure Python + Pillow)
                                     -> ClipboardPort / ImageStore adapters
```

The arrows are allowed calls. Lower layers must not import their callers. The X11 adapter, GTK views, clipboard adapter, and file dialogs belong at the edge. Pure modules must import without a display server, so `pytest` can run headlessly.

## Suggested package layout

```text
src/shooty/
  __main__.py             # CLI arguments and application startup
  app.py                  # Gtk.Application, windows, command routing
  model.py                # Rect, Snapshot, CaptureRequest, color/tool settings
  capture/
    ports.py              # CaptureBackend protocol
    service.py            # snapshot, crop, and result dispatch
    x11.py                # X11 implementation and monitor geometry
    selection.py          # state machine, hit testing, resize/move
    overlay.py            # GTK/Cairo rendering and input translation
  editor/
    document.py           # pixels, selection, saved state, undo/redo
    operations.py         # image transforms and drawing geometry
    tools.py              # press/move/release tool state
    window.py             # GTK editor UI
  io/
    clipboard.py          # Gtk.Clipboard adapter
    image_store.py        # PNG read/write adapter
packaging/
  install.sh              # user-local launcher, icon, and app installation
  uninstall.sh            # remove only Shooty-owned user files
tests/
  test_geometry.py
  test_selection.py
  test_capture_service.py
  test_editor_operations.py
  test_editor_document.py
  test_tools.py
docs/manual-test.md
```

Names may change, but preserve the boundaries. Do not place a 1,000-line application in `__main__.py` or `app.py`.

## Data contracts and coordinate rules

- Use immutable `Rect(x, y, width, height)` values with positive width/height for an actual capture. Treat bounds as half-open: `[x, x+width) × [y, y+height)`. Normalize two drag points in one helper. Define clearly whether the pointer release pixel is included; tests must lock the rule.
- Distinguish **desktop logical coordinates**, **snapshot pixel coordinates**, and **editor image pixels**. A snapshot carries the desktop origin, pixel size, and monitor/scale mapping needed to convert between them. Never assume the primary monitor starts at `(0, 0)` or that the scale factor is one.
- `CaptureBackend.capture_desktop() -> DesktopSnapshot` returns image pixels plus geometry metadata. No GTK window or X11 handle escapes from this adapter.
- `CaptureService.capture_from_snapshot(snapshot, rect) -> CapturedImage` crops the frozen image. `capture_fresh_region(rect)` obtains a new snapshot and uses the same crop path. Reject empty or out-of-bounds rectangles with explicit errors.
- `CapturedImage` owns pixels, dimensions, and optional capture metadata. The editor receives a copy or immutable source so edits cannot mutate the capture snapshot.
- Use a small `CaptureResultHandler` protocol, such as `handle(image)`, to route a completed capture to a new editor window. Tests can supply a recording handler.
- The editor document exposes commands such as `apply(operation)`, `undo()`, `redo()`, `copy_selection()`, and `paste_image(image, position)`. Views call these methods; they do not alter pixel arrays directly.
- The clipboard adapter uses the standard X11 `CLIPBOARD` selection for Ctrl+C/Ctrl+V. Keep a copy of image data alive for as long as the clipboard owns it.

## Selection state machine

Use explicit states: `IDLE`, `CREATING`, `READY`, and `ADJUSTING`. Input events produce a new selection state and a redraw request. Hit-test corners first, then edges, then interior, using a fixed handle tolerance in **screen logical pixels**. In `READY`, hovering chooses the appropriate resize or move cursor. While dragging, preserve the opposite edge/corner and prevent negative dimensions. Escape cancels the capture session; Enter captures only a nonempty rectangle.

Draw the frozen desktop image first, then the dim layer clipped to the area outside the selection, then the dashed outline and handles. The magnifier samples the frozen pixels. Keep the Capture button reachable when the pointer moves onto it; avoid repositioning it under the pointer during a click. The final crop always uses the original snapshot, never pixels rendered in the overlay.

## Editor tool contract

Each pointer tool handles `press(image_point)`, `move(image_point)`, `release(image_point)`, and `cancel()`. It returns preview geometry during movement and one operation on release. Convert canvas coordinates to image pixels before calling a tool. Do not write preview pixels into the document. This makes cancellation and Undo predictable.

- Pen: record points during drag; commit a stroke on release.
- Line, rectangle, circle, ellipse: normalize drag geometry; circle constrains equal axes. Define a single stroke-width rule and use it consistently for preview and final rendering.
- Arrow: press fixes the tail, move previews the shaft and head, release fixes the head. Use primary color. Derive arrowhead points from the normalized direction vector, with a head size based on stroke width and a sensible minimum/maximum. A zero-length drag makes no operation.
- Text: collect text and font settings in a dialog or inline editor, then commit one operation. Primary is glyph color; secondary is a solid background or `None` for transparency.
- Eyedropper: sample the image pixel under the pointer, not a scaled display pixel or preview overlay; update the selected color slot.
- Image selection: store a rectangle separately from image pixels. Paste creates a floating region; moving it is a preview, and commit is one undoable operation. Escape cancels the floating region.

Give each editor window its own `EditorDocument`, selection, tool state, and undo history. The clipboard is shared at the desktop boundary. For Save/dirty state, track a saved history position or unique revision identity that survives Undo/Redo and branch edits; copying must not change dirty state. Save failures must leave the document dirty.

## Milestones and acceptance checks

1. **Package skeleton, geometry, and release spike.** Create installable package, CLI entry point, data types, and `pytest` setup. Unit tests cover normalization, half-open crop bounds, negative desktop origins, and scale conversion. `python -m shooty --help` works without a display. Produce a minimal user-local release archive and install it on a clean Ubuntu 24.04 user account without root; resolve packaging blockers before building the editor.
2. **Capture backend and service.** Implement X11 snapshot and the pure crop service. Tests use a fake backend with patterned pixels. Manually confirm the screenshot matches visible GNOME X11 content and excludes Shooty UI.
3. **Overlay and first editor window.** Implement crosshair, dimming, selection, dashed border, Enter/Escape, and opening a new editor. Then add handle resizing, move, cursor changes, magnifier, and Capture button. Unit-test the selection state machine; manually check each cursor and monitor edge.
4. **Editor operations.** Implement flips, rotations, pen, line, arrow, rectangle, circle, ellipse, text, colors, and eyedropper. Write image-level tests for pixels/bounds and tool tests for preview versus commit. Verify arrow directions and zero-length drag.
5. **Clipboard, selection, and persistence.** Implement Ctrl+C/Ctrl+V image transfer, floating paste, Undo/Redo, PNG save/reopen, and dirty-close dialog. Test with in-memory adapters plus manual paste into a different application.
6. **Desktop integration and release.** Add icon, `.desktop` file, install instructions, Shift+Alt+S shortcut instructions, dock pinning, and optional AppIndicator. Build a versioned GitHub Release archive on Ubuntu 24.04, then manually test fresh install, upgrade, uninstall, and repeated shortcut invocations with several editor windows open.

At the end of every milestone: run the focused tests, run the full test suite, update the manual checklist, and state what remains unverified. Do not move a feature into a later milestone without updating the plan.

## Future automation seam

Keep the capture service callable without constructing the overlay or editor. A later command can accept `--region X1,Y1,X2,Y2 --every SECONDS --output ...` and call `capture_fresh_region()` on a timer. Do not implement this now, but write one service test proving that direct-region capture and interactive capture use the same crop rules. The result handler can later choose editor, clipboard, file, or script callback.

## Root-free GitHub distribution

The primary end-user artifact should be a versioned Linux archive, built and tested on Ubuntu 24.04. Start with a PyInstaller one-directory bundle and verify that it includes the Python runtime, PyGObject bindings, Cairo/Pillow modules, and required GTK typelibs/resources. If a clean-machine test reveals missing system libraries, record exactly what Ubuntu Desktop already supplies and what the bundle must include; do not silently require `apt` or developer packages. PyGObject documents PyInstaller as a supported deployment option, but the actual bundle still needs target-system testing.

The archive should include `install.sh`, `uninstall.sh`, the bundled app, a `.desktop` file, and icons. `install.sh` copies into `${XDG_DATA_HOME:-$HOME/.local/share}/shooty`, creates `${HOME}/.local/bin/shooty`, and installs the desktop entry and icon under user XDG data directories. It must be idempotent, avoid overwriting unrelated files, and explain how to add `~/.local/bin` to `PATH` if needed. `uninstall.sh` removes only files it installed. Keep the executable command and desktop entry stable across upgrades. Add a release checksum and a clean-user smoke test that runs `shooty --version`, launches the GUI, and opens an image.

The end-user instructions should show one install path from a tagged GitHub Release. Keep Python package metadata for development and building, but do not require an end-user Python package manager. Make the archive install, upgrade, and uninstall checks part of release acceptance.
