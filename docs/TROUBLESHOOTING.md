# Troubleshooting Guide

> Common issues, diagnostics, and fixes for the HIVE Launcher.
>
> ⚠️ **EDUCATIONAL RESEARCH ONLY.**

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation)
3. [Vision Pipeline Issues](#vision)
4. [OCR Issues](#ocr)
5. [Window Capture Issues](#capture)
6. [Bot Behavior Issues](#behavior)
7. [Profile & Config Issues](#profiles)
8. [Logging & Monitoring Issues](#logging)
9. [Performance Issues](#performance)
10. [Test Failures](#tests)

---

## Quick Diagnostics

Run this script to check your environment:

```python
import sys
print(f"Python: {sys.version}")

checks = {}

# OpenCV
try:
    import cv2
    checks["OpenCV"] = cv2.__version__
except ImportError:
    checks["OpenCV"] = "MISSING — pip install opencv-python"

# NumPy
try:
    import numpy
    checks["NumPy"] = numpy.__version__
except ImportError:
    checks["NumPy"] = "MISSING — pip install numpy"

# Tesseract
try:
    import pytesseract
    ver = pytesseract.get_tesseract_version()
    checks["Tesseract"] = str(ver)
except Exception as e:
    checks["Tesseract"] = f"ERROR — {e}"

# PyQt6
try:
    from PyQt6.QtWidgets import QApplication
    checks["PyQt6"] = "OK"
except ImportError:
    checks["PyQt6"] = "MISSING — pip install PyQt6"

# Win32
try:
    import win32gui
    checks["pywin32"] = "OK"
except ImportError:
    checks["pywin32"] = "MISSING — pip install pywin32"

# YOLO
try:
    from ultralytics import YOLO
    checks["ultralytics"] = "OK"
except (ImportError, OSError):
    checks["ultralytics"] = "MISSING or DLL error (optional)"

# EasyOCR
try:
    import easyocr
    checks["EasyOCR"] = "OK"
except ImportError:
    checks["EasyOCR"] = "MISSING (optional — pip install easyocr)"

for name, status in checks.items():
    icon = "✓" if "MISSING" not in status and "ERROR" not in status else "✗"
    print(f"  {icon} {name}: {status}")
```

---

## Installation Issues

### `pip install -e .` fails with PEP 660 error

**Symptom:**
```
ERROR: Project file has a 'build-backend' ... does not support PEP 660
```

**Fix:**
```bash
# Option 1: Install without editable mode
pip install .

# Option 2: Compat mode
pip install -e . --config-settings editable_mode=compat

# Option 3: Install deps manually
pip install opencv-python pytesseract mss keyboard pyqt5 Pillow pywin32
```

### `ultralytics` / `torch` DLL crash on Windows

**Symptom:**
```
Windows fatal exception: access violation
... torch/__init__.py ... _load_dll_libraries
```

**Cause:** Corrupted or incompatible PyTorch DLLs.

**Fix:**
```bash
# Option 1: Reinstall torch
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Option 2: Skip YOLO entirely (optional dependency)
# The vision pipeline works without it — template matching + OCR handle most cases
```

**Verify:** The system gracefully degrades when YOLO is unavailable:
```python
from launcher.vision import AutoROIFinder  # still works
# YOLORegionDetector will not be importable — that's OK
```

### `PyQt6` not found

**Symptom:**
```
ImportError: PyQt6 not available
```

**Fix:**
```bash
pip install PyQt6
# or for older systems:
pip install PyQt5
```

### `pywin32` PostInstall script failed

**Symptom:**
```
ImportError: DLL load failed while importing win32gui
```

**Fix:**
```bash
pip uninstall pywin32 -y
pip install pywin32
# Run post-install script manually:
python -m pywin32_postinstall -install
```

---

## Vision Pipeline Issues

### Auto-calibration returns low confidence

**Symptom:**
```python
result = finder.calibrate(screenshot)
print(result.confidence)  # < 0.5
```

**Causes & Fixes:**

| Cause | Fix |
|---|---|
| Screenshot too dark / too bright | Adjust monitor brightness; use CLAHE |
| Non-standard table skin | Create a manual YAML ROI config |
| Resized / scaled window | Capture at native resolution |
| Obstructed table (overlapping windows) | Use `WindowCapturer` with `include_border=False` |
| Animation in progress | Wait for stable frame, then capture |

**Debug:**
```python
result = finder.calibrate(screenshot)
for anchor in result.anchors:
    print(f"  {anchor.name}: type={anchor.anchor_type.value}, conf={anchor.confidence:.2f}")
```

### No cards detected

**Symptom:** `CardRecognizer.read()` returns empty string.

**Fixes:**
1. Check that the card region is correctly cropped
2. Try multiple preprocessing strategies:
```python
import cv2
region = screenshot[850:960, 860:940]
# Save for inspection
cv2.imwrite("debug_card_region.png", region)
```
3. Verify card is face-up (not face-down / hidden)
4. Check template bank has matching card images

### Template matching returns false positives

**Fix:** Increase confidence threshold:
```python
matches = matcher.match(image, threshold=0.85)  # default 0.75
```

Or use NMS (non-max suppression) — already built into `MultiTemplateMatcher`.

---

## OCR Issues

### Tesseract not found

**Symptom:**
```
pytesseract.pytesseract.TesseractNotFoundError: tesseract is not installed
```

**Fix:**
1. Install Tesseract: https://github.com/tesseract-ocr/tesseract
2. Add to PATH: `C:\Program Files\Tesseract-OCR`
3. Or set path in code:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### OCR reads wrong numbers

**Symptom:** Pot shows "1,234" but OCR reads "1.234" or "l,234".

**Fixes:**
1. **Character whitelist** — restrict to digits + expected chars:
```python
text = pytesseract.image_to_string(region, config="--psm 7 -c tessedit_char_whitelist=0123456789,.$kKmM")
```

2. **Preprocessing** — ensure high contrast:
```python
import cv2
gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

3. **EasyOCR fallback** — often better for non-standard fonts:
```python
import easyocr
reader = easyocr.Reader(["en"])
result = reader.readtext(region, detail=0)
```

### OCR is slow (>5s per region)

**Fixes:**
1. Reduce region size — crop tightly around the text
2. Use PSM 7 (single line) instead of default:
```python
text = pytesseract.image_to_string(region, config="--psm 7")
```
3. Disable unnecessary Tesseract features:
```python
text = pytesseract.image_to_string(region, config="--psm 7 --oem 3")
```

---

## Window Capture Issues

### `WindowCapturer` returns None

**Symptom:**
```python
image = capturer.capture_window_by_hwnd(hwnd)
print(image)  # None
```

**Fixes:**
1. Verify window handle is valid:
```python
import win32gui
print(win32gui.IsWindow(hwnd))  # should be True
print(win32gui.GetWindowText(hwnd))  # should show window title
```

2. Window might be minimized:
```python
import win32gui, win32con
if win32gui.IsIconic(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
```

3. Try client-area capture:
```python
image = capturer.capture_window_by_hwnd(hwnd, include_border=False)
```

### Black / empty screenshot

**Cause:** Hardware-accelerated windows sometimes return black with BitBlt.

**Fix:**
```python
# Fallback to ImageGrab with window rect
import win32gui
from PIL import ImageGrab
import numpy as np, cv2

rect = win32gui.GetWindowRect(hwnd)
screen = np.array(ImageGrab.grab(bbox=rect))
image = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
```

### Wrong window captured

**Fix:** List all windows and find the correct one:
```python
import win32gui

def list_windows():
    windows = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append((hwnd, title))
    win32gui.EnumWindows(callback, None)
    return windows

for hwnd, title in list_windows():
    if "poker" in title.lower():
        print(f"  hwnd={hwnd}: {title}")
```

---

## Bot Behavior Issues

### Bot acts too fast / looks robotic

**Fix:** Increase timing delays:
```python
loader.hot_override("bot_1", {
    "delay_min": 0.8,
    "delay_max": 4.0,
})
```

Or switch to a slower profile:
```python
loader.hot_swap("bot_1", "rock")
```

### Mouse paths look mechanical

**Fix:** Increase mouse curve intensity and jitter:
```json
{
  "mouse": {
    "curve_intensity": 7,
    "speed_mult": 1.2,
    "jitter": 1.5,
    "overshoot_prob": 0.5
  }
}
```

### Anti-pattern detector flags bot as robotic

**Symptom:**
```python
report = executor.self_test(n=100)
print(report.is_human_like)  # False
```

**Check which metric fails:**
```python
print(f"Delay CV: {report.delay_cv:.2f}")         # want > 0.20
print(f"Unique coords: {report.coord_unique_frac:.0%}")  # want > 60%
print(f"Path similarity: {report.path_sim_mean:.2f}")     # want < 0.90
print(f"Timing CV: {report.timing_cv:.2f}")        # want > 0.20
```

**Fixes by metric:**

| Metric | Problem | Fix |
|---|---|---|
| delay_cv too low | Delays too uniform | Increase delay range or use `erratic` style |
| coord_unique_frac too low | Clicking same pixel | Increase jitter + click offset |
| path_sim too high | Paths too similar | Increase curve_intensity |
| timing_cv too low | Actions too regular | Use larger think_time ranges |

### Bot doesn't click buttons

**Causes:**
1. ROI zones are wrong — recalibrate or check YAML config
2. Button text changed (update detection) — check with OCR debug
3. Window moved after calibration — recapture + recalibrate

---

## Profile & Config Issues

### Profile validation fails

**Symptom:**
```
ProfileValidator: aggression_level must be 1..10
```

**Fix:** Check the JSON file for typos:
```bash
python -c "import json; json.load(open('config/bot_profiles.json'))"
```

Common mistakes:
- `aggression_level: 0` → must be 1–10
- `preflop_open > 1.0` → must be 0.0–1.0
- `delay_min > delay_max` → min must be < max
- Invalid `behavior_style` → must be `aggressive`/`passive`/`balanced`/`erratic`

### Bot uses wrong profile

**Check assignments:**
```python
loader = BotConfigLoader()
assignment = loader.get_assignment("bot_1")
print(f"Profile: {assignment.profile_name}")
print(f"Overrides: {assignment.overrides}")
```

**Check changelog:**
```python
for entry in loader.changelog[-5:]:
    print(entry)
```

### Changes not applied after hot-reload

**Ensure BotInstance is linked:**
```python
# Hot-swap sends settings to the BotInstance only if it exists in bot_manager
loader.hot_swap("bot_1", "shark")

# Verify settings were applied
settings = loader.load_for_bot("bot_1")
print(settings.aggression_level)  # should match shark's 8
```

---

## Logging & Monitoring Issues

### Logs not appearing in JSON format

**Fix:** Initialize structured logging at startup:
```python
from launcher.structured_logger import setup_structured_logging

setup_structured_logging(
    log_dir="logs",
    console=True,      # also print to stdout
    level="INFO",
)
```

### SQLite log store grows too large

**Fix:** Periodically clean old logs:
```python
from launcher.log_storage import SQLiteLogStore
import time

store = SQLiteLogStore("logs/bot_logs.db")

# Delete logs older than 7 days
cutoff = time.time() - 7 * 86400
store.delete(before_ts=cutoff)
```

### Telegram alerts not sending

**Checklist:**
1. Bot token is correct (`123456:ABC...`)
2. Chat ID is correct (use `@userinfobot` to find)
3. Bot has been added to the chat/channel
4. Bot has "send messages" permission in the group

**Test with dry-run:**
```python
from launcher.telegram_alerts import TelegramSender

# dry_run=True to test without actually sending
sender = TelegramSender(bot_token="123:ABC", chat_id="-100123", dry_run=True)
result = sender.send("Test message")
print(f"Would send: {result.success}")
```

**Test with real send:**
```python
sender = TelegramSender(bot_token="YOUR_TOKEN", chat_id="YOUR_CHAT_ID")
result = sender.send("🔔 Test alert from HIVE Launcher")
print(f"Sent: {result.success}, message_id: {result.message_id}")
```

### Elasticsearch connection fails

**Fix:**
```python
from launcher.log_storage import ElasticLogStore

store = ElasticLogStore(
    hosts=["http://localhost:9200"],  # check URL
    index="hive-logs",
    # If auth required:
    username="elastic",
    password="changeme",
)

# Verify connection
try:
    count = store.count()
    print(f"Connected, {count} docs")
except Exception as e:
    print(f"Connection failed: {e}")
```

---

## Performance Issues

### Vision pipeline is slow (>10s per frame)

**Diagnosis:**
```python
import time

t0 = time.time()
image = capturer.capture_window_by_hwnd(hwnd)
t1 = time.time()
result = finder.calibrate(image)
t2 = time.time()
cards = card_recog.read(region)
t3 = time.time()

print(f"Capture: {t1-t0:.2f}s")
print(f"Calibrate: {t2-t1:.2f}s")
print(f"OCR: {t3-t2:.2f}s")
```

**Fixes:**

| Bottleneck | Fix |
|---|---|
| Capture slow | Use `include_border=False` (smaller image) |
| Calibration slow | Use cached ROI from YAML (skip auto-calibration) |
| OCR slow | Reduce region size; use PSM 7; skip EasyOCR if not needed |
| YOLO slow | Use lighter model (`yolov8n` vs `yolov8s`); or skip YOLO |

### High CPU usage

**Fixes:**
1. Increase capture interval (don't capture every frame):
```python
import time
while running:
    process_frame()
    time.sleep(0.5)  # 2 FPS is enough for poker
```

2. Disable unnecessary detection layers
3. Use cached ROI zones instead of re-calibrating each frame

### Memory leak

**Symptom:** Memory grows over time.

**Fixes:**
1. Clear LogAggregator periodically:
```python
from launcher.structured_logger import LogAggregator
aggregator.clear()
```
2. Limit in-memory log history:
```python
aggregator = LogAggregator(max_records=10000)
```

---

## Test Failures

### Torch access violation during tests

**Symptom:**
```
Windows fatal exception: access violation
... torch/__init__.py ...
```

**Fix:** Run tests excluding YOLO-dependent modules:
```bash
# Run specific test files
python -m pytest launcher/tests/test_structured_logger.py launcher/tests/test_log_storage.py -v

# Or exclude vision __init__ imports by running individual modules
python -m pytest launcher/tests/ -k "not yolo" -v
```

All test modules use `skipUnless(MODULE_AVAILABLE)` to gracefully skip when
dependencies are unavailable.

### Tests fail on CI / different machine

**Common causes:**
- Different screen resolution (ROI tests)
- Missing Tesseract installation
- Different random seed behavior

**Fix:** All unit tests use synthetic data and fixed seeds. If tests fail
only on a specific environment, check:
```bash
python -m pytest launcher/tests/ -v --tb=short 2>&1 | findstr "FAIL"
```

### How to run all launcher tests

```bash
# All tests (may crash if torch DLLs are broken)
python -m pytest launcher/tests/ -v

# Safe subset (no YOLO/torch dependency)
python -m pytest launcher/tests/test_ab_testing.py launcher/tests/test_bot_profile_manager.py launcher/tests/test_bot_config_loader.py launcher/tests/test_structured_logger.py launcher/tests/test_log_storage.py launcher/tests/test_telegram_alerts.py launcher/tests/test_mouse_curve_generator.py launcher/tests/test_behavioral_variance.py launcher/tests/test_anti_pattern_executor.py -v
```

---

## Getting Help

1. Check the logs: `logs/hive.json` (if structured logging is set up)
2. Enable debug level: `setup_structured_logging(level="DEBUG")`
3. Run the diagnostic script from [Quick Diagnostics](#quick-diagnostics)
4. Check `config/` for invalid JSON: `python -c "import json; json.load(open('config/bot_profiles.json'))"`
5. Verify window capture: save screenshots with `cv2.imwrite("debug.png", image)`
