"""
Behavioral Variance — Phase 2 of action_executor.md.

Defines player behavior profiles (aggressive, passive, balanced, random)
that modulate action execution timing, mouse dynamics, and decision
patterns to make bot behavior less predictable and more human-like.

Each profile controls:
  - Pre-action think time (delay before clicking)
  - Mouse movement speed and curvature
  - Click precision (how close to button center)
  - Action tempo (time between consecutive actions)
  - Micro-behaviors (double-clicks, hover, hesitation)
  - Variance drift (profile slowly shifts over a session)

Usage::

    profile = BehaviorProfile.aggressive()
    sampler = BehaviorSampler(profile)

    think_time = sampler.sample_think_time("raise")
    mouse_cfg  = sampler.sample_mouse_config()
    click_off  = sampler.sample_click_offset()

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BehaviorStyle(str, Enum):
    """Named behavior styles."""
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    BALANCED = "balanced"
    ERRATIC = "erratic"
    CUSTOM = "custom"


class ActionType(str, Enum):
    """Poker action types for timing differentiation."""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALLIN = "allin"


# ---------------------------------------------------------------------------
# Profile data model
# ---------------------------------------------------------------------------


@dataclass
class ThinkTimeConfig:
    """Per-action think time range (seconds).

    Attributes:
        min_s:  minimum think time
        max_s:  maximum think time
        sigma:  std-dev for normal distribution (clipped to [min, max])
    """
    min_s: float = 0.3
    max_s: float = 2.0
    sigma: float = 0.4


@dataclass
class MouseConfig:
    """Mouse movement parameters for a behavior style.

    Attributes:
        curve_intensity: Bézier curvature (0–10)
        speed_mult:      multiplier on base movement speed (>1 = slower)
        jitter:          hand-tremor amplitude (pixels)
        overshoot_prob:  probability of overshoot-and-correct [0–1]
        click_offset:    max random offset from button center (pixels)
    """
    curve_intensity: float = 5.0
    speed_mult: float = 1.0
    jitter: float = 0.8
    overshoot_prob: float = 0.5
    click_offset: int = 3


@dataclass
class TempoConfig:
    """Tempo between consecutive actions.

    Attributes:
        inter_action_min: minimum gap between two actions (seconds)
        inter_action_max: maximum gap
        burst_prob:       probability of a "burst" (quick double action)
        hesitation_prob:  probability of a hesitation pause mid-sequence
        hesitation_extra: extra seconds added on hesitation
    """
    inter_action_min: float = 0.8
    inter_action_max: float = 3.0
    burst_prob: float = 0.05
    hesitation_prob: float = 0.10
    hesitation_extra: float = 1.5


@dataclass
class BehaviorProfile:
    """Complete behavior profile for action execution.

    Combines think-time, mouse, and tempo configs plus metadata.
    """
    style: BehaviorStyle = BehaviorStyle.BALANCED
    think_times: Dict[str, ThinkTimeConfig] = field(default_factory=dict)
    mouse: MouseConfig = field(default_factory=MouseConfig)
    tempo: TempoConfig = field(default_factory=TempoConfig)
    variance_drift_rate: float = 0.02   # how fast profile drifts per action

    def __post_init__(self):
        # Fill in defaults for missing action types
        defaults = self._default_think_times(self.style)
        for k, v in defaults.items():
            self.think_times.setdefault(k, v)

    # -- factory methods -----------------------------------------------------

    @classmethod
    def aggressive(cls) -> BehaviorProfile:
        """Fast, decisive, low hesitation."""
        return cls(
            style=BehaviorStyle.AGGRESSIVE,
            think_times={
                ActionType.FOLD.value:  ThinkTimeConfig(0.15, 0.8, 0.2),
                ActionType.CHECK.value: ThinkTimeConfig(0.10, 0.6, 0.15),
                ActionType.CALL.value:  ThinkTimeConfig(0.20, 1.0, 0.25),
                ActionType.BET.value:   ThinkTimeConfig(0.30, 1.5, 0.3),
                ActionType.RAISE.value: ThinkTimeConfig(0.25, 1.2, 0.25),
                ActionType.ALLIN.value: ThinkTimeConfig(0.40, 2.0, 0.4),
            },
            mouse=MouseConfig(
                curve_intensity=3.0,
                speed_mult=0.7,
                jitter=0.5,
                overshoot_prob=0.3,
                click_offset=2,
            ),
            tempo=TempoConfig(
                inter_action_min=0.4,
                inter_action_max=1.5,
                burst_prob=0.12,
                hesitation_prob=0.05,
                hesitation_extra=0.8,
            ),
            variance_drift_rate=0.03,
        )

    @classmethod
    def passive(cls) -> BehaviorProfile:
        """Slow, cautious, longer think times."""
        return cls(
            style=BehaviorStyle.PASSIVE,
            think_times={
                ActionType.FOLD.value:  ThinkTimeConfig(0.5, 2.0, 0.5),
                ActionType.CHECK.value: ThinkTimeConfig(0.4, 1.5, 0.4),
                ActionType.CALL.value:  ThinkTimeConfig(0.8, 3.0, 0.6),
                ActionType.BET.value:   ThinkTimeConfig(1.2, 4.0, 0.8),
                ActionType.RAISE.value: ThinkTimeConfig(1.0, 3.5, 0.7),
                ActionType.ALLIN.value: ThinkTimeConfig(2.0, 5.0, 1.0),
            },
            mouse=MouseConfig(
                curve_intensity=7.0,
                speed_mult=1.4,
                jitter=1.2,
                overshoot_prob=0.6,
                click_offset=5,
            ),
            tempo=TempoConfig(
                inter_action_min=1.5,
                inter_action_max=4.0,
                burst_prob=0.02,
                hesitation_prob=0.20,
                hesitation_extra=2.5,
            ),
            variance_drift_rate=0.01,
        )

    @classmethod
    def balanced(cls) -> BehaviorProfile:
        """Middle ground — default human-like behavior."""
        return cls(
            style=BehaviorStyle.BALANCED,
            think_times={
                ActionType.FOLD.value:  ThinkTimeConfig(0.3, 1.2, 0.3),
                ActionType.CHECK.value: ThinkTimeConfig(0.2, 1.0, 0.25),
                ActionType.CALL.value:  ThinkTimeConfig(0.4, 2.0, 0.4),
                ActionType.BET.value:   ThinkTimeConfig(0.6, 2.5, 0.5),
                ActionType.RAISE.value: ThinkTimeConfig(0.5, 2.2, 0.45),
                ActionType.ALLIN.value: ThinkTimeConfig(1.0, 3.5, 0.7),
            },
            mouse=MouseConfig(
                curve_intensity=5.0,
                speed_mult=1.0,
                jitter=0.8,
                overshoot_prob=0.5,
                click_offset=3,
            ),
            tempo=TempoConfig(
                inter_action_min=0.8,
                inter_action_max=3.0,
                burst_prob=0.05,
                hesitation_prob=0.10,
                hesitation_extra=1.5,
            ),
            variance_drift_rate=0.02,
        )

    @classmethod
    def erratic(cls) -> BehaviorProfile:
        """Unpredictable — wide ranges, frequent bursts and hesitations."""
        return cls(
            style=BehaviorStyle.ERRATIC,
            think_times={
                ActionType.FOLD.value:  ThinkTimeConfig(0.1, 3.0, 1.0),
                ActionType.CHECK.value: ThinkTimeConfig(0.1, 2.5, 0.8),
                ActionType.CALL.value:  ThinkTimeConfig(0.1, 4.0, 1.2),
                ActionType.BET.value:   ThinkTimeConfig(0.2, 5.0, 1.5),
                ActionType.RAISE.value: ThinkTimeConfig(0.1, 4.5, 1.3),
                ActionType.ALLIN.value: ThinkTimeConfig(0.3, 6.0, 1.8),
            },
            mouse=MouseConfig(
                curve_intensity=8.0,
                speed_mult=1.2,
                jitter=1.5,
                overshoot_prob=0.7,
                click_offset=6,
            ),
            tempo=TempoConfig(
                inter_action_min=0.3,
                inter_action_max=5.0,
                burst_prob=0.15,
                hesitation_prob=0.20,
                hesitation_extra=3.0,
            ),
            variance_drift_rate=0.05,
        )

    @staticmethod
    def _default_think_times(style: BehaviorStyle) -> Dict[str, ThinkTimeConfig]:
        """Fallback think times for unspecified actions."""
        return {
            ActionType.FOLD.value:  ThinkTimeConfig(0.3, 1.5, 0.3),
            ActionType.CHECK.value: ThinkTimeConfig(0.2, 1.2, 0.3),
            ActionType.CALL.value:  ThinkTimeConfig(0.4, 2.0, 0.4),
            ActionType.BET.value:   ThinkTimeConfig(0.6, 2.5, 0.5),
            ActionType.RAISE.value: ThinkTimeConfig(0.5, 2.2, 0.45),
            ActionType.ALLIN.value: ThinkTimeConfig(1.0, 3.5, 0.7),
        }


# ---------------------------------------------------------------------------
# Behavior sampler
# ---------------------------------------------------------------------------


class BehaviorSampler:
    """Samples randomised execution parameters from a ``BehaviorProfile``.

    Supports session-long *variance drift*: the profile slowly mutates
    over time so that behaviour is not identical across a long session.

    Parameters:
        profile:          the behaviour profile to sample from
        session_seed:     optional seed for reproducibility
        enable_drift:     whether to drift the profile over time
    """

    def __init__(
        self,
        profile: Optional[BehaviorProfile] = None,
        session_seed: Optional[int] = None,
        enable_drift: bool = True,
    ):
        self.profile = profile or BehaviorProfile.balanced()
        self.enable_drift = enable_drift
        self._rng = random.Random(session_seed)
        self._action_count = 0
        self._last_action_time = 0.0

        # Drift state (mutable copies of key params)
        self._drift_speed_mult = self.profile.mouse.speed_mult
        self._drift_curve = self.profile.mouse.curve_intensity
        self._drift_think_mult = 1.0

    # -- public API ----------------------------------------------------------

    def sample_think_time(self, action: str) -> float:
        """Sample a think-time delay (seconds) for the given action."""
        cfg = self.profile.think_times.get(
            action.lower(),
            ThinkTimeConfig(),
        )
        raw = self._rng.gauss((cfg.min_s + cfg.max_s) / 2, cfg.sigma)
        clamped = max(cfg.min_s, min(cfg.max_s, raw))

        # Apply drift
        clamped *= self._drift_think_mult

        self._tick()
        return max(0.01, clamped)

    def sample_mouse_config(self) -> Dict[str, float]:
        """Sample mouse-movement parameters as a dict.

        Keys: ``curve_intensity``, ``speed_mult``, ``jitter``,
        ``overshoot`` (bool as 0/1).
        """
        m = self.profile.mouse
        overshoot = 1.0 if self._rng.random() < m.overshoot_prob else 0.0

        return {
            "curve_intensity": max(0, min(10, self._drift_curve + self._rng.gauss(0, 0.5))),
            "speed_mult": max(0.3, self._drift_speed_mult + self._rng.gauss(0, 0.1)),
            "jitter": max(0, m.jitter + self._rng.gauss(0, 0.2)),
            "overshoot": overshoot,
        }

    def sample_click_offset(self) -> Tuple[int, int]:
        """Sample a random (dx, dy) offset from button center."""
        r = self.profile.mouse.click_offset
        dx = self._rng.randint(-r, r)
        dy = self._rng.randint(-r, r)
        return (dx, dy)

    def sample_inter_action_delay(self) -> float:
        """Sample delay between two consecutive actions (seconds)."""
        t = self.profile.tempo

        # Base delay
        base = self._rng.uniform(t.inter_action_min, t.inter_action_max)

        # Burst (quick follow-up)?
        if self._rng.random() < t.burst_prob:
            base *= 0.3

        # Hesitation?
        if self._rng.random() < t.hesitation_prob:
            base += self._rng.uniform(0, t.hesitation_extra)

        return max(0.05, base * self._drift_think_mult)

    def sample_should_hover(self) -> bool:
        """Should the cursor hover over the button before clicking?

        Humans sometimes hover for a moment. Probability depends on style.
        """
        hover_prob = {
            BehaviorStyle.AGGRESSIVE: 0.10,
            BehaviorStyle.PASSIVE: 0.35,
            BehaviorStyle.BALANCED: 0.20,
            BehaviorStyle.ERRATIC: 0.30,
            BehaviorStyle.CUSTOM: 0.20,
        }.get(self.profile.style, 0.20)
        return self._rng.random() < hover_prob

    def sample_hover_time(self) -> float:
        """How long to hover before clicking (seconds)."""
        return self._rng.uniform(0.1, 0.6)

    def sample_double_click_prob(self) -> bool:
        """Rare accidental double-click (< 2%)."""
        return self._rng.random() < 0.015

    @property
    def action_count(self) -> int:
        return self._action_count

    @property
    def style(self) -> BehaviorStyle:
        return self.profile.style

    def reset_drift(self):
        """Reset drift state to profile defaults."""
        self._drift_speed_mult = self.profile.mouse.speed_mult
        self._drift_curve = self.profile.mouse.curve_intensity
        self._drift_think_mult = 1.0
        self._action_count = 0

    # -- drift ---------------------------------------------------------------

    def _tick(self):
        """Advance one action and apply drift."""
        self._action_count += 1
        if not self.enable_drift:
            return

        rate = self.profile.variance_drift_rate
        self._drift_speed_mult += self._rng.gauss(0, rate * 0.1)
        self._drift_speed_mult = max(0.4, min(2.0, self._drift_speed_mult))

        self._drift_curve += self._rng.gauss(0, rate * 1.0)
        self._drift_curve = max(0, min(10, self._drift_curve))

        self._drift_think_mult += self._rng.gauss(0, rate * 0.05)
        self._drift_think_mult = max(0.5, min(2.0, self._drift_think_mult))


# ---------------------------------------------------------------------------
# Random profile mixer
# ---------------------------------------------------------------------------


class ProfileMixer:
    """Create hybrid profiles by mixing two or more profiles.

    Useful for generating unique, non-repeating behavior fingerprints.
    """

    @staticmethod
    def mix(
        profiles: List[BehaviorProfile],
        weights: Optional[List[float]] = None,
    ) -> BehaviorProfile:
        """Weighted mix of multiple profiles.

        Numeric fields are interpolated; categorical fields
        come from the highest-weight profile.
        """
        if not profiles:
            return BehaviorProfile.balanced()
        if len(profiles) == 1:
            return profiles[0]

        if weights is None:
            weights = [1.0 / len(profiles)] * len(profiles)

        # Normalise weights
        total = sum(weights)
        weights = [w / total for w in weights]

        # Interpolate mouse config
        mouse = MouseConfig(
            curve_intensity=sum(p.mouse.curve_intensity * w for p, w in zip(profiles, weights)),
            speed_mult=sum(p.mouse.speed_mult * w for p, w in zip(profiles, weights)),
            jitter=sum(p.mouse.jitter * w for p, w in zip(profiles, weights)),
            overshoot_prob=sum(p.mouse.overshoot_prob * w for p, w in zip(profiles, weights)),
            click_offset=int(sum(p.mouse.click_offset * w for p, w in zip(profiles, weights))),
        )

        # Interpolate tempo
        tempo = TempoConfig(
            inter_action_min=sum(p.tempo.inter_action_min * w for p, w in zip(profiles, weights)),
            inter_action_max=sum(p.tempo.inter_action_max * w for p, w in zip(profiles, weights)),
            burst_prob=sum(p.tempo.burst_prob * w for p, w in zip(profiles, weights)),
            hesitation_prob=sum(p.tempo.hesitation_prob * w for p, w in zip(profiles, weights)),
            hesitation_extra=sum(p.tempo.hesitation_extra * w for p, w in zip(profiles, weights)),
        )

        # Interpolate think times
        all_actions = set()
        for p in profiles:
            all_actions.update(p.think_times.keys())

        think_times: Dict[str, ThinkTimeConfig] = {}
        for act in all_actions:
            cfgs = [p.think_times.get(act, ThinkTimeConfig()) for p in profiles]
            think_times[act] = ThinkTimeConfig(
                min_s=sum(c.min_s * w for c, w in zip(cfgs, weights)),
                max_s=sum(c.max_s * w for c, w in zip(cfgs, weights)),
                sigma=sum(c.sigma * w for c, w in zip(cfgs, weights)),
            )

        # Style from dominant profile
        dominant_idx = weights.index(max(weights))
        style = profiles[dominant_idx].style

        drift = sum(p.variance_drift_rate * w for p, w in zip(profiles, weights))

        return BehaviorProfile(
            style=style,
            think_times=think_times,
            mouse=mouse,
            tempo=tempo,
            variance_drift_rate=drift,
        )

    @staticmethod
    def random_profile(seed: Optional[int] = None) -> BehaviorProfile:
        """Generate a fully randomised profile."""
        rng = random.Random(seed)
        all_profiles = [
            BehaviorProfile.aggressive(),
            BehaviorProfile.passive(),
            BehaviorProfile.balanced(),
            BehaviorProfile.erratic(),
        ]
        # Random weights
        weights = [rng.random() for _ in all_profiles]
        return ProfileMixer.mix(all_profiles, weights)
