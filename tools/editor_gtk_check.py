"""Exercise the live GTK editor callbacks on an X11 display.

Run with: PYTHONPATH=src /usr/bin/python3 tools/editor_gtk_check.py
The canvas events are synthesized, so this is an integration smoke check, not
a substitute for visually checking mouse behavior on the target desktop.
"""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gio, Gtk
from PIL import Image

from shooty.capture.overlay import open_editor
from shooty.model import CapturedImage


def widgets_under(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from widgets_under(child)


def canvas_event(area, event_type, x, y):
    event = Gdk.Event.new(event_type)
    event.window = area.get_window()
    event.send_event = True
    event.x, event.y = x, y
    event.button = 1
    event.time = Gdk.CURRENT_TIME
    event.device = Gdk.Display.get_default().get_default_seat().get_pointer()
    Gtk.main_do_event(event)


def drag(area, start, end):
    canvas_event(area, Gdk.EventType.BUTTON_PRESS, *start)
    canvas_event(area, Gdk.EventType.MOTION_NOTIFY, *end)
    canvas_event(area, Gdk.EventType.BUTTON_RELEASE, *end)


app = Gtk.Application(application_id="org.shooty.EditorGtkCheck", flags=Gio.ApplicationFlags.NON_UNIQUE)


def activate(application):
    window = open_editor(application, CapturedImage(Image.new("RGBA", (300, 200), (20, 30, 40, 255))))
    window.set_default_size(900, 650)
    window.present()

    def check():
        widgets = list(widgets_under(window))
        area = next(w for w in widgets if isinstance(w, Gtk.DrawingArea))
        tools = {w.get_label().lower(): w for w in widgets if isinstance(w, Gtk.ToggleButton)}
        buttons = [w for w in widgets if isinstance(w, Gtk.Button)]
        assert window.document.zoom == 1

        start = len(window.document._history)
        tools["line"].set_active(True)
        canvas_event(area, Gdk.EventType.BUTTON_PRESS, 10, 10)
        canvas_event(area, Gdk.EventType.MOTION_NOTIFY, 80, 50)
        assert len(window.document._history) == start
        assert window.document.image.getpixel((10, 10)) == (20, 30, 40, 255)
        canvas_event(area, Gdk.EventType.BUTTON_RELEASE, 80, 50)

        for name, a, b in (
            ("arrow", (20, 90), (130, 90)), ("pen", (15, 20), (50, 50)),
            ("rectangle", (30, 30), (60, 60)), ("circle", (30, 30), (60, 60)),
            ("ellipse", (30, 30), (60, 60)),
        ):
            tools[name].set_active(True)
            drag(area, a, b)
        assert len(window.document._history) == start + 6
        count = len(window.document._history)
        tools["arrow"].set_active(True)
        drag(area, (30, 30), (30, 30))
        assert len(window.document._history) == count

        def click_tip(tip):
            next(w for w in buttons if w.get_tooltip_text() == tip).clicked()

        for tip in ("flip_horizontal", "flip_vertical", "rotate_left", "rotate_right"):
            click_tip(tip)
        assert window.document.image.size == (300, 200)

        color_buttons = [w for w in widgets if isinstance(w, Gtk.ColorButton)]
        color_buttons[0].set_rgba(Gdk.RGBA(.1, .2, .3, 1))
        color_buttons[0].emit("color-set")
        assert window.document.primary == (26, 51, 76, 255)
        none = next(w for w in widgets if isinstance(w, Gtk.CheckButton))
        none.set_active(True)
        assert window.document.secondary is None
        slot = next(w for w in widgets if isinstance(w, Gtk.ComboBoxText))
        slot.set_active(1)
        tools["eyedropper"].set_active(True)
        canvas_event(area, Gdk.EventType.BUTTON_PRESS, 0, 0)
        assert window.document.secondary == (20, 30, 40, 255) and not none.get_active(), (window.document.secondary, none.get_active(), slot.get_active(), tools["eyedropper"].get_active())

        font = next(w for w in widgets if isinstance(w, Gtk.FontButton))
        font.set_font_name("DejaVu Serif")
        font.emit("font-set")
        size = next(w for w in widgets if isinstance(w, Gtk.SpinButton) and w.get_value_as_int() == 16)
        size.set_value(24)
        assert window.document.font_size == 24

        tools["text"].set_active(True)

        def answer_text_dialog():
            dialogs = [w for w in Gtk.Window.list_toplevels() if w.get_title() == "Add text"]
            if not dialogs:
                return True

            def find_entry(widget):
                if isinstance(widget, Gtk.Entry):
                    return widget
                if isinstance(widget, Gtk.Container):
                    for child in widget.get_children():
                        found = find_entry(child)
                        if found:
                            return found

            find_entry(dialogs[0]).set_text("UI")
            dialogs[0].response(Gtk.ResponseType.OK)
            return False

        before_text = len(window.document._history)
        GLib.timeout_add(20, answer_text_dialog)
        canvas_event(area, Gdk.EventType.BUTTON_PRESS, 100, 100)
        assert len(window.document._history) == before_text + 1

        next(w for w in buttons if w.get_label() == "100%").clicked()
        assert window.document.zoom == 1
        window.document.zoom = .2
        next(w for w in buttons if w.get_label() == "Fit").clicked()
        assert window.document.zoom > .2
        print("GTK editor check passed: drawing, preview/commit, arrows, text, colors, eyedropper, transforms, zoom")
        application.quit()
        return False

    GLib.timeout_add(600, check)


app.connect("activate", activate)
app.run([])
