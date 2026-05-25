"""
Auto-ROI Demo — запуск полного пайплайна roadmap13.

Что делает:
  1. Генерирует синтетический скриншот с шаблонами
  2. Запускает multi-scale find_anchors
  3. Рассчитывает все ROI зоны
  4. Рисует результат на изображении
  5. Сохраняет debug-картинку
  6. (Опционально) пытается найти реальное окно покер-клиента

Запуск:
  python test_auto_roi_demo.py
  python test_auto_roi_demo.py --live   (попробовать найти реальное окно)
"""
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from bridge.vision.anchor_detector import (
    detect_roi,
    find_anchors,
    calculate_all_roi,
    load_config,
    AnchorMatch,
    ROIZone,
)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates", "anchors")
OUTPUT_FILE = "auto_roi_debug.png"

ANCHOR_POSITIONS = [
    ("logo_coinpoker", (10, 5)),
    ("btn_fold", (200, 520)),
    ("btn_call", (340, 520)),
    ("btn_raise", (480, 520)),
    ("btn_check", (200, 490)),
    ("chip_icon", (350, 420)),
    ("pot_icon", (350, 200)),
    ("dealer_button", (300, 350)),
    ("table_border", (100, 100)),
    ("table_corner", (5, 80)),
]

ZONE_COLORS = [
    (0, 255, 0),    # green
    (255, 0, 0),    # blue
    (0, 0, 255),    # red
    (255, 255, 0),  # cyan
    (0, 255, 255),  # yellow
    (255, 0, 255),  # magenta
    (128, 255, 0),  # lime
    (0, 128, 255),  # orange
    (255, 128, 0),  # light blue
    (128, 0, 255),  # purple
]


