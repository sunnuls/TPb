"""Stub card recognition module."""

from __future__ import annotations

from PIL import Image


def recognize_cards(_image: Image.Image) -> list[str]:
    # TODO: integrate ML model / template matching; return list like ["As","Kd",...]
    return []


