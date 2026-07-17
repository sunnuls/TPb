"""
Tests for ADBBackend and `list_adb_devices` (mobile emulator transport).

SAFETY NOTE: These tests never invoke a real `adb` binary — all subprocess
calls are mocked. They test parsing logic, safety gating, and the
CaptureBackend contract only.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from bridge.emulator.adb_backend import ADBBackend, ADBDeviceInfo, list_adb_devices
from bridge.emulator.capture_backend import BackendResolution, CaptureBackend
from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode


def _completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestListAdbDevices:
    """Parsing of `adb devices -l` output."""

    @patch("bridge.emulator.adb_backend.shutil.which", return_value="/usr/bin/adb")
    @patch("bridge.emulator.adb_backend.subprocess.run")
    def test_parses_multiple_devices(self, mock_run, _mock_which):
        mock_run.return_value = _completed(
            stdout=(
                "List of devices attached\n"
                "127.0.0.1:5555  device product:LDPlayer model:LDPlayer transport_id:3\n"
                "emulator-5554   offline\n"
                "\n"
            )
        )

        devices = list_adb_devices()

        assert len(devices) == 2
        assert devices[0] == ADBDeviceInfo(
            serial="127.0.0.1:5555", state="device", model="LDPlayer", transport_id="3"
        )
        assert devices[0].is_ready() is True
        assert devices[1].serial == "emulator-5554"
        assert devices[1].is_ready() is False

    @patch("bridge.emulator.adb_backend.shutil.which", return_value="/usr/bin/adb")
    @patch("bridge.emulator.adb_backend.subprocess.run")
    def test_empty_output(self, mock_run, _mock_which):
        mock_run.return_value = _completed(stdout="List of devices attached\n")
        assert list_adb_devices() == []

    @patch("bridge.emulator.adb_backend.shutil.which", return_value=None)
    def test_adb_not_installed(self, _mock_which):
        assert list_adb_devices() == []

    @patch("bridge.emulator.adb_backend.shutil.which", return_value="/usr/bin/adb")
    @patch("bridge.emulator.adb_backend.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="adb", timeout=8))
    def test_timeout_returns_empty(self, _mock_run, _mock_which):
        assert list_adb_devices() == []


class TestADBBackendContract:
    """ADBBackend implements the CaptureBackend interface."""

    def test_is_capture_backend(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.DRY_RUN))
        backend = ADBBackend(serial="127.0.0.1:5555", safety=safety)
        assert isinstance(backend, CaptureBackend)
        assert "127.0.0.1:5555" in repr(backend)


class TestADBBackendConnection:
    @patch("bridge.emulator.adb_backend.list_adb_devices")
    def test_is_connected_true(self, mock_list):
        mock_list.return_value = [ADBDeviceInfo(serial="127.0.0.1:5555", state="device")]
        backend = ADBBackend(serial="127.0.0.1:5555", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.is_connected() is True

    @patch("bridge.emulator.adb_backend.list_adb_devices")
    def test_is_connected_false_when_absent(self, mock_list):
        mock_list.return_value = []
        backend = ADBBackend(serial="127.0.0.1:5555", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.is_connected() is False

    @patch("bridge.emulator.adb_backend.list_adb_devices")
    def test_is_connected_false_when_offline(self, mock_list):
        mock_list.return_value = [ADBDeviceInfo(serial="127.0.0.1:5555", state="offline")]
        backend = ADBBackend(serial="127.0.0.1:5555", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.is_connected() is False


class TestADBBackendResolution:
    @patch.object(ADBBackend, "_adb_shell", return_value="Physical size: 720x1280\n")
    def test_parses_resolution(self, _mock_shell):
        backend = ADBBackend(serial="s1", safety=SafetyFramework(config=SafetyConfig()))
        res = backend.get_resolution()
        assert res == BackendResolution(width=720, height=1280)

    @patch.object(ADBBackend, "_adb_shell", return_value=None)
    def test_resolution_none_on_failure(self, _mock_shell):
        backend = ADBBackend(serial="s1", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.get_resolution() is None

    @patch.object(ADBBackend, "_adb_shell", return_value="garbage")
    def test_resolution_none_on_unparsable(self, _mock_shell):
        backend = ADBBackend(serial="s1", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.get_resolution() is None


class TestADBBackendCapture:
    @patch("bridge.emulator.adb_backend.CV2_AVAILABLE", True)
    @patch("bridge.emulator.adb_backend.cv2")
    @patch("bridge.emulator.adb_backend.subprocess.run")
    def test_capture_success(self, mock_run, mock_cv2):
        fake_png_bytes = b"\x89PNG-fake-bytes"
        mock_run.return_value = _completed(stdout=fake_png_bytes)
        fake_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        mock_cv2.imdecode.return_value = fake_frame

        backend = ADBBackend(serial="s1", safety=SafetyFramework(config=SafetyConfig()))
        frame = backend.capture()

        assert frame is not None
        assert frame.shape == (10, 10, 3)
        assert backend._consecutive_failures == 0

    @patch("bridge.emulator.adb_backend.subprocess.run")
    def test_capture_returns_none_on_empty_stdout(self, mock_run):
        mock_run.return_value = _completed(stdout=b"")
        backend = ADBBackend(serial="s1", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.capture() is None
        assert backend._consecutive_failures == 1

    @patch("bridge.emulator.adb_backend.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="adb", timeout=8))
    def test_capture_returns_none_on_timeout(self, _mock_run):
        backend = ADBBackend(serial="s1", safety=SafetyFramework(config=SafetyConfig()))
        assert backend.capture() is None


class TestADBBackendInputSafety:
    """Real input (click/swipe/type/key) must require UNSAFE mode."""

    def test_click_blocked_in_dry_run(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.DRY_RUN))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "_adb_shell") as mock_shell:
            assert backend.click(10, 20) is False
            mock_shell.assert_not_called()

    def test_click_blocked_in_safe_mode(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.SAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "_adb_shell") as mock_shell:
            assert backend.click(10, 20) is False
            mock_shell.assert_not_called()

    def test_click_executes_in_unsafe_mode(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.UNSAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "_adb_shell", return_value="") as mock_shell:
            assert backend.click(10, 20) is True
            mock_shell.assert_called_once_with(["input", "tap", "10", "20"])

    def test_swipe_executes_in_unsafe_mode(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.UNSAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "_adb_shell", return_value="") as mock_shell:
            assert backend.swipe(0, 0, 100, 200, duration_ms=250) is True
            mock_shell.assert_called_once_with(["input", "swipe", "0", "0", "100", "200", "250"])

    def test_type_text_escapes_spaces(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.UNSAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "_adb_shell", return_value="") as mock_shell:
            assert backend.type_text("all in") is True
            mock_shell.assert_called_once_with(["input", "text", "all%sin"])

    def test_key_event_executes_in_unsafe_mode(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.UNSAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "_adb_shell", return_value="") as mock_shell:
            assert backend.key_event("BACK") is True
            mock_shell.assert_called_once_with(["input", "keyevent", "BACK"])


class TestClickRelative:
    def test_click_relative_uses_resolution(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.UNSAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "get_resolution", return_value=BackendResolution(720, 1280)):
            with patch.object(backend, "click", return_value=True) as mock_click:
                assert backend.click_relative(0.5, 0.9) is True
                mock_click.assert_called_once_with(360, 1152)

    def test_click_relative_false_without_resolution(self):
        safety = SafetyFramework(config=SafetyConfig(mode=SafetyMode.UNSAFE))
        backend = ADBBackend(serial="s1", safety=safety)
        with patch.object(backend, "get_resolution", return_value=None):
            assert backend.click_relative(0.5, 0.5) is False
