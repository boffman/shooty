"""Boundaries for desktop capture adapters."""
from typing import Protocol

from shooty.model import DesktopSnapshot


class CaptureBackend(Protocol):
    """Capture the composed desktop before any selection UI is shown."""

    def capture_desktop(self) -> DesktopSnapshot:
        """Return an immutable-in-practice pixel snapshot and monitor mapping."""
        ...
