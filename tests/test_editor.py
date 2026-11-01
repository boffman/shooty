from PIL import Image
from shooty.editor.document import EditorDocument, Shape, ToolState, arrow_points


def test_transforms_dimensions_and_pixels():
    d=EditorDocument(Image.new("RGBA",(3,2),(0,0,0,255))); d.image.putpixel((0,0),(255,0,0,255))
    d.transform("flip_horizontal"); assert d.image.getpixel((2,0))[0]==255
    d.transform("rotate_left"); assert d.image.size==(2,3) and d.image.getpixel((0,0))[0]==255
    d.transform("rotate_right"); assert d.image.size==(3,2) and d.image.getpixel((2,0))[0]==255
    d.transform("flip_vertical"); assert d.image.getpixel((2,1))[0]==255


def test_preview_does_not_mutate_then_release_commits_once():
    d=EditorDocument(Image.new("RGBA",(30,30),(0,0,0,0))); t=ToolState(d)
    t.press((2,3)); t.move((20,3)); assert d.image.getbbox() is None
    t.release((20,3)); assert d.image.getbbox() is not None and len(d._history)==1


def test_arrow_direction_head_and_zero_drag():
    ends=arrow_points((2,10),(22,10),2); assert ends and ends[0][0]<22 and ends[1][0]<22
    d=EditorDocument(Image.new("RGBA",(30,30),(0,0,0,0))); d.tool="arrow"; t=ToolState(d)
    t.press((5,5)); assert t.release((5,5)) is None and not d._history
    t.press((5,15)); t.move((25,15)); shape=t.release((25,15))
    assert shape.points==((5,15),(25,15)) and d.image.getpixel((25,15))[3]
    ends=arrow_points((5,15),(25,15),2)
    assert all(d.image.getpixel(point)[3] for point in ends)


def test_color_and_text_background_modes():
    d=EditorDocument(Image.new("RGBA",(100,40),(0,0,0,0))); d.primary=(255,0,0,255); d.secondary=(0,0,255,255)
    d.apply(Shape("text",((5,5),),d.primary,2,d.secondary,"A",24))
    assert (0,0,255,255) in d.image.get_flattened_data()
    d.image=Image.new("RGBA",(100,40),(0,0,0,0)); d.apply(Shape("text",((5,5),),d.primary,2,None,"A",24))
    assert d.image.getbbox() is not None and any(px[3]==0 for px in d.image.get_flattened_data())
    d.image.putpixel((90,30),(3,4,5,255)); assert d.sample(90,30)==(3,4,5,255)==d.primary


def test_document_and_tool_state_are_per_window():
    a=EditorDocument(Image.new("RGBA",(5,5))); b=EditorDocument(Image.new("RGBA",(5,5)))
    ta,tb=ToolState(a),ToolState(b); ta.press((1,1)); ta.move((4,4))
    assert tb.preview is None and b.image.getbbox() is None


def test_shape_bounds_and_pixels():
    for kind in ("line","rectangle","circle","ellipse","pen"):
        d=EditorDocument(Image.new("RGBA",(40,40),(0,0,0,0)))
        d.apply(Shape(kind,((5,6),(20,16)),(8,9,10,255),2))
        bbox=d.image.getbbox()
        assert bbox is not None and bbox[0]>=0 and bbox[1]>=0 and bbox[2]<=40 and bbox[3]<=40
        assert (8,9,10,255) in d.image.get_flattened_data()
        if kind=="circle": assert abs((bbox[2]-bbox[0])-(bbox[3]-bbox[1]))<=2
        if kind=="ellipse": assert (bbox[2]-bbox[0])>(bbox[3]-bbox[1])


class MemoryClipboard:
    def __init__(self): self.image=None; self.fail_write=False; self.fail_read=False
    def write_image(self,image):
        if self.fail_write: raise OSError("clipboard write failed")
        self.image=image.copy()
    def read_image(self):
        if self.fail_read: raise OSError("clipboard read failed")
        return self.image.copy() if self.image else None


class MemoryStore:
    def __init__(self): self.images={}; self.fail=False
    def save_png(self,path,image):
        if self.fail: raise OSError("disk full")
        self.images[str(path)]=image.copy()
    def load_image(self,path): return self.images[str(path)].copy()


