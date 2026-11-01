"""GTK-free rectangle selection state and hit testing.

Coordinates are desktop logical coordinates, with half-open bounds. The
desktop bounds and selection use the same coordinate space.
"""
from dataclasses import dataclass
from enum import Enum

from shooty.model import Rect


class SelectionState(str, Enum):
    IDLE = "idle"
    CREATING = "creating"
    READY = "ready"
    ADJUSTING = "adjusting"


class Handle(str, Enum):
    NW = "nw"
    N = "n"
    NE = "ne"
    E = "e"
    SE = "se"
    S = "s"
    SW = "sw"
    W = "w"
    MOVE = "move"


@dataclass
class SelectionModel:
    """Selection interaction model; has no GTK or image dependencies."""
    bounds: Rect
    tolerance: float = 8
    state: SelectionState = SelectionState.IDLE
    rect: Rect | None = None
    _start: tuple[float, float] | None = None
    _initial: Rect | None = None
    _handle: Handle | None = None

    def clamp_point(self, x: float, y: float) -> tuple[float, float]:
        return (min(max(x, self.bounds.x), self.bounds.right),
                min(max(y, self.bounds.y), self.bounds.bottom))

    def hit_test(self, x: float, y: float) -> Handle | None:
        r = self.rect
        if r is None:
            return None
        left, right, top, bottom = r.x, r.right, r.y, r.bottom
        near_l, near_r = abs(x-left) <= self.tolerance, abs(x-right) <= self.tolerance
        near_t, near_b = abs(y-top) <= self.tolerance, abs(y-bottom) <= self.tolerance
        for condition, handle in (
            (near_l and near_t, Handle.NW), (near_r and near_t, Handle.NE),
            (near_r and near_b, Handle.SE), (near_l and near_b, Handle.SW),
            (near_t and left <= x <= right, Handle.N),
            (near_r and top <= y <= bottom, Handle.E),
            (near_b and left <= x <= right, Handle.S),
            (near_l and top <= y <= bottom, Handle.W),
        ):
            if condition:
                return handle
        if left < x < right and top < y < bottom:
            return Handle.MOVE
        return None

    def press(self, x: float, y: float) -> None:
        point = self.clamp_point(x, y)
        if self.state == SelectionState.READY and self.rect:
            handle = self.hit_test(*point)
            if handle is not None:
                self._handle, self._start, self._initial = handle, point, self.rect
                self.state = SelectionState.ADJUSTING
                return
        self._start = point
        self.rect = None
        self.state = SelectionState.CREATING

    def motion(self, x: float, y: float) -> None:
        if self.state not in (SelectionState.CREATING, SelectionState.ADJUSTING):
            return
        point = self.clamp_point(x, y)
        if self.state == SelectionState.CREATING:
            assert self._start is not None
            x1, y1 = self._start
            left, top = min(x1, point[0]), min(y1, point[1])
            right, bottom = max(x1, point[0]), max(y1, point[1])
            if right > left and bottom > top:
                self.rect = Rect(round(left), round(top), round(right-left), round(bottom-top))
            return
        assert self._start is not None and self._initial is not None and self._handle is not None
        self.rect = self._adjust(point)

    def release(self, x: float, y: float) -> None:
        self.motion(x, y)
        if self.state == SelectionState.CREATING:
            self.state = SelectionState.READY if self.rect else SelectionState.IDLE
        elif self.state == SelectionState.ADJUSTING:
            self.state = SelectionState.READY
        self._start = self._initial = None
        self._handle = None

    def cancel(self) -> None:
        self.state, self.rect = SelectionState.IDLE, None
        self._start = self._initial = None
        self._handle = None

    def _adjust(self, point: tuple[float, float]) -> Rect:
        assert self._initial and self._handle and self._start
        r, h = self._initial, self._handle
        dx, dy = point[0]-self._start[0], point[1]-self._start[1]
        l, t, rr, b = r.x, r.y, r.right, r.bottom
        if h == Handle.MOVE:
            l = round(min(max(r.x+dx, self.bounds.x), self.bounds.right-r.width))
            t = round(min(max(r.y+dy, self.bounds.y), self.bounds.bottom-r.height))
            return Rect(l, t, r.width, r.height)
        if "w" in h.value:
            l = round(min(max(point[0], self.bounds.x), rr-1))
        if "e" in h.value:
            rr = round(max(min(point[0], self.bounds.right), l+1))
        if "n" in h.value:
            t = round(min(max(point[1], self.bounds.y), b-1))
        if "s" in h.value:
            b = round(max(min(point[1], self.bounds.bottom), t+1))
        return Rect(l, t, rr-l, b-t)
