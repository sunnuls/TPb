"""
Human Timing Module — Anti-Detection Timing Layer.

Generates realistic action delays that mimic human decision-making patterns.
Bypasses timing analysis used by poker rooms to detect bots.

Key features:
  - Normal distribution with fat tails (humans are unpredictable)
  - Hand-strength-dependent timing (strong hands = slow down sometimes)
  - Rare "thinking sessions" (8-15 second pauses that humans have)
  - Fake mouse hover before click (move toward button, pause, then click)
  - Per-profile timing personalities (tight = slower, loose = faster)
  - Time-of-day variance (night sessions play faster than morning)

Usage::

    timer = HumanTiming(profile="shark")
    delay = timer.pre_action_delay(hand_equity=0.75, action="raise")
    time.sleep(delay)

    # Or with fake hover:
    timer.apply_with_hover(target_x=950, target_y=995, action_fn=lambda: click_raise())
"""

from __future__ import annotations

import math
import random
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)


class TimingProfile(str, Enum):
    """Timing personality presets that match bot profiles."""
    SHARK   = "shark"    # Mostly fast, occasional deep think
    ROCK    = "rock"     # Slow and deliberate
    TAG     = "tag"      # Medium-paced, consistent
    LAG     = "lag"      # Variable, unpredictable
    FISH    = "fish"     # Fast + erratic (mimics bad player)
    DEFAULT = "default"  # Balanced


@dataclass
class TimingConfig:
    """Per-profile timing parameters."""
    # Pre-action base delay (seconds) — mean and std of normal distribution
    mean_delay: float = 2.5
    std_delay: float  = 1.8

    # Hard min/max clamp after sampling
    min_delay: float = 0.3
    max_delay: float = 12.0

    # Probability of triggering a "thinking session" (long pause)
    think_probability: float = 0.08   # 8% of actions
    think_min: float = 8.0
    think_max: float = 18.0

    # Probability of fake hover-and-retreat before clicking
    hover_probability: float = 0.25   # 25% chance of moving to button and back

    # Equity impact: add extra delay when equity > threshold (slow-playing)
    strong_hand_threshold: float = 0.75
    strong_hand_extra_mean: float = 1.5
    strong_hand_extra_std:  float = 1.2

    # Extra delay on first action of a new hand (reading cards)
    first_action_extra: float = 1.2


# Profile presets
_PROFILES: dict[str, TimingConfig] = {
    TimingProfile.SHARK: TimingConfig(
        mean_delay=1.8, std_delay=1.4,
        min_delay=0.2, max_delay=10.0,
        think_probability=0.06,
        hover_probability=0.20,
    ),
    TimingProfile.ROCK: TimingConfig(
        mean_delay=4.5, std_delay=2.5,
        min_delay=1.0, max_delay=20.0,
        think_probability=0.15,
        hover_probability=0.35,
        strong_hand_extra_mean=2.5,
    ),
    TimingProfile.TAG: TimingConfig(
        mean_delay=2.8, std_delay=1.6,
        min_delay=0.4, max_delay=14.0,
        think_probability=0.09,
        hover_probability=0.25,
    ),
    TimingProfile.LAG: TimingConfig(
        mean_delay=2.0, std_delay=2.8,   # high std = very erratic
        min_delay=0.2, max_delay=15.0,
        think_probability=0.12,
        hover_probability=0.30,
    ),
    TimingProfile.FISH: TimingConfig(
        mean_delay=1.2, std_delay=1.0,   # fast but with random spikes
        min_delay=0.1, max_delay=8.0,
        think_probability=0.05,
        hover_probability=0.15,
        strong_hand_extra_mean=0.3,
    ),
    TimingProfile.DEFAULT: TimingConfig(),
}


