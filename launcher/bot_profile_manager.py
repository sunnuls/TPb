"""
Bot Profile Manager — Phase 1 of settings.md.

Loads, validates, and manages JSON-based bot profiles from
``config/bot_profiles.json``.  Each profile defines aggression,
equity thresholds, bet sizing, timing, mouse parameters, and
session configuration.

Integrates with the existing ``BotSettings`` dataclass and the
``BehaviorProfile`` / ``BehaviorSampler`` from Phase 2 of
action_executor.md.

Usage::

    mgr = BotProfileManager()
    profile = mgr.get_profile("shark")
    settings = mgr.profile_to_settings("shark")
    mgr.set_active_profile("bot_1", "tag")

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from launcher.bot_settings import BotSettings, StrategyPreset

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

# Equity threshold keys
EQUITY_KEYS = [
    "preflop_open",
    "preflop_call",
    "postflop_bet",
    "postflop_call",
    "river_bluff",
]

# Bet sizing keys
BET_SIZING_KEYS = [
    "open_raise_bb",
    "cbet_pot_fraction",
    "turn_pot_fraction",
    "river_pot_fraction",
    "max_bet_multiplier",
]

# Timing keys
TIMING_KEYS = [
    "delay_min",
    "delay_max",
    "think_time_fold",
    "think_time_call",
    "think_time_raise",
    "think_time_allin",
]

# Mouse keys
MOUSE_KEYS = [
    "curve_intensity",
    "speed_mult",
    "jitter",
    "overshoot_prob",
]

VALID_BEHAVIOR_STYLES = {"aggressive", "passive", "balanced", "erratic"}


@dataclass
class EquityThresholds:
    """Equity thresholds for different game stages."""
    preflop_open: float = 0.65
    preflop_call: float = 0.58
    postflop_bet: float = 0.52
    postflop_call: float = 0.48
    river_bluff: float = 0.25

    def to_dict(self) -> Dict[str, float]:
        return {
            "preflop_open": self.preflop_open,
            "preflop_call": self.preflop_call,
            "postflop_bet": self.postflop_bet,
            "postflop_call": self.postflop_call,
            "river_bluff": self.river_bluff,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EquityThresholds:
        return cls(
            preflop_open=float(data.get("preflop_open", 0.65)),
            preflop_call=float(data.get("preflop_call", 0.58)),
            postflop_bet=float(data.get("postflop_bet", 0.52)),
            postflop_call=float(data.get("postflop_call", 0.48)),
            river_bluff=float(data.get("river_bluff", 0.25)),
        )


@dataclass
class BetSizing:
    """Bet sizing configuration."""
    open_raise_bb: float = 2.8
    cbet_pot_fraction: float = 0.60
    turn_pot_fraction: float = 0.55
    river_pot_fraction: float = 0.65
    max_bet_multiplier: float = 3.5

    def to_dict(self) -> Dict[str, float]:
        return {
            "open_raise_bb": self.open_raise_bb,
            "cbet_pot_fraction": self.cbet_pot_fraction,
            "turn_pot_fraction": self.turn_pot_fraction,
            "river_pot_fraction": self.river_pot_fraction,
            "max_bet_multiplier": self.max_bet_multiplier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BetSizing:
        return cls(
            open_raise_bb=float(data.get("open_raise_bb", 2.8)),
            cbet_pot_fraction=float(data.get("cbet_pot_fraction", 0.60)),
            turn_pot_fraction=float(data.get("turn_pot_fraction", 0.55)),
            river_pot_fraction=float(data.get("river_pot_fraction", 0.65)),
            max_bet_multiplier=float(data.get("max_bet_multiplier", 3.5)),
        )


@dataclass
class TimingConfig:
    """Timing parameters for actions."""
    delay_min: float = 0.4
    delay_max: float = 3.0
    think_time_fold: Tuple[float, float] = (0.3, 1.0)
    think_time_call: Tuple[float, float] = (0.5, 2.0)
    think_time_raise: Tuple[float, float] = (0.6, 2.5)
    think_time_allin: Tuple[float, float] = (1.0, 3.5)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delay_min": self.delay_min,
            "delay_max": self.delay_max,
            "think_time_fold": list(self.think_time_fold),
            "think_time_call": list(self.think_time_call),
            "think_time_raise": list(self.think_time_raise),
            "think_time_allin": list(self.think_time_allin),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimingConfig:
        def _pair(key: str, default: Tuple[float, float]) -> Tuple[float, float]:
            val = data.get(key, list(default))
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                return (float(val[0]), float(val[1]))
            return default

        return cls(
            delay_min=float(data.get("delay_min", 0.4)),
            delay_max=float(data.get("delay_max", 3.0)),
            think_time_fold=_pair("think_time_fold", (0.3, 1.0)),
            think_time_call=_pair("think_time_call", (0.5, 2.0)),
            think_time_raise=_pair("think_time_raise", (0.6, 2.5)),
            think_time_allin=_pair("think_time_allin", (1.0, 3.5)),
        )


@dataclass
class MouseProfile:
    """Mouse movement parameters."""
    curve_intensity: int = 5
    speed_mult: float = 1.0
    jitter: float = 0.8
    overshoot_prob: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "curve_intensity": self.curve_intensity,
            "speed_mult": self.speed_mult,
            "jitter": self.jitter,
            "overshoot_prob": self.overshoot_prob,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MouseProfile:
        return cls(
            curve_intensity=int(data.get("curve_intensity", 5)),
            speed_mult=float(data.get("speed_mult", 1.0)),
            jitter=float(data.get("jitter", 0.8)),
            overshoot_prob=float(data.get("overshoot_prob", 0.5)),
        )


@dataclass
class SessionConfig:
    """Session-level configuration."""
    max_session_time: int = 120
    auto_rejoin: bool = True
    table_select_min_vpip: int = 28

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_session_time": self.max_session_time,
            "auto_rejoin": self.auto_rejoin,
            "table_select_min_vpip": self.table_select_min_vpip,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionConfig:
        return cls(
            max_session_time=int(data.get("max_session_time", 120)),
            auto_rejoin=bool(data.get("auto_rejoin", True)),
            table_select_min_vpip=int(data.get("table_select_min_vpip", 28)),
        )


@dataclass
class BotProfile:
    """Complete bot profile loaded from JSON.

    Attributes:
        name:               profile key (e.g. "shark", "rock")
        display_name:       human-readable name
        description:        short description
        aggression_level:   1-10
        equity:             equity thresholds per game stage
        bet_sizing:         bet sizing config
        timing:             action timing config
        mouse:              mouse movement config
        session:            session-level config
        behavior_style:     aggressive / passive / balanced / erratic
    """
    name: str = "custom"
    display_name: str = "Custom"
    description: str = ""
    aggression_level: int = 5
    equity: EquityThresholds = field(default_factory=EquityThresholds)
    bet_sizing: BetSizing = field(default_factory=BetSizing)
    timing: TimingConfig = field(default_factory=TimingConfig)
    mouse: MouseProfile = field(default_factory=MouseProfile)
    session: SessionConfig = field(default_factory=SessionConfig)
    behavior_style: str = "balanced"

    def __post_init__(self):
        self.aggression_level = max(1, min(10, self.aggression_level))
        if self.behavior_style not in VALID_BEHAVIOR_STYLES:
            self.behavior_style = "balanced"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_name": self.display_name,
            "description": self.description,
            "aggression_level": self.aggression_level,
            "equity_thresholds": self.equity.to_dict(),
            "bet_sizing": self.bet_sizing.to_dict(),
            "timing": self.timing.to_dict(),
            "mouse": self.mouse.to_dict(),
            "session": self.session.to_dict(),
            "behavior_style": self.behavior_style,
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> BotProfile:
        return cls(
            name=name,
            display_name=data.get("display_name", name.capitalize()),
            description=data.get("description", ""),
            aggression_level=int(data.get("aggression_level", 5)),
            equity=EquityThresholds.from_dict(data.get("equity_thresholds", {})),
            bet_sizing=BetSizing.from_dict(data.get("bet_sizing", {})),
            timing=TimingConfig.from_dict(data.get("timing", {})),
            mouse=MouseProfile.from_dict(data.get("mouse", {})),
            session=SessionConfig.from_dict(data.get("session", {})),
            behavior_style=data.get("behavior_style", "balanced"),
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationError:
    """A single profile validation issue."""
    profile_name: str
    field: str
    message: str
    severity: str = "error"   # "error" | "warning"


class ProfileValidator:
    """Validates BotProfile data for consistency and sane ranges."""

    def validate(self, profile: BotProfile) -> List[ValidationError]:
        errors: List[ValidationError] = []
        name = profile.name

        # Aggression
        if not (1 <= profile.aggression_level <= 10):
            errors.append(ValidationError(name, "aggression_level",
                                          f"Must be 1-10, got {profile.aggression_level}"))

        # Equity thresholds — each should be [0,1]
        eq = profile.equity
        for k in ["preflop_open", "preflop_call", "postflop_bet",
                   "postflop_call", "river_bluff"]:
            v = getattr(eq, k)
            if not (0.0 <= v <= 1.0):
                errors.append(ValidationError(name, f"equity.{k}",
                                              f"Must be 0.0-1.0, got {v}"))

        # Bet sizing — positive
        bs = profile.bet_sizing
        for k in ["open_raise_bb", "cbet_pot_fraction", "turn_pot_fraction",
                   "river_pot_fraction", "max_bet_multiplier"]:
            v = getattr(bs, k)
            if v <= 0:
                errors.append(ValidationError(name, f"bet_sizing.{k}",
                                              f"Must be > 0, got {v}"))

        # Timing — delay_min < delay_max
        t = profile.timing
        if t.delay_min > t.delay_max:
            errors.append(ValidationError(name, "timing.delay",
                                          f"delay_min ({t.delay_min}) > delay_max ({t.delay_max})"))

        # Think time pairs — first < second
        for pair_name in ["think_time_fold", "think_time_call",
                          "think_time_raise", "think_time_allin"]:
            pair = getattr(t, pair_name)
            if pair[0] > pair[1]:
                errors.append(ValidationError(name, f"timing.{pair_name}",
                                              f"min ({pair[0]}) > max ({pair[1]})"))

        # Mouse
        m = profile.mouse
        if not (0 <= m.curve_intensity <= 10):
            errors.append(ValidationError(name, "mouse.curve_intensity",
                                          f"Must be 0-10, got {m.curve_intensity}"))
        if m.speed_mult <= 0:
            errors.append(ValidationError(name, "mouse.speed_mult",
                                          f"Must be > 0, got {m.speed_mult}"))
        if not (0 <= m.overshoot_prob <= 1):
            errors.append(ValidationError(name, "mouse.overshoot_prob",
                                          f"Must be 0-1, got {m.overshoot_prob}"))

        # Behavior style
        if profile.behavior_style not in VALID_BEHAVIOR_STYLES:
            errors.append(ValidationError(name, "behavior_style",
                                          f"Unknown style: {profile.behavior_style}"))

        return errors


# ---------------------------------------------------------------------------
# Profile manager
# ---------------------------------------------------------------------------


class BotProfileManager:
    """Manages JSON-based bot profiles.

    Features:
      - Load/save profiles from ``config/bot_profiles.json``
      - List, get, add, update, delete profiles
      - Validate profiles
      - Convert profiles to ``BotSettings`` instances
      - Track active profile per bot

    Parameters:
        profiles_path:  path to the JSON file (default: config/bot_profiles.json)
    """

    DEFAULT_PATH = Path("config") / "bot_profiles.json"

    def __init__(self, profiles_path: Optional[Path] = None):
        self._path = Path(profiles_path) if profiles_path else self.DEFAULT_PATH
        self._profiles: Dict[str, BotProfile] = {}
        self._active: Dict[str, str] = {}   # bot_id → profile_name
        self._validator = ProfileValidator()

        if self._path.exists():
            self.load()

    # -- I/O -----------------------------------------------------------------

    def load(self, path: Optional[Path] = None) -> int:
        """Load profiles from JSON file.

        Returns:
            number of profiles loaded
        """
        p = Path(path) if path else self._path
        if not p.exists():
            return 0

        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)

        profiles_data = raw.get("profiles", {})
        loaded = 0
        for name, data in profiles_data.items():
            self._profiles[name] = BotProfile.from_dict(name, data)
            loaded += 1

        return loaded

    def save(self, path: Optional[Path] = None) -> bool:
        """Save current profiles to JSON file."""
        p = Path(path) if path else self._path
        p.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "_meta": {
                "version": "1.0.0",
                "description": "Bot behavior profiles. EDUCATIONAL RESEARCH ONLY.",
            },
            "profiles": {
                name: prof.to_dict() for name, prof in self._profiles.items()
            },
        }

        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return True

    # -- CRUD ----------------------------------------------------------------

    def list_profiles(self) -> List[str]:
        """Return sorted list of profile names."""
        return sorted(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[BotProfile]:
        """Get a profile by name (returns a deep copy)."""
        p = self._profiles.get(name)
        return copy.deepcopy(p) if p else None

    def add_profile(self, profile: BotProfile) -> bool:
        """Add or overwrite a profile."""
        self._profiles[profile.name] = copy.deepcopy(profile)
        return True

    def update_profile(self, name: str, overrides: Dict[str, Any]) -> Optional[BotProfile]:
        """Update specific fields of an existing profile.

        Args:
            name:       profile name
            overrides:  dict of field→value (supports nested: "equity.preflop_open")

        Returns:
            Updated profile or None if not found.
        """
        existing = self._profiles.get(name)
        if existing is None:
            return None

        d = existing.to_dict()
        for key, value in overrides.items():
            parts = key.split(".", 1)
            if len(parts) == 2:
                section, subkey = parts
                section_map = {
                    "equity": "equity_thresholds",
                    "bet_sizing": "bet_sizing",
                    "timing": "timing",
                    "mouse": "mouse",
                    "session": "session",
                }
                actual_section = section_map.get(section, section)
                if actual_section in d and isinstance(d[actual_section], dict):
                    d[actual_section][subkey] = value
            else:
                d[key] = value

        updated = BotProfile.from_dict(name, d)
        self._profiles[name] = updated
        return copy.deepcopy(updated)

    def delete_profile(self, name: str) -> bool:
        """Delete a profile. Returns True if it existed."""
        if name in self._profiles:
            del self._profiles[name]
            # Remove from active mappings
            to_remove = [bid for bid, pn in self._active.items() if pn == name]
            for bid in to_remove:
                del self._active[bid]
            return True
        return False

    def profile_count(self) -> int:
        return len(self._profiles)

    # -- Validation ----------------------------------------------------------

    def validate_profile(self, name: str) -> List[ValidationError]:
        p = self._profiles.get(name)
        if p is None:
            return [ValidationError(name, "*", "Profile not found")]
        return self._validator.validate(p)

    def validate_all(self) -> Dict[str, List[ValidationError]]:
        """Validate all profiles. Returns {name: [errors]}."""
        result = {}
        for name in self._profiles:
            errs = self.validate_profile(name)
            if errs:
                result[name] = errs
        return result

    # -- Conversion to BotSettings ------------------------------------------

    def profile_to_settings(self, name: str) -> Optional[BotSettings]:
        """Convert a profile to a ``BotSettings`` instance."""
        p = self._profiles.get(name)
        if p is None:
            return None

        # Map behavior_style → StrategyPreset
        preset_map = {
            "aggressive": StrategyPreset.AGGRESSIVE,
            "passive": StrategyPreset.CONSERVATIVE,
            "balanced": StrategyPreset.BALANCED,
            "erratic": StrategyPreset.CUSTOM,
        }
        preset = preset_map.get(p.behavior_style, StrategyPreset.CUSTOM)

        return BotSettings(
            preset=preset,
            aggression_level=p.aggression_level,
            equity_threshold=p.equity.postflop_bet,  # primary threshold
            max_bet_multiplier=p.bet_sizing.max_bet_multiplier,
            delay_min=p.timing.delay_min,
            delay_max=p.timing.delay_max,
            mouse_curve_intensity=p.mouse.curve_intensity,
            max_session_time=p.session.max_session_time,
            auto_rejoin=p.session.auto_rejoin,
        )

    # -- Active profile tracking --------------------------------------------

    def set_active_profile(self, bot_id: str, profile_name: str) -> bool:
        """Set the active profile for a bot."""
        if profile_name not in self._profiles:
            return False
        self._active[bot_id] = profile_name
        return True

    def get_active_profile(self, bot_id: str) -> Optional[str]:
        """Get the active profile name for a bot."""
        return self._active.get(bot_id)

    def get_active_settings(self, bot_id: str) -> Optional[BotSettings]:
        """Get BotSettings for the bot's active profile."""
        name = self._active.get(bot_id)
        if name is None:
            return None
        return self.profile_to_settings(name)

    def list_active(self) -> Dict[str, str]:
        """Return all active bot→profile mappings."""
        return dict(self._active)

    # -- Utility -------------------------------------------------------------

    def clone_profile(self, source_name: str, new_name: str) -> Optional[BotProfile]:
        """Clone a profile under a new name."""
        src = self._profiles.get(source_name)
        if src is None:
            return None
        cloned = copy.deepcopy(src)
        cloned.name = new_name
        cloned.display_name = f"{src.display_name} (copy)"
        self._profiles[new_name] = cloned
        return copy.deepcopy(cloned)

    def reset_to_defaults(self) -> int:
        """Reload profiles from disk, discarding in-memory changes."""
        self._profiles.clear()
        self._active.clear()
        return self.load()
