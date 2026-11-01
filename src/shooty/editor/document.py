"""Per-window image state and immutable drawing operations."""
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class ImageRect:
    """Half-open rectangle in editor image-pixel coordinates."""
    x: int
    y: int
    width: int
    height: int
    @property
    def right(self): return self.x + self.width
    @property
    def bottom(self): return self.y + self.height
    @classmethod
    def from_points(cls, x1, y1, x2, y2):
        left, right = sorted((x1, x2)); top, bottom = sorted((y1, y2))
        return cls(left, top, right-left, bottom-top)


@dataclass(frozen=True)
class Shape:
    kind: str
    points: tuple[tuple[int, int], ...]
    color: tuple[int, int, int, int]
    width: int = 2
    secondary: tuple[int, int, int, int] | None = None
    text: str = ""
    font_size: int = 16
    font_family: str = "Sans"


def arrow_points(tail, head, width):
    """Return the two arrowhead endpoints, or None for a zero vector."""
    import math
    dx, dy = head[0]-tail[0], head[1]-tail[1]
    length = math.hypot(dx, dy)
    if not length: return None
    size = max(8, min(24, width*4))
    ux, uy = dx/length, dy/length
    base = (head[0]-ux*size, head[1]-uy*size)
    return tuple((round(base[0]+s*(-uy)*size*.45), round(base[1]+s*ux*size*.45)) for s in (-1, 1))


def draw_shape(image, shape):
    """Render one operation into a copy; all points are image pixels."""
    result = image.copy().convert("RGBA")
    d = ImageDraw.Draw(result)
    p, c, w = shape.points, shape.color, max(1, shape.width)
    if shape.kind in ("pen", "line"):
        if len(p) == 1: d.point(p[0], fill=c)
        else: d.line(p, fill=c, width=w)
    elif shape.kind in ("rectangle", "ellipse", "circle"):
        a, b = p[0], p[-1]
        if shape.kind == "circle":
            side = max(abs(b[0]-a[0]), abs(b[1]-a[1]))
            b = (a[0] + (side if b[0]>=a[0] else -side), a[1] + (side if b[1]>=a[1] else -side))
        box = (min(a[0],b[0]), min(a[1],b[1]), max(a[0],b[0]), max(a[1],b[1]))
        getattr(d, {"rectangle":"rectangle", "ellipse":"ellipse", "circle":"ellipse"}[shape.kind])(box, outline=c, width=w)
    elif shape.kind == "arrow":
        a,b=p
        if a == b: return result
        d.line((a,b), fill=c, width=w)
        ends=arrow_points(a,b,w)
        if ends: d.line((ends[0],b,ends[1]), fill=c, width=w)
    elif shape.kind == "text":
        x,y=p[0]
        family=shape.font_family.lower()
        font_file="DejaVuSerif.ttf" if "serif" in family else "DejaVuSansMono.ttf" if ("mono" in family or "courier" in family) else "DejaVuSans.ttf"
        font=ImageFont.truetype(font_file, shape.font_size)
        box=d.textbbox((x,y),shape.text,font=font)
        if shape.secondary is not None: d.rectangle(box, fill=shape.secondary)
        d.text((x,y),shape.text,font=font,fill=c)
    return result


