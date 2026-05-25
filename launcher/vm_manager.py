"""
VM Manager — Hyper-V Virtual Machine Management.

Manages Hyper-V VMs for running isolated poker client instances.
Each VM runs a separate Windows OS with its own poker client, IP, and account.

Architecture:
    Host (Windows 11 Pro/Enterprise)
    ├── Hyper-V VM 1 → CoinPoker Account A → Residential Proxy RU
    ├── Hyper-V VM 2 → CoinPoker Account B → Residential Proxy DE
    └── Hyper-V VM 3 → CoinPoker Account C → Residential Proxy FR

This module communicates with Hyper-V via PowerShell commands.
Screenshots are captured at the hypervisor level — the guest VM cannot
detect or prevent this capture method (unlike SetWindowDisplayAffinity).

Requirements:
    - Windows 10/11 Pro or Enterprise (Hyper-V feature)
    - PowerShell 5.1+ with Hyper-V cmdlets
    - Hyper-V enabled: Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

Usage::

    mgr = VMManager()
    vms = mgr.list_vms()
    mgr.start_vm("Bot1")
    frame = mgr.capture_vm_screenshot("Bot1")
    mgr.send_vm_input("Bot1", "click", x=500, y=300)
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VMState(str, Enum):
    """Hyper-V VM power states."""
    RUNNING    = "Running"
    OFF        = "Off"
    SAVED      = "Saved"
    PAUSED     = "Paused"
    STARTING   = "Starting"
    STOPPING   = "Stopping"
    UNKNOWN    = "Unknown"


@dataclass
class VMInfo:
    """Information about a Hyper-V VM."""
    name: str
    state: VMState = VMState.UNKNOWN
    cpu_count: int = 2
    memory_mb: int = 4096
    uptime_seconds: float = 0.0
    ip_address: str = ""
    notes: str = ""

    def is_running(self) -> bool:
        return self.state == VMState.RUNNING


@dataclass
class VMConfig:
    """Configuration for creating a new VM."""
    name: str
    memory_mb: int = 4096
    cpu_count: int = 2
    disk_size_gb: int = 60
    switch_name: str = "Default Switch"
    # Proxy to route through for network isolation
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_user: str = ""
    proxy_pass: str = ""
    # Geographic identity matching the proxy location
    timezone: str = "UTC"
    locale: str = "en-US"
    account_label: str = ""


class VMManager:
    """
    Manages Hyper-V VMs for isolated poker bot instances.

    All VM operations use PowerShell cmdlets via subprocess.
    Screenshot capture uses Get-VMVideo which is invisible to guest OS.
    """

    def __init__(self, powershell_path: str = "powershell") -> None:
        self._ps = powershell_path
        self._available: Optional[bool] = None

    # ── Availability check ───────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """True if Hyper-V PowerShell module is accessible."""
        if self._available is None:
            self._available = self._check_hyperv()
        return self._available

    def _check_hyperv(self) -> bool:
        result = self._run_ps(
            "Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V "
            "| Select-Object -ExpandProperty State",
            timeout=15,
        )
        if result and "Enabled" in result:
            logger.info("VMManager: Hyper-V is enabled")
            return True
        # Try just importing the module
        result2 = self._run_ps("Import-Module Hyper-V -ErrorAction SilentlyContinue; "
                               "Get-Command Get-VM | Select-Object -ExpandProperty Name",
                               timeout=10)
        ok = bool(result2 and "Get-VM" in result2)
        logger.info("VMManager: Hyper-V module available = %s", ok)
        return ok

    # ── VM listing ───────────────────────────────────────────────────────────

    def list_vms(self) -> List[VMInfo]:
        """Return list of all VMs on this host."""
        script = (
            "Get-VM | Select-Object Name, State, ProcessorCount, "
            "MemoryAssigned, Uptime | ConvertTo-Json"
        )
        raw = self._run_ps(script)
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            vms = []
            for item in data:
                name  = item.get("Name", "")
                state_str = item.get("State", {})
                if isinstance(state_str, dict):
                    state_str = state_str.get("value", "Unknown")
                try:
                    state = VMState(str(state_str))
                except ValueError:
                    state = VMState.UNKNOWN

                mem_mb = item.get("MemoryAssigned", 0)
                if isinstance(mem_mb, (int, float)):
                    mem_mb = int(mem_mb) // (1024 * 1024)

                uptime = item.get("Uptime", {})
                uptime_s = 0.0
                if isinstance(uptime, dict):
                    uptime_s = (
                        uptime.get("TotalSeconds", 0)
                        or uptime.get("Days", 0) * 86400
                        + uptime.get("Hours", 0) * 3600
                        + uptime.get("Minutes", 0) * 60
                        + uptime.get("Seconds", 0)
                    )

                vms.append(VMInfo(
                    name=name,
                    state=state,
                    cpu_count=item.get("ProcessorCount", 2),
                    memory_mb=mem_mb,
                    uptime_seconds=float(uptime_s),
                ))
            return vms
        except Exception as exc:
            logger.error("list_vms parse error: %s", exc)
            return []

    def get_vm(self, name: str) -> Optional[VMInfo]:
        """Get info about a specific VM by name."""
        vms = self.list_vms()
        return next((v for v in vms if v.name == name), None)

    # ── VM lifecycle ─────────────────────────────────────────────────────────

    def start_vm(self, name: str, wait: bool = True, timeout: float = 60.0) -> bool:
        """Start a VM.

        Args:
            name:    VM name.
            wait:    Wait until VM is Running state.
            timeout: Max seconds to wait.

        Returns:
            True if started successfully.
        """
        result = self._run_ps(f"Start-VM -Name '{name}'")
        if result is None:
            logger.error("start_vm: PowerShell error for VM '%s'", name)
            return False

        if wait:
            deadline = time.time() + timeout
            while time.time() < deadline:
                info = self.get_vm(name)
                if info and info.state == VMState.RUNNING:
                    logger.info("VM '%s' is running", name)
                    return True
                time.sleep(2)
            logger.warning("start_vm: VM '%s' did not reach Running state in %.0fs", name, timeout)
            return False
        return True

    def stop_vm(self, name: str, force: bool = False) -> bool:
        """Gracefully (or forcefully) stop a VM."""
        flag = "-TurnOff" if force else "-Force"
        result = self._run_ps(f"Stop-VM -Name '{name}' {flag}")
        return result is not None

    def save_vm(self, name: str) -> bool:
        """Save (hibernate) a VM."""
        result = self._run_ps(f"Save-VM -Name '{name}'")
        return result is not None

    def checkpoint_vm(self, name: str, checkpoint_name: str = "clean_state") -> bool:
        """Create a checkpoint (snapshot) of a VM."""
        result = self._run_ps(
            f"Checkpoint-VM -Name '{name}' -SnapshotName '{checkpoint_name}'"
        )
        return result is not None

    def restore_checkpoint(self, name: str, checkpoint_name: str = "clean_state") -> bool:
        """Restore a VM to a checkpoint."""
        result = self._run_ps(
            f"Restore-VMCheckpoint -VMName '{name}' -Name '{checkpoint_name}' -Confirm:$false"
        )
        return result is not None

    # ── Screenshot (stealth — invisible to guest) ────────────────────────────

    def capture_vm_screenshot(self, name: str) -> Optional[np.ndarray]:
        """Capture a screenshot of a VM at the hypervisor level.

        This is completely invisible to the guest OS.
        The poker client inside the VM cannot detect this capture.

        Uses Save-VMVideo PowerShell cmdlet to export a BMP frame,
        then loads it as a numpy BGR array.

        Args:
            name: VM name.

        Returns:
            BGR numpy array or None on failure.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp:
                tmp_path = tmp.name

            script = f"Save-VMVideo -VMName '{name}' -DestinationPath '{tmp_path}'"
            result = self._run_ps(script, timeout=10)
            if result is None:
                logger.warning("capture_vm_screenshot: Save-VMVideo failed for '%s'", name)
                return None

            path = Path(tmp_path)
            if not path.exists() or path.stat().st_size < 100:
                logger.warning("capture_vm_screenshot: output file missing or empty")
                return None

            try:
                import cv2
                img = cv2.imread(str(path))
                path.unlink(missing_ok=True)
                return img
            except ImportError:
                # Fallback: use PIL
                try:
                    from PIL import Image
                    img_pil = Image.open(str(path))
                    arr = np.array(img_pil)
                    path.unlink(missing_ok=True)
                    # PIL loads as RGB, convert to BGR
                    if len(arr.shape) == 3 and arr.shape[2] >= 3:
                        arr = arr[:, :, ::-1]
                    return arr
                except Exception as pil_exc:
                    logger.error("capture_vm_screenshot: PIL failed: %s", pil_exc)
                    path.unlink(missing_ok=True)
                    return None

        except Exception as exc:
            logger.error("capture_vm_screenshot error for '%s': %s", name, exc)
            return None

    # ── Input injection (via PowerShell → VMConnect) ─────────────────────────

    def send_mouse_click(
        self,
        vm_name: str,
        x: int,
        y: int,
        button: str = "left",
    ) -> bool:
        """Send a mouse click to a VM via a helper agent script.

        Requires a small agent (vm_agent.py) running inside the VM
        that listens on a local port for click commands.

        This is cleaner than using VMConnect COM API (which requires
        elevation and specific Windows features).

        Args:
            vm_name: VM name (used to look up agent connection).
            x, y:    Coordinates in guest screen space.
            button:  "left" or "right".

        Returns:
            True if command was sent successfully.
        """
        agent_port = self._get_agent_port(vm_name)
        if agent_port is None:
            logger.warning("send_mouse_click: no agent for VM '%s'", vm_name)
            return False
        return self._send_agent_command(
            agent_port,
            {"action": "click", "x": x, "y": y, "button": button},
        )

    def send_key(self, vm_name: str, key: str) -> bool:
        """Send a key press to a VM agent."""
        agent_port = self._get_agent_port(vm_name)
        if agent_port is None:
            return False
        return self._send_agent_command(
            agent_port,
            {"action": "key", "key": key},
        )

    # ── VM creation helper ───────────────────────────────────────────────────

    def create_vm(self, cfg: VMConfig) -> bool:
        """Create a new Generation 2 Hyper-V VM.

        Note: This creates the VM shell only. You must:
        1. Attach a Windows ISO and install the OS manually.
        2. Install the poker client inside the VM.
        3. Install vm_agent.py in the VM for input injection.
        4. Set up proxy routing inside the VM.

        Args:
            cfg: VM configuration.

        Returns:
            True if VM was created.
        """
        script = (
            f"New-VM -Name '{cfg.name}' "
            f"-MemoryStartupBytes {cfg.memory_mb * 1024 * 1024} "
            f"-Generation 2 "
            f"-SwitchName '{cfg.switch_name}'; "
            f"Set-VMProcessor -VMName '{cfg.name}' -Count {cfg.cpu_count}; "
            f"New-VHD -Path 'C:\\VMs\\{cfg.name}\\disk.vhdx' "
            f"-SizeBytes {cfg.disk_size_gb}GB -Dynamic; "
            f"Add-VMHardDiskDrive -VMName '{cfg.name}' "
            f"-Path 'C:\\VMs\\{cfg.name}\\disk.vhdx'"
        )
        result = self._run_ps(script)
        if result is None:
            logger.error("create_vm: failed to create VM '%s'", cfg.name)
            return False
        logger.info("VM '%s' created (%.0fMB RAM, %d CPU)", cfg.name, cfg.memory_mb, cfg.cpu_count)
        return True

    # ── Network config ───────────────────────────────────────────────────────

    def configure_vm_proxy(
        self,
        vm_name: str,
        proxy_host: str,
        proxy_port: int,
        proxy_user: str = "",
        proxy_pass: str = "",
    ) -> bool:
        """Configure system-wide proxy inside the VM.

        Sets Windows system proxy via netsh/registry through the VM agent.
        The poker client will route through this proxy automatically.

        Args:
            vm_name:    VM name.
            proxy_host: Residential proxy hostname/IP.
            proxy_port: Proxy port.
            proxy_user: Optional proxy username.
            proxy_pass: Optional proxy password.

        Returns:
            True if command was sent.
        """
        agent_port = self._get_agent_port(vm_name)
        if agent_port is None:
            return False
        return self._send_agent_command(
            agent_port,
            {
                "action": "set_proxy",
                "host": proxy_host,
                "port": proxy_port,
                "user": proxy_user,
                "pass": proxy_pass,
            },
        )

    def randomize_vm_hardware_id(self, vm_name: str) -> bool:
        """Randomize VM hardware identifiers to avoid fingerprinting.

        Changes: MAC address, BIOS GUID, SMBIOS serial numbers.

        Args:
            vm_name: VM name (must be Off state).

        Returns:
            True if MAC was changed (other IDs require manual BIOS editing).
        """
        import random
        mac = "02:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}".format(
            *[random.randint(0, 255) for _ in range(5)]
        )
        script = (
            f"$adapter = Get-VMNetworkAdapter -VMName '{vm_name}'; "
            f"Set-VMNetworkAdapter -VMNetworkAdapter $adapter "
            f"-StaticMacAddress '{mac.replace(':', '')}'"
        )
        result = self._run_ps(script)
        ok = result is not None
        if ok:
            logger.info("VM '%s': randomized MAC to %s", vm_name, mac)
        return ok

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _run_ps(self, script: str, timeout: float = 30.0) -> Optional[str]:
        """Execute a PowerShell script and return stdout."""
        try:
            result = subprocess.run(
                [self._ps, "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0 and result.stderr:
                err = result.stderr.strip()
                if "not recognized" in err.lower() or "access" in err.lower():
                    logger.error("PowerShell error: %s", err[:200])
                else:
                    logger.debug("PS stderr: %s", err[:200])
            return result.stdout.strip() or ""
        except subprocess.TimeoutExpired:
            logger.error("PowerShell command timed out (%.0fs)", timeout)
            return None
        except FileNotFoundError:
            logger.error("PowerShell not found at '%s'", self._ps)
            return None
        except Exception as exc:
            logger.error("_run_ps error: %s", exc)
            return None

    # Agent port mapping (loaded from config)
    _AGENT_CONFIG = Path("config/vm_network.yaml")

    def _get_agent_port(self, vm_name: str) -> Optional[int]:
        """Look up the agent listening port for a VM (from config)."""
        try:
            import yaml
            if not self._AGENT_CONFIG.exists():
                return None
            data = yaml.safe_load(self._AGENT_CONFIG.read_text(encoding="utf-8"))
            vms = data.get("vms", {})
            vm_data = vms.get(vm_name, {})
            return vm_data.get("agent_port")
        except Exception:
            return None

    def _send_agent_command(self, port: int, payload: Dict[str, Any]) -> bool:
        """Send a JSON command to the VM agent running on localhost:port."""
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=3.0) as sock:
                msg = json.dumps(payload).encode() + b"\n"
                sock.sendall(msg)
            return True
        except Exception as exc:
            logger.debug("Agent command failed (port=%d): %s", port, exc)
            return False
