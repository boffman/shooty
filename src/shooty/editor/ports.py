"""Boundary protocols and Pillow image-store implementation for editor documents."""
from pathlib import Path
from typing import Protocol
from PIL import Image


class ClipboardPort(Protocol):
    def write_image(self, image: Image.Image) -> None: ...
    def read_image(self) -> Image.Image | None: ...


class ImageStore(Protocol):
    def save_png(self, path, image: Image.Image) -> None: ...
    def load_image(self, path) -> Image.Image: ...


class PillowImageStore:
    """PNG store. Existing paths are overwritten only after caller approval."""
    def save_png(self, path, image):
        image.save(path, format="PNG")

    def load_image(self, path):
        with Image.open(path) as image:
            return image.convert("RGBA")


class GtkClipboard:
    """GTK CLIPBOARD adapter; call only from the GTK main thread."""
    def __init__(self, gtk_clipboard):
        self.clipboard = gtk_clipboard
        self._owned_image = None
        self._owned_pixbuf = None

    def write_image(self, image):
        self._owned_image = image.convert("RGBA").copy()
        import gi
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf, GLib
        raw = self._owned_image.tobytes()
        self._owned_pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(raw), GdkPixbuf.Colorspace.RGB, True, 8,
            self._owned_image.width, self._owned_image.height, self._owned_image.width * 4)
        self.clipboard.set_image(self._owned_pixbuf)
        self.clipboard.store()

    def read_image(self):
        pixbuf = self.clipboard.wait_for_image()
        if pixbuf is None: return None
        pixels = pixbuf.get_pixels()
        channels, stride = pixbuf.get_n_channels(), pixbuf.get_rowstride()
        mode = "RGBA" if pixbuf.get_has_alpha() else "RGB"
        raw = b"".join(pixels[y*stride:y*stride+pixbuf.get_width()*channels]
                       for y in range(pixbuf.get_height()))
        return Image.frombytes(mode, (pixbuf.get_width(), pixbuf.get_height()), raw).convert("RGBA")
