from __future__ import annotations

from copy import deepcopy

from coach_app.schemas.poker import PokerGameState


def normalize_poker_state_to_bb(state: PokerGameState) -> PokerGameState:
    """
    Normalize numeric values into big blinds (BB) when possible.

    - If big_blind == 0, returns a copy unchanged.
    - Pot, stacks, blinds, ante are divided by big_blind.
    """
    st = deepcopy(state)
    if st.big_blind <= 0:
        return st

    bb = st.big_blind
    st.small_blind = st.small_blind / bb
    st.big_blind = 1.0
    st.ante = st.ante / bb
    st.pot = st.pot / bb
    for p in st.players:
        p.stack = p.stack / bb
    return st


