"""Live GTK/X11 smoke check for milestone 5 clipboard and persistence UI."""
import os
import io
import subprocess
import tempfile
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk
from PIL import Image

from shooty.capture.overlay import open_editor
from shooty.editor.ports import GtkClipboard
from shooty.model import CapturedImage

app = Gtk.Application(application_id="org.shooty.Milestone5Check", flags=Gio.ApplicationFlags.NON_UNIQUE)


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children(): yield from descendants(child)


def canvas_event(area, event_type, x, y):
    event = Gdk.Event.new(event_type); event.window = area.get_window(); event.send_event = True
    event.x, event.y, event.button, event.time = x, y, 1, Gdk.CURRENT_TIME
    event.device = Gdk.Display.get_default().get_default_seat().get_pointer()
    Gtk.main_do_event(event)


def drag(area, start, end):
    canvas_event(area, Gdk.EventType.BUTTON_PRESS, *start)
    canvas_event(area, Gdk.EventType.MOTION_NOTIFY, *end)
    canvas_event(area, Gdk.EventType.BUTTON_RELEASE, *end)


def named_dialog(title):
    return next(w for w in Gtk.Window.list_toplevels() if w.get_visible() and w.get_title() == title)


def answer_dialog(title, response, filename=None):
    try: dialog = named_dialog(title)
    except StopIteration: return True
    dialog.response(response)
    return False


def activate(application):
    application.hold()
    pixel = (213, 74, 31, 255)
    a = open_editor(application, CapturedImage(Image.new("RGBA", (40, 30), pixel)))
    b = open_editor(application, CapturedImage(Image.new("RGBA", (40, 30), (0, 0, 0, 255))))
    a.present(); b.present()

    def run_check():
        clip_a = GtkClipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD))
        clip_b = GtkClipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD))
        wa, wb = list(descendants(a)), list(descendants(b))
        area_a = next(w for w in wa if isinstance(w, Gtk.DrawingArea))
        area_b = next(w for w in wb if isinstance(w, Gtk.DrawingArea))
        toggle_a = next(w for w in wa if isinstance(w, Gtk.ToggleButton) and w.get_label().lower() == "selection")
        toggle_a.set_active(True); drag(area_a, (3, 4), (8, 9))
        assert (a.document.selection.width, a.document.selection.height) == (5, 5)
        next(w for w in wa if isinstance(w, Gtk.Button) and w.get_label() == "Copy").clicked()
        export = subprocess.Popen(["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], stdout=subprocess.PIPE)
        deadline = time.monotonic() + 3
        while export.poll() is None and time.monotonic() < deadline:
            while Gtk.events_pending(): Gtk.main_iteration_do(False)
            time.sleep(.01)
        payload, _ = export.communicate(timeout=1)
        assert Image.open(io.BytesIO(payload)).size == (5, 5)
        assert clip_b.read_image().size == (5, 5)
        next(w for w in wb if isinstance(w, Gtk.Button) and w.get_label() == "Paste").clicked()
        drag(area_b, (0, 0), (10, 11))
        next(w for w in wb if isinstance(w, Gtk.Button) and w.get_label() == "Commit paste").clicked()
        assert b.document.image.getpixel((10, 11)) == pixel

        # Exercise a separate image-capable X11 application as clipboard owner.
        external = os.path.join(tempfile.gettempdir(), "shooty-m5-external.png")
        Image.new("RGBA", (3, 2), (19, 27, 201, 255)).save(external)
        subprocess.run(["xclip", "-selection", "clipboard", "-t", "image/png", "-i", external], check=True)
        assert b.document.paste_from_clipboard(clip_b, (0, 0))
        assert b.document.floating[0].size == (3, 2)
        b.document.cancel_paste()

        destination = os.path.join(os.getcwd(), "Screenshot.png")
        try: os.unlink(destination)
        except FileNotFoundError: pass
        widgets = list(descendants(a))
        save_button = next(w for w in widgets if isinstance(w, Gtk.Button) and w.get_label() == "Save")
        GLib.timeout_add(100, lambda: answer_dialog("Save image", Gtk.ResponseType.ACCEPT))
        save_button.clicked()
        assert os.path.exists(destination) and Image.open(destination).format == "PNG" and not a.document.dirty

        # Dirty close: Cancel retains the window; Discard closes it.
        a.document.transform("flip_horizontal"); assert a.document.dirty
        GLib.timeout_add(50, lambda: answer_dialog("Unsaved changes", Gtk.ResponseType.CANCEL))
        a.close(); assert a.get_visible() and a.document.dirty
        GLib.timeout_add(50, lambda: answer_dialog("Unsaved changes", Gtk.ResponseType.NO))
        a.close()
        def finish_check():
            assert not a.get_visible()
            b.document.transform("flip_vertical")
            close_path = destination
            b.document.path = destination
            GLib.timeout_add(50, lambda: answer_dialog("Unsaved changes", Gtk.ResponseType.YES))
            b.close()
            def verify_saved_close():
                assert not b.get_visible() and not b.document.dirty and b.document.path == close_path
                print("Milestone 5 GTK check passed: cross-window clipboard, xclip PNG export/import, PNG save, dirty close Cancel/Discard/Save")
                os.unlink(destination)
                application.release(); application.quit(); return False
            GLib.timeout_add(200, verify_saved_close)
            return False
        GLib.timeout_add(200, finish_check)
        return False

    GLib.timeout_add(500, run_check)


app.connect("activate", activate)
app.run([])
