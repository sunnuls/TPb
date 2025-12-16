from coach_app.engine.poker.ranges.range import Range


def test_range_normalize_clamps_and_drops_zero():
    r = Range(hands={"AKs": 1.2, "AQo": 0.5, "72o": 0.0, "X": -1}, metadata={"name": "t"})
    rn = r.normalize()
    assert "AKs" in rn.hands and rn.hands["AKs"] == 1.0
    assert "AQo" in rn.hands and rn.hands["AQo"] == 0.5
    assert "72o" not in rn.hands
    assert "X" not in rn.hands


def test_range_describe_contains_name_and_count():
    r = Range(hands={"AA": 1.0, "AKs": 1.0, "AQo": 0.5}, metadata={"name": "RFI_CO", "position": "CO"})
    s = r.describe(limit=2)
    assert "RFI_CO" in s
    assert "n=3" in s

from coach_app.engine.poker.ranges.range import Range
from coach_app.engine.poker.ranges.presets import preset_rfi
from coach_app.schemas.poker import Position


def test_range_normalize_clamps_and_drops_zeros():
    r = Range(hands={"AKs": 1.2, "AQo": 0.5, "72o": 0.0, "TT": -1.0})
    n = r.normalize()
    assert n.hands["AKs"] == 1.0
    assert n.hands["AQo"] == 0.5
    assert "72o" not in n.hands
    assert "TT" not in n.hands


def test_range_merge_adds_weights_and_clamps():
    a = Range(hands={"AKs": 0.6, "AQo": 0.5})
    b = Range(hands={"AKs": 0.6, "TT": 1.0})
    m = a.merge(b)
    assert m.hands["AKs"] == 1.0
    assert m.hands["AQo"] == 0.5
    assert m.hands["TT"] == 1.0


def test_range_describe_contains_metadata_and_count():
    r = preset_rfi(Position.BTN, stack_bucket="cash_deep")
    s = r.describe(limit=3)
    assert "n=" in s
    assert "name=" in s
    assert "stack_bucket=" in s


