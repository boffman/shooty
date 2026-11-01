import pytest

from shooty.capture.selection import Handle, SelectionModel, SelectionState
from shooty.model import Rect


def drag(model, start, end):
    model.press(*start); model.motion(*end); model.release(*end)


@pytest.mark.parametrize("start,end,expected", [
    ((10, 10), (40, 30), Rect(10, 10, 30, 20)),
    ((40, 30), (10, 10), Rect(10, 10, 30, 20)),
    ((40, 10), (10, 30), Rect(10, 10, 30, 20)),
    ((10, 30), (40, 10), Rect(10, 10, 30, 20)),
])
def test_creation_normalizes_all_drag_directions(start, end, expected):
    model = SelectionModel(Rect(0, 0, 100, 80))
    drag(model, start, end)
    assert model.rect == expected
    assert model.state is SelectionState.READY


@pytest.mark.parametrize("point,handle", [
    ((10, 10), Handle.NW), ((25, 10), Handle.N), ((40, 10), Handle.NE),
    ((40, 20), Handle.E), ((40, 30), Handle.SE), ((25, 30), Handle.S),
    ((10, 30), Handle.SW), ((10, 20), Handle.W), ((25, 20), Handle.MOVE),
])
def test_hit_tests_all_handles_and_interior(point, handle):
    model = SelectionModel(Rect(0, 0, 100, 80), rect=Rect(10, 10, 30, 20),
                           state=SelectionState.READY)
    assert model.hit_test(*point) is handle


@pytest.mark.parametrize("handle,start,end,expected", [
    (Handle.NW, (10,10), (5,4), Rect(5,4,35,26)),
    (Handle.N, (25,10), (25,5), Rect(10,5,30,25)),
    (Handle.NE, (40,10), (45,5), Rect(10,5,35,25)),
    (Handle.E, (40,20), (50,20), Rect(10,10,40,20)),
    (Handle.SE, (40,30), (50,40), Rect(10,10,40,30)),
    (Handle.S, (25,30), (25,40), Rect(10,10,30,30)),
    (Handle.SW, (10,30), (5,40), Rect(5,10,35,30)),
    (Handle.W, (10,20), (5,20), Rect(5,10,35,20)),
])
def test_resize_each_handle_preserves_opposite_edges(handle,start,end,expected):
    model=SelectionModel(Rect(0,0,100,80), rect=Rect(10,10,30,20), state=SelectionState.READY)
    model.press(*start); assert model.state is SelectionState.ADJUSTING
    model.motion(*end); model.release(*end)
    assert model.rect == expected
    assert model.state is SelectionState.READY


def test_interior_move_and_clamping_at_each_desktop_edge():
    model=SelectionModel(Rect(0,0,100,80), rect=Rect(10,10,30,20), state=SelectionState.READY)
    drag(model,(20,20),(200,200))
    assert model.rect == Rect(70,60,30,20)
    drag(model,(85,70),(-100,-100))
    assert model.rect == Rect(0,0,30,20)


def test_resize_clamps_and_keeps_nonempty_rect():
    model=SelectionModel(Rect(0,0,100,80), rect=Rect(10,10,30,20), state=SelectionState.READY)
    model.press(10,20); model.motion(120,20); model.release(120,20)
    assert model.rect == Rect(39,10,1,20)


def test_escape_cancel_resets_selection_and_empty_drag_does_not_become_ready():
    model=SelectionModel(Rect(0,0,100,80))
    drag(model,(2,2),(2,2))
    assert model.rect is None and model.state is SelectionState.IDLE
    drag(model,(2,2),(20,20)); model.cancel()
    assert model.rect is None and model.state is SelectionState.IDLE

