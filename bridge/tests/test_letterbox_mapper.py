"""Unit tests for LetterboxMapper — resolution independence."""

from __future__ import annotations

import pytest

from bridge.vision.yolo_engine import LetterboxMapper


NATIVE_SIZES = [
    (720, 1280),
    (1080, 1920),
    (1440, 3120),
    (480, 800),
]


@pytest.mark.parametrize("nw,nh", NATIVE_SIZES)
def test_center_box_maps_to_native_center(nw, nh):
    m = LetterboxMapper(nw, nh, model_size=640)
    # Tiny box at exact center of the letterboxed model canvas
    cx_m = 0.5
    cy_m = 0.5
    half = 0.01
    box = (cx_m - half, cy_m - half, cx_m + half, cy_m + half)
    cx, cy = m.center(box)
    assert abs(cx - nw // 2) <= 2
    assert abs(cy - nh // 2) <= 2


@pytest.mark.parametrize("nw,nh", NATIVE_SIZES)
def test_edge_box_stays_in_bounds(nw, nh):
    m = LetterboxMapper(nw, nh, model_size=640)
    # Near top-left of model canvas
    box = (0.0, 0.0, 0.05, 0.05)
    x1, y1, x2, y2 = m.to_native(box)
    assert 0 <= x1 <= x2 <= nw
    assert 0 <= y1 <= y2 <= nh
    cx, cy = m.center(box)
    assert 0 <= cx < nw
    assert 0 <= cy < nh

    # Near bottom-right
    box2 = (0.95, 0.95, 1.0, 1.0)
    x1, y1, x2, y2 = m.to_native(box2)
    assert 0 <= x1 <= x2 <= nw
    assert 0 <= y1 <= y2 <= nh
    cx, cy = m.center(box2)
    assert 0 <= cx < nw
    assert 0 <= cy < nh


@pytest.mark.parametrize("nw,nh", NATIVE_SIZES)
@pytest.mark.parametrize(
    "pt",
    [
        (0.0, 0.0),
        (1.0, 1.0),
        (0.5, 0.5),
        (0.25, 0.75),
        (0.9, 0.1),
    ],
)
def test_round_trip_native_point(nw, nh, pt):
    m = LetterboxMapper(nw, nh, model_size=640)
    nx = pt[0] * (nw - 1)
    ny = pt[1] * (nh - 1)
    u, v = m.native_point_to_norm(nx, ny)
    # Degenerate zero-area box at that point
    box = (u, v, u, v)
    x1, y1, x2, y2 = m.to_native(box)
    assert abs(x1 - nx) <= 2
    assert abs(y1 - ny) <= 2
