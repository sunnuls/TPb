from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from coach_app.ingest.vision.generic_adapter import GenericVisionAdapter


def _draw_char_box(img: Image.Image, *, x: int, y: int, ch: str) -> None:
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    d.rectangle([x, y, x + 17, y + 17], fill=(255, 255, 255))
    d.text((x + 1, y + 0), ch, fill=(0, 0, 0), font=font)


def _draw_token(img: Image.Image, *, x: int, y: int, token: str) -> None:
    assert len(token) == 2
    _draw_char_box(img, x=x, y=y, ch=token[0])
    _draw_char_box(img, x=x + 18, y=y, ch=token[1])


def test_generic_vision_adapter_detects_hero_and_board_and_street_flop():
    img = Image.new("RGB", (220, 260), (255, 255, 255))

    # board (3 cards) well above hero
    _draw_token(img, x=10, y=40, token="Ad")
    _draw_token(img, x=70, y=40, token="7c")
    _draw_token(img, x=130, y=40, token="2s")

    # hero hole (2 cards) near bottom
    _draw_token(img, x=60, y=200, token="Ah")
    _draw_token(img, x=120, y=200, token="Ks")

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    adapter = GenericVisionAdapter(game="poker")
    res = adapter.parse(buf.getvalue())

    assert res.adapter_name == "generic"
    assert res.adapter_version == "1.0"

    assert res.partial_state.get("hero_hole") == ["Ah", "Ks"]
    assert res.partial_state.get("board") == ["Ad", "7c", "2s"]
    assert res.partial_state.get("street") == "flop"

    # Confidence rules: cards 0.9..1.0, street max 0.8
    assert 0.9 <= float(res.confidence_map["hero_hole"]) <= 1.0
    assert 0.9 <= float(res.confidence_map["board"]) <= 1.0
    assert float(res.confidence_map["street"]) <= 0.8
