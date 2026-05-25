#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for scaling.md — Phase 2: Fingerprint spoofing.

Covers:
- DeviceFingerprint data model & serialization
- BrowserProfile, ScreenProfile, SystemProfile, HardwareProfile
- FingerprintGenerator — determinism, uniqueness, realism
- FingerprintStore — cache, persistence, invalidation
- HeaderInjector — header generation
- 100-bot uniqueness acceptance test
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from device_emulation import (
    OSType,
    BrowserType,
    BrowserProfile,
    ScreenProfile,
    SystemProfile,
    HardwareProfile,
    DeviceFingerprint,
    FingerprintGenerator,
    FingerprintStore,
    HeaderInjector,
)


# ===========================================================================
# Test Enums
# ===========================================================================

class TestEnums(unittest.TestCase):
    def test_os_types(self):
        self.assertEqual(OSType.WINDOWS, "windows")
        self.assertEqual(OSType.MACOS, "macos")

    def test_browser_types(self):
        self.assertEqual(BrowserType.CHROME, "chrome")
        self.assertEqual(BrowserType.FIREFOX, "firefox")


# ===========================================================================
# Test Profile dataclasses
# ===========================================================================

class TestBrowserProfile(unittest.TestCase):
    def test_to_dict(self):
        bp = BrowserProfile(browser_type=BrowserType.CHROME, version="120.0")
        d = bp.to_dict()
        self.assertEqual(d["browser"], "chrome")
        self.assertEqual(d["version"], "120.0")


class TestScreenProfile(unittest.TestCase):
    def test_resolution(self):
        sp = ScreenProfile(width=1920, height=1080)
        self.assertEqual(sp.resolution, "1920x1080")

    def test_to_dict(self):
        sp = ScreenProfile()
        d = sp.to_dict()
        self.assertIn("width", d)
        self.assertIn("pixel_ratio", d)


class TestSystemProfile(unittest.TestCase):
    def test_to_dict(self):
        sp = SystemProfile(timezone="Europe/Moscow", language="ru-RU")
        d = sp.to_dict()
        self.assertEqual(d["timezone"], "Europe/Moscow")
        self.assertEqual(d["language"], "ru-RU")


class TestHardwareProfile(unittest.TestCase):
    def test_to_dict(self):
        hp = HardwareProfile(cpu_cores=16, memory_gb=32)
        d = hp.to_dict()
        self.assertEqual(d["cpu_cores"], 16)
        self.assertEqual(d["memory_gb"], 32)


# ===========================================================================
# Test DeviceFingerprint
# ===========================================================================

class TestDeviceFingerprint(unittest.TestCase):
    def test_to_headers(self):
        fp = DeviceFingerprint(
            browser=BrowserProfile(
                browser_type=BrowserType.CHROME,
                version="120.0.6099.130",
                user_agent="Mozilla/5.0 Chrome/120",
            ),
            system=SystemProfile(language="en-US", languages=["en-US", "en"]),
        )
        h = fp.to_headers()
        self.assertEqual(h["User-Agent"], "Mozilla/5.0 Chrome/120")
        self.assertIn("Accept-Language", h)
        self.assertIn("Sec-Ch-Ua", h)
        self.assertIn("Sec-Ch-Ua-Platform", h)

    def test_to_headers_firefox(self):
        fp = DeviceFingerprint(
            browser=BrowserProfile(browser_type=BrowserType.FIREFOX),
            system=SystemProfile(language="de-DE"),
        )
        h = fp.to_headers()
        self.assertIn("User-Agent", h)
        # Firefox doesn't have Sec-Ch-Ua
        self.assertNotIn("Sec-Ch-Ua", h)

    def test_to_dict_from_dict(self):
        gen = FingerprintGenerator()
        fp = gen.generate("test_bot")
        d = fp.to_dict()
        fp2 = DeviceFingerprint.from_dict(d)

        self.assertEqual(fp.bot_id, fp2.bot_id)
        self.assertEqual(fp.browser.user_agent, fp2.browser.user_agent)
        self.assertEqual(fp.screen.width, fp2.screen.width)
        self.assertEqual(fp.system.timezone, fp2.system.timezone)
        self.assertEqual(fp.canvas_hash, fp2.canvas_hash)

    def test_accept_language(self):
        fp = DeviceFingerprint(
            system=SystemProfile(languages=["en-US", "en", "de"]),
        )
        h = fp.to_headers()
        al = h["Accept-Language"]
        self.assertTrue(al.startswith("en-US"))
        self.assertIn("en;q=", al)

    def test_dnt_header(self):
        fp = DeviceFingerprint(
            browser=BrowserProfile(browser_type=BrowserType.FIREFOX),
            system=SystemProfile(do_not_track=True),
        )
        h = fp.to_headers()
        self.assertEqual(h.get("DNT"), "1")