class HumanTiming:
    """
    Generates human-like pre-action delays for bot actions.

    Integrates with RealActionExecutor to replace the simplistic
    uniform random delays with realistic statistical distributions.

    Parameters
    ----------
    profile : str
        Timing profile name.  One of: shark, rock, tag, lag, fish, default.
    seed : int | None
        Optional RNG seed for reproducible testing.
    """

    def __init__(
        self,
        profile: str = "default",
        seed: Optional[int] = None,
    ) -> None:
        self._rng = random.Random(seed)
        self.profile_name = profile
        self.config = _PROFILES.get(profile, _PROFILES[TimingProfile.DEFAULT])

        # State tracking
        self._action_count: int = 0
        self._last_action_time: float = 0.0
        self._current_hand_action_count: int = 0

        logger.debug("HumanTiming: profile='%s'", profile)

    # ── Public API ───────────────────────────────────────────────────────────

    def pre_action_delay(
        self,
        hand_equity: float = 0.5,
        action: str = "call",
        is_first_action: bool = False,
    ) -> float:
        """Calculate a realistic delay before executing a poker action.

        Parameters
        ----------
        hand_equity : float
            Current hand equity [0.0, 1.0].  Higher equity may trigger
            slow-play extension.
        action : str
            Action type: fold / check / call / raise / bet / allin.
        is_first_action : bool
            True if this is the first action of a new hand (reading cards).

        Returns
        -------
        float
            Delay in seconds.  Call ``time.sleep(delay)`` before acting.
        """
        cfg = self.config
        rng = self._rng

        # 1. Base delay from truncated normal distribution
        raw = rng.gauss(cfg.mean_delay, cfg.std_delay)
        delay = max(cfg.min_delay, min(cfg.max_delay, raw))

        # 2. Thinking session (rare long pause)
        if rng.random() < cfg.think_probability:
            think_time = rng.uniform(cfg.think_min, cfg.think_max)
            logger.debug(
                "HumanTiming: thinking session %.1fs (action=%s)", think_time, action
            )
            delay = max(delay, think_time)

        # 3. Strong-hand slow-play extension
        if hand_equity >= cfg.strong_hand_threshold:
            extra = abs(rng.gauss(
                cfg.strong_hand_extra_mean, cfg.strong_hand_extra_std
            ))
            # Only apply extra 60% of the time (unpredictable)
            if rng.random() < 0.60:
                delay += extra
                logger.debug(
                    "HumanTiming: strong-hand pause +%.1fs (equity=%.2f)",
                    extra, hand_equity,
                )

        # 4. First-action of hand: add card-reading time
        if is_first_action:
            delay += cfg.first_action_extra + rng.uniform(0, 0.8)

        # 5. Fold is usually faster (decision already made)
        if action.lower() == "fold":
            delay *= rng.uniform(0.4, 0.8)
            delay = max(cfg.min_delay, delay)

        # 6. All-in is usually slower (big moment)
        if action.lower() in ("allin", "all-in", "all_in"):
            delay += rng.uniform(1.5, 4.5)

        # 7. Time-of-day variance: night = slightly faster
        hour = time.localtime().tm_hour
        if 23 <= hour or hour < 4:   # late night
            delay *= rng.uniform(0.80, 0.95)
        elif 8 <= hour < 12:          # morning
            delay *= rng.uniform(1.05, 1.20)

        # Final clamp
        delay = max(cfg.min_delay, min(cfg.max_delay * 1.5, delay))

        self._action_count += 1
        self._last_action_time = time.time()
        self._current_hand_action_count += 1

        logger.debug(
            "HumanTiming: %.2fs delay for action='%s' equity=%.2f",
            delay, action, hand_equity,
        )
        return delay

    def should_fake_hover(self) -> bool:
        """Return True if the bot should perform a fake hover before clicking.

        The fake hover moves the cursor toward the button, pauses briefly,
        moves away, then moves back to click — mimicking human hesitation.
        """
        return self._rng.random() < self.config.hover_probability

    def hover_retreat_path(
        self,
        target: Tuple[int, int],
        current: Tuple[int, int],
    ) -> list[Tuple[int, int, float]]:
        """Generate a fake hover-and-retreat path.

        Returns a list of (x, y, pause_seconds) waypoints:
          1. Move 60-80% of the way toward target, pause 0.3-0.8s
          2. Retreat slightly (random direction)
          3. Return to target

        Args:
            target:  (x, y) of the button to click.
            current: (x, y) of the current cursor position.

        Returns:
            List of (x, y, pause_seconds) tuples.
        """
        rng = self._rng
        tx, ty = target
        cx, cy = current

        # Step 1: Move 60-80% toward the button
        frac = rng.uniform(0.60, 0.82)
        mid_x = int(cx + (tx - cx) * frac)
        mid_y = int(cy + (ty - cy) * frac)

        # Add slight wobble to mid-point
        mid_x += rng.randint(-8, 8)
        mid_y += rng.randint(-6, 6)

        # Step 2: Retreat — move slightly away (perpendicular or backward)
        retreat_dx = rng.randint(-25, 25)
        retreat_dy = rng.randint(-15, 15)
        ret_x = mid_x + retreat_dx
        ret_y = mid_y + retreat_dy

        # Step 3: Final destination = actual target with small click offset
        final_x = tx + rng.randint(-3, 3)
        final_y = ty + rng.randint(-2, 2)

        pause_at_mid    = rng.uniform(0.25, 0.75)
        pause_at_retreat = rng.uniform(0.05, 0.20)

        return [
            (mid_x,  mid_y,  pause_at_mid),
            (ret_x,  ret_y,  pause_at_retreat),
            (final_x, final_y, 0.0),
        ]

    def apply_with_hover(
        self,
        target_x: int,
        target_y: int,
        action_fn: Callable[[], None],
        *,
        hand_equity: float = 0.5,
        action: str = "call",
        move_fn: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Apply full human-like timing + optional fake hover, then call action_fn.

        This is the main entry point to use in RealActionExecutor.

        Parameters
        ----------
        target_x, target_y : int
            Screen coordinates of the button to click.
        action_fn : callable
            The actual click / keyboard action to perform.
        hand_equity : float
            Current hand equity [0.0, 1.0].
        action : str
            Action type for timing classification.
        move_fn : callable(x, y) | None
            Function to move the mouse.  If None, tries pyautogui.moveTo.
        """
        # 1. Pre-action delay
        delay = self.pre_action_delay(hand_equity=hand_equity, action=action)
        time.sleep(delay)

        # 2. Optional fake hover-retreat
        if self.should_fake_hover() and move_fn is not None:
            try:
                import pyautogui
                cx, cy = pyautogui.position()
            except Exception:
                cx, cy = target_x - 200, target_y

            waypoints = self.hover_retreat_path((target_x, target_y), (cx, cy))
            for wx, wy, pause in waypoints:
                move_fn(wx, wy)
                if pause > 0:
                    time.sleep(pause)

        # 3. Execute the action
        action_fn()

    def new_hand(self) -> None:
        """Signal that a new hand has started — resets per-hand counters."""
        self._current_hand_action_count = 0

    def reset(self) -> None:
        """Full reset of all counters."""
        self._action_count = 0
        self._last_action_time = 0.0
        self._current_hand_action_count = 0

    # ── Stats ────────────────────────────────────────────────────────────────

    @property
    def total_actions(self) -> int:
        return self._action_count

    @property
    def seconds_since_last_action(self) -> float:
        if self._last_action_time == 0.0:
            return 0.0
        return time.time() - self._last_action_time

    def get_stats(self) -> dict:
        return {
            "profile": self.profile_name,
            "total_actions": self._action_count,
            "seconds_since_last": round(self.seconds_since_last_action, 1),
            "mean_delay": self.config.mean_delay,
            "think_probability": self.config.think_probability,
        }


def make_timing(profile: str) -> HumanTiming:
    """Factory: create a HumanTiming instance for the given bot profile name."""
    return HumanTiming(profile=profile)
