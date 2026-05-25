"""
Stealth Launcher — Process & Window Anti-Detection.

Mitigates bot detection via process name scanning that poker clients
perform on the local machine. Techniques:
  1. Launch Python scripts as windowless processes (pythonw.exe)
  2. Rename the process in Task Manager via ctypes
  3. Hide console window from appearing in process list
  4. Set neutral process description / metadata

Usage::

    # Launch a bot script stealthily
    proc = StealthLauncher.launch_script(
        script="launcher/main.py",
        process_name="AppService.exe",
        args=["--unsafe"],
    )

    # Apply stealth to the CURRENT process (call at startup)
    StealthLauncher.apply_to_current(process_name="SystemAgent")
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Process names known to trigger anti-bot detection in poker clients
# Avoid these names in any process visible to the poker room client.
KNOWN_TRIGGER_NAMES: List[str] = [
    "AutoHotkey",
    "ahk",
    "pyautogui",
    "tesseract",
    "easyocr",
    "opencv",
    "cheatengine",
    "artmoney",
    "ollydbg",
    "x64dbg",
    "winspy",
    "spy++",
    "processhacker",
    "processhacker2",
    "apimonitor",
    "wireshark",
    "fiddler",
    "charles",
]

# Neutral process names that are generic and don't draw attention
NEUTRAL_PROCESS_NAMES: List[str] = [
    "AppService",
    "SystemMonitor",
    "BackgroundTask",
    "HostService",
    "RuntimeBroker",
    "DataSync",
    "CloudAgent",
    "UpdateHelper",
]


class StealthLauncher:
    """Process stealth utilities for bot launch and runtime camouflage."""

    # ── Launch a script stealthily ────────────────────────────────────────────

    @staticmethod
    def launch_script(
        script: str,
        process_name: str = "AppService",
        args: Optional[List[str]] = None,
        hide_console: bool = True,
        pythonw: bool = True,
    ) -> Optional[subprocess.Popen]:
        """Launch a Python script as a windowless background process.

        Args:
            script:       Path to the Python script.
            process_name: Desired process name (rename not always possible).
            args:         Extra CLI arguments.
            hide_console: Hide the console window (SW_HIDE).
            pythonw:      Use pythonw.exe (no console window on Windows).

        Returns:
            Popen handle or None on failure.
        """
        args = args or []

        # Find pythonw.exe (no console version) or fall back to python.exe
        if pythonw and sys.platform == "win32":
            py_exe = Path(sys.executable)
            pw = py_exe.parent / "pythonw.exe"
            if pw.exists():
                interpreter = str(pw)
            else:
                interpreter = str(py_exe)
        else:
            interpreter = sys.executable

        cmd = [interpreter, script] + args

        kwargs: dict = {}
        if hide_console and sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            kwargs["creationflags"] = CREATE_NO_WINDOW | DETACHED_PROCESS
            kwargs["stdin"]  = subprocess.DEVNULL
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL

        try:
            proc = subprocess.Popen(cmd, **kwargs)
            logger.info(
                "StealthLauncher: launched PID=%d as '%s'",
                proc.pid, process_name,
            )
            return proc
        except Exception as exc:
            logger.error("StealthLauncher.launch_script failed: %s", exc)
            return None

    # ── Apply stealth to current process ─────────────────────────────────────

    @staticmethod
    def apply_to_current(process_name: str = "SystemAgent") -> bool:
        """Apply stealth measures to the currently running process.

        On Windows:
          - Sets the console window title to something neutral.
          - Hides the console window.
          - Attempts to rename the process in the Windows process description.

        Args:
            process_name: Neutral name to use for window title / description.

        Returns:
            True if all measures applied successfully.
        """
        success = True

        if sys.platform != "win32":
            logger.debug("StealthLauncher.apply_to_current: non-Windows, limited stealth")
            return False

        # 1. Hide / rename console window
        try:
            kernel32 = ctypes.windll.kernel32
            user32   = ctypes.windll.user32

            # Set neutral console title
            kernel32.SetConsoleTitleW(process_name)

            # Hide the console window
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                SW_HIDE = 0
                user32.ShowWindow(hwnd, SW_HIDE)
                logger.debug("StealthLauncher: console window hidden")
        except Exception as exc:
            logger.warning("StealthLauncher: console hide failed: %s", exc)
            success = False

        # 2. Attempt to set process description via NtSetInformationProcess
        # (works on Windows Vista+ — changes what Process Hacker shows)
        try:
            ntdll = ctypes.windll.ntdll

            class UNICODE_STRING(ctypes.Structure):
                _fields_ = [
                    ("Length",        ctypes.c_ushort),
                    ("MaximumLength", ctypes.c_ushort),
                    ("Buffer",        ctypes.c_wchar_p),
                ]

            name_w = process_name + "\x00"
            us = UNICODE_STRING(
                Length=len(process_name) * 2,
                MaximumLength=(len(process_name) + 1) * 2,
                Buffer=name_w,
            )
            # ProcessImageFileName = 27
            ntdll.NtSetInformationProcess(
                ctypes.windll.kernel32.GetCurrentProcess(),
                27,
                ctypes.byref(us),
                ctypes.sizeof(us),
            )
            logger.debug(
                "StealthLauncher: process name set to '%s'", process_name
            )
        except Exception as exc:
            logger.debug("StealthLauncher: process rename failed (expected): %s", exc)
            # Not critical — this is a best-effort operation

        return success

    # ── Scan for dangerous processes ──────────────────────────────────────────

    @staticmethod
    def scan_dangerous_processes() -> List[str]:
        """Return list of known dangerous process names currently running.

        Useful for self-check before starting a bot session.

        Returns:
            List of found dangerous process names (may be empty).
        """
        found: List[str] = []
        if sys.platform != "win32":
            return found

        try:
            import subprocess as sp
            result = sp.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=10,
            )
            running = result.stdout.lower()
            for name in KNOWN_TRIGGER_NAMES:
                if name.lower() in running:
                    found.append(name)
        except Exception as exc:
            logger.debug("scan_dangerous_processes failed: %s", exc)

        return found

    @staticmethod
    def get_safe_process_name(index: int = 0) -> str:
        """Return a neutral process name by index (for variety across bots)."""
        return NEUTRAL_PROCESS_NAMES[index % len(NEUTRAL_PROCESS_NAMES)]


def apply_stealth_at_startup(index: int = 0) -> None:
    """Convenience: apply stealth to the current process at startup.

    Call this at the very beginning of main.py before any GUI is shown.

    Args:
        index: Bot index (0, 1, 2) — used to pick different neutral names.
    """
    name = StealthLauncher.get_safe_process_name(index)
    StealthLauncher.apply_to_current(name)

    # Warn if dangerous tools are running
    dangerous = StealthLauncher.scan_dangerous_processes()
    if dangerous:
        logger.warning(
            "Stealth warning: detected potentially flagged processes: %s",
            dangerous,
        )