class EditorDocument:
    def __init__(self, image):
        self.image=image.convert("RGBA").copy()
        self.primary=(255,0,0,255); self.secondary=(255,255,255,255)
        self.tool="pen"; self.width=2; self.zoom=1.0; self.font_size=16; self.font_family="Sans"
        self.selection = None
        self.floating = None  # (RGBA pixels, (x, y)); preview only until commit
        self._states = [(self.image.copy(), 0, None)]
        self._cursor = 0
        self._next_revision = 1
        self.revision = 0
        self.saved_revision = 0
        self.path = None

    @property
    def dirty(self):
        return self.revision != self.saved_revision

    @property
    def can_undo(self): return self._cursor > 0

    @property
    def can_redo(self): return self._cursor + 1 < len(self._states)

    @property
    def _history(self):
        """Compatibility view used by the milestone 4 pointer checks."""
        return [s[0] for s in self._states[:self._cursor]]

    def _commit_state(self):
        del self._states[self._cursor + 1:]
        self.revision = self._next_revision
        self._next_revision += 1
        self._states.append((self.image.copy(), self.revision, self.selection))
        self._cursor += 1

    def _restore(self):
        image, self.revision, self.selection = self._states[self._cursor]
        self.image = image.copy()
        self.floating = None

    def apply(self, shape):
        self.image=draw_shape(self.image,shape)
        self._commit_state()

    def transform(self, action):
        actions={"flip_horizontal":Image.Transpose.FLIP_LEFT_RIGHT,"flip_vertical":Image.Transpose.FLIP_TOP_BOTTOM,
                 "rotate_left":Image.Transpose.ROTATE_90,"rotate_right":Image.Transpose.ROTATE_270}
        old_width, old_height = self.image.size
        self.image=self.image.transpose(actions[action])
        if self.selection:
            r=self.selection
            if action == "flip_horizontal": self.selection=ImageRect(old_width-r.right,r.y,r.width,r.height)
            elif action == "flip_vertical": self.selection=ImageRect(r.x,old_height-r.bottom,r.width,r.height)
            elif action == "rotate_left": self.selection=ImageRect(r.y,old_width-r.right,r.height,r.width)
            else: self.selection=ImageRect(old_height-r.bottom,r.x,r.height,r.width)
        self._commit_state()

    def undo(self):
        if self.can_undo:
            self._cursor -= 1; self._restore(); return True
        return False

    def redo(self):
        if self.can_redo:
            self._cursor += 1; self._restore(); return True
        return False

    def set_selection(self, rect):
        if rect is not None and (rect.width <= 0 or rect.height <= 0):
            raise ValueError("selection must have positive dimensions")
        if rect is not None and (rect.x < 0 or rect.y < 0 or rect.right > self.image.width or rect.bottom > self.image.height):
            raise ValueError("selection is outside the image")
        self.selection = rect
        image, revision, _ = self._states[self._cursor]
        self._states[self._cursor] = (image, revision, rect)

    def select_points(self, first, second):
        rect = ImageRect.from_points(*first, *second)
        if rect.width == 0 or rect.height == 0:
            self.set_selection(None)
            return None
        self.set_selection(rect)
        return rect

    def copy_selection(self, clipboard):
        if self.selection is None: raise ValueError("no image selection")
        r = self.selection
        clipboard.write_image(self.image.crop((r.x, r.y, r.right, r.bottom)).copy())

    def paste_image(self, image, position=(0, 0)):
        if image is None: raise ValueError("clipboard contains no image")
        self.floating = (image.convert("RGBA").copy(), tuple(position))

    def paste_from_clipboard(self, clipboard, position=(0, 0)):
        image = clipboard.read_image()
        if image is None: return False
        self.paste_image(image, position); return True

    def move_floating(self, position):
        if self.floating is None: return False
        image, _ = self.floating; self.floating = (image, tuple(position)); return True

    def commit_paste(self):
        if self.floating is None: return False
        image, (x, y) = self.floating
        base = self.image.copy()
        left, top = max(0, int(x)), max(0, int(y))
        right, bottom = min(self.image.width, int(x)+image.width), min(self.image.height, int(y)+image.height)
        if right > left and bottom > top:
            crop = image.crop((left-int(x), top-int(y), right-int(x), bottom-int(y)))
            base.alpha_composite(crop, (left, top))
        self.image = base; self.floating = None; self._commit_state(); return True

    def cancel_paste(self):
        if self.floating is None: return False
        self.floating = None; return True

    def copy_image_for_display(self):
        image = self.image.copy()
        if self.floating is not None:
            floating, (x, y) = self.floating
            left, top = max(0, int(x)), max(0, int(y))
            right, bottom = min(image.width, int(x)+floating.width), min(image.height, int(y)+floating.height)
            if right > left and bottom > top:
                crop = floating.crop((left-int(x), top-int(y), right-int(x), bottom-int(y)))
                image.alpha_composite(crop, (left, top))
        return image

    def save(self, store, path=None):
        target = path if path is not None else self.path
        if target is None: raise ValueError("save path required")
        store.save_png(target, self.image.copy())
        self.path = str(target)
        self.saved_revision = self.revision
        return self.path

    @classmethod
    def reopen(cls, store, path):
        doc = cls(store.load_image(path)); doc.path = str(path)
        doc.saved_revision = doc.revision
        return doc

    def sample(self, x, y):
        color=self.image.getpixel((x,y)); self.primary=color
        return color


class ToolState:
    """Pointer transaction: preview stays geometry-only until release."""
    def __init__(self, document): self.document=document; self.start=None; self.points=[]
    @property
    def preview(self):
        if self.start is None:return None
        return Shape(self.document.tool, tuple(self.points), self.document.primary, self.document.width, self.document.secondary)
    def press(self, point): self.start=point; self.points=[point]
    def move(self, point):
        if self.start is not None:
            if self.document.tool=="pen": self.points.append(point)
            else: self.points=[self.start,point]
    def release(self, point):
        if self.start is None:return None
        self.move(point); shape=self.preview; self.start=None
        if shape.kind=="arrow" and shape.points[0]==shape.points[-1]:return None
        self.document.apply(shape); return shape
    def cancel(self): self.start=None; self.points=[]
