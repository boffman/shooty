"""Exercise the GTK overlay with synthetic X11 input under Xvfb.

Requires the system Python GTK/Pillow bindings and optional python-xlib.
Run this script through xvfb-run; it is intentionally separate from pytest so
the pure suite remains display-independent.
"""
import subprocess
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
from PIL import Image
from Xlib import X, XK, display
from Xlib.ext import xtest

from shooty.capture.overlay import SelectionOverlay, open_editor
from shooty.capture.service import CaptureService
from shooty.model import DesktopSnapshot, MonitorMapping, Rect

SCENARIOS = ('button', 'enter', 'escape', 'inspect')
scenario = sys.argv[1] if len(sys.argv) > 1 else 'button'
if scenario not in SCENARIOS:
    raise SystemExit(f"scenario must be one of: {', '.join(SCENARIOS)}")
xdisplay = display.Display()
image = Image.new('RGB', (1000, 700))
for y in range(image.height):
    for x in range(image.width):
        image.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
snapshot = DesktopSnapshot(image, (MonitorMapping(Rect(0, 0, 1000, 700), Rect(0, 0, 1000, 700)),))

class NoRecapture:
    def capture_desktop(self):
        raise AssertionError('overlay must use the supplied pre-overlay snapshot')

app = Gtk.Application(application_id='org.shooty.XvfbCheck', flags=Gio.ApplicationFlags.NON_UNIQUE)
state = {'step': 0, 'overlay': None, 'editor': None, 'failed': False}


def point(x, y):
    xtest.fake_input(xdisplay, X.MotionNotify, x=x, y=y)
    xdisplay.sync()


def drag(start, end):
    point(*start)
    xtest.fake_input(xdisplay, X.ButtonPress, detail=1)
    point(*end)
    xtest.fake_input(xdisplay, X.ButtonRelease, detail=1)
    xdisplay.sync()


def finish_check():
    result = state.get('result')
    assert result is not None, 'capture handler did not receive a crop'
    expected_size = (200, 150) if scenario == 'enter' else (270, 220)
    assert result.image.size == expected_size, result.image.size
    expected_origin = (100, 100) if scenario == 'enter' else (90, 90)
    assert result.image.getpixel((0, 0)) == image.getpixel(expected_origin)
    editor = state['editor']
    assert editor is not None and editor.get_title() == 'Shooty'
    print(scenario.upper() + '_FLOW_OK', result.image.size, 'editor window opened', flush=True)
    app.quit()
    return False


def escape_done(captured):
    assert captured is None, captured
    print('ESCAPE_FLOW_OK selection cancelled', flush=True)
    app.quit()


def activate(_app):
    service = CaptureService(NoRecapture())
    callback = escape_done if scenario == 'escape' else lambda captured: on_capture(captured)
    overlay = SelectionOverlay(app, service, snapshot, callback)
    state['overlay'] = overlay
    overlay.show()
    GLib.timeout_add(300, do_step)
    GLib.timeout_add_seconds(15, timed_out)


def timed_out():
    state['failed'] = True
    print('XVFB_CHECK_TIMEOUT', flush=True)
    app.quit()
    return False


def on_capture(captured):
    state['result'] = captured
    state['editor'] = open_editor(app, captured)
    GLib.timeout_add(200, finish_check)


sequence = [
    # Create in reverse so normalization is exercised through GTK events.
    ((300, 250), (100, 100), Rect(100, 100, 200, 150)),
    ((100, 100), (90, 90), Rect(90, 90, 210, 160)),
    ((195, 90), (195, 80), Rect(90, 80, 210, 170)),
    ((300, 80), (310, 70), Rect(90, 70, 220, 180)),
    ((310, 160), (330, 160), Rect(90, 70, 240, 180)),
    ((330, 250), (340, 260), Rect(90, 70, 250, 190)),
    ((215, 260), (220, 280), Rect(90, 70, 250, 210)),
    ((90, 280), (80, 290), Rect(80, 70, 260, 220)),
    ((80, 180), (70, 180), Rect(70, 70, 270, 220)),
    ((200, 180), (220, 200), Rect(90, 90, 270, 220)),
]


def verify_step():
    i = state['step']
    model = state['overlay'].model
    if model.rect != sequence[i][2]:
        raise AssertionError(f'step {i} expected {sequence[i][2]}, got {model.rect}')
    assert model.state.value == 'ready'
    print('STEP_OK', i, model.rect)
    state['step'] += 1
    if scenario == 'button' and i == 0:
        state['cursor_i'] = 0
        GLib.timeout_add(100, cursor_test)
    else:
        GLib.timeout_add(100, do_step)
    return False