# ===========================================================================
# Test FingerprintGenerator
# ===========================================================================

class TestFingerprintGenerator(unittest.TestCase):
    def test_deterministic(self):
        """Same bot_id produces same fingerprint."""
        gen = FingerprintGenerator()
        fp1 = gen.generate("bot_42")
        fp2 = gen.generate("bot_42")
        self.assertEqual(fp1.browser.user_agent, fp2.browser.user_agent)
        self.assertEqual(fp1.screen.width, fp2.screen.width)
        self.assertEqual(fp1.system.timezone, fp2.system.timezone)
        self.assertEqual(fp1.canvas_hash, fp2.canvas_hash)

    def test_different_bots_different(self):
        """Different bot_ids produce different fingerprints."""
        gen = FingerprintGenerator()
        fp1 = gen.generate("bot_1")
        fp2 = gen.generate("bot_2")
        # Very unlikely all fields match
        different = (
            fp1.browser.user_agent != fp2.browser.user_agent or
            fp1.screen.width != fp2.screen.width or
            fp1.canvas_hash != fp2.canvas_hash
        )
        self.assertTrue(different)

    def test_base_seed_matters(self):
        """Different base_seed produces different results for same bot_id."""
        gen1 = FingerprintGenerator(base_seed=0)
        gen2 = FingerprintGenerator(base_seed=999)
        fp1 = gen1.generate("bot_1")
        fp2 = gen2.generate("bot_1")
        self.assertNotEqual(fp1.canvas_hash, fp2.canvas_hash)

    def test_user_agent_realistic(self):
        """User-Agent must contain Mozilla/5.0."""
        gen = FingerprintGenerator()
        for i in range(50):
            fp = gen.generate(f"bot_{i}")
            self.assertTrue(
                fp.browser.user_agent.startswith("Mozilla/5.0"),
                f"UA not realistic: {fp.browser.user_agent}",
            )

    def test_valid_screen_resolution(self):
        gen = FingerprintGenerator()
        for i in range(50):
            fp = gen.generate(f"bot_{i}")
            self.assertGreater(fp.screen.width, 0)
            self.assertGreater(fp.screen.height, 0)

    def test_canvas_hash_unique(self):
        gen = FingerprintGenerator()
        hashes = {gen.generate(f"bot_{i}").canvas_hash for i in range(100)}
        # All 100 should be unique
        self.assertEqual(len(hashes), 100)

    def test_os_distribution(self):
        """OS distribution roughly matches config (65% Win, 20% Mac, 15% Linux)."""
        gen = FingerprintGenerator()
        os_counts = {}
        n = 200
        for i in range(n):
            fp = gen.generate(f"bot_dist_{i}")
            os_counts[fp.system.os_type] = os_counts.get(fp.system.os_type, 0) + 1

        # Windows should be most common
        self.assertGreater(os_counts.get(OSType.WINDOWS, 0), n * 0.3)

    def test_browser_version_present(self):
        gen = FingerprintGenerator()
        for i in range(30):
            fp = gen.generate(f"bot_ver_{i}")
            self.assertTrue(len(fp.browser.version) > 0)

    def test_fonts_non_empty(self):
        gen = FingerprintGenerator()
        for i in range(20):
            fp = gen.generate(f"bot_font_{i}")
            self.assertGreater(len(fp.installed_fonts), 5)

    def test_hardware_realistic(self):
        gen = FingerprintGenerator()
        for i in range(30):
            fp = gen.generate(f"bot_hw_{i}")
            self.assertIn(fp.hardware.cpu_cores, [2, 4, 6, 8, 12, 16])
            self.assertIn(fp.hardware.memory_gb, [4, 8, 16, 32])


# ===========================================================================
# Test FingerprintStore
# ===========================================================================

