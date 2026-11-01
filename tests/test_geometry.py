from shooty.model import CoordinateMapping, Rect


def test_normalized_half_open_rectangle():
    rect = Rect.from_points(8, 9, 2, 4)
    assert rect == Rect(2, 4, 6, 5)
    assert (rect.right, rect.bottom) == (8, 9)


def test_negative_desktop_origin_mapping():
    m = CoordinateMapping(-1920, -200, 0, 0, 1.0)
    assert m.logical_to_pixel(-1910, -190) == (10, 10)


def test_scaled_mapping_floors_to_pixel():
    m = CoordinateMapping(0, 0, 0, 0, 2.0)
    assert m.logical_to_pixel(3.9, 4.2) == (7, 8)
