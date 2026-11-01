# Copyable implementation goals

Use these in order, one `/goal` per fresh Codex thread opened in this repository. The prompts refer to the files and tests in the shared checkout, so clearing conversation context between milestones is fine. Do not start the next milestone until the current goal is verified and complete. Each goal asks the agent to print the next prompt verbatim when it finishes; that printed prompt is for the user to copy into a new thread.

The six milestones and acceptance checks are in [ARCHITECTURE.md](ARCHITECTURE.md). The product requirements are in [PLAN.md](PLAN.md). [AGENTS.md](AGENTS.md) applies to every coding turn.

## Goal 1 — Package skeleton, geometry, and installation proof

```text
/goal Complete milestone 1 of ARCHITECTURE.md for Shooty on Ubuntu 24.04 GNOME X11. Read AGENTS.md, PLAN.md, and ARCHITECTURE.md first. Create the installable Python package, shooty CLI and --help/--version commands, core rectangle and coordinate data types, pytest setup, and focused tests for normalized half-open rectangles, negative monitor origins, and logical-to-pixel mapping. Build a minimal GitHub Release-style archive with a root-free user-local install/uninstall path and prove it works from a clean user account without sudo or a Python package manager; document exact commands and evidence. Keep GTK imports out of headless CLI/help and pure modules. Run the focused and full test suites. Fix failures and continue until the acceptance checks pass. If target-system verification is unavailable, report the precise unverified check and required environment rather than claiming completion. Once the goal is achieved, report files changed and test/install evidence, then print the complete Goal 2 /goal prompt from GOALS.md verbatim in one code block as the final item. Do not begin Goal 2.
```

## Goal 2 — X11 capture backend and service

```text
/goal Complete milestone 2 of ARCHITECTURE.md for Shooty on Ubuntu 24.04 GNOME X11. Read AGENTS.md, PLAN.md, and ARCHITECTURE.md and inspect the current code before editing. Implement the CaptureBackend boundary, an X11 desktop snapshot with pixels and monitor mapping, and CaptureService paths for cropping an existing pre-overlay snapshot and capturing a fresh requested region. Reject invalid regions explicitly. Use fake-backend patterned-image unit tests to prove crop coordinates, edge bounds, and equal crop rules for interactive and direct requests. Manually verify on a real GNOME X11 desktop that the backend captures visible composed content at correct pixels and that capture failure is reported clearly; record the result in docs/manual-test.md. Run focused and full tests, repair failures, and preserve milestone 1 behavior. If the real desktop is unavailable, identify the unverified check rather than declaring the milestone complete. Once the goal is achieved, report evidence and print the complete Goal 3 /goal prompt from GOALS.md verbatim in one code block as the final item. Do not begin Goal 3.
```

## Goal 3 — Selection overlay and first editor window

```text
/goal Complete milestone 3 of ARCHITECTURE.md for Shooty on Ubuntu 24.04 GNOME X11. Read AGENTS.md, PLAN.md, and ARCHITECTURE.md and inspect completed milestones. Make shooty capture enter an overlay over a frozen pre-overlay desktop image with crosshair, dark outside area, clear selected area, dashed border, dimensions, and Enter/Escape controls. Add all corner and side resizing, interior move, correct hover cursors, pixel magnifier, and a stable clickable Capture button. Confirmed captures must crop the original snapshot and open in a new editor window; repeated invocations may leave several editors open. Keep selection state and hit testing free of GTK. Unit-test drag directions, handles, movement, clamping, transitions, and capture dispatch; manually check overlay and magnifier behavior on GNOME X11 and record the results. Run focused and full tests and fix failures. If GUI verification is unavailable, report exactly what remains unverified rather than claiming completion. Once the goal is achieved, report evidence and print the complete Goal 4 /goal prompt from GOALS.md verbatim in one code block as the final item. Do not begin Goal 4.
```

## Goal 4 — Editor operations and drawing tools

```text
/goal Complete milestone 4 of ARCHITECTURE.md for Shooty on Ubuntu 24.04 GNOME X11. Read AGENTS.md, PLAN.md, and ARCHITECTURE.md and inspect the existing editor. Implement per-window EditorDocument and tool state, fit and 100% zoom, horizontal/vertical flips, both 90-degree rotations, pen, line, arrow, rectangle, circle, ellipse, text, primary/secondary color controls including secondary None, and eyedropper. Preview drags without modifying document pixels; commit one operation on release. For arrows, mouse press fixes the tail, movement previews the head, and release commits shaft and head in primary color; zero-length drag commits nothing. Text uses primary glyphs over secondary background or transparency. Write focused headless tests for transforms, drawing bounds/pixels, preview/commit, arrow direction and head placement, colors, text background, and per-window isolation. Run focused and full tests, manually verify the GTK tools, and record evidence. Do not claim GUI checks passed if they could not run. Once the goal is achieved, report evidence and print the complete Goal 5 /goal prompt from GOALS.md verbatim in one code block as the final item. Do not begin Goal 5.
```

## Goal 5 — Clipboard, image selection, undo, and persistence

```text
/goal Complete milestone 5 of ARCHITECTURE.md for Shooty on Ubuntu 24.04 GNOME X11. Read AGENTS.md, PLAN.md, and ARCHITECTURE.md and inspect the current implementation. Add rectangular editor-image selection, copy to the normal Ctrl+C/Ctrl+V CLIPBOARD, paste from another Shooty editor or image-capable application as a movable floating region, commit/cancel, and undo/redo for all editor changes. Add PNG save/reopen, overwrite handling, saved-revision tracking, and Save/Discard/Cancel confirmation when closing a dirty image. Copy must not mark an image saved; failed saves remain dirty. Keep document logic separate from GTK clipboard and dialogs. Unit-test selection and paste pixels, cross-document isolation, undo branches, saved-state transitions, and store/clipboard failures with fakes. Manually test cross-window and external-app clipboard transfer, file dialogs, and close choices; record results. Run focused and full tests and repair regressions. If GUI checks are unavailable, report exact remaining verification rather than declaring completion. Once the goal is achieved, report evidence and print the complete Goal 6 /goal prompt from GOALS.md verbatim in one code block as the final item. Do not begin Goal 6.
```

## Goal 6 — Desktop integration and release

```text
/goal Complete milestone 6 of ARCHITECTURE.md and finish Shooty for Ubuntu 24.04 GNOME X11. Read AGENTS.md, PLAN.md, and ARCHITECTURE.md, audit all requirements against the implementation, and fix gaps found. Finish and publish a tagged GitHub Release with the root-free archive, user-local install/upgrade/uninstall scripts, stable shooty command, .desktop launcher and icon, dock pinning instructions, Shift+Alt+S custom shortcut instructions, optional top-bar AppIndicator, and README. Build the release artifact on Ubuntu 24.04 and verify it from a clean user account without sudo or a Python package manager. Run the full automated suite and the complete docs/manual-test.md checklist, including multiple simultaneous editors and repeated shortcut captures. Record release URL, artifact name, checksum, test commands/results, and any unverified target-desktop checks; if repository access or required checks are unavailable, report the blocker rather than claiming completion. When every requirement is verified, report the final release evidence and completion summary. This is the last goal; do not print or start another goal.
```
