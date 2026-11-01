# Instructions for implementing Shooty

Read [PLAN.md](PLAN.md) and [ARCHITECTURE.md](ARCHITECTURE.md) before coding. The target is Ubuntu 24.04 GNOME on X11, using Python, PyGObject/GTK 3, Cairo, Pillow, and pytest. [GOALS.md](GOALS.md) contains one copyable `/goal` prompt per milestone.

## Working rules

- Implement one milestone at a time in the order listed in `ARCHITECTURE.md`. Complete its tests and acceptance check before starting the next milestone.
- Keep GTK, X11, filesystem dialogs, and clipboard calls out of the pure geometry and image modules. Pass dependencies through constructors. Do not use global mutable application state.
- Put behavior in small named functions or classes. Prefer explicit data types and documented coordinate spaces over clever abstractions. Avoid a generic plugin framework or scheduler in the first release.
- Add or update focused `pytest` tests for each piece of non-UI behavior as it is implemented. Test public behavior and edge cases; use fakes for capture and clipboard boundaries. Run the relevant tests after each change and the full suite at each milestone.
- The interactive capture must crop the screenshot taken **before** the overlay appears. It must never recapture the screen after the overlay is visible.
- Keep CLI, capture service, and editor independent so a later direct-region or timed capture can reuse them.
- Maintain a short `README.md` with install, launch, keyboard shortcut, test, and supported-session instructions as implementation progresses.
- Prove the root-free GitHub Release install path early. Do not assume development headers, a Python package manager, or `sudo` are available to the end user. Keep developer setup separate from end-user installation.
- If a GUI behavior cannot be tested headlessly, record a manual test in `docs/manual-test.md` and run it on a real Ubuntu 24.04 GNOME X11 session when available. Do not claim a GUI check passed without running it.
- If a milestone is blocked by an unavailable X11 desktop, continue pure modules and tests; report the precise unverified behavior.

## Definition of done

A milestone is done when its behavior is implemented, its focused tests pass, and its manual checks are documented. The project is done when every requirement in `PLAN.md` is present and the final manual checklist has been run on the target desktop.
