"""GNOME Shell composed-screen capture adapter for X11 sessions."""
import os
import tempfile

from PIL import Image

from shooty.model import DesktopSnapshot, MonitorMapping, Rect
from .service import CaptureError


class X11CaptureBackend:
    """Read a composed desktop image through GNOME Shell's screenshot API.

    The method captures the whole desktop in one operation. Call it before
    constructing or showing the selection overlay.
    """

    def __init__(self, bus=None, display=None):
        # Imports are deferred so pure code and --help work without a display.
        try:
            import gi
            gi.require_version("Gdk", "3.0")
            gi.require_version("GdkX11", "3.0")
            from gi.repository import Gdk, GdkX11, Gio, GLib
        except Exception as exc:
            raise CaptureError(f"GTK 3/Gio capture support is unavailable: {exc}") from exc
        self._Gdk, self._GdkX11, self._Gio, self._GLib = Gdk, GdkX11, Gio, GLib
        self._bus = bus if bus is not None else Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._display = display if display is not None else Gdk.Display.get_default()

    def capture_desktop(self) -> DesktopSnapshot:
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or not os.environ.get("DISPLAY"):
            raise CaptureError("Shooty capture requires an X11 desktop session")
        if self._display is None:
            raise CaptureError("no active X11 display is available")
        if not isinstance(self._display, self._GdkX11.X11Display):
            raise CaptureError("Shooty capture requires an X11 desktop session")
        filename = None
        shell_error = None
        try:
            fd, filename = tempfile.mkstemp(prefix="shooty-desktop-", suffix=".png")
            os.close(fd)
            params = self._GLib.Variant("(bbs)", (False, False, filename))
            result = self._bus.call_sync(
                "org.gnome.Shell", "/org/gnome/Shell/Screenshot",
                "org.gnome.Shell.Screenshot", "Screenshot", params,
                None, self._Gio.DBusCallFlags.NONE, 30000, None)
            success, actual_filename = result.unpack()
            if success:
                image = Image.open(actual_filename or filename).convert("RGBA")
                image.load()
                return DesktopSnapshot(image=image, monitors=self._monitor_mappings(image.size))
            shell_error = "GNOME Shell reported that desktop capture failed"
        except Exception as exc:
            shell_error = str(exc)
        finally:
            if filename:
                try:
                    os.unlink(filename)
                except FileNotFoundError:
                    pass
        # Some GNOME policies disable Shell's screenshot method. Under X11,
        # GDK can read the compositor's visible root contents directly.
        try:
            image = self._capture_gdk_root()
            return DesktopSnapshot(image=image, monitors=self._monitor_mappings(image.size))
        except Exception as exc:
            raise CaptureError(
                "GNOME Shell and X11 screen readback both failed "
                f"(Shell: {shell_error}; X11: {exc})") from exc

    def _capture_gdk_root(self) -> Image.Image:
        screen = self._display.get_default_screen()
        root = screen.get_root_window()
        width, height = screen.get_width(), screen.get_height()
        pixbuf = self._Gdk.pixbuf_get_from_window(root, 0, 0, width, height)
        if pixbuf is None:
            raise RuntimeError("GDK returned no pixels from the X11 root window")
        mode = "RGBA" if pixbuf.get_has_alpha() else "RGB"
        return Image.frombytes(mode, (pixbuf.get_width(), pixbuf.get_height()),
                               bytes(pixbuf.get_pixels()), "raw", mode,
                               pixbuf.get_rowstride(), 1)

    def _monitor_mappings(self, image_size: tuple[int, int]) -> tuple[MonitorMapping, ...]:
        count = self._display.get_n_monitors()
        if count == 0:
            raise CaptureError("the X11 display reports no monitors")
        data = []
        for index in range(count):
            monitor = self._display.get_monitor(index)
            geometry = monitor.get_geometry()
            scale = max(1, monitor.get_scale_factor())
            logical = Rect(geometry.x, geometry.y, geometry.width, geometry.height)
            data.append((logical, scale))
        origin_x = min(rect.x for rect, _ in data)
        origin_y = min(rect.y for rect, _ in data)
        mappings = tuple(MonitorMapping(
            logical_rect=rect,
            pixel_rect=Rect((rect.x - origin_x) * scale, (rect.y - origin_y) * scale,
                            rect.width * scale, rect.height * scale))
            for rect, scale in data)
        right = max(m.pixel_rect.right for m in mappings)
        bottom = max(m.pixel_rect.bottom for m in mappings)
        if right > image_size[0] or bottom > image_size[1]:
            raise CaptureError(
                "GNOME screenshot dimensions do not match the X11 monitor mapping "
                f"(image {image_size[0]}x{image_size[1]}, mapped bounds {right}x{bottom})")
        return mappings
