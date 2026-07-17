"""
Smoke test: PokerStars mobile on MuMu — capture, OCR pot, find action buttons, act.

Usage:
    python tools/test_ps_mobile_live.py --serial emulator-5556
    python tools/test_ps_mobile_live.py --serial emulator-5556 --act fold
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    pytesseract = None  # type: ignore


def ocr_region(img: np.ndarray, y0: float, y1: float, x0: float = 0.0, x1: float = 1.0) -> str:
    if pytesseract is None:
        return ""
    h, w = img.shape[:2]
    crop = img[int(h * y0) : int(h * y1), int(w * x0) : int(w * x1)]
    if crop.size == 0:
        return ""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return pytesseract.image_to_string(gray, lang="rus+eng", config="--psm 6").strip()


def parse_pot(text: str) -> float | None:
    m = re.search(r"(?:Банк|Bank|Pot)\s*[:：]?\s*([\d\s.,]+)", text, re.I)
    if not m:
        m = re.search(r"([\d][\d\s.,]{0,10})", text)
    if not m:
        return None
    raw = re.sub(r"[^\d]", "", m.group(1))
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def find_green_buttons(img: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return list of (cx, cy, w, h) for green action buttons in lower third."""
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (35, 60, 60), (95, 255, 255))
    mask[: int(h * 0.65), :] = 0
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    buttons = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw > 120 and bh > 50 and bw * bh > 8000:
            buttons.append((x + bw // 2, y + bh // 2, bw, bh))
    buttons.sort(key=lambda t: t[0])
    return buttons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", default="emulator-5556")
    ap.add_argument("--act", choices=["none", "fold", "check", "call"], default="none")
    ap.add_argument("--loops", type=int, default=8)
    args = ap.parse_args()

    from bridge.emulator.adb_backend import ADBBackend
    from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode

    mode = SafetyMode.UNSAFE if args.act != "none" else SafetyMode.DRY_RUN
    backend = ADBBackend(
        serial=args.serial,
        safety=SafetyFramework(config=SafetyConfig(mode=mode)),
    )
    print(f"serial={args.serial} connected={backend.is_connected()} mode={mode.name}")

    out_dir = ROOT / "tools"
    for i in range(args.loops):
        img = backend.capture()
        if img is None:
            print(f"[{i}] capture failed")
            time.sleep(1)
            continue
        path = out_dir / f"_ps_live_{i}.png"
        cv2.imwrite(str(path), img)

        pot_text = ocr_region(img, 0.38, 0.55, 0.15, 0.85)
        hero_text = ocr_region(img, 0.72, 0.95, 0.05, 0.55)
        pot = parse_pot(pot_text)
        buttons = find_green_buttons(img)
        pot_preview = repr(pot_text)[:60]
        hero_preview = repr(hero_text)[:80]
        print(f"[{i}] pot_ocr={pot_preview} pot={pot} buttons={buttons}")
        print(f"     hero_ocr={hero_preview}")

        if args.act != "none" and buttons:
            # typical mobile: left=fold, mid=check/call, right=raise
            if args.act == "fold" and len(buttons) >= 1:
                cx, cy = buttons[0][0], buttons[0][1]
            elif args.act in ("check", "call") and len(buttons) >= 2:
                cx, cy = buttons[1][0], buttons[1][1]
            else:
                cx, cy = buttons[0][0], buttons[0][1]
            print(f"     ACT {args.act} -> tap ({cx},{cy})")
            backend.click(cx, cy)
            time.sleep(2)
            img2 = backend.capture()
            if img2 is not None:
                cv2.imwrite(str(out_dir / "_ps_live_after_act.png"), img2)
            return 0

        time.sleep(1.2)

    print("done (no action taken or buttons never appeared)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
