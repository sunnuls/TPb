# Vision Setup Guide

> Complete guide to configuring and using the HIVE Launcher vision pipeline.
>
> ⚠️ **EDUCATIONAL RESEARCH ONLY.**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Screen Capture (WindowCapturer)](#screen-capture)
4. [ROI Configuration](#roi-configuration)
5. [Auto-Calibration (AutoROIFinder)](#auto-calibration)
6. [Template Matching](#template-matching)
7. [OCR Engine](#ocr-engine)
8. [YOLOv8 Region Detection](#yolov8-region-detection)
9. [Lobby Scanner](#lobby-scanner)
10. [Mouse Humanization](#mouse-humanization)
11. [Full Pipeline Example](#full-pipeline-example)

---

## Prerequisites

| Dependency | Required | Notes |
|---|---|---|
| Python 3.11+ | Yes | Tested on 3.11.9 |
| OpenCV (`opencv-python`) | Yes | `pip install opencv-python` |
| NumPy | Yes | Included with OpenCV |
| Tesseract OCR | Yes | System install + PATH |
| pytesseract | Yes | `pip install pytesseract` |
| PyQt6 | For GUI | `pip install PyQt6` |
| pywin32 | For Win32 capture | `pip install pywin32` |
| Pillow | Yes | `pip install Pillow` |
| EasyOCR | Optional | Fallback OCR engine |
| ultralytics | Optional | YOLOv8 detection |

## Installation

### Step 1: Core dependencies

```bash
pip install opencv-python numpy pytesseract Pillow pywin32
```

### Step 2: Tesseract OCR (Windows)

1. Download installer from: https://github.com/tesseract-ocr/tesseract
2. Install to default path (e.g. `C:\Program Files\Tesseract-OCR`)
3. Add to system `PATH`:

```powershell
# Verify installation
tesseract --version
```

4. If Tesseract is not in PATH, set it in code:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Step 3: Optional — EasyOCR fallback

```bash
pip install easyocr
```

### Step 4: Optional — YOLOv8

```bash
pip install ultralytics
```

> **Note:** `ultralytics` pulls `torch` which is ~2 GB. If torch DLL loading
> fails on your system, the YOLO detector will gracefully degrade and the rest
> of the vision pipeline continues to work.

### Step 5: Verify installation

```python
from launcher.vision import (
    WindowCapturer,
    AutoUIDetector,
    AutoROIFinder,
    MultiTemplateMatcher,
    RobustOCR,
    MouseCurveGenerator,
)
print("All vision modules loaded successfully!")
```

---

## Screen Capture

`WindowCapturer` uses the Win32 API for direct window capture — works even
when the poker window is partially occluded.

### Basic usage

```python
from launcher.vision import WindowCapturer
import win32gui

capturer = WindowCapturer()

# Find the poker window
hwnd = win32gui.FindWindow(None, "PokerStars")

# Capture the full window (including border)
image = capturer.capture_window_by_hwnd(hwnd, include_border=True)

# Capture only the client area (recommended)
image = capturer.capture_window_by_hwnd(hwnd, include_border=False)

# image is a numpy array (BGR format), ready for OpenCV
print(f"Captured: {image.shape}")  # e.g. (1080, 1920, 3)
```

### Capture by window title

```python
image = capturer.capture_by_title("PokerStars")
```

### Fallback to ImageGrab

If Win32 is unavailable (non-Windows), the capturer falls back to `PIL.ImageGrab`:

```python
from PIL import ImageGrab
import numpy as np, cv2

screen = np.array(ImageGrab.grab())
image = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
```

---

## ROI Configuration

ROI (Region of Interest) zones map screen areas to game elements. Configs
are YAML files stored in `config/rooms/`.

### File structure

```
config/rooms/
├── pokerstars.yaml
├── 888poker.yaml
├── ggpoker.yaml
├── ignition.yaml
└── partypoker.yaml
```

### YAML format

```yaml
room_name: "pokerstars"
resolution: "1920x1080"

rois:
  hero_card_1:
    x: 860
    y: 850
    width: 80
    height: 110

  hero_card_2:
    x: 960
    y: 850
    width: 80
    height: 110

  pot:
    x: 850
    y: 350
    width: 200
    height: 40

  fold_button:
    x: 750
    y: 1000
    width: 100
    height: 40

  # ... more zones

colors:
  table_felt: [53, 101, 77]
  card_back: [42, 68, 123]
  button_active: [255, 200, 50]

ocr:
  pot_prefix: "Pot:"
  decimal_separator: "."
  thousands_separator: ","

cards:
  rank_height: 20
  suit_height: 15
  rank_y_offset: 10
  suit_y_offset: 35
```

### Standard ROI zones

| Zone | Description |
|---|---|
| `hero_card_1`, `hero_card_2` | Hero's hole cards |
| `board_card_1` … `board_card_5` | Community cards |
| `pot` | Current pot size |
| `hero_stack` | Hero's chip stack |
| `villain_1_stack` … `villain_5_stack` | Opponents' stacks |
| `fold_button`, `call_button`, `raise_button` | Action buttons |
| `bet_amount_field` | Bet/raise input field |
| `table_type_indicator` | Cash/tournament indicator |
| `street_indicator` | Current street |

### Creating a new room config

1. Take a screenshot of the table at native resolution
2. Open the screenshot in an image editor (Paint, GIMP)
3. Note pixel coordinates of each zone
4. Copy `pokerstars.yaml` and edit coordinates
5. Save as `config/rooms/your_room.yaml`

---

## Auto-Calibration

`AutoROIFinder` automatically detects ROI zones from a table screenshot using
visual anchors (colors, shapes, text, edges).

### Basic usage

```python
from launcher.vision import AutoROIFinder
import cv2

finder = AutoROIFinder()

# Load a screenshot
screenshot = cv2.imread("table_screenshot.png")

# Run calibration
result = finder.calibrate(screenshot)

print(f"Confidence: {result.confidence:.0%}")
print(f"Anchors found: {len(result.anchors)}")

for name, zone in result.zones.items():
    print(f"  {name}: x={zone[0]}, y={zone[1]}, w={zone[2]}, h={zone[3]}")
```

### Anchor types

| Type | Detection method | What it finds |
|---|---|---|
| `COLOR` | HSV color thresholding | Green felt, card backs, buttons |
| `SHAPE` | Contour analysis | Card rectangles, chip circles |
| `TEXT` | Tesseract OCR | "Fold", "Call", "Raise", pot amounts |
| `EDGE` | Edge detection (Canny) | Table borders, card edges |

### How calibration works

1. **Felt detection** — finds the green table area via HSV thresholding
2. **Button detection** — locates action buttons by color contrast
3. **Card detection** — finds rectangular shapes with card-like proportions
4. **Text detection** — OCR scan for known labels ("Fold", "Pot:")
5. **Zone inference** — computes all standard zones relative to found anchors

### Saving calibration results

```python
import json

result_dict = {name: list(zone) for name, zone in result.zones.items()}
with open("config/roi/my_table.json", "w") as f:
    json.dump(result_dict, f, indent=2)
```

---

## Template Matching

`MultiTemplateMatcher` provides scale-invariant template matching for
detecting cards, buttons, and UI elements.

### Setup template bank

```python
from launcher.vision import TemplateBank, MultiTemplateMatcher
import cv2

bank = TemplateBank()

# Add card templates (crop from reference screenshots)
bank.add("Ah", cv2.imread("templates/cards/Ah.png", cv2.IMREAD_GRAYSCALE))
bank.add("Kd", cv2.imread("templates/cards/Kd.png", cv2.IMREAD_GRAYSCALE))
# ... add all 52 cards

matcher = MultiTemplateMatcher(bank)
```

### Detect cards in an image

```python
image = cv2.imread("table.png")

# Match at multiple scales (0.8x to 1.2x)
matches = matcher.match(image, threshold=0.75, scales=[0.8, 0.9, 1.0, 1.1, 1.2])

for m in matches:
    print(f"Found {m.template_name} at ({m.x}, {m.y}) conf={m.confidence:.2f}")
```

---

## OCR Engine

`RobustOCR` combines Tesseract and EasyOCR with multi-strategy preprocessing.

### Basic usage

```python
from launcher.vision import RobustOCR
import cv2

ocr = RobustOCR()

# Read text from an image region
region = cv2.imread("pot_region.png")
text = ocr.read(region)
print(f"Text: {text}")
```

### Numeric recognition

```python
from launcher.vision import NumericRecognizer

recog = NumericRecognizer()
pot_region = image[350:390, 850:1050]  # crop pot area

value = recog.read(pot_region)
print(f"Pot: ${value}")  # handles "1.2k" → 1200, "1.5m" → 1500000
```

### Card recognition

```python
from launcher.vision import CardRecognizer

card_recog = CardRecognizer()
card_region = image[850:960, 860:940]  # crop one card

card = card_recog.read(card_region)
print(f"Card: {card}")  # e.g. "Ah", "Kd"
```

### Preprocessing strategies

The OCR engine automatically tries multiple preprocessing pipelines:

1. **Grayscale + threshold** — works for clean, high-contrast text
2. **CLAHE (adaptive histogram)** — enhances low-contrast images
3. **HSV isolation** — extracts colored text on colored backgrounds
4. **Morphological cleanup** — removes noise, fills gaps
5. **Inversion** — handles white-on-dark text
6. **Gaussian blur + sharp** — reduces noise in blurry screenshots

---

## YOLOv8 Region Detection

`YOLORegionDetector` uses an ML model to detect table regions. Optional —
the pipeline works without it.

### Setup

```python
from launcher.vision import YOLORegionDetector

# Load a pretrained model (or train your own)
detector = YOLORegionDetector(model_path="weights/best.pt")

# Detect regions
result = detector.detect(screenshot, conf_threshold=0.5)

for det in result.detections:
    print(f"{det.class_name}: ({det.x1},{det.y1}) → ({det.x2},{det.y2}), conf={det.confidence:.2f}")
```

### Region classes

| Class | Description |
|---|---|
| `hero_cards` | Area containing hero's hole cards |
| `board` | Community card area |
| `pot` | Pot display |
| `buttons` | Action buttons row |
| `stacks` | Chip stacks |
| `chat` | Chat/log area |
| `dealer_button` | Dealer position indicator |

### Training your own model

```python
from launcher.vision import RegionDatasetGenerator

# Generate YOLO-format dataset from labeled screenshots
gen = RegionDatasetGenerator(output_dir="datasets/poker_regions")
gen.add_image("screenshot.png", labels={
    "hero_cards": (860, 850, 180, 110),
    "board": (700, 450, 430, 95),
    "pot": (850, 350, 200, 40),
})
gen.save()

# Train with ultralytics CLI
# yolo detect train data=datasets/poker_regions/data.yaml model=yolov8n.pt epochs=100
```

---

## Lobby Scanner

Multi-source lobby scanning with rate-limit protection.

### OCR-based scanning

```python
from launcher.vision import LobbyOCR

lobby_ocr = LobbyOCR()
result = lobby_ocr.scan(lobby_screenshot)

for table in result.rows:
    print(f"Table: {table.name}, Stakes: {table.stakes}, Players: {table.players}")
```

### HTTP-based scanning (fallback)

```python
from launcher.vision import LobbyHTTPParser, EndpointConfig, RoomBackend

parser = LobbyHTTPParser()
parser.add_backend(RoomBackend(
    name="pokerstars",
    endpoint=EndpointConfig(url="https://api.pokerstars.com/lobby", format="json"),
))

result = parser.fetch("pokerstars")
for table in result.tables:
    print(f"{table.name}: {table.stakes} ({table.players}/{table.max_players})")
```

### Anti-rate-limit orchestrator

```python
from launcher.vision import LobbyAntiLimit

scanner = LobbyAntiLimit(
    ocr_engine=lobby_ocr,
    http_parser=parser,
    proxy_list=["socks5://proxy1:1080", "socks5://proxy2:1080"],
)

# Scans with adaptive delay, circuit breaker, proxy rotation
tables = scanner.scan(room="pokerstars")
print(f"Found {len(tables)} tables")
print(f"Stats: {scanner.stats}")
```

---

## Mouse Humanization

Bézier-based mouse trajectories to avoid pattern detection.

### Basic curve generation

```python
from launcher.vision import MouseCurveGenerator

gen = MouseCurveGenerator(intensity=5)

# Generate a path from A to B
path = gen.generate(start=(100, 200), end=(500, 400))

print(f"Points: {path.length}, Distance: {path.distance:.0f}px")

for pt in path.points:
    # pt.x, pt.y = position; pt.dt = time delta (seconds)
    move_mouse(pt.x, pt.y)
    sleep(pt.dt)
```

### Intensity levels

| Level | Curve shape | Use case |
|---|---|---|
| 1–3 | Nearly straight | Shark / LAG — quick, decisive |
| 4–6 | Moderate curves | TAG / balanced play |
| 7–10 | Wild curves, overshoots | Fish / erratic — mimics inexperienced player |

### Behavioral profiles

```python
from launcher.vision import BehaviorSampler, BehaviorProfile

# Pre-built styles
sampler = BehaviorSampler(BehaviorProfile.aggressive())

think_time = sampler.sample_think_time("raise")  # seconds to "think"
mouse_cfg = sampler.sample_mouse_config()          # intensity, speed, jitter
click_off = sampler.sample_click_offset()          # pixel offset from center
tempo = sampler.sample_tempo()                     # actions-per-minute pace
```

### Anti-pattern executor

```python
from launcher.vision import AntiPatternExecutor

executor = AntiPatternExecutor(session_seed=42)

result = executor.execute_click(target=(500, 400))
# result.path       — MousePath used
# result.delay      — pre-click think time
# result.end_pos    — actual click position (with jitter)
# result.style      — behavior style used

# Self-test: verify no detectable patterns
report = executor.self_test(n=100, target=(500, 400))
print(f"Delay CV: {report.delay_cv:.2f}")              # > 0.20 = human-like
print(f"Unique coords: {report.coord_unique_frac:.0%}") # > 60% = good
print(f"Timing CV: {report.timing_cv:.2f}")             # > 0.20 = human-like
print(f"Pass: {report.is_human_like}")
```

---

## Full Pipeline Example

Complete vision cycle: capture → detect → extract → act.

```python
import win32gui
from launcher.vision import (
    WindowCapturer,
    AutoROIFinder,
    RobustOCR,
    CardRecognizer,
    NumericRecognizer,
    AntiPatternExecutor,
)

# 1. Capture
capturer = WindowCapturer()
hwnd = win32gui.FindWindow(None, "PokerStars")
image = capturer.capture_window_by_hwnd(hwnd, include_border=False)

# 2. Detect zones
finder = AutoROIFinder()
calibration = finder.calibrate(image)

# 3. Extract game state
card_recog = CardRecognizer()
num_recog = NumericRecognizer()

hero_cards = []
for card_zone in ["hero_card_1", "hero_card_2"]:
    if card_zone in calibration.zones:
        x, y, w, h = calibration.zones[card_zone]
        region = image[y:y+h, x:x+w]
        hero_cards.append(card_recog.read(region))

pot_zone = calibration.zones.get("pot")
if pot_zone:
    x, y, w, h = pot_zone
    pot = num_recog.read(image[y:y+h, x:x+w])

print(f"Hero: {hero_cards}, Pot: {pot}")

# 4. Execute action (after decision engine)
executor = AntiPatternExecutor(session_seed=42)
call_btn = calibration.zones.get("call_button", (870, 1000, 100, 40))
center = (call_btn[0] + call_btn[2] // 2, call_btn[1] + call_btn[3] // 2)
result = executor.execute_click(target=center)
```

---

## Tips

- **Resolution matters**: ROI configs are resolution-specific. Create
  separate configs for 1920x1080, 1366x768, etc. Or use auto-calibration.
- **Test on real screenshots**: Save a few screenshots from your actual poker
  client and test the pipeline offline.
- **YOLO is optional**: Template matching + OCR work well for most skins.
  Only train YOLO if you need to support many different table themes.
- **EasyOCR as fallback**: Install `easyocr` for better results on unusual
  fonts. Tesseract alone handles ~90% of standard poker UIs.
- **Always validate**: Vision output should always be validated before
  feeding into the decision engine. Use confidence thresholds.
