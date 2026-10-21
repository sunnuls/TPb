from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


@dataclass(frozen=True)
class Range:
    """
    Range Model v0.

    `hands` is a deterministic mapping from hand notation -> weight in [0..1].
    Examples: "AKs", "AQo", "TT".

    Weight semantics (v0):
    - 1.0: always included
    - 0.5: mixed frequency
    - 0.0: excluded (will be removed by normalize())
    """

    hands: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalize(self) -> "Range":
        """Clamp weights to [0..1], drop 0s, keep deterministic ordering by key sort."""
        cleaned = {k: _clamp01(float(v)) for k, v in self.hands.items()}
        cleaned = {k: v for k, v in cleaned.items() if v > 0.0}
        cleaned = dict(sorted(cleaned.items(), key=lambda kv: kv[0]))
        return Range(hands=cleaned, metadata=dict(self.metadata))

    def merge(self, other: "Range") -> "Range":
        """Union-like merge: add weights and clamp to 1.0."""
        a = self.normalize()
        b = other.normalize()
        out: dict[str, float] = dict(a.hands)
        for k, w in b.hands.items():
            out[k] = _clamp01(out.get(k, 0.0) + float(w))
        md = dict(a.metadata)
        md.update({f"merged_from:{k}": v for k, v in b.metadata.items()})
        return Range(hands=out, metadata=md).normalize()

    def contains(self, hand: str) -> bool:
        return self.normalize().hands.get(hand, 0.0) > 0.0

    def weight(self, hand: str) -> float:
        return float(self.normalize().hands.get(hand, 0.0))

    def describe(self, *, limit: int = 12) -> str:
        """
        Human-readable short summary.
        Example: "AKs(100%), AQo(50%), TT(100%), ... (n=18)"
        """
        r = self.normalize()
        items = list(r.hands.items())
        parts: list[str] = []
        for k, w in items[:limit]:
            parts.append(f"{k}({int(round(w * 100))}%)")
        more = "" if len(items) <= limit else ", ..."
        meta_bits: list[str] = []
        for mk in ("name", "position", "stack_bucket", "action_type"):
            if mk in r.metadata:
                meta_bits.append(f"{mk}={r.metadata[mk]}")
        meta = f" [{' '.join(meta_bits)}]" if meta_bits else ""
        return f"{', '.join(parts)}{more} (n={len(items)}){meta}"