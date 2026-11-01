"""GTK application wiring for capture sessions and independent editors."""
from .capture.overlay import SelectionOverlay, open_editor
from .capture.service import CaptureService
from .capture.x11 import X11CaptureBackend


def run(command="capture", filename=None):
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gio

    class ShootyApplication(Gtk.Application):
        def __init__(self):
            # Each shortcut invocation gets a session; each result gets its own editor.
            super().__init__(application_id="org.shooty.Shooty",
                             flags=Gio.ApplicationFlags.NON_UNIQUE)
            self.windows = []

        def do_activate(self):
            if command == "indicator":
                try:
                    from .indicator import install_indicator
                    self.indicator = install_indicator(self, Gtk)
                except Exception as exc:
                    print(f"shooty: optional AppIndicator unavailable: {exc}")
                    self.quit()
                return
            if command == "open":
                from PIL import Image
                from .model import CapturedImage
                try:
                    image = Image.open(filename).convert("RGBA")
                    self.windows.append(open_editor(self, CapturedImage(image)))
                except Exception as exc:
                    print(f"shooty: could not open {filename}: {exc}")
                return
            self._start_capture()

        def _start_capture(self):
            try:
                service = CaptureService(X11CaptureBackend())
                # This call must finish before any Shooty window is created.
                snapshot = service.capture_desktop()
                overlay = SelectionOverlay(self, service, snapshot,
                    lambda image: self._captured(image))
                self.overlay = overlay
                overlay.show()
            except Exception as exc:
                print(f"shooty: could not start capture overlay: {exc}")
                dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CLOSE, text=f"Shooty could not capture the desktop: {exc}")
                dialog.run(); dialog.destroy()
                if command != "indicator":
                    self.quit()

        def _captured(self, image):
            if image is not None:
                self.windows.append(open_editor(self, image))
            elif command != "indicator":
                self.quit()

    app = ShootyApplication()
    return app.run([])