class TestFingerprintStore(unittest.TestCase):
    def test_cache(self):
        store = FingerprintStore()
        fp1 = store.get("bot_1")
        fp2 = store.get("bot_1")
        self.assertIs(fp1, fp2)  # same object

    def test_size(self):
        store = FingerprintStore()
        store.get("bot_1")
        store.get("bot_2")
        self.assertEqual(store.size, 2)

    def test_invalidate(self):
        store = FingerprintStore()
        fp1 = store.get("bot_1")
        store.invalidate("bot_1")
        fp2 = store.get("bot_1")
        # Regenerated but deterministic — same content
        self.assertEqual(fp1.canvas_hash, fp2.canvas_hash)
        self.assertIsNot(fp1, fp2)

    def test_clear(self):
        store = FingerprintStore()
        store.get("bot_1")
        store.get("bot_2")
        store.clear()
        self.assertEqual(store.size, 0)

    def test_persist_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "fp.json"
            store = FingerprintStore(persist_path=path)
            store.get("bot_1")
            store.get("bot_2")
            store.save()

            self.assertTrue(path.exists())

            # Load into new store
            store2 = FingerprintStore(persist_path=path)
            self.assertEqual(store2.size, 2)
            fp = store2.get("bot_1")
            self.assertEqual(fp.bot_id, "bot_1")

    def test_all_fingerprints(self):
        store = FingerprintStore()
        store.get("a")
        store.get("b")
        all_fp = store.all_fingerprints()
        self.assertIn("a", all_fp)
        self.assertIn("b", all_fp)


# ===========================================================================
# Test HeaderInjector
# ===========================================================================

class TestHeaderInjector(unittest.TestCase):
    def test_inject(self):
        store = FingerprintStore()
        injector = HeaderInjector(store)
        headers = injector.inject("bot_1")
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept-Language", headers)

    def test_inject_merge(self):
        store = FingerprintStore()
        injector = HeaderInjector(store)
        headers = injector.inject("bot_1", {"X-Custom": "value"})
        self.assertIn("User-Agent", headers)
        self.assertEqual(headers["X-Custom"], "value")

    def test_inject_consistent(self):
        store = FingerprintStore()
        injector = HeaderInjector(store)
        h1 = injector.inject("bot_1")
        h2 = injector.inject("bot_1")
        self.assertEqual(h1["User-Agent"], h2["User-Agent"])


# ===========================================================================
# Acceptance: 100 bots — all unique fingerprints
# ===========================================================================

class TestHundredBotFingerprints(unittest.TestCase):
    """Acceptance test: 100 bots must have unique, realistic fingerprints."""

    def test_100_unique_user_agents(self):
        gen = FingerprintGenerator()
        uas = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            uas.add(fp.browser.user_agent)
        # Should have high uniqueness (some overlaps expected
        # due to limited browser version pool × OS combos)
        self.assertGreater(len(uas), 40)

    def test_100_unique_canvas_hashes(self):
        gen = FingerprintGenerator()
        hashes = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            hashes.add(fp.canvas_hash)
        self.assertEqual(len(hashes), 100)

    def test_100_unique_webgl_hashes(self):
        gen = FingerprintGenerator()
        hashes = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            hashes.add(fp.webgl_hash)
        self.assertEqual(len(hashes), 100)

    def test_100_all_valid_headers(self):
        store = FingerprintStore()
        injector = HeaderInjector(store)
        for i in range(100):
            headers = injector.inject(f"bot_{i}")
            self.assertIn("User-Agent", headers)
            self.assertIn("Accept-Language", headers)
            self.assertTrue(headers["User-Agent"].startswith("Mozilla/5.0"))

    def test_100_diverse_os(self):
        gen = FingerprintGenerator()
        os_types = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            os_types.add(fp.system.os_type)
        # Should have at least 2 different OS types
        self.assertGreaterEqual(len(os_types), 2)

    def test_100_diverse_browsers(self):
        gen = FingerprintGenerator()
        browsers = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            browsers.add(fp.browser.browser_type)
        self.assertGreaterEqual(len(browsers), 2)

    def test_100_diverse_resolutions(self):
        gen = FingerprintGenerator()
        resolutions = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            resolutions.add(fp.screen.resolution)
        self.assertGreater(len(resolutions), 5)

    def test_100_diverse_timezones(self):
        gen = FingerprintGenerator()
        tzs = set()
        for i in range(100):
            fp = gen.generate(f"bot_{i}")
            tzs.add(fp.system.timezone)
        self.assertGreater(len(tzs), 5)

    def test_100_deterministic_consistency(self):
        """Running generation twice for all 100 gives same results."""
        gen = FingerprintGenerator()
        for i in range(100):
            fp1 = gen.generate(f"bot_{i}")
            fp2 = gen.generate(f"bot_{i}")
            self.assertEqual(fp1.canvas_hash, fp2.canvas_hash)
            self.assertEqual(fp1.browser.user_agent, fp2.browser.user_agent)


if __name__ == "__main__":
    unittest.main()
