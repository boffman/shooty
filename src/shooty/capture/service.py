"""Capture orchestration and pure snapshot cropping."""
from shooty.model import CapturedImage, DesktopSnapshot, Rect
from .ports import CaptureBackend


class CaptureError(RuntimeError):
    """Base class for desktop capture failures."""


class InvalidRegionError(CaptureError, ValueError):
    """Requested logical region is empty, outside the desktop, or in a gap."""


def crop_snapshot(snapshot: DesktopSnapshot, rect: Rect) -> CapturedImage:
    """Crop a logical desktop region from a frozen snapshot.

    Rectangles are half-open. Monitor mappings translate each intersected
    logical rectangle into snapshot pixels; the resulting pixel bounds are
    cropped as one image, including any physical pixels between monitors.
    """
    if rect.width <= 0 or rect.height <= 0:
        raise InvalidRegionError("capture region must have positive width and height")
    if not snapshot.monitors:
        raise InvalidRegionError("snapshot has no monitor mappings")

    # A grid of request and monitor edges lets us reject gaps and map mixed
    # scale regions without assuming a single desktop-wide scale factor.
    xs = sorted({rect.x, rect.right, *(max(rect.x, m.logical_rect.x) for m in snapshot.monitors),
                 *(min(rect.right, m.logical_rect.right) for m in snapshot.monitors)})
    ys = sorted({rect.y, rect.bottom, *(max(rect.y, m.logical_rect.y) for m in snapshot.monitors),
                 *(min(rect.bottom, m.logical_rect.bottom) for m in snapshot.monitors)})
    pixel_bounds: list[tuple[int, int, int, int]] = []
    for left, right in zip(xs, xs[1:]):
        if left < rect.x or right > rect.right or left == right:
            continue
        for top, bottom in zip(ys, ys[1:]):
            if top < rect.y or bottom > rect.bottom or top == bottom:
                continue
            monitor = next((m for m in snapshot.monitors
                            if m.logical_rect.x <= left and right <= m.logical_rect.right
                            and m.logical_rect.y <= top and bottom <= m.logical_rect.bottom), None)
            if monitor is None:
                raise InvalidRegionError("capture region crosses an area with no monitor")
            logical, pixels = monitor.logical_rect, monitor.pixel_rect
            sx, sy = pixels.width / logical.width, pixels.height / logical.height
            px1 = pixels.x + round((left - logical.x) * sx)
            px2 = pixels.x + round((right - logical.x) * sx)
            py1 = pixels.y + round((top - logical.y) * sy)
            py2 = pixels.y + round((bottom - logical.y) * sy)
            pixel_bounds.append((px1, py1, px2, py2))

    if not pixel_bounds:
        raise InvalidRegionError("capture region is outside the desktop")
    x1 = min(p[0] for p in pixel_bounds)
    y1 = min(p[1] for p in pixel_bounds)
    x2 = max(p[2] for p in pixel_bounds)
    y2 = max(p[3] for p in pixel_bounds)
    if x1 < 0 or y1 < 0 or x2 > snapshot.image.width or y2 > snapshot.image.height:
        raise InvalidRegionError("monitor mapping falls outside the captured image")
    if x1 >= x2 or y1 >= y2:
        raise InvalidRegionError("capture region maps to an empty pixel rectangle")
    return CapturedImage(snapshot.image.crop((x1, y1, x2, y2)))


class CaptureService:
    """Shared crop path for interactive frozen snapshots and fresh captures."""

    def __init__(self, backend: CaptureBackend):
        self._backend = backend

    def capture_desktop(self) -> DesktopSnapshot:
        """Take a snapshot; callers must do so before displaying overlays."""
        try:
            return self._backend.capture_desktop()
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError(f"could not capture the desktop: {exc}") from exc

    def capture_from_snapshot(self, snapshot: DesktopSnapshot, rect: Rect) -> CapturedImage:
        return crop_snapshot(snapshot, rect)

    def capture_fresh_region(self, rect: Rect) -> CapturedImage:
        return self.capture_from_snapshot(self.capture_desktop(), rect)
