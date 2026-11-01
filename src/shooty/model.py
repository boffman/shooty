"""Pure geometry and desktop coordinate mappings."""
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


@dataclass(frozen=True)
class Rect:
    """Positive-size rectangle in desktop logical coordinates, half-open."""
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_points(cls, x1: int, y1: int, x2: int, y2: int) -> "Rect":
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        return cls(left, top, right - left, bottom - top)

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True)
class CoordinateMapping:
    """Uniform logical-to-pixel mapping for a desktop snapshot."""
    logical_origin_x: int
    logical_origin_y: int
    pixel_origin_x: int
    pixel_origin_y: int
    scale: float

    def logical_to_pixel(self, x: float, y: float) -> tuple[int, int]:
        return (self.pixel_origin_x + math.floor((x - self.logical_origin_x) * self.scale),
                self.pixel_origin_y + math.floor((y - self.logical_origin_y) * self.scale))


@dataclass(frozen=True)
class MonitorMapping:
    """One monitor's half-open desktop-logical and snapshot-pixel bounds."""
    logical_rect: Rect
    pixel_rect: Rect


@dataclass(frozen=True)
class DesktopSnapshot:
    """Pixels captured before UI is shown, plus per-monitor coordinate mapping."""
    image: "Image.Image"
    monitors: tuple[MonitorMapping, ...]


@dataclass(frozen=True)
class CapturedImage:
    """Independent image pixels returned by a capture operation."""
    image: "Image.Image"

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height
