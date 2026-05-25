# TPb — HIVE: Coordinated Multi-Agent Poker Bot Network

> **Educational research prototype** for studying coordinated AI agents in simulated game theory environments.
> Not intended for real-money play. For academic and research purposes only.

---

## What is HIVE?

HIVE is an autonomous multi-bot poker system that coordinates a network of AI agents to play together at the same table. The system demonstrates advanced concepts in multi-agent coordination, information sharing, and collaborative decision-making within adversarial game theory environments.

**Core concept:** 3 AI bots join a table with 1–3 human players, share hole cards in real time, compute collective equity, and execute coordinated manipulation strategies (3vs1).

### Key capabilities

- **Launcher Hub** — desktop application (PyQt6) for managing accounts, windows, ROI zones, and bot lifecycles
- **Multi-Bot Pool** — manage 5+ bot instances simultaneously with per-bot profiles (shark, rock, tag, lag, fish)
- **Auto Window Discovery** — find poker client windows by title/process, capture via Win32 API
- **Auto ROI Detection** — template matching (cv2.matchTemplate) to auto-calibrate screen zones without manual input
- **Lobby Scanner** — OCR-based lobby parsing to find tables with 1–3 human players and free seats
- **Auto Table Fill** — automatically seat 3 bots at target tables matching criteria
- **Account Binding** — bind bot IDs to poker room nicknames and window handles with health checks
- **Real-Time Card Sharing** — encrypted hole card exchange between bots via CentralHub (WebSocket)
- **Collusion Engine** — auto-activation when 3 bots are seated; compute collective equity from 6 known cards
- **3vs1 Manipulation** — street-aware aggression escalation, coordinated traps, isolation plays, squeeze strategies
- **Action Execution** — humanized mouse/keyboard with Bezier curves, behavioral variance, anti-pattern detection
- **Vision Pipeline** — template matching + OCR (Tesseract/EasyOCR) + optional YOLOv8 for card/UI detection

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    HIVE Launcher (PyQt6 GUI)              │
│  Accounts │ Bot Control │ Dashboard │ Logs │ Settings     │
├──────────────────────────────────────────────────────────┤
│                    Bot Manager (Pool of N bots)           │
│  BotInstance │ BotSettings │ Profiles │ A/B Testing       │
├──────────────────────────────────────────────────────────┤
│                    HIVE Coordination Layer                 │
│  CentralHub (WS) │ CardSharing │ CollusionActivator       │
│  ManipulationEngine │ CollectiveDecision                  │
├──────────────────────────────────────────────────────────┤
│                    Bridge Layer                            │
│  ScreenCapture │ AnchorDetector │ StateBridge │ ROI       │
│  ActionTranslator │ RealExecutor │ Safety                 │
├──────────────────────────────────────────────────────────┤
│                    Vision Layer                            │
│  AutoROIFinder │ LobbyOCR │ CardExtractor │ TemplateMatch │
│  AutoNavigator │ AutoUIDetector │ WindowCapturer          │
├──────────────────────────────────────────────────────────┤
│                    Target: Poker Client Windows            │
│  CoinPoker │ PokerStars │ GGPoker │ ...                   │
└──────────────────────────────────────────────────────────┘
```

### Directory structure

```
TPb/
├── launcher/                  # HIVE Launcher application
│   ├── main.py                # PyQt6 GUI entry point
│   ├── bot_instance.py        # Single bot: Vision → Decision → Action + auto-ROI
│   ├── bot_manager.py         # Bot pool management
│   ├── bot_settings.py        # Per-bot configuration
│   ├── bot_profile_manager.py # JSON profiles (shark/rock/tag/lag/fish)
│   ├── bot_account_binder.py  # Bot ↔ account ↔ window binding
│   ├── collusion_coordinator.py  # HIVE card sharing coordination
│   ├── auto_seating.py        # Auto table selection & seating
│   ├── auto_bot_controller.py # Automated bot lifecycle
│   ├── lobby_scanner.py       # Lobby monitoring & table discovery
│   └── vision/                # Vision sub-modules
│       ├── auto_roi_finder.py
│       ├── lobby_ocr.py
│       ├── auto_navigator.py
│       ├── window_capturer.py
│       ├── mouse_curve_generator.py
│       └── anti_pattern_executor.py
│
├── bridge/                    # Vision → State → Action bridge
│   ├── screen_capture.py      # Win32 capture + auto_find_window
│   ├── state_bridge.py        # Vision data → game state
│   ├── action_translator.py   # Decisions → UI actions
│   ├── roi_manager.py         # ROI zone management
│   ├── safety.py              # Kill switch & safety checks
│   ├── action/
│   │   └── real_executor.py   # Mouse/keyboard execution + lobby clicks
│   └── vision/
│       ├── anchor_detector.py # cv2.matchTemplate anchor detection + ROI calc
│       ├── card_extractor.py  # Card recognition
│       └── numeric_parser.py  # Pot/stack OCR
│
├── sim_engine/                # Decision & coordination engines
│   ├── central_hub.py         # WebSocket hub for multi-agent state sync
│   ├── collective_decision.py # Collective equity & decision
│   └── state/                 # Game state management
│
├── hive/                      # HIVE-specific modules
│   ├── bot_pool.py            # BotPool + HiveTeam (3 bots)
│   ├── card_sharing.py        # Encrypted hole card exchange
│   ├── collusion_activation.py # Auto-detect 3 seated → activate collusion
│   └── manipulation_logic.py  # 3vs1 manipulation strategies
│
├── auto_fill.py               # AutoFiller: assign bots to target tables
├── live_table_scanner.py      # LiveTableScanner with SeatInfo
│
├── config/
│   ├── anchor_templates.yaml  # Anchor template matching config
│   ├── active_window.json     # Last found poker window
│   ├── bot_profiles.json      # 5 preset bot profiles
│   └── rooms/                 # Per-room ROI configs
│
├── templates/
│   └── anchors/               # Template images for auto-ROI
│
├── tests/                     # 600+ unit tests
│
├── coach_app/                 # Legacy coach engine (analysis/explain)
│   ├── rta/live_rta.py        # Live RTA loop (with auto-ROI integration)
│   └── engine/                # Poker analysis engine
│
└── docs/
    ├── POLICY.md              # Research use policy
    └── ARCHITECTURE.md        # System architecture