def test_selection_copy_clipboard_paste_move_commit_and_cancel():
    source=EditorDocument(Image.new("RGBA",(5,4),(0,0,0,0)))
    source.image.putpixel((1,1),(255,0,0,255)); source.image.putpixel((2,2),(0,255,0,255))
    source.select_points((1,1),(3,3)); clipboard=MemoryClipboard(); source.copy_selection(clipboard)
    assert clipboard.image.size==(2,2) and clipboard.image.getpixel((0,0))==(255,0,0,255)
    assert not source.dirty  # copy does not create a revision
    target=EditorDocument(Image.new("RGBA",(5,4),(0,0,255,255)))
    assert target.paste_from_clipboard(clipboard,(0,0))
    target.move_floating((2,1)); assert target.image.getpixel((2,1))==(0,0,255,255)
    target.commit_paste()
    assert target.image.getpixel((2,1))==(255,0,0,255) and target.dirty
    assert source.image.getpixel((1,1))==(255,0,0,255)  # documents do not alias
    target.paste_image(Image.new("RGBA",(1,1),(9,8,7,255)),(0,0)); target.cancel_paste()
    assert target.image.getpixel((0,0))==(0,0,255,255)


def test_undo_redo_branches_and_saved_revision_identity():
    d=EditorDocument(Image.new("RGBA",(10,10),(0,0,0,0)))
    d.apply(Shape("line",((1,1),(2,2)),(255,0,0,255))); first=d.revision
    d.undo(); assert not d.dirty and d.can_redo
    d.apply(Shape("line",((4,4),(5,5)),(0,255,0,255)))
    assert not d.can_redo and d.dirty and d.revision != first
    d.undo(); assert not d.dirty
    d.redo(); assert d.dirty


def test_store_save_reopen_dirty_transitions_and_failures():
    store=MemoryStore(); d=EditorDocument(Image.new("RGBA",(3,2),(1,2,3,255)))
    d.apply(Shape("line",((0,0),(2,1)),(9,9,9,255)))
    store.fail=True
    try: d.save(store,"x.png")
    except OSError: pass
    else: assert False
    assert d.dirty and d.path is None
    store.fail=False; d.save(store,"x.png"); assert not d.dirty
    reopened=EditorDocument.reopen(store,"x.png"); assert not reopened.dirty and reopened.image==d.image
    reopened.apply(Shape("line",((0,1),(2,0)),(4,5,6,255))); assert reopened.dirty
    reopened.undo(); assert not reopened.dirty


def test_clipboard_errors_do_not_mutate_document_or_saved_state():
    d=EditorDocument(Image.new("RGBA",(2,2),(0,0,0,0))); d.select_points((0,0),(1,1))
    clipboard=MemoryClipboard(); clipboard.fail_write=True
    try: d.copy_selection(clipboard)
    except OSError: pass
    else: assert False
    assert not d.dirty and d.floating is None
    clipboard.fail_write=False; clipboard.write_image(Image.new("RGBA",(1,1),(1,1,1,255)))
    clipboard.fail_read=True
    try: d.paste_from_clipboard(clipboard)
    except OSError: pass
    else: assert False
    assert d.floating is None and not d.dirty


def test_selection_transforms_with_image_and_undo_redo():
    d=EditorDocument(Image.new("RGBA",(5,3)))
    d.select_points((1,0),(4,2)); d.transform("rotate_left")
    assert (d.selection.x,d.selection.y,d.selection.width,d.selection.height)==(0,1,2,3)
    d.undo(); assert (d.selection.x,d.selection.y,d.selection.width,d.selection.height)==(1,0,3,2)
    d.redo(); assert (d.selection.x,d.selection.y,d.selection.width,d.selection.height)==(0,1,2,3)


def test_selection_rejects_empty_or_out_of_bounds_regions():
    d=EditorDocument(Image.new("RGBA",(4,3)))
    assert d.select_points((2,2),(2,0)) is None
    try: d.select_points((-1,0),(2,2))
    except ValueError: pass
    else: assert False
    try: d.copy_selection(MemoryClipboard())
    except ValueError: pass
    else: assert False


def test_floating_paste_can_preview_and_commit_past_canvas_edges():
    d=EditorDocument(Image.new("RGBA",(2,2),(0,0,0,255)))
    d.paste_image(Image.new("RGBA",(3,3),(200,10,20,255)),(-1,-1))
    preview=d.copy_image_for_display()
    assert preview.getpixel((0,0))==(200,10,20,255)
    assert d.commit_paste() and d.image.getpixel((1,1))==(200,10,20,255)


def test_png_store_round_trip(tmp_path):
    from shooty.editor.ports import PillowImageStore
    store=PillowImageStore(); d=EditorDocument(Image.new("RGBA",(3,2),(10,20,30,40)))
    path=tmp_path/"roundtrip.png"; d.save(store,path)
    reopened=EditorDocument.reopen(store,path)
    assert reopened.image.size==(3,2) and reopened.image.getpixel((1,1))==(10,20,30,40)
    assert reopened.path==str(path) and not reopened.dirty
