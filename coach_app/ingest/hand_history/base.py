from __future__ import annotations

from abc import ABC, abstractmethod

from coach_app.schemas.poker import PokerGameState


class HandHistoryParser(ABC):
    """Parse a room-specific hand history text into a PokerGameState (possibly partial with confidence)."""

    room: str

    @abstractmethod
    def parse(self, hand_history_text: str) -> PokerGameState:
        raise NotImplementedError


