"""GTK selection overlay and editor-window launcher."""
from .selection import Handle, SelectionModel, SelectionState
from .service import CaptureService, InvalidRegionError
from .controller import dispatch_selection
from shooty.model import Rect


def _gtk():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    # Register Pycairo's foreign converter explicitly; this also supports
    # frozen launchers where PyInstaller cannot infer GI's runtime import.
    gi.require_foreign("cairo")
    from gi.repository import Gdk, GdkPixbuf, Gtk, GLib
    return Gdk, GdkPixbuf, Gtk, GLib


def open_editor(application, captured):
    Gdk, GdkPixbuf, Gtk, GLib = _gtk()
    from shooty.editor.document import EditorDocument, ToolState
    from shooty.editor.ports import GtkClipboard, PillowImageStore
    doc=EditorDocument(captured.image); tools=ToolState(doc)
    clipboard=GtkClipboard(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)); store=PillowImageStore()
    paste_drag=[None]
    doc.zoom=min(1.0, 820/max(1,doc.image.height), 1080/max(1,doc.image.width))
    window=Gtk.ApplicationWindow(application=application,title="Shooty — Editor")
    window.set_default_size(max(720,min(captured.width+40,1200)),max(420,min(captured.height+100,900)))
    root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); bar=Gtk.Box(spacing=3); settings_bar=Gtk.Box(spacing=5)
    area=Gtk.DrawingArea(); area.set_can_focus(True)
    area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK)
    scroller=Gtk.ScrolledWindow(); scroller.add(area)
    def refresh():
        scale=doc.zoom; area.set_size_request(max(1,round(doc.image.width*scale)),max(1,round(doc.image.height*scale))); area.queue_draw()
    def render(cr, preview=True):
        image=doc.copy_image_for_display()
        if preview and tools.preview:
            from shooty.editor.document import draw_shape
            image=draw_shape(image,tools.preview)
        rgba=image.tobytes(); pix=GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(rgba),GdkPixbuf.Colorspace.RGB,True,8,image.width,image.height,image.width*4)
        cr.save(); cr.scale(doc.zoom,doc.zoom); Gdk.cairo_set_source_pixbuf(cr,pix,0,0); cr.paint(); cr.restore()
        if doc.selection:
            r=doc.selection; cr.save(); cr.scale(doc.zoom,doc.zoom); cr.set_source_rgb(1,1,0); cr.set_line_width(1/doc.zoom); cr.set_dash([4/doc.zoom,3/doc.zoom]); cr.rectangle(r.x+.5,r.y+.5,r.width-1,r.height-1); cr.stroke(); cr.restore()
    area.connect("draw",lambda _w,cr:(render(cr),False)[1])
    def coord(e): return (max(0,min(doc.image.width-1,int(e.x/doc.zoom))),max(0,min(doc.image.height-1,int(e.y/doc.zoom))))
    def press(_w,e):
        p=coord(e)
        if doc.floating is not None:
            image,(x,y)=doc.floating
            if x<=p[0]<x+image.width and y<=p[1]<y+image.height:
                paste_drag[0]=(p[0]-x,p[1]-y); return True
        if doc.tool=="eyedropper":
            color=doc.image.getpixel(p)
            set_picked_color(color)
            refresh()
        elif doc.tool=="text":
            dialog=Gtk.Dialog(title="Add text",transient_for=window,flags=0); dialog.add_button("Cancel",Gtk.ResponseType.CANCEL); dialog.add_button("Add",Gtk.ResponseType.OK)
            entry=Gtk.Entry(); entry.set_text("Text"); dialog.get_content_area().add(entry); dialog.show_all()
            if dialog.run()==Gtk.ResponseType.OK:
                from shooty.editor.document import Shape
                doc.apply(Shape("text",(p,),doc.primary,doc.width,doc.secondary,entry.get_text(),doc.font_size,doc.font_family))
            dialog.destroy(); refresh()
        else: tools.press(p); area.queue_draw()
        return True
    def motion(_w,e):
        if paste_drag[0] is not None:
            p=coord(e); doc.move_floating((p[0]-paste_drag[0][0],p[1]-paste_drag[0][1])); area.queue_draw()
        elif tools.start is not None: tools.move(coord(e)); area.queue_draw()
        return True
    def release(_w,e):
        if paste_drag[0] is not None:
            p=coord(e); doc.move_floating((p[0]-paste_drag[0][0],p[1]-paste_drag[0][1])); paste_drag[0]=None; refresh(); return True
        if doc.tool=="selection" and tools.start is not None:
            a,b=tools.start,coord(e); tools.cancel()
            if a!=b: doc.select_points(a,b)
            refresh(); return True
        if tools.start is not None: tools.release(coord(e)); refresh()
        return True
    area.connect("button-press-event",press); area.connect("motion-notify-event",motion); area.connect("button-release-event",release)
    tool_buttons=[]
    for name in ("pen","line","arrow","rectangle","circle","ellipse","text","eyedropper","selection"):
        b=Gtk.ToggleButton(label=name.title())
        def select_tool(button, n=name):
            if button.get_active():
                doc.tool=n
                for other in tool_buttons:
                    if other is not button and other.get_active(): other.set_active(False)
        b.connect("toggled",select_tool); tool_buttons.append(b); bar.pack_start(b,False,False,0)
        if name=="pen": b.set_active(True)
    for label,action in (("↔","flip_horizontal"),("↕","flip_vertical"),("⟲","rotate_left"),("⟳","rotate_right")):
        b=Gtk.Button(label=label); b.set_tooltip_text(action); b.connect("clicked",lambda _b,a=action:(doc.transform(a),refresh())); bar.pack_start(b,False,False,0)
    for label,z in (("Fit",0),("100%",1)):
        b=Gtk.Button(label=label)
        def zoom(_b,value=z):
            available_w=max(100,scroller.get_allocated_width()-24)
            available_h=max(100,scroller.get_allocated_height()-24)
            doc.zoom=1.0 if value else min(1.0,available_h/doc.image.height,available_w/doc.image.width); refresh()
        b.connect("clicked",zoom); bar.pack_start(b,False,False,0)
    primary=Gtk.ColorButton(); secondary=Gtk.ColorButton(); none=Gtk.CheckButton(label="Secondary None")
    slot=Gtk.ComboBoxText(); slot.append_text("Primary"); slot.append_text("Secondary"); slot.set_active(0)
    def rgba(c): return (round(c.red*255),round(c.green*255),round(c.blue*255),round(c.alpha*255))
    primary.set_use_alpha(True); secondary.set_use_alpha(True)
    primary.set_rgba(Gdk.RGBA(*(v/255 for v in doc.primary)))
    secondary.set_rgba(Gdk.RGBA(*(v/255 for v in doc.secondary)))
    primary.connect("color-set",lambda b:setattr(doc,"primary",rgba(b.get_rgba())))
    def set_secondary(button):
        color=rgba(button.get_rgba()); doc.secondary=color
        if none.get_active(): none.set_active(False)
    secondary.connect("color-set",set_secondary)
    none.connect("toggled",lambda b:setattr(doc,"secondary",None if b.get_active() else rgba(secondary.get_rgba())))
    width=Gtk.SpinButton.new_with_range(1,64,1); width.set_value(2); width.connect("value-changed",lambda b:setattr(doc,"width",b.get_value_as_int()))
    font=Gtk.FontButton.new_with_font("DejaVu Sans 16"); font.set_use_size(False)
    font.connect("font-set",lambda b:setattr(doc,"font_family",b.get_font_name()))
    font_size=Gtk.SpinButton.new_with_range(1,256,1); font_size.set_value(16); font_size.connect("value-changed",lambda b:setattr(doc,"font_size",b.get_value_as_int()))
    settings_bar.pack_start(slot,False,False,0); settings_bar.pack_start(Gtk.Label(label="Primary"),False,False,0); settings_bar.pack_start(primary,False,False,0); settings_bar.pack_start(Gtk.Label(label="Secondary"),False,False,0); settings_bar.pack_start(secondary,False,False,0); settings_bar.pack_start(none,False,False,0); settings_bar.pack_start(Gtk.Label(label="Stroke"),False,False,0); settings_bar.pack_start(width,False,False,0); settings_bar.pack_start(font,False,False,0); settings_bar.pack_start(font_size,False,False,0)
    def set_picked_color(color):
        color=tuple(color)
        rgba_color=Gdk.RGBA(color[0]/255,color[1]/255,color[2]/255,color[3]/255)
        if slot.get_active()==0:
            doc.primary=color; primary.set_rgba(rgba_color)
        else:
            doc.secondary=color; secondary.set_rgba(rgba_color)
            if none.get_active(): none.set_active(False)
    actions=Gtk.Box(spacing=3)
    def action_button(label, callback):
        button=Gtk.Button(label=label); button.connect("clicked",callback); actions.pack_start(button,False,False,0); return button
    def save_document(*_):
        target=doc.path
        if target is None:
            chooser=Gtk.FileChooserDialog(title="Save image",transient_for=window,action=Gtk.FileChooserAction.SAVE)
            chooser.add_buttons("Cancel",Gtk.ResponseType.CANCEL,"Save",Gtk.ResponseType.ACCEPT)
            chooser.set_do_overwrite_confirmation(True); chooser.set_current_name("Screenshot.png")
            response=chooser.run(); target=chooser.get_filename() if response==Gtk.ResponseType.ACCEPT else None; chooser.destroy()
            if target is None:return False
        try: doc.save(store,target); window.set_title("Shooty — "+target); return True
        except Exception as exc:
            dialog=Gtk.MessageDialog(transient_for=window,flags=0,message_type=Gtk.MessageType.ERROR,buttons=Gtk.ButtonsType.CLOSE,text=f"Could not save image: {exc}"); dialog.run(); dialog.destroy(); return False
    def close_request(*_):
        if not doc.dirty: return False
        dialog=Gtk.MessageDialog(transient_for=window,flags=0,message_type=Gtk.MessageType.QUESTION,buttons=Gtk.ButtonsType.NONE,text="Save changes before closing?")
        dialog.set_title("Unsaved changes")
        dialog.add_buttons("Cancel",Gtk.ResponseType.CANCEL,"Discard",Gtk.ResponseType.NO,"Save",Gtk.ResponseType.YES)
        response=dialog.run(); dialog.destroy()
        if response==Gtk.ResponseType.CANCEL:return True
        if response==Gtk.ResponseType.YES and not save_document():return True
        return False
    action_button("Copy",lambda *_: doc.copy_selection(clipboard) if doc.selection else clipboard.write_image(doc.image.copy()))
    action_button("Paste",lambda *_: (doc.paste_from_clipboard(clipboard,(0,0)),refresh()))
    action_button("Commit paste",lambda *_:(doc.commit_paste(),refresh()))
    action_button("Cancel paste",lambda *_:(doc.cancel_paste(),refresh()))
    action_button("Undo",lambda *_:(doc.undo(),refresh()))
    action_button("Redo",lambda *_:(doc.redo(),refresh()))
    action_button("Save",save_document)
    action_button("Close",lambda *_:window.close())
    root.pack_start(actions,False,False,0); root.pack_start(bar,False,False,0); root.pack_start(settings_bar,False,False,0); root.pack_start(scroller,True,True,0); window.add(root)
    area.connect("key-press-event",lambda _w,e: _editor_key(e,doc,clipboard,refresh))
    window.connect("delete-event",close_request)
    window.document=doc; window.tool_state=tools
    refresh(); window.show_all(); return window


