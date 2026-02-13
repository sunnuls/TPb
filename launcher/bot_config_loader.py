"""
Bot Config Loader — Phase 2 of settings.md.

Per-bot configuration that loads at startup and supports on-the-fly
changes.  Bridges ``BotProfileManager`` (JSON profiles) with
``BotManager`` / ``BotInstance`` so every bot gets its individual
settings on startup, and changes can be pushed mid-session.

Features:
  - Persisted bot→profile mapping (``config/bot_assignments.json``)
  - Startup loading: every bot automatically receives its assigned profile
  - Hot-reload: change a bot's profile without restart
  - Fallback to global default profile
  - Override support: per-bot field overrides on top of a profile
  - Change log: tracks when and what was changed

Usage::

    loader = BotConfigLoader()
    loader.assign("bot_1", "shark")
    settings = loader.load_for_bot("bot_1")

    # On-the-fly change
    loader.hot_swap("bot_1", "rock")

    # Startup integration
    loader.startup_load_all(bot_manager)

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import copy
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from launcher.bot_settings import BotSettings
from launcher.bot_profile_manager import BotProfileManager, BotProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class BotAssignment:
    """Per-bot profile assignment with optional overrides.

    Attributes:
        bot_id:         the bot identifier (or account_id)
        profile_name:   name of the assigned profile from bot_profiles.json
        overrides:      field-level overrides on top of the profile
        assigned_at:    timestamp of last assignment
    """
    bot_id: str = ""
    profile_name: str = "tag"
    overrides: Dict[str, Any] = field(default_factory=dict)
    assigned_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "overrides": self.overrides,
            "assigned_at": self.assigned_at,
        }

    @classmethod
    def from_dict(cls, bot_id: str, data: Dict[str, Any]) -> BotAssignment:
        return cls(
            bot_id=bot_id,
            profile_name=data.get("profile_name", "tag"),
            overrides=data.get("overrides", {}),
            assigned_at=data.get("assigned_at", time.time()),
        )


@dataclass
class ChangeLogEntry:
    """Records a single config change event."""
    bot_id: str
    old_profile: str
    new_profile: str
    timestamp: float = field(default_factory=time.time)
    source: str = "manual"     # "manual" | "startup" | "hot_swap" | "fallback"


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


class BotConfigLoader:
    """Per-bot configuration loader with startup + hot-reload.

    Parameters:
        profile_manager:    BotProfileManager instance (or auto-created)
        assignments_path:   path to bot_assignments.json
        default_profile:    fallback profile name
    """

    DEFAULT_ASSIGNMENTS = Path("config") / "bot_assignments.json"

    def __init__(
        self,
        profile_manager: Optional[BotProfileManager] = None,
        assignments_path: Optional[Path] = None,
        default_profile: str = "tag",
    ):
        self._pm = profile_manager or BotProfileManager()
        self._path = Path(assignments_path) if assignments_path else self.DEFAULT_ASSIGNMENTS
        self._default = default_profile
        self._assignments: Dict[str, BotAssignment] = {}
        self._changelog: List[ChangeLogEntry] = []
        self._loaded = False

        if self._path.exists():
            self._load_assignments()

    # -- Persistence ---------------------------------------------------------

    def _load_assignments(self) -> int:
        """Load bot→profile assignments from disk."""
        if not self._path.exists():
            return 0

        with open(self._path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        assignments = raw.get("assignments", {})
        loaded = 0
        for bot_id, data in assignments.items():
            self._assignments[bot_id] = BotAssignment.from_dict(bot_id, data)
            loaded += 1

        self._default = raw.get("default_profile", self._default)
        self._loaded = True
        return loaded

    def save_assignments(self) -> bool:
        """Persist current assignments to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "default_profile": self._default,
            "assignments": {
                bot_id: a.to_dict() for bot_id, a in self._assignments.items()
            },
        }

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return True

    # -- Assignment CRUD -----------------------------------------------------

    def assign(
        self,
        bot_id: str,
        profile_name: str,
        overrides: Optional[Dict[str, Any]] = None,
        source: str = "manual",
    ) -> bool:
        """Assign a profile to a bot.

        Args:
            bot_id:        bot or account identifier
            profile_name:  name from bot_profiles.json
            overrides:     optional per-bot field overrides
            source:        who triggered the assignment

        Returns:
            True if the profile exists and was assigned.
        """
        if self._pm.get_profile(profile_name) is None:
            logger.warning(f"Profile '{profile_name}' not found — assignment skipped")
            return False

        old = self._assignments.get(bot_id)
        old_name = old.profile_name if old else ""

        self._assignments[bot_id] = BotAssignment(
            bot_id=bot_id,
            profile_name=profile_name,
            overrides=overrides or {},
        )
        self._pm.set_active_profile(bot_id, profile_name)

        self._changelog.append(ChangeLogEntry(
            bot_id=bot_id,
            old_profile=old_name,
            new_profile=profile_name,
            source=source,
        ))

        return True

    def unassign(self, bot_id: str) -> bool:
        """Remove a bot's assignment (falls back to default)."""
        if bot_id in self._assignments:
            del self._assignments[bot_id]
            return True
        return False

    def get_assignment(self, bot_id: str) -> Optional[BotAssignment]:
        """Get the current assignment for a bot."""
        return self._assignments.get(bot_id)

    def list_assignments(self) -> Dict[str, str]:
        """Return {bot_id: profile_name} for all assigned bots."""
        return {bid: a.profile_name for bid, a in self._assignments.items()}

    # -- Loading settings ----------------------------------------------------

    def load_for_bot(self, bot_id: str) -> BotSettings:
        """Load ``BotSettings`` for a specific bot.

        Resolution order:
          1. Per-bot assignment + overrides
          2. Default profile
          3. BotSettings() hard-coded defaults

        Returns:
            ``BotSettings`` ready for the bot to use.
        """
        assignment = self._assignments.get(bot_id)
        profile_name = assignment.profile_name if assignment else self._default

        # Get profile
        profile = self._pm.get_profile(profile_name)
        if profile is None:
            # Fallback to default
            profile = self._pm.get_profile(self._default)
            if profile is None:
                logger.warning(f"Default profile '{self._default}' not found — using hardcoded defaults")
                return BotSettings()

        # Convert to settings
        settings = self._pm.profile_to_settings(profile_name)
        if settings is None:
            return BotSettings()

        # Apply per-bot overrides
        if assignment and assignment.overrides:
            settings = self._apply_overrides(settings, assignment.overrides)

        return settings

    def load_profile_for_bot(self, bot_id: str) -> Optional[BotProfile]:
        """Load the full ``BotProfile`` for a bot (not just BotSettings)."""
        assignment = self._assignments.get(bot_id)
        profile_name = assignment.profile_name if assignment else self._default
        return self._pm.get_profile(profile_name)

    # -- Hot reload ----------------------------------------------------------

    def hot_swap(self, bot_id: str, new_profile: str) -> Optional[BotSettings]:
        """Change a bot's profile on-the-fly and return new settings.

        Does NOT restart the bot — caller is responsible for pushing
        the new settings to the running instance.

        Returns:
            New ``BotSettings`` if successful, None if profile not found.
        """
        ok = self.assign(bot_id, new_profile, source="hot_swap")
        if not ok:
            return None
        return self.load_for_bot(bot_id)

    def hot_override(
        self,
        bot_id: str,
        overrides: Dict[str, Any],
    ) -> Optional[BotSettings]:
        """Apply field-level overrides on-the-fly.

        If bot has no assignment yet, uses the default profile.

        Returns:
            Updated ``BotSettings``.
        """
        if bot_id not in self._assignments:
            self.assign(bot_id, self._default, source="fallback")

        assignment = self._assignments[bot_id]
        assignment.overrides.update(overrides)
        assignment.assigned_at = time.time()

        self._changelog.append(ChangeLogEntry(
            bot_id=bot_id,
            old_profile=assignment.profile_name,
            new_profile=assignment.profile_name,
            source="hot_override",
        ))

        return self.load_for_bot(bot_id)

    # -- Startup integration -------------------------------------------------

    def startup_load_all(self, bot_instances: Dict[str, Any]) -> int:
        """Load settings for all known bots at startup.

        Accepts a dict of ``{bot_id: BotInstance}`` (or any object with
        a ``.settings`` attribute).

        Returns:
            Number of bots that received custom profiles.
        """
        loaded = 0
        for bot_id, bot in bot_instances.items():
            settings = self.load_for_bot(bot_id)
            if hasattr(bot, "settings"):
                bot.settings = settings
                loaded += 1
                logger.info(f"Loaded profile for {bot_id[:8]}: "
                            f"{self.get_effective_profile_name(bot_id)}")

        return loaded

    def get_effective_profile_name(self, bot_id: str) -> str:
        """Return the profile name actually in effect for this bot."""
        a = self._assignments.get(bot_id)
        return a.profile_name if a else self._default

    # -- Changelog -----------------------------------------------------------

    @property
    def changelog(self) -> List[ChangeLogEntry]:
        return list(self._changelog)

    def changelog_for_bot(self, bot_id: str) -> List[ChangeLogEntry]:
        return [e for e in self._changelog if e.bot_id == bot_id]

    def clear_changelog(self):
        self._changelog.clear()

    # -- Properties ----------------------------------------------------------

    @property
    def default_profile(self) -> str:
        return self._default

    @default_profile.setter
    def default_profile(self, name: str):
        if self._pm.get_profile(name) is not None:
            self._default = name

    @property
    def assignment_count(self) -> int:
        return len(self._assignments)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _apply_overrides(settings: BotSettings, overrides: Dict[str, Any]) -> BotSettings:
        """Apply a dict of overrides to a BotSettings instance."""
        d = settings.to_dict()
        for key, value in overrides.items():
            if key in d:
                d[key] = value
        return BotSettings.from_dict(d)