cursor_cases = [
    ((100, 100), Gdk.CursorType.TOP_LEFT_CORNER),
    ((200, 100), Gdk.CursorType.TOP_SIDE),
    ((300, 100), Gdk.CursorType.TOP_RIGHT_CORNER),
    ((300, 175), Gdk.CursorType.RIGHT_SIDE),
    ((300, 250), Gdk.CursorType.BOTTOM_RIGHT_CORNER),
    ((200, 250), Gdk.CursorType.BOTTOM_SIDE),
    ((100, 250), Gdk.CursorType.BOTTOM_LEFT_CORNER),
    ((100, 175), Gdk.CursorType.LEFT_SIDE),
    ((200, 175), Gdk.CursorType.FLEUR),
    ((400, 400), Gdk.CursorType.CROSSHAIR),
]


def cursor_test():
    i = state['cursor_i']
    if i >= len(cursor_cases):
        GLib.timeout_add(100, do_step)
        return False
    point(*cursor_cases[i][0])
    GLib.timeout_add(100, cursor_verify)
    return False


def cursor_verify():
    i = state['cursor_i']
    expected = cursor_cases[i][1]
    cursor = state['overlay'].window.get_window().get_cursor()
    actual = cursor.get_cursor_type()
    assert actual == expected, (i, actual, expected)
    print('CURSOR_OK', i, expected.value_nick, flush=True)
    state['cursor_i'] += 1
    GLib.timeout_add(50, cursor_test)
    return False


def save_screenshot():
    subprocess.run(['xwd', '-root', '-silent', '-out', '/tmp/shooty-xvfb-overlay.xwd'], check=True)
    print('OVERLAY_SCREENSHOT_SAVED', flush=True)
    app.quit()
    return False


def do_step():
    print('DO_STEP', state['step'], flush=True)
    overlay = state['overlay']
    if scenario == 'escape':
        if state['step'] == 0:
            drag((280, 220), (120, 120))
            state['step'] = 1
            GLib.timeout_add(200, do_step)
            return False
        if state['step'] == 1:
            assert overlay.model.rect == Rect(120, 120, 160, 100)
            keycode = xdisplay.keysym_to_keycode(XK.string_to_keysym('Escape'))
            xtest.fake_input(xdisplay, X.KeyPress, detail=keycode)
            xtest.fake_input(xdisplay, X.KeyRelease, detail=keycode)
            xdisplay.sync()
            state['step'] = 2
            return False
        return False
    if scenario == 'enter':
        if state['step'] == 0:
            drag((300, 250), (100, 100))
            state['step'] = 1
            GLib.timeout_add(200, do_step)
            return False
        if state['step'] == 1:
            assert overlay.model.rect == Rect(100, 100, 200, 150)
            keycode = xdisplay.keysym_to_keycode(XK.string_to_keysym('Return'))
            xtest.fake_input(xdisplay, X.KeyPress, detail=keycode)
            xtest.fake_input(xdisplay, X.KeyRelease, detail=keycode)
            xdisplay.sync()
            state['step'] = 2
            return False
        return False
    if state['step'] == 0:
        drag(*sequence[0][:2])
        GLib.timeout_add(200, verify_step)
        return False
    i = state['step']
    if 1 <= i < len(sequence):
        drag(*sequence[i][:2])
        GLib.timeout_add(200, verify_step)
        return False
    if i == len(sequence):
        if scenario == 'inspect':
            point(800, 600)
            GLib.timeout_add(200, save_screenshot)
            return False
        button = overlay.button
        allocation = button.get_allocation()
        original = (allocation.x, allocation.y, allocation.width, allocation.height)
        margins = (button.get_margin_start(), button.get_margin_top())
        assert button.get_visible() and button.get_mapped()
        point(900, 600)
        GLib.timeout_add(150, lambda: check_button(original, margins))
        return False
    return False


def check_button(original, margins):
    button = state['overlay'].button
    allocation = button.get_allocation()
    actual = (allocation.x, allocation.y, allocation.width, allocation.height)
    assert actual == original, (original, actual)
    assert (button.get_margin_start(), button.get_margin_top()) == margins
    x = button.get_margin_start() + allocation.width // 2
    y = button.get_margin_top() + allocation.height // 2
    point(x, y)
    xtest.fake_input(xdisplay, X.ButtonPress, detail=1)
    xtest.fake_input(xdisplay, X.ButtonRelease, detail=1)
    xdisplay.sync()
    print('BUTTON_STABLE_AND_CLICKED_OK', margins, flush=True)
    return False


app.connect('activate', activate)
app.run([])
raise SystemExit(1 if state['failed'] else 0)