def _editor_key(event, doc, clipboard, refresh):
    Gdk, _, _, _ = _gtk()
    if event.state & Gdk.ModifierType.CONTROL_MASK:
        if event.keyval in (Gdk.KEY_c, Gdk.KEY_C):
            if doc.selection: doc.copy_selection(clipboard)
            else: clipboard.write_image(doc.image.copy())
            return True
        if event.keyval in (Gdk.KEY_v, Gdk.KEY_V): doc.paste_from_clipboard(clipboard,(0,0)); refresh(); return True
        if event.keyval in (Gdk.KEY_z, Gdk.KEY_Z): doc.undo(); refresh(); return True
        if event.keyval in (Gdk.KEY_y, Gdk.KEY_Y): doc.redo(); refresh(); return True
    if event.keyval==Gdk.KEY_Escape and doc.floating is not None: doc.cancel_paste(); refresh(); return True
    if event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter) and doc.floating is not None: doc.commit_paste(); refresh(); return True
    return False


class SelectionOverlay:
    """One capture session. The snapshot is supplied before this is shown."""
    def __init__(self, application, service: CaptureService, snapshot, on_done):
        Gdk, GdkPixbuf, Gtk, GLib = _gtk()
        self.Gdk, self.GdkPixbuf, self.Gtk, self.GLib = Gdk, GdkPixbuf, Gtk, GLib
        self.service, self.snapshot, self.on_done = service, snapshot, on_done
        rects = [m.logical_rect for m in snapshot.monitors]
        self.bounds = Rect(min(r.x for r in rects), min(r.y for r in rects),
                           max(r.right for r in rects)-min(r.x for r in rects),
                           max(r.bottom for r in rects)-min(r.y for r in rects))
        self.model = SelectionModel(self.bounds)
        self.pointer = (self.bounds.x, self.bounds.y)
        self.magnifier_anchor = None
        self.window = Gtk.ApplicationWindow(application=application, title="Select a region")
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_accept_focus(True)
        self.window.set_app_paintable(True)
        self.window.move(self.bounds.x, self.bounds.y)
        self.window.set_default_size(self.bounds.width, self.bounds.height)
        self.overlay = Gtk.Overlay()
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_size_request(self.bounds.width, self.bounds.height)
        self.canvas.set_can_focus(True)
        self.canvas.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK |
                               Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.overlay.add(self.canvas)
        self.button = Gtk.Button(label="Capture")
        self.button.set_halign(Gtk.Align.START)
        self.button.set_valign(Gtk.Align.START)
        self.button.set_no_show_all(True)
        self.overlay.add_overlay(self.button)
        self.button.connect("realize", lambda widget: widget.get_window().set_cursor(
            Gdk.Cursor.new(Gdk.CursorType.HAND2)))
        self.window.add(self.overlay)
        self.canvas.connect("draw", self._draw)
        self.canvas.connect("button-press-event", self._press)
        self.canvas.connect("button-release-event", self._release)
        self.canvas.connect("motion-notify-event", self._motion)
        self.window.connect("key-press-event", self._key)
        self.window.connect("delete-event", self._delete)
        self.button.connect("clicked", lambda *_: self._confirm())
        self._monitor_pixbufs = tuple(
            self._make_pixbuf(snapshot.image.crop((m.pixel_rect.x, m.pixel_rect.y,
                                                    m.pixel_rect.right, m.pixel_rect.bottom)))
            for m in snapshot.monitors)
        self._finished = False

    def _make_pixbuf(self, image):
        data = image.convert("RGBA").tobytes()
        return self.GdkPixbuf.Pixbuf.new_from_bytes(
            self.GLib.Bytes.new(data), self.GdkPixbuf.Colorspace.RGB, True, 8,
            image.width, image.height, image.width * 4)

    def show(self):
        self.window.show_all()
        # Apply the virtual-desktop origin after mapping; some window managers
        # ignore the pre-map position hint for application windows.
        self.window.move(self.bounds.x, self.bounds.y)
        self.button.hide()
        self.canvas.grab_focus()
        self.window.present()
        # Mutter places fullscreen client windows above ordinary keep-above
        # windows. The selector must cover fullscreen desktop content too.
        self.window.fullscreen()
        self._set_window_cursor(self.Gdk.CursorType.CROSSHAIR)
        # Apply a final X11 restack after Mutter processes the fullscreen
        # request, so a previously fullscreen application cannot stay above.
        self.GLib.timeout_add(100, self._raise_window)

    def _raise_window(self):
        gdk_window = self.window.get_window()
        if gdk_window is not None:
            gdk_window.raise_()
        return False

    def _draw(self, widget, cr):
        cr.save()
        for monitor, source in zip(self.snapshot.monitors, self._monitor_pixbufs):
            p, r = monitor.pixel_rect, monitor.logical_rect
            cr.save()
            cr.translate(r.x-self.bounds.x, r.y-self.bounds.y)
            cr.scale(r.width/p.width, r.height/p.height)
            self.Gdk.cairo_set_source_pixbuf(cr, source, 0, 0)
            cr.paint()
            cr.restore()
        r = self.model.rect
        cr.set_source_rgba(0, 0, 0, .55)
        if r is None:
            cr.paint()
        else:
            l, t, rr, b = r.x-self.bounds.x, r.y-self.bounds.y, r.right-self.bounds.x, r.bottom-self.bounds.y
            cr.rectangle(0, 0, self.bounds.width, t); cr.rectangle(0, b, self.bounds.width, self.bounds.height-b)
            cr.rectangle(0, t, l, b-t); cr.rectangle(rr, t, self.bounds.width-rr, b-t); cr.fill()
            cr.set_source_rgba(1, 1, 1, .95); cr.set_line_width(1.5); cr.set_dash([6, 4])
            cr.rectangle(l+.5, t+.5, max(0, rr-l-1), max(0, b-t-1)); cr.stroke(); cr.set_dash([])
            cr.set_source_rgba(1, 1, 1, 1); cr.select_font_face("Sans", 0, 0); cr.set_font_size(14)
            try:
                crop = self.service.capture_from_snapshot(self.snapshot, r)
                dimensions = f"{crop.width} × {crop.height} px"
            except InvalidRegionError:
                dimensions = "Region includes an area without a monitor"
            cr.move_to(l+6, max(18, t-6)); cr.show_text(dimensions)
            self._draw_magnifier(cr)
        cr.restore()
        return False

    def _draw_magnifier(self, cr):
        x, y = self.pointer
        monitor = next((m for m in self.snapshot.monitors if m.logical_rect.x <= x < m.logical_rect.right and
                        m.logical_rect.y <= y < m.logical_rect.bottom), self.snapshot.monitors[0])
        lr, pr = monitor.logical_rect, monitor.pixel_rect
        # If the pointer is in a virtual-desktop gap, sample the nearest pixel
        # on this monitor. Clamp the source coordinates to its actual pixels.
        x = min(max(x, lr.x), lr.right-1e-6)
        y = min(max(y, lr.y), lr.bottom-1e-6)
        px = min(pr.right-1, pr.x + int((x-lr.x)*pr.width/lr.width))
        py = min(pr.bottom-1, pr.y + int((y-lr.y)*pr.height/lr.height))
        image = self.snapshot.image
        monitor_image = image.crop((pr.x, pr.y, pr.right, pr.bottom))
        tile = monitor_image.crop((px-pr.x-8, py-pr.y-8, px-pr.x+9, py-pr.y+9))
        tile = tile.resize((136, 136), ImageNearest)
        pix = self._make_pixbuf(tile)
        if self.magnifier_anchor is not None and self.model.state == SelectionState.READY:
            mx, my = self.magnifier_anchor
        else:
            mx, my = self._magnifier_origin(self.pointer)
        cr.set_source_rgb(.05,.05,.05); cr.rectangle(mx-2,my-2,140,140); cr.fill()
        self.Gdk.cairo_set_source_pixbuf(cr,pix,mx,my); cr.paint()
        cr.set_source_rgb(1,.2,.2); cr.set_line_width(1)
        cr.move_to(mx+68,my); cr.line_to(mx+68,my+136); cr.move_to(mx,my+68); cr.line_to(mx+136,my+68); cr.stroke()
        pixel = image.getpixel((min(px,image.width-1),min(py,image.height-1)))
        cr.set_source_rgb(1,1,1); cr.rectangle(mx,my+136,136,15); cr.fill()
        cr.set_source_rgb(0,0,0); cr.set_font_size(10); cr.move_to(mx+3,my+147)
        cr.show_text(f"({px}, {py})  {pixel[:3]}")

    def _local(self, event):
        return event.x+self.bounds.x, event.y+self.bounds.y

    def _magnifier_origin(self, pointer):
        mx = min(max(round(pointer[0]-self.bounds.x+24), 0), max(0, self.bounds.width-140))
        my = round(pointer[1]-self.bounds.y+24)
        if my+152 > self.bounds.height:
            my=max(0, round(pointer[1]-self.bounds.y-176))
        return mx, my

    def _press(self, _w, e):
        if e.button == 1: self.model.press(*self._local(e)); self.canvas.queue_draw()
        return True

    def _release(self, _w, e):
        if e.button == 1:
            self.model.release(*self._local(e)); self.canvas.queue_draw(); self._position_button()
        return True

    def _motion(self, _w, e):
        self.pointer = self._local(e)
        if self.model.state in (SelectionState.CREATING, SelectionState.ADJUSTING):
            self.model.motion(*self.pointer)
        else:
            self._set_cursor(self.model.hit_test(*self.pointer))
        self.canvas.queue_draw()
        return True

    def _set_cursor(self, handle):
        cursors = {None:self.Gdk.CursorType.CROSSHAIR, Handle.MOVE:self.Gdk.CursorType.FLEUR,
                   Handle.N:self.Gdk.CursorType.TOP_SIDE, Handle.S:self.Gdk.CursorType.BOTTOM_SIDE,
                   Handle.E:self.Gdk.CursorType.RIGHT_SIDE, Handle.W:self.Gdk.CursorType.LEFT_SIDE,
                   Handle.NW:self.Gdk.CursorType.TOP_LEFT_CORNER, Handle.SE:self.Gdk.CursorType.BOTTOM_RIGHT_CORNER,
                   Handle.NE:self.Gdk.CursorType.TOP_RIGHT_CORNER, Handle.SW:self.Gdk.CursorType.BOTTOM_LEFT_CORNER}
        self._set_window_cursor(cursors[handle])

    def _set_window_cursor(self, cursor_type):
        gdk_window = self.window.get_window()
        if gdk_window is not None:
            gdk_window.set_cursor(self.Gdk.Cursor.new(cursor_type))

    def _position_button(self):
        if not self.model.rect: self.button.hide(); return
        self.magnifier_anchor = self._magnifier_origin(self.pointer)
        x, y = self.magnifier_anchor
        if y + 186 > self.bounds.height:
            y = max(8, y - 38)
        else:
            y += 154
        x = min(max(x, 8), max(8, self.bounds.width-100))
        self.button.set_margin_start(x); self.button.set_margin_top(y); self.button.show()

    def _key(self, _w, e):
        if e.keyval == self.Gdk.KEY_Escape: self._finish(None); return True
        if e.keyval in (self.Gdk.KEY_Return, self.Gdk.KEY_KP_Enter): self._confirm(); return True
        return False

    def _confirm(self):
        if self.model.rect and self.model.state == SelectionState.READY:
            try:
                dispatch_selection(self.service, self.snapshot, self.model.rect, self._finish)
            except Exception as exc:
                dialog=self.Gtk.MessageDialog(transient_for=self.window,flags=0,message_type=self.Gtk.MessageType.ERROR,
                    buttons=self.Gtk.ButtonsType.CLOSE,text=str(exc)); dialog.run(); dialog.destroy()

    def _finish(self, captured):
        if self._finished:return
        self._finished=True; self.window.destroy(); self.on_done(captured)

    def _delete(self, *_): self._finish(None); return True


from PIL import Image as _Image
ImageNearest = getattr(getattr(_Image, "Resampling", _Image), "NEAREST")
