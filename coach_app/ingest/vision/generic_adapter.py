from __future__ import annotations

import io
from typing import Any, Literal

from PIL import Image

from coach_app.ingest.vision.base import VisionAdapter, VisionParseResult
from coach_app.ingest.vision.cards import CardTokenDetection, detect_card_tokens
from coach_app.schemas.common import Street


class GenericVisionAdapter(VisionAdapter):
    """
    Stub adapter: returns an empty partial state with low confidence.
    Intended as an integration point for OCR/card recognition plugins.
    """

    adapter_name = "generic"
    adapter_version = "1.0"

    def __init__(self, *, game: Literal["poker", "blackjack"] = "poker") -> None:
        self.game = game

    def parse(self, image: bytes | Image.Image) -> VisionParseResult:
        # In real life:
        # - use adapter_config ROIs to crop regions
        # - run OCR on stack/pot labels
        # - run card recognition on card ROIs
        # - return partial poker/blackjack state
        img = image
        if isinstance(image, (bytes, bytearray)):
            img = Image.open(io.BytesIO(image)).convert("RGB")
        elif isinstance(image, Image.Image):
            img = image.convert("RGB")
        else:
            raise TypeError("image must be bytes or PIL.Image")

        dets, det_warnings = detect_card_tokens(img)

        partial_state: dict[str, Any] = {}
        confidence_map: dict[str, float] = {}
        warnings: list[str] = list(det_warnings)

        if self.game == "poker":
            poker_partial, poker_conf, poker_warn = self._parse_poker_from_detections(dets)
            partial_state.update(poker_partial)
            confidence_map.update(poker_conf)
            warnings.extend(poker_warn)
        else:
            bj_partial, bj_conf, bj_warn = self._parse_blackjack_from_detections(dets)
            partial_state.update(bj_partial)
            confidence_map.update(bj_conf)
            warnings.extend(bj_warn)

        return VisionParseResult(
            partial_state=partial_state,
            confidence_map=confidence_map,
            warnings=warnings,
            adapter_name=self.adapter_name,
            adapter_version=self.adapter_version,
        )

    def _parse_poker_from_detections(
        self, dets: list[CardTokenDetection]
    ) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        warnings: list[str] = []
        if not dets:
            return {}, {}, ["Карты на изображении не найдены."]

        groups: dict[int, list[CardTokenDetection]] = {}
        bin_px = 50
        for d in dets:
            k = int(round(d.y / float(bin_px)))
            groups.setdefault(k, []).append(d)
        for k in groups:
            groups[k].sort(key=lambda d: d.x)

        group_items = sorted(groups.items(), key=lambda kv: (kv[1][0].y if kv[1] else 0))

        hero_groups = [(k, g) for k, g in group_items if len(g) == 2]
        board_groups = [(k, g) for k, g in group_items if len(g) in (3, 4, 5)]

        hero: list[CardTokenDetection] | None = None
        if len(hero_groups) == 1:
            hero = hero_groups[0][1]
        elif len(hero_groups) > 1:
            warnings.append("Найдено несколько кандидатов на карты героя; hero_hole пропущен как неоднозначный.")
        else:
            warnings.append("Не удалось уверенно выделить 2 карты героя.")

        board: list[CardTokenDetection] | None = None
        if hero is not None:
            hero_y = float(sum(d.y for d in hero)) / 2.0
            above = [(k, g) for k, g in board_groups if float(sum(d.y for d in g)) / len(g) < hero_y - 80]
            if len(above) == 1:
                board = above[0][1]
            elif len(above) > 1:
                warnings.append("Найдено несколько кандидатов на борд; борд пропущен как неоднозначный.")
        else:
            if len(board_groups) == 1:
                board = board_groups[0][1]

        poker: dict[str, Any] = {}
        conf: dict[str, float] = {}

        if hero is not None:
            hero_tokens = [d.token for d in hero]
            if len(set(hero_tokens)) != 2:
                warnings.append("Карты героя содержат дубликаты/конфликт; пропускаю hero_hole.")
            else:
                poker["hero_hole"] = hero_tokens
                conf["hero_hole"] = float(min(d.confidence for d in hero))

        if board is not None:
            board_tokens = [d.token for d in board]
            if len(set(board_tokens)) != len(board_tokens):
                warnings.append("Карты борда содержат дубликаты/конфликт; пропускаю board.")
            else:
                poker["board"] = board_tokens
                conf["board"] = float(min(d.confidence for d in board))

        street: Street | None = None
        if "board" in poker:
            n = len(poker["board"])
            if n == 3:
                street = Street.FLOP
            elif n == 4:
                street = Street.TURN
            elif n == 5:
                street = Street.RIVER
        else:
            if "hero_hole" in poker and len(dets) == 2:
                street = Street.PREFLOP

        if street is not None:
            poker["street"] = street.value
            conf["street"] = 0.8
        else:
            warnings.append("Улица не определена (недостаточно уверенных карт борда).")

        if not poker:
            return {}, {}, warnings
        return poker, conf, warnings

    def _parse_blackjack_from_detections(
        self, dets: list[CardTokenDetection]
    ) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        warnings: list[str] = []
        # Minimal stub: only when exactly 3 cards are clearly detected.
        if len(dets) != 3:
            return {}, {}, ["Blackjack vision: недостаточно уверенных карт для извлечения player_hand/dealer_upcard."]

        s = sorted(dets, key=lambda d: d.y)
        dealer = s[0]
        player = s[1:]
        if len(player) != 2:
            return {}, {}, ["Blackjack vision: не удалось выделить 2 карты игрока."]

        bj = {"dealer_upcard": dealer.token, "player_hand": [d.token for d in player]}
        conf = {
            "dealer_upcard": float(dealer.confidence),
            "player_hand": float(min(d.confidence for d in player)),
        }
        return bj, conf, warnings


