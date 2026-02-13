#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
humanization_layer.py — Behavioral variance для надёжных humanized кликов.

Phase 2 of action_executor.md.

Стили поведения:
- AGGRESSIVE: быстрые решения, минимум задержки, резкие движения
- PASSIVE: медленные решения, длинные паузы, осторожные движения
- NEUTRAL: средний стиль
- RANDOM: случайное переключение между стилями
- TILTED: ускоренный после проигрыша (нетерпеливый)

Каждый стиль влияет на:
- Think time (время на размышление)
- Mouse speed & curvature
- Click precision (offset от центра кнопки)
- Inter-action delays
- Fatigue accumulation
- Action-specific variance (fold vs raise)

Usage::

    layer = HumanizationLayer(style=PlayStyle.AGGRESSIVE)
    params = layer.get_action_params("raise", hand_strength=0.85)
    print(params.think_time, params.mouse_intensity, params.click_offset)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Play styles
# ---------------------------------------------------------------------------

class PlayStyle(str, Enum):
    """Behavioral style affecting all humanization parameters."""
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    RANDOM = "random"
    TILTED = "tilted"


# ---------------------------------------------------------------------------
# Behavioral profile — configurable parameters per style
# ---------------------------------------------------------------------------

@dataclass
class BehavioralProfile:
    """Full set of humanization parameters for a play style.

    All times in seconds, distances in pixels.
    """
    # Think time
    think_base: float = 1.5         # base thinking time
    think_variance: float = 0.8     # ± random range
    think_min: float = 0.3          # floor
    think_max: float = 8.0          # ceiling

    # Mouse movement
    mouse_intensity: float = 5.0    # Bézier curvature 0–10
    mouse_speed_base: float = 0.6   # seconds per 1000px
    mouse_jitter: float = 0.8       # hand tremor amplitude
    mouse_overshoot: bool = True

    # Click precision
    click_offset_range: int = 3     # max px offset from target centre
    double_click_chance: float = 0.0  # probability of accidental double-click

    # Inter-action delays
    delay_base: float = 0.2         # base delay before action
    delay_variance: float = 0.15    # ± random range
    delay_between_actions: float = 0.5

    # Fatigue
    fatigue_rate: float = 0.03      # per action
    fatigue_max: float = 0.4        # max 40% slowdown
    fatigue_recovery: float = 0.01  # recovery per idle second

    # Action-type multipliers (think_time *= multiplier)
    action_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "fold": 0.6,
        "check": 0.5,
        "call": 0.8,
        "bet": 1.2,
        "raise": 1.3,
        "all_in": 1.8,
    })

    # Hand-strength influence: strong hands → faster/slower decisions
    strength_influence: float = 0.3  # how much hand strength affects timing


# ---------------------------------------------------------------------------
# Style presets
# ---------------------------------------------------------------------------

