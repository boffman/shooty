"""Pure dispatch boundary used when a selection is confirmed."""
from typing import Callable

from shooty.model import CapturedImage, DesktopSnapshot, Rect
from .service import CaptureService


def dispatch_selection(service: CaptureService, snapshot: DesktopSnapshot,
                       rect: Rect, handler: Callable[[CapturedImage], None]) -> CapturedImage:
    """Crop the pre-overlay snapshot and deliver that image exactly once."""
    captured = service.capture_from_snapshot(snapshot, rect)
    handler(captured)
    return captured
