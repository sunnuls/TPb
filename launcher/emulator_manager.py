"""
Emulator Manager — Android emulator pool management for HIVE bots.

Mirrors `launcher/bot_account_binder.py` (bot ↔ nickname ↔ HWND) and
`launcher/vm_manager.py` (Hyper-V VM lifecycle), but for a pool of
Android emulator instances (LDPlayer, MuMu, BlueStacks, Nox, stock AVD)
addressed via ADB.

Replaces "one bot = one desktop window" with "one bot = one emulator
instance", so a single host machine can run many more concurrent bots
(emulators are far lighter than full VMs, and denser than desktop
windows). The HIVE coordination layer (CentralHub / HiveCoordinator /
CollusionCoordinator) is unaffected — it only cares about `bot_id`,
not how that bot captures its screen or clicks buttons.

Features:
  - Discover all ADB-visible emulator instances (`adb devices -l`)
  - Bind bot_id ↔ emulator serial, persisted to `config/emulator_bindings.json`
  - Launch/stop emulator instances via vendor console tools
    (LDPlayer `ldconsole.exe`, MuMu `MuMuManager.exe`) when configured
  - Health-check: verify a bound emulator is still reachable over ADB
  - Factory: `get_backend(bot_id)` returns a ready `ADBBackend`

Usage::

    mgr = EmulatorManager()
    mgr.discover()                          # populate from `adb devices -l`
    mgr.bind("bot_1", serial="127.0.0.1:5555")
    backend = mgr.get_backend("bot_1")
    frame = backend.capture()

⚠️ EDUCATIONAL RESEARCH ONLY.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from bridge.emulator.adb_backend import ADBBackend, ADBDeviceInfo, list_adb_devices
    ADB_BACKEND_AVAILABLE = True
except Exception:
    ADB_BACKEND_AVAILABLE = False
    ADBBackend = None  # type: ignore[misc,assignment]
    ADBDeviceInfo = None  # type: ignore[misc,assignment]

    def list_adb_devices(*_args, **_kwargs) -> List:  # type: ignore[misc]
        return []


DEFAULT_BINDINGS_FILE = Path("config/emulator_bindings.json")


class EmulatorStatus(str, Enum):
    """Health status of a bound emulator instance."""
    BOUND = "bound"          # serial set, ADB reports "device" (ready)
    OFFLINE = "offline"      # serial set, ADB reports offline/unauthorized
    UNREACHABLE = "unreachable"  # serial set, not visible to ADB at all
    UNBOUND = "unbound"      # no serial assigned yet


@dataclass
class EmulatorInstance:
    """One bot ↔ emulator-instance binding.

    Attributes:
        bot_id:       Unique bot identifier (matches `BotInstance.bot_id`).
        serial:       ADB serial, e.g. "127.0.0.1:5555" or "emulator-5554".
        vendor:       Emulator vendor label ("ldplayer", "mumu", "generic", ...).
        instance_index: Vendor-specific instance index (used for console launch).
        model:        Reported device model (from `adb devices -l`).
        status:       Current health status.
        bound_at:     Timestamp of last successful bind.
        last_check:   Timestamp of last health check.
    """
    bot_id: str = ""
    serial: str = ""
    vendor: str = "generic"
    instance_index: int = -1
    model: str = ""
    status: EmulatorStatus = EmulatorStatus.UNBOUND
    bound_at: float = 0.0
    last_check: float = 0.0

    def to_dict(self) -> dict:
        return {
            "bot_id": self.bot_id,
            "serial": self.serial,
            "vendor": self.vendor,
            "instance_index": self.instance_index,
            "model": self.model,
            "status": self.status.value,
            "bound_at": self.bound_at,
            "last_check": self.last_check,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EmulatorInstance":
        return cls(
            bot_id=data.get("bot_id", ""),
            serial=data.get("serial", ""),
            vendor=data.get("vendor", "generic"),
            instance_index=data.get("instance_index", -1),
            model=data.get("model", ""),
            status=EmulatorStatus(data.get("status", "unbound")),
            bound_at=data.get("bound_at", 0.0),
            last_check=data.get("last_check", 0.0),
        )


# Vendor console executables used for launch/stop (best-effort; only used
# if the corresponding emulator is actually installed at the given path).
_VENDOR_CONSOLES = {
    "ldplayer": r"C:\LDPlayer\LDPlayer9\ldconsole.exe",
    "mumu": r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuManager.exe",
}


class EmulatorManager:
    """
    Manages a pool of Android emulator instances for the bot pool.

    Analogous to `BotAccountBinder` (HWND-based) but for ADB serials.
    Persists bindings to JSON so restarts don't lose bot ↔ emulator
    assignments.
    """

    def __init__(
        self,
        bindings_file: Path = DEFAULT_BINDINGS_FILE,
        adb_path: str = "adb",
    ) -> None:
        self.bindings_file = Path(bindings_file)
        self.adb_path = adb_path
        self.instances: Dict[str, EmulatorInstance] = {}  # bot_id -> instance
        self._backends: Dict[str, "ADBBackend"] = {}       # bot_id -> cached backend

        self._load()
        logger.info("EmulatorManager initialized (%d bound instances)", len(self.instances))

    # ── Discovery ────────────────────────────────────────────────────────

    def discover(self) -> List["ADBDeviceInfo"]:
        """Return all emulator instances currently visible to ADB.

        Does not bind anything — use `bind()` to assign a discovered
        serial to a bot_id.
        """
        devices = list_adb_devices(self.adb_path)
        logger.info("EmulatorManager.discover: found %d ADB device(s)", len(devices))
        return devices

    def unassigned_devices(self) -> List["ADBDeviceInfo"]:
        """Devices visible to ADB that are not yet bound to any bot."""
        bound_serials = {inst.serial for inst in self.instances.values()}
        return [d for d in self.discover() if d.serial not in bound_serials and d.is_ready()]

    # ── Binding ──────────────────────────────────────────────────────────

    def bind(self, bot_id: str, serial: str, vendor: str = "generic", instance_index: int = -1) -> EmulatorInstance:
        """Bind a bot_id to an emulator's ADB serial."""
        model = ""
        for d in self.discover():
            if d.serial == serial:
                model = d.model
                break

        inst = EmulatorInstance(
            bot_id=bot_id,
            serial=serial,
            vendor=vendor,
            instance_index=instance_index,
            model=model,
            status=EmulatorStatus.BOUND,
            bound_at=time.time(),
            last_check=time.time(),
        )
        self.instances[bot_id] = inst
        self._backends.pop(bot_id, None)  # invalidate cached backend
        self._save()
        logger.info("EmulatorManager: bound bot '%s' -> serial '%s'", bot_id, serial)
        return inst

    def auto_bind_all(self, bot_ids: List[str], vendor: str = "generic") -> Dict[str, Optional[EmulatorInstance]]:
        """Bind each bot_id to the next unassigned, ready ADB device.

        Convenient for spinning up N bots against N already-running
        emulator instances without manually looking up serials.
        Returns a mapping bot_id -> EmulatorInstance (or None if no
        free device was available for that bot).
        """
        results: Dict[str, Optional[EmulatorInstance]] = {}
        free = [d for d in self.unassigned_devices()]
        for bot_id in bot_ids:
            if bot_id in self.instances and self.instances[bot_id].serial:
                results[bot_id] = self.instances[bot_id]
                continue
            if not free:
                logger.warning("auto_bind_all: no free emulator for bot '%s'", bot_id)
                results[bot_id] = None
                continue
            device = free.pop(0)
            results[bot_id] = self.bind(bot_id, serial=device.serial, vendor=vendor)
        return results

    def unbind(self, bot_id: str) -> bool:
        """Remove a bot's emulator binding."""
        if bot_id not in self.instances:
            return False
        del self.instances[bot_id]
        self._backends.pop(bot_id, None)
        self._save()
        logger.info("EmulatorManager: unbound bot '%s'", bot_id)
        return True

    def get(self, bot_id: str) -> Optional[EmulatorInstance]:
        return self.instances.get(bot_id)

    # ── Health checks ────────────────────────────────────────────────────

    def health_check(self, bot_id: str) -> EmulatorStatus:
        """Refresh and return the health status of a bound instance."""
        inst = self.instances.get(bot_id)
        if inst is None or not inst.serial:
            return EmulatorStatus.UNBOUND

        devices = {d.serial: d for d in self.discover()}
        device = devices.get(inst.serial)

        if device is None:
            inst.status = EmulatorStatus.UNREACHABLE
        elif device.is_ready():
            inst.status = EmulatorStatus.BOUND
            inst.model = device.model or inst.model
        else:
            inst.status = EmulatorStatus.OFFLINE

        inst.last_check = time.time()
        self._save()
        return inst.status

    def health_check_all(self) -> Dict[str, EmulatorStatus]:
        return {bot_id: self.health_check(bot_id) for bot_id in list(self.instances.keys())}

    # ── Backend factory ──────────────────────────────────────────────────

    def get_backend(self, bot_id: str):
        """Return a cached `ADBBackend` for a bound bot, or None."""
        if not ADB_BACKEND_AVAILABLE:
            logger.warning("get_backend: ADBBackend not available (import failed)")
            return None
        inst = self.instances.get(bot_id)
        if inst is None or not inst.serial:
            return None
        if bot_id not in self._backends:
            self._backends[bot_id] = ADBBackend(serial=inst.serial, adb_path=self.adb_path)
        return self._backends[bot_id]

    # ── Vendor console launch/stop (best-effort) ────────────────────────

    def launch_instance(self, vendor: str, instance_index: int, timeout: float = 60.0) -> bool:
        """Launch an emulator instance via its vendor's console tool.

        Only LDPlayer and MuMu are wired up (the two most common tools
        for running many Android instances on one Windows host). Returns
        False if the vendor console isn't found — the instance can still
        be started manually and then bound via `bind()`.
        """
        console = _VENDOR_CONSOLES.get(vendor)
        if not console or not Path(console).exists():
            logger.warning("launch_instance: no console tool found for vendor '%s'", vendor)
            return False

        try:
            if vendor == "ldplayer":
                subprocess.run([console, "launch", "--index", str(instance_index)], timeout=timeout, check=False)
            elif vendor == "mumu":
                subprocess.run([console, "control", "-v", str(instance_index), "launch"], timeout=timeout, check=False)
            else:
                return False
            logger.info("launch_instance: requested launch of %s instance #%d", vendor, instance_index)
            return True
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.error("launch_instance failed: %s", exc)
            return False

    def stop_instance(self, vendor: str, instance_index: int, timeout: float = 30.0) -> bool:
        """Stop an emulator instance via its vendor's console tool."""
        console = _VENDOR_CONSOLES.get(vendor)
        if not console or not Path(console).exists():
            logger.warning("stop_instance: no console tool found for vendor '%s'", vendor)
            return False

        try:
            if vendor == "ldplayer":
                subprocess.run([console, "quit", "--index", str(instance_index)], timeout=timeout, check=False)
            elif vendor == "mumu":
                subprocess.run([console, "control", "-v", str(instance_index), "shutdown"], timeout=timeout, check=False)
            else:
                return False
            return True
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.error("stop_instance failed: %s", exc)
            return False

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.bindings_file.exists():
            return
        try:
            data = json.loads(self.bindings_file.read_text(encoding="utf-8"))
            for item in data.get("instances", []):
                inst = EmulatorInstance.from_dict(item)
                if inst.bot_id:
                    self.instances[inst.bot_id] = inst
        except Exception as exc:
            logger.error("EmulatorManager: failed to load bindings: %s", exc)

    def _save(self) -> None:
        try:
            self.bindings_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"instances": [inst.to_dict() for inst in self.instances.values()]}
            self.bindings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("EmulatorManager: failed to save bindings: %s", exc)
