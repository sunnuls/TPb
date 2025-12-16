from __future__ import annotations

from coach_app.engine.poker.ranges.range import Range
from coach_app.schemas.poker import Position


def _r(name: str, *, position: str | None, stack_bucket: str, action_type: str, hands: dict[str, float]) -> Range:
    return Range(
        hands=hands,
        metadata={
            "name": name,
            "position": position,
            "stack_bucket": stack_bucket,
            "action_type": action_type,
        },
    ).normalize()


"""
Range presets are intentionally SMALL and readable.

Notation:
- Pairs: "TT"
- Suited: "AKs"
- Offsuit: "AQo"

Stack buckets:
- cash_deep (100bb+)
- cash_mid (<60bb but >=25bb)
- cash_short (<25bb)
- mtt_40plus (>=40bb)
- mtt_20_40 (20-40bb)
- mtt_lt20 (<20bb)
"""


def preset_rfi(position: Position, *, stack_bucket: str) -> Range:
    # Minimal RFI cores; loosen late position.
    if position == Position.UTG:
        hands = {"AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "AKs": 1, "AKo": 1, "AQs": 1, "AQo": 0.5, "AJs": 0.5, "KQs": 0.5}
    elif position == Position.HJ:
        hands = {"AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "99": 1, "AKs": 1, "AKo": 1, "AQs": 1, "AQo": 0.75, "AJs": 0.75, "KQs": 0.75, "ATs": 0.5}
    elif position == Position.CO:
        hands = {
            "AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "99": 1, "88": 0.75,
            "AKs": 1, "AKo": 1, "AQs": 1, "AQo": 1, "AJs": 1, "ATs": 0.75, "A5s": 0.5,
            "KQs": 1, "KJs": 0.75, "QJs": 0.75, "JTs": 0.75, "T9s": 0.5,
        }
    elif position == Position.BTN:
        hands = {
            "AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "99": 1, "88": 1, "77": 0.75, "66": 0.5,
            "AKs": 1, "AKo": 1, "AQs": 1, "AQo": 1, "AJs": 1, "ATs": 1, "A9s": 0.75, "A5s": 0.75,
            "KQs": 1, "KJs": 1, "KTs": 0.75, "QJs": 1, "QTs": 0.75, "JTs": 1, "T9s": 0.75, "98s": 0.5,
        }
    elif position == Position.SB:
        hands = {
            "AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "99": 1, "88": 0.75, "77": 0.5,
            "AKs": 1, "AKo": 1, "AQs": 1, "AQo": 0.75, "AJs": 0.75, "ATs": 0.75, "A5s": 0.5,
            "KQs": 0.75, "KJs": 0.5, "QJs": 0.5, "JTs": 0.5,
        }
    else:
        # BB typically doesn't "RFI" (limps are out of scope); keep small.
        hands = {"AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "AKs": 1, "AKo": 1}

    # Stack adjustments: short stacks tighten opens a bit.
    if stack_bucket in ("mtt_lt20", "cash_short"):
        hands = {k: v for k, v in hands.items() if k in {"AA","KK","QQ","JJ","TT","99","AKs","AKo","AQs","AQo"}}
    return _r(f"RFI_{position.value}", position=position.value, stack_bucket=stack_bucket, action_type="rfi", hands=hands)


def preset_bb_defend_vs_btn(*, stack_bucket: str) -> Range:
    # BB defend (call) vs BTN open: suited broadways, pairs, suited connectors.
    hands = {
        "AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "99": 1, "88": 1, "77": 1, "66": 0.75, "55": 0.5,
        "AKs": 1, "AQs": 1, "AJs": 1, "ATs": 1, "A9s": 0.75, "A5s": 0.75,
        "KQs": 1, "KJs": 1, "KTs": 0.75, "QJs": 1, "QTs": 0.75, "JTs": 1, "T9s": 0.75, "98s": 0.75, "87s": 0.5,
        "AQo": 0.75, "KQo": 0.5,
    }
    if stack_bucket in ("mtt_lt20", "cash_short"):
        # short stack: defend tighter, prefer shove/3bet or fold (handled elsewhere)
        hands = {k: v for k, v in hands.items() if k in {"AA","KK","QQ","JJ","TT","99","AKs","AQs","AQo","KQs"}}
    return _r("BB_DEFEND_vs_BTN", position="BB", stack_bucket=stack_bucket, action_type="defend_call", hands=hands)


def preset_3bet_vs_late(*, stack_bucket: str, opener: str) -> Range:
    # Simple 3bet range vs CO/BTN open.
    hands = {"AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "AKs": 1, "AKo": 1, "AQs": 0.75, "A5s": 0.5, "KQs": 0.5}
    if stack_bucket in ("mtt_lt20", "cash_short"):
        hands = {"AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 0.75, "AKs": 1, "AKo": 1, "AQs": 0.75}
    return _r(f"3BET_vs_{opener}", position=None, stack_bucket=stack_bucket, action_type="3bet", hands=hands)


def preset_shove_v0(position: Position, *, stack_bucket: str) -> Range:
    # For MTT short stack <20bb: shove/fold style (very conservative v0)
    hands = {"AA": 1, "KK": 1, "QQ": 1, "JJ": 1, "TT": 1, "99": 1, "AKs": 1, "AKo": 1, "AQs": 1, "AQo": 0.75, "AJs": 0.5}
    if position in (Position.BTN, Position.SB):
        hands |= {"88": 0.75, "77": 0.5, "ATs": 0.75, "A5s": 0.5, "KQs": 0.5}
    return _r(f"SHOVE_{position.value}", position=position.value, stack_bucket=stack_bucket, action_type="shove", hands=hands)