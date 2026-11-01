from PIL import Image
import pytest

from shooty.capture.service import CaptureError, CaptureService, InvalidRegionError
from shooty.model import DesktopSnapshot, MonitorMapping, Rect


def patterned_snapshot():
    # Each pixel encodes its coordinates so crop origin and exclusive edges
    # are observable without relying on visual inspection.
    image = Image.new("RGB", (8, 4))
    for y in range(image.height):
        for x in range(image.width):
            image.putpixel((x, y), (x, y, 0))
    monitors = (MonitorMapping(Rect(-4, 10, 8, 4), Rect(0, 0, 8, 4)),)
    return DesktopSnapshot(image, monitors)


class FakeBackend:
    def __init__(self, snapshot=None, error=None):
        self.snapshot, self.error, self.calls = snapshot, error, 0

    def capture_desktop(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.snapshot


def test_interactive_snapshot_crop_uses_logical_to_pixel_mapping():
    snapshot = patterned_snapshot()
    service = CaptureService(FakeBackend(snapshot))
    region = Rect(-2, 11, 3, 2)
    result = service.capture_from_snapshot(snapshot, region)
    assert (result.width, result.height) == (3, 2)
    assert result.image.getpixel((0, 0)) == (2, 1, 0)
    assert result.image.getpixel((2, 1)) == (4, 2, 0)
    direct = CaptureService(FakeBackend(snapshot)).capture_fresh_region(region)
    assert direct.image.tobytes() == result.image.tobytes()


def test_direct_capture_uses_same_crop_and_includes_last_pixel_before_half_open_edge():
    backend = FakeBackend(patterned_snapshot())
    result = CaptureService(backend).capture_fresh_region(Rect(3, 12, 1, 1))
    assert result.image.getpixel((0, 0)) == (7, 2, 0)
    assert backend.calls == 1


@pytest.mark.parametrize("rect", [Rect(0, 0, 0, 2), Rect(0, 0, 2, 0), Rect(5, 11, 1, 1)])
def test_invalid_and_out_of_bounds_regions_are_rejected(rect):
    with pytest.raises(InvalidRegionError):
        CaptureService(FakeBackend(patterned_snapshot())).capture_fresh_region(rect)


def test_region_touching_right_and_bottom_edges_is_valid():
    result = CaptureService(FakeBackend(patterned_snapshot())).capture_fresh_region(
        Rect(3, 13, 1, 1))
    assert result.image.getpixel((0, 0)) == (7, 3, 0)


def test_mixed_monitor_scale_mapping_uses_each_monitor_scale():
    image = Image.new("RGB", (6, 2))
    for x in range(6):
        image.putpixel((x, 0), (x, 0, 0))
    snapshot = DesktopSnapshot(image, (
        MonitorMapping(Rect(0, 0, 2, 2), Rect(0, 0, 2, 2)),
        MonitorMapping(Rect(2, 0, 2, 2), Rect(2, 0, 4, 2)),
    ))
    result = CaptureService(FakeBackend(snapshot)).capture_from_snapshot(snapshot, Rect(1, 0, 2, 1))
    assert result.image.size == (3, 1)
    assert [result.image.getpixel((x, 0))[0] for x in range(3)] == [1, 2, 3]


def test_region_crossing_monitor_gap_is_rejected():
    snapshot = DesktopSnapshot(Image.new("RGB", (4, 1)), (
        MonitorMapping(Rect(0, 0, 1, 1), Rect(0, 0, 1, 1)),
        MonitorMapping(Rect(3, 0, 1, 1), Rect(3, 0, 1, 1)),
    ))
    with pytest.raises(InvalidRegionError, match="no monitor"):
        CaptureService(FakeBackend(snapshot)).capture_from_snapshot(snapshot, Rect(0, 0, 4, 1))


def test_backend_failure_is_reported_as_capture_error():
    service = CaptureService(FakeBackend(error=OSError("permission denied")))
    with pytest.raises(CaptureError, match="could not capture the desktop: permission denied"):
        service.capture_fresh_region(Rect(0, 0, 1, 1))