def generate_screenshot(width=800, height=600):
    img = np.full((height, width, 3), (30, 50, 30), dtype=np.uint8)
    noise = np.random.randint(-5, 6, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    positions = {}
    for name, (px, py) in ANCHOR_POSITIONS:
        path = os.path.join(TEMPLATES_DIR, f"{name}.png")
        tmpl = cv2.imread(path)
        if tmpl is None:
            continue
        th, tw = tmpl.shape[:2]
        px = max(0, min(px, width - tw))
        py = max(0, min(py, height - th))
        img[py:py + th, px:px + tw] = tmpl
        positions[name] = (px, py, tw, th)

    return img, positions


def draw_results(img, anchors, zones):
    vis = img.copy()

    for i, a in enumerate(anchors):
        color = ZONE_COLORS[i % len(ZONE_COLORS)]
        cv2.rectangle(vis, (a.x, a.y), (a.x + a.w, a.y + a.h), color, 2)
        label = f"{a.name} ({a.confidence:.2f} s={a.scale:.1f})"
        cv2.putText(vis, label, (a.x, a.y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    for i, z in enumerate(zones):
        color = ZONE_COLORS[(i + 5) % len(ZONE_COLORS)]
        cv2.rectangle(vis, (z.x, z.y), (z.x + z.w, z.y + z.h), color, 1)
        label = f"ROI:{z.name}"
        cv2.putText(vis, label, (z.x + 2, z.y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

    return vis


def run_synthetic_demo():
    print("=" * 60)
    print("  Auto-ROI Demo — Synthetic Screenshot")
    print("=" * 60)

    config = load_config()
    print(f"\n[Config] {len(config['anchors'])} anchors, {len(config['derived_zones'])} derived zones")
    print(f"[Config] Anchors: {', '.join(config['anchors'].keys())}")

    print("\n[1] Generating synthetic screenshot (800x600)...")
    img, expected = generate_screenshot()
    print(f"    Pasted {len(expected)} templates")

    print("\n[2] Running multi-scale find_anchors...")
    t0 = time.perf_counter()
    anchors = find_anchors(img, config=config)
    t1 = time.perf_counter()
    print(f"    Found {len(anchors)}/{len(config['anchors'])} anchors in {(t1-t0)*1000:.0f}ms")

    for a in anchors:
        print(f"      {a.name:20s}  pos=({a.x:4d},{a.y:4d})  conf={a.confidence:.3f}  scale={a.scale:.2f}")

    print(f"\n[3] Calculating all ROI zones...")
    t2 = time.perf_counter()
    zones = calculate_all_roi(anchors, image_shape=img.shape[:2], config=config)
    t3 = time.perf_counter()
    print(f"    Computed {len(zones)} zones in {(t3-t2)*1000:.0f}ms")

    for z in zones:
        print(f"      {z.name:20s}  ({z.x:4d},{z.y:4d}) {z.w:3d}x{z.h:3d}  src={z.source}  conf={z.confidence:.3f}")

    accuracy = len(anchors) / len(config['anchors']) * 100
    print(f"\n[4] Accuracy: {accuracy:.0f}% ({len(anchors)}/{len(config['anchors'])})")

    print(f"\n[5] Drawing debug visualization...")
    vis = draw_results(img, anchors, zones)
    cv2.imwrite(OUTPUT_FILE, vis)
    print(f"    Saved: {OUTPUT_FILE}")

    total_ms = (t3 - t0) * 1000
    print(f"\n[Summary]")
    print(f"    Anchors found:   {len(anchors)}/{len(config['anchors'])}")
    print(f"    ROI zones:       {len(zones)}")
    print(f"    Total time:      {total_ms:.0f}ms")
    print(f"    Accuracy:        {accuracy:.0f}%")
    print(f"    Status:          {'PASS' if accuracy >= 92 else 'FAIL'} (threshold: 92%)")
    print()

    return accuracy >= 92


def run_multi_resolution_test():
    print("=" * 60)
    print("  Multi-Resolution Stress Test")
    print("=" * 60)

    config = load_config()
    resolutions = [
        (640, 480), (800, 600), (900, 650), (1024, 768),
        (1100, 800), (1280, 960), (750, 550),
    ]

    results = []
    for w, h in resolutions:
        img, _ = generate_screenshot(w, h)
        anchors, zones = detect_roi(img, config=config)
        rate = len(anchors) / len(config['anchors']) * 100
        results.append((w, h, len(anchors), len(zones), rate))
        status = "OK" if rate >= 70 else "LOW"
        print(f"  {w:4d}x{h:4d} — anchors: {len(anchors):2d}/{len(config['anchors'])}  zones: {len(zones):2d}  accuracy: {rate:5.1f}%  [{status}]")

    avg = sum(r[4] for r in results) / len(results)
    print(f"\n  Average accuracy: {avg:.1f}%")
    return avg


def run_live_demo():
    print("\n" + "=" * 60)
    print("  Live Window Search")
    print("=" * 60)

    try:
        from bridge.screen_capture import ScreenCapture
    except ImportError:
        print("  [SKIP] bridge.screen_capture not available (missing win32 deps?)")
        return

    try:
        from bridge.safety import SafetyConfig, SafetyFramework, SafetyMode
        SafetyFramework.get_instance(SafetyConfig(mode=SafetyMode.DRY_RUN))
    except Exception:
        pass

    sc = ScreenCapture()
    print("  Searching for poker client window...")
    hwnd = sc.auto_find_window()

    if hwnd:
        print(f"  Found window: hwnd={hwnd}")
        if sc.current_window:
            w = sc.current_window
            print(f"    Title:  {w.title}")
            print(f"    Size:   {w.width}x{w.height}")
            print(f"    Pos:    ({w.x}, {w.y})")
    else:
        print("  No poker window found on desktop (expected in test environment)")

    saved = ScreenCapture.load_active_window()
    if saved:
        print(f"  Last saved window: {saved.get('title', '?')} (hwnd={saved.get('hwnd')})")
    else:
        print("  No previously saved window config")


def main():
    live = "--live" in sys.argv

    ok = run_synthetic_demo()
    avg = run_multi_resolution_test()

    if live:
        run_live_demo()

    print("\n" + "=" * 60)
    print("  FINAL RESULT")
    print("=" * 60)
    print(f"  Synthetic demo:     {'PASS' if ok else 'FAIL'}")
    print(f"  Multi-res average:  {avg:.1f}%")
    print(f"  Overall:            {'PASS' if ok and avg >= 80 else 'NEEDS REVIEW'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
