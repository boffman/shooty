# Shooty implementation plan

## Target and approach

- Target **Ubuntu 24.04 GNOME running an X11 session**. Detect the display backend at startup and show a clear error for unsupported sessions. Wayland support is a separate project because its capture and overlay permissions differ.
- Build a small desktop application in Python with PyGObject/GTK 3, Cairo, Pillow, and GdkPixbuf. GTK provides windows, drawing, cursor changes, image clipboard support, and dialogs without a browser runtime.
- Distribute a tested Ubuntu 24.04 GitHub Release archive containing the application, launcher, and icon. A user-local installer must work without root.
- Expose `shooty capture` to enter region selection immediately, `shooty` to launch the normal application, and `shooty open FILE` to open an image in an editor. Use a single application instance to route repeated capture commands while allowing many editor windows.
- Keep the capture controller, selection geometry, editor document, drawing tools, clipboard, and desktop integration as separate modules. The editor document owns the image pixels and undo history; each window owns its own document.

## Architecture and extension points

- Define plain data types for `ScreenRect`, `CaptureRequest`, `CapturedImage`, tool settings, and editor commands. Coordinates use an explicit desktop coordinate space and a separate image pixel coordinate space; conversions happen at one boundary.
- Define a `CaptureBackend` interface with a `capture_desktop()` operation returning pixels and monitor mapping. The X11 implementation handles screen access; selection UI calls this interface rather than X11 APIs directly. A future Wayland implementation can supply another backend.
- Define a `CaptureService` that can crop a supplied desktop snapshot or take a fresh snapshot and crop a requested rectangle, then hand the result to a result handler. Interactive selection uses its pre-overlay snapshot; a future script or timer can request a fresh capture without opening an overlay.
- Keep selection geometry and hit-testing free of GTK. The overlay translates pointer and keyboard events into state changes and renders the resulting selection state.
- Keep image transforms and drawing operations in an `EditorDocument` and command objects, independent of widgets. The GTK editor renders the document and invokes commands. Undo/Redo acts on commands or document snapshots according to operation size.
- Isolate `ClipboardPort`, `ImageStore`, and `CaptureResultHandler` interfaces so copying, saving, and opening an editor can be composed or replaced. Avoid putting UI dialogs inside these services.
- Do not build a scheduler or scripting language in the first version. Preserve a callable `capture_region(rect)` path and a stable command-line entry point so a later `shooty capture --region X1,Y1,X2,Y2` and timed capture runner can be added without changing the editor or X11 backend.

## 1. Prove the X11 capture path

1. Read the composed desktop into an immutable image buffer **before** showing any Shooty overlay. Test the chosen X11/GDK readback method against GNOME's compositor; switch to a direct X11 capture method if the root-window readback does not contain the visible desktop.
2. Record monitor bounds and the mapping between GTK logical coordinates and image pixels. Test multiple monitors, negative monitor origins, mixed scale factors, and monitor edges.
3. Capture only once per selection session so the dimming, magnifier, pointer, and controls never appear in the screenshot. Fail visibly if the desktop cannot be read.

## 2. Selection overlay

1. Show a borderless, always-on-top overlay covering the virtual desktop. Draw the frozen screenshot, a translucent dark layer outside the selection, and a contrasting dashed selection outline. Start with a crosshair cursor.
2. Implement a state machine: idle, creating selection, adjusting selection, and ready to capture. Normalize drag direction so any pair of corners works. Escape cancels; Enter captures a nonempty selection.
3. Hit-test the four corners, four edges, and selection interior. Change to diagonal, horizontal, vertical, or move cursors as appropriate. Dragging a handle resizes; dragging inside moves the region. Clamp the result to valid captured pixels and show its pixel dimensions.
4. Show a magnifier containing nearby **original** pixels, with a center crosshair and pixel coordinates. Place it away from the pointer and keep it within a monitor. Provide a Capture button adjacent to it; keep that button stable and clickable once a selection exists.
5. On confirmation, crop the frozen image at full pixel resolution, close the overlay, and open the crop in a new editor window. A new shortcut invocation starts another independent capture.

## 3. Editor

1. Provide a canvas with fit-to-window and 100% zoom, a compact tool palette, and toolbar actions for Copy, Save, and Close. Each capture gets its own window and document.
2. Add horizontal and vertical flips and 90-degree rotations in both directions. Keep dimensions, selection bounds, and undo history consistent after transforms.
3. Add freehand pen, line, arrow, rectangle, circle, and ellipse tools. Preview shapes during dragging; commit on release. The arrow tool sets its tail on mouse press, tracks its head at the pointer while dragging, and commits the shaft and arrowhead at the release position, using the primary color. Offer stroke width and primary/secondary color controls. The circle tool constrains equal width and height; the ellipse is unconstrained.
4. Add an eyedropper that samples the displayed image pixel into the selected color slot. Add a text tool with font and size controls; render glyphs in the primary color over the secondary color, or no background when secondary is set to None.
5. Add rectangular image selection, Copy, and Paste. Copy places the selected pixels on the standard Ctrl+C/Ctrl+V `CLIPBOARD` as an image. Paste creates a movable floating image region that can be committed or cancelled, including when the source is another Shooty editor window. Support Undo/Redo for edits and paste commits.
6. Save as PNG by default, with a file chooser and overwrite confirmation. Track the saved revision; prompt to Save, Discard, or Cancel on closing a dirty document. Copying does not mark the document saved.

## 4. Desktop integration

1. Install a `shooty` command and a freedesktop `.desktop` launcher with an icon into user-owned locations so Shooty appears in the application grid and can be pinned to the Ubuntu Dock.
2. Document the GNOME custom keyboard shortcut: command `shooty capture`, suggested binding Shift+Alt+S. The launcher also offers a Capture action where supported.
3. Offer an optional persistent top-bar AppIndicator with Capture and Quit actions, using Ubuntu's AppIndicator support. The dock launcher and shortcut work without a resident process.
4. Build and publish a versioned GitHub Release archive, with a user-local install/uninstall path and a short first-run guide. Test installation on a clean Ubuntu 24.04 GNOME X11 account without `sudo`.

## 5. Tests, verification, and delivery order

1. Use `pytest` from the start. Add unit tests alongside each module before moving to the next milestone. Test public behavior through the interfaces, with a fake capture backend and in-memory clipboard/store where useful. Prove the user-local release installation path early, before the editor becomes large.
2. Test rectangle normalization, edge/corner hit-testing, movement, resizing, clamping, and logical-to-pixel coordinate mapping. Verify capture readback separately on a real GNOME X11 session.
3. Complete and manually test the overlay: all drag directions, handles, cursor shapes, magnifier, Enter/button/Escape, multi-monitor edges, and repeated invocation.
4. Test image transforms, drawing geometry (including arrow direction, head placement, and a zero-length drag), text background modes, color picking, selection and paste behavior, dirty revision tracking, and Undo/Redo as the editor tools are implemented.
5. Add service tests showing that interactive and direct-region capture requests reach the same backend and result handler. This is the contract for later scripting and timed captures.
6. Test PNG save/reopen, clipboard paste into another app, dirty-close choices, multiple simultaneous windows, keyboard shortcut, dock pinning, and optional top-bar indicator.
7. Keep a manual GNOME X11 checklist for compositor and desktop behavior that cannot be reliably covered by headless unit tests.

## Confirmed decisions

- First target: Ubuntu 24.04 GNOME on X11.
- Copy and paste use the usual Ctrl+C/Ctrl+V `CLIPBOARD` selection.
- The top-bar indicator is optional.
- An ordinary Ubuntu 24.04 user must be able to install from GitHub without root.
