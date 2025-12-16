from __future__ import annotations

from coach_app.ingest.hand_history.base import HandHistoryParser
from coach_app.schemas.common import Street
from coach_app.schemas.poker import PlayerSeat, PokerGameState, PokerGameType


class PokerStarsStubParser(HandHistoryParser):
    """
    Stub parser.
    TODO: Implement full PokerStars HH parsing (seats, blinds, actions, street progression).
    """

    room = "pokerstars"

    def parse(self, hand_history_text: str) -> PokerGameState:
        # MVP: return a minimal placeholder state with low confidence.
        return PokerGameState(
            game_type=PokerGameType.NLHE_6MAX_CASH,
            street=Street.PREFLOP,
            players=[
                PlayerSeat(seat_no=1, name="Hero", stack=100.0, is_hero=True),
                PlayerSeat(seat_no=2, name="Villain", stack=100.0),
            ],
            small_blind=0.5,
            big_blind=1.0,
            ante=0.0,
            pot=1.5,
            hero_hole=[],
            board=[],
            to_act_seat_no=1,
            last_aggressive_action="none",
            confidence={"value": 0.2, "source": "hand_history", "notes": ["Stub parser: incomplete state"]},
        )


