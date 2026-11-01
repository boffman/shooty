from PIL import Image

from shooty.capture.controller import dispatch_selection
from shooty.capture.service import CaptureService
from shooty.model import DesktopSnapshot, MonitorMapping, Rect


class Backend:
    def capture_desktop(self):
        raise AssertionError("interactive selection must not recapture after overlay")


def test_selection_dispatch_crops_supplied_frozen_snapshot_once():
    source = Image.new("RGB", (4, 3), "red")
    snapshot = DesktopSnapshot(source, (MonitorMapping(Rect(0, 0, 4, 3), Rect(0, 0, 4, 3)),))
    delivered=[]
    result=dispatch_selection(CaptureService(Backend()), snapshot, Rect(1, 1, 2, 1), delivered.append)
    assert delivered == [result]
    assert result.image.size == (2,1)
    assert result.image.getpixel((0,0)) == (255,0,0)