STYLE_PROFILES: Dict[PlayStyle, BehavioralProfile] = {
    PlayStyle.AGGRESSIVE: BehavioralProfile(
        think_base=0.8,
        think_variance=0.4,
        think_min=0.2,
        think_max=3.0,
        mouse_intensity=7.0,
        mouse_speed_base=0.4,
        mouse_jitter=1.0,
        mouse_overshoot=True,
        click_offset_range=5,
        double_click_chance=0.02,
        delay_base=0.1,
        delay_variance=0.08,
        delay_between_actions=0.3,
        fatigue_rate=0.05,
        fatigue_max=0.5,
        strength_influence=0.15,
        action_multipliers={
            "fold": 0.3, "check": 0.3, "call": 0.5,
            "bet": 0.8, "raise": 0.9, "all_in": 1.2,
        },
    ),
    PlayStyle.PASSIVE: BehavioralProfile(
        think_base=2.5,
        think_variance=1.2,
        think_min=0.8,
        think_max=10.0,
        mouse_intensity=3.0,
        mouse_speed_base=0.9,
        mouse_jitter=0.5,
        mouse_overshoot=False,
        click_offset_range=2,
        double_click_chance=0.0,
        delay_base=0.4,
        delay_variance=0.3,
        delay_between_actions=0.8,
        fatigue_rate=0.02,
        fatigue_max=0.3,
        strength_influence=0.4,
        action_multipliers={
            "fold": 0.8, "check": 0.7, "call": 1.0,
            "bet": 1.5, "raise": 1.8, "all_in": 2.5,
        },
    ),
    PlayStyle.NEUTRAL: BehavioralProfile(),  # defaults
    PlayStyle.TILTED: BehavioralProfile(
        think_base=0.5,
        think_variance=0.3,
        think_min=0.1,
        think_max=2.0,
        mouse_intensity=8.0,
        mouse_speed_base=0.3,
        mouse_jitter=1.5,
        mouse_overshoot=True,
        click_offset_range=7,
        double_click_chance=0.05,
        delay_base=0.05,
        delay_variance=0.05,
        delay_between_actions=0.15,
        fatigue_rate=0.08,
        fatigue_max=0.6,
        strength_influence=0.1,
        action_multipliers={
            "fold": 0.2, "check": 0.2, "call": 0.3,
            "bet": 0.5, "raise": 0.6, "all_in": 0.8,
        },
    ),
}


# ---------------------------------------------------------------------------
# Action parameters — output of the humanization layer
# ---------------------------------------------------------------------------

@dataclass
class ActionParams:
    """Computed humanization parameters for a single action."""
    think_time: float = 1.0
    delay_before: float = 0.1
    mouse_intensity: float = 5.0
    mouse_speed: float = 0.6
    mouse_jitter: float = 0.8
    mouse_overshoot: bool = True
    click_offset: int = 3
    execution_time: float = 0.2
    total_time: float = 1.3
    style: str = "neutral"
    action: str = ""
    fatigue: float = 0.0

    def summary(self) -> str:
        return (
            f"[{self.style}] {self.action}: think={self.think_time:.2f}s "
            f"delay={self.delay_before:.2f}s exec={self.execution_time:.2f}s "
            f"total={self.total_time:.2f}s mouse_int={self.mouse_intensity:.1f} "
            f"offset={self.click_offset}px fatigue={self.fatigue:.0%}"
        )


# ---------------------------------------------------------------------------
# HumanizationLayer
# ---------------------------------------------------------------------------

