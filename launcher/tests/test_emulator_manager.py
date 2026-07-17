"""
Tests for EmulatorManager — Android emulator pool management.

SAFETY NOTE: No real ADB/emulator processes are invoked; all device
discovery is mocked at the `launcher.emulator_manager.list_adb_devices`
seam.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bridge.emulator.adb_backend import ADBBackend, ADBDeviceInfo
from launcher.emulator_manager import (
    EmulatorInstance,
    EmulatorManager,
    EmulatorStatus,
)


@pytest.fixture
def bindings_file(tmp_path):
    return tmp_path / "emulator_bindings.json"


class TestEmulatorInstance:
    def test_round_trip_dict(self):
        inst = EmulatorInstance(
            bot_id="bot_1", serial="127.0.0.1:5555", vendor="ldplayer",
            instance_index=2, model="LDPlayer", status=EmulatorStatus.BOUND,
            bound_at=100.0, last_check=101.0,
        )
        restored = EmulatorInstance.from_dict(inst.to_dict())
        assert restored == inst


class TestEmulatorManagerBinding:
    @patch("launcher.emulator_manager.list_adb_devices")
    def test_bind_creates_instance(self, mock_list, bindings_file):
        mock_list.return_value = [ADBDeviceInfo(serial="127.0.0.1:5555", state="device", model="LDPlayer")]

        mgr = EmulatorManager(bindings_file=bindings_file)
        inst = mgr.bind("bot_1", serial="127.0.0.1:5555", vendor="ldplayer")

        assert inst.bot_id == "bot_1"
        assert inst.serial == "127.0.0.1:5555"
        assert inst.model == "LDPlayer"
        assert inst.status == EmulatorStatus.BOUND
        assert mgr.get("bot_1") is inst

    @patch("launcher.emulator_manager.list_adb_devices", return_value=[])
    def test_bind_persists_to_disk(self, _mock_list, bindings_file):
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="127.0.0.1:5555")

        assert bindings_file.exists()

        mgr2 = EmulatorManager(bindings_file=bindings_file)
        assert mgr2.get("bot_1") is not None
        assert mgr2.get("bot_1").serial == "127.0.0.1:5555"

    @patch("launcher.emulator_manager.list_adb_devices", return_value=[])
    def test_unbind_removes_instance(self, _mock_list, bindings_file):
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="127.0.0.1:5555")

        assert mgr.unbind("bot_1") is True
        assert mgr.get("bot_1") is None
        assert mgr.unbind("bot_1") is False


class TestEmulatorManagerAutoBind:
    @patch("launcher.emulator_manager.list_adb_devices")
    def test_auto_bind_assigns_free_devices(self, mock_list, bindings_file):
        mock_list.return_value = [
            ADBDeviceInfo(serial="s1", state="device"),
            ADBDeviceInfo(serial="s2", state="device"),
            ADBDeviceInfo(serial="s3", state="offline"),
        ]
        mgr = EmulatorManager(bindings_file=bindings_file)

        results = mgr.auto_bind_all(["bot_1", "bot_2", "bot_3"])

        assert results["bot_1"].serial == "s1"
        assert results["bot_2"].serial == "s2"
        assert results["bot_3"] is None  # s3 offline, not ready

    @patch("launcher.emulator_manager.list_adb_devices")
    def test_auto_bind_skips_already_bound(self, mock_list, bindings_file):
        mock_list.return_value = [ADBDeviceInfo(serial="s1", state="device")]
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="existing-serial")

        results = mgr.auto_bind_all(["bot_1"])

        assert results["bot_1"].serial == "existing-serial"


class TestEmulatorManagerHealthCheck:
    @patch("launcher.emulator_manager.list_adb_devices")
    def test_health_check_bound(self, mock_list, bindings_file):
        mock_list.return_value = [ADBDeviceInfo(serial="s1", state="device")]
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="s1")

        assert mgr.health_check("bot_1") == EmulatorStatus.BOUND

    @patch("launcher.emulator_manager.list_adb_devices")
    def test_health_check_unreachable(self, mock_list, bindings_file):
        mock_list.return_value = [ADBDeviceInfo(serial="s1", state="device")]
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="s1")

        mock_list.return_value = []  # device disappeared
        assert mgr.health_check("bot_1") == EmulatorStatus.UNREACHABLE

    @patch("launcher.emulator_manager.list_adb_devices")
    def test_health_check_offline(self, mock_list, bindings_file):
        mock_list.return_value = [ADBDeviceInfo(serial="s1", state="device")]
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="s1")

        mock_list.return_value = [ADBDeviceInfo(serial="s1", state="offline")]
        assert mgr.health_check("bot_1") == EmulatorStatus.OFFLINE

    @patch("launcher.emulator_manager.list_adb_devices", return_value=[])
    def test_health_check_unbound(self, _mock_list, bindings_file):
        mgr = EmulatorManager(bindings_file=bindings_file)
        assert mgr.health_check("no_such_bot") == EmulatorStatus.UNBOUND

    @patch("launcher.emulator_manager.list_adb_devices")
    def test_health_check_all(self, mock_list, bindings_file):
        mock_list.return_value = [
            ADBDeviceInfo(serial="s1", state="device"),
            ADBDeviceInfo(serial="s2", state="device"),
        ]
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="s1")
        mgr.bind("bot_2", serial="s2")

        statuses = mgr.health_check_all()
        assert statuses == {"bot_1": EmulatorStatus.BOUND, "bot_2": EmulatorStatus.BOUND}


class TestEmulatorManagerBackendFactory:
    @patch("launcher.emulator_manager.list_adb_devices", return_value=[])
    def test_get_backend_returns_adb_backend(self, _mock_list, bindings_file):
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="s1")

        backend = mgr.get_backend("bot_1")

        assert isinstance(backend, ADBBackend)
        assert backend.serial == "s1"
        # Cached: second call returns the same instance.
        assert mgr.get_backend("bot_1") is backend

    @patch("launcher.emulator_manager.list_adb_devices", return_value=[])
    def test_get_backend_none_when_unbound(self, _mock_list, bindings_file):
        mgr = EmulatorManager(bindings_file=bindings_file)
        assert mgr.get_backend("no_such_bot") is None

    @patch("launcher.emulator_manager.list_adb_devices", return_value=[])
    def test_rebind_invalidates_cached_backend(self, _mock_list, bindings_file):
        mgr = EmulatorManager(bindings_file=bindings_file)
        mgr.bind("bot_1", serial="s1")
        backend1 = mgr.get_backend("bot_1")

        mgr.bind("bot_1", serial="s2")
        backend2 = mgr.get_backend("bot_1")

        assert backend1 is not backend2
        assert backend2.serial == "s2"


class TestEmulatorManagerLaunchStop:
    def test_launch_instance_missing_console_returns_false(self, bindings_file):
        with patch("launcher.emulator_manager.list_adb_devices", return_value=[]):
            mgr = EmulatorManager(bindings_file=bindings_file)
        assert mgr.launch_instance("ldplayer", instance_index=0) is False

    def test_stop_instance_unknown_vendor_returns_false(self, bindings_file):
        with patch("launcher.emulator_manager.list_adb_devices", return_value=[]):
            mgr = EmulatorManager(bindings_file=bindings_file)
        assert mgr.stop_instance("unknown_vendor", instance_index=0) is False