```

---

## HIVE Flow (end-to-end)

```
1. Launch HIVE Hub
   └─→ Load accounts, bind windows

2. Lobby Scan
   └─→ OCR lobby → find tables with 1–3 humans, ≥3 free seats

3. Auto-Fill
   └─→ Assign 3 bots from pool → seat at target table

4. Auto-ROI
   └─→ auto_find_window() → find_anchors() → calculate_relative_roi()
   └─→ Fallback: config percentages or manual 2-point selection

5. Game Loop (per bot)
   └─→ Capture screen → Detect cards/pot/buttons → Build game state

6. Card Exchange
   └─→ CentralHub.exchange_hole_cards() → 3 bots share 6 cards
   └─→ Validate no duplicates → compute collective equity

7. Collective Decision
   └─→ ManipulationEngine.decide_enhanced()
   └─→ Street-aware aggression: preflop(0.8x) → flop(1.0x) → turn(1.2x) → river(1.5x)
   └─→ Strategies: squeeze, coordinated trap, isolation, pot building, controlled fold

8. Action Execution
   └─→ RealActionExecutor with humanized mouse + behavioral variance
   └─→ Anti-pattern detection to avoid bot-like behavior

9. Repeat from step 5 (every hand)
   └─→ ROI refresh every 30 seconds
```

---

## Quickstart

### Install

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,live]"
```

### Launch HIVE GUI

```bash
python -m launcher.main
```

### Run headless (no GUI)

```python
from launcher.auto_bot_controller import AutoBotController
controller = AutoBotController()
controller.start()
```

### Run tests

```bash
pytest
pytest launcher/tests/ -v    # launcher tests
pytest tests/ -v             # integration tests
```

---

## Bot Profiles

| Profile | Style | Aggression | Equity Threshold | Description |
|---------|-------|------------|------------------|-------------|
| `shark` | Tight-Aggressive | 8/10 | 0.60 | Fast, high fold equity |
| `rock` | Tight-Passive | 2/10 | 0.78 | Premium hands only |
| `tag` | TAG (balanced) | 6/10 | 0.65 | Solid default |
| `lag` | Loose-Aggressive | 9/10 | 0.48 | Wide range, pressure |
| `fish` | Loose-Passive | 4/10 | 0.50 | Mimics recreational player |

---

## 3vs1 Manipulation Strategies

| Strategy | Trigger | Description |
|----------|---------|-------------|
| `AGGRESSIVE_SQUEEZE` | Collective equity > 75% | All 3 bots apply max pressure |
| `COORDINATED_TRAP` | Equity 65–75%, turn/river | First bot checks, second raises (check-raise) |
| `ISOLATION` | Equity 55–65%, opponent folds > 60% | Force heads-up vs strongest bot hand |
| `POT_BUILDING` | Medium equity 40–55% | Gradual pot inflation |
| `CONTROLLED_FOLD` | Equity < 40% | Minimize losses, preserve stack |

---

## Documentation

| Guide | Description |
|-------|-------------|
| [`docs/POLICY.md`](docs/POLICY.md) | Research use policy & ethical guidelines |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture overview |
| [`docs/VISION_SETUP.md`](docs/VISION_SETUP.md) | Vision pipeline setup |
| [`docs/BOT_PROFILES.md`](docs/BOT_PROFILES.md) | Bot profiles & A/B testing |
| [`docs/API_HUB_DECISION.md`](docs/API_HUB_DECISION.md) | CentralHub & Decision engine API |

---

## Disclaimer

> **This is an educational research prototype** for studying coordinated AI agents in simulated game theory environments.
>
> The system demonstrates multi-agent coordination, information asymmetry exploitation, and collaborative decision-making — concepts studied in academic game theory, multi-agent systems, and mechanism design research.
>
> **This software is NOT intended for use in real-money poker or any form of gambling.**
> Using coordinated bots (collusion) in real poker is illegal and violates the terms of service of all poker platforms.
>
> The authors assume no liability for misuse of this software.

---

## License

MIT License — See LICENSE file for details.

**Maintained by:** @sunnuls