class HumanizationLayer:
    """
    Computes humanized action parameters based on behavioral style.

    Tracks session state (fatigue, action count) and adjusts parameters
    dynamically. Supports style switching mid-session (tilt detection).

    Args:
        style: Initial play style
        profile: Custom profile (overrides style preset)
        seed: Random seed for reproducibility (testing)
    """

    def __init__(
        self,
        style: PlayStyle = PlayStyle.NEUTRAL,
        profile: Optional[BehavioralProfile] = None,
        seed: Optional[int] = None,
    ):
        self._style = style
        self._profile = profile or self._resolve_profile(style)
        self._rng = random.Random(seed)

        # Session state
        self._actions_count = 0
        self._fatigue = 0.0
        self._last_action_time = time.monotonic()
        self._style_history: List[Tuple[float, PlayStyle]] = [(0.0, style)]

    # -- Properties --

    @property
    def style(self) -> PlayStyle:
        return self._style

    @property
    def profile(self) -> BehavioralProfile:
        return self._profile

    @property
    def fatigue(self) -> float:
        return self._fatigue

    @property
    def actions_count(self) -> int:
        return self._actions_count

    # -- Style management --

    def set_style(self, style: PlayStyle):
        """Switch play style (e.g. on tilt)."""
        self._style = style
        self._profile = self._resolve_profile(style)
        self._style_history.append((time.monotonic(), style))
        logger.info("Style changed to %s", style.value)

    @staticmethod
    def _resolve_profile(style: PlayStyle) -> BehavioralProfile:
        if style == PlayStyle.RANDOM:
            # Pick a random non-RANDOM style
            choices = [s for s in PlayStyle if s != PlayStyle.RANDOM]
            picked = random.choice(choices)
            return STYLE_PROFILES.get(picked, BehavioralProfile())
        return STYLE_PROFILES.get(style, BehavioralProfile())

    # -- Core: compute action params --

    def get_action_params(
        self,
        action: str,
        hand_strength: float = 0.5,
        is_important: bool = False,
    ) -> ActionParams:
        """Compute humanized parameters for an action.

        Args:
            action: Action type (fold, check, call, bet, raise, all_in)
            hand_strength: 0.0–1.0
            is_important: True for big decisions (all-in, big bet)

        Returns:
            ActionParams with all timing and mouse parameters.
        """
        p = self._profile

        # If RANDOM, maybe switch sub-style occasionally
        if self._style == PlayStyle.RANDOM and self._rng.random() < 0.15:
            choices = [s for s in PlayStyle if s != PlayStyle.RANDOM]
            self._profile = STYLE_PROFILES.get(
                self._rng.choice(choices), BehavioralProfile()
            )
            p = self._profile

        # 1. Think time
        think = p.think_base + self._rng.uniform(-p.think_variance, p.think_variance)

        # Action multiplier
        mult = p.action_multipliers.get(action.lower(), 1.0)
        think *= mult

        # Hand strength influence
        # Strong hand → faster (aggressive style) or slower (passive, to "Hollywood")
        strength_adj = 1.0 - (hand_strength - 0.5) * p.strength_influence
        think *= strength_adj

        # Important decisions take longer
        if is_important:
            think *= self._rng.uniform(1.3, 1.8)

        # Fatigue
        think *= (1.0 + self._fatigue)

        think = max(p.think_min, min(think, p.think_max))

        # 2. Delay before action
        delay = p.delay_base + self._rng.uniform(-p.delay_variance, p.delay_variance)
        delay = max(0.01, delay)

        # 3. Execution time
        exec_time = self._execution_time(action)

        # 4. Mouse params
        mouse_int = p.mouse_intensity + self._rng.uniform(-0.5, 0.5)
        mouse_int = max(0.0, min(10.0, mouse_int))
        mouse_speed = p.mouse_speed_base * (1.0 + self._fatigue * 0.3)
        click_off = max(0, p.click_offset_range + self._rng.randint(-1, 1))

        # 5. Total
        total = delay + think + exec_time

        # 6. Update state
        self._actions_count += 1
        self._fatigue = min(
            p.fatigue_max,
            self._fatigue + p.fatigue_rate,
        )
        self._last_action_time = time.monotonic()

        return ActionParams(
            think_time=think,
            delay_before=delay,
            mouse_intensity=mouse_int,
            mouse_speed=mouse_speed,
            mouse_jitter=p.mouse_jitter,
            mouse_overshoot=p.mouse_overshoot,
            click_offset=click_off,
            execution_time=exec_time,
            total_time=total,
            style=self._style.value,
            action=action,
            fatigue=self._fatigue,
        )

    def _execution_time(self, action: str) -> float:
        """Compute execution time based on action type."""
        a = action.lower()
        if a in ("fold", "check"):
            return self._rng.uniform(0.12, 0.25)
        elif a == "call":
            return self._rng.uniform(0.15, 0.30)
        elif a in ("bet", "raise"):
            return self._rng.uniform(0.25, 0.50)
        elif a == "all_in":
            return self._rng.uniform(0.20, 0.40)
        return self._rng.uniform(0.15, 0.35)

    # -- Fatigue management --

    def reset_fatigue(self):
        """Reset fatigue (simulated break)."""
        self._fatigue = 0.0

    def idle_recovery(self, seconds: float):
        """Recover fatigue from idle time."""
        recovery = seconds * self._profile.fatigue_recovery
        self._fatigue = max(0.0, self._fatigue - recovery)

    # -- Statistics --

    def get_stats(self) -> Dict:
        """Get session statistics."""
        return {
            "style": self._style.value,
            "actions_count": self._actions_count,
            "fatigue": self._fatigue,
            "style_changes": len(self._style_history),
        }
