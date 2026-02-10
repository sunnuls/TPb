# HIVE Launcher - Educational Game Theory Research

## ⚠️ CRITICAL WARNINGS

**EXTREMELY UNETHICAL AND ILLEGAL**

This application manages coordinated bot operations (COLLUSION) for educational research ONLY.

### Legal & Ethical Restrictions

1. **ILLEGAL IN REAL POKER:**
   - Implements coordinated collusion
   - Violates Terms of Service of ALL poker sites
   - May constitute criminal fraud
   - Guaranteed permanent account bans

2. **EDUCATIONAL RESEARCH ONLY:**
   - Academic game theory studies
   - Multi-agent coordination research
   - Ethical AI research
   - NEVER for financial gain

3. **EXPLICIT CONSENT REQUIRED:**
   - ALL participants must be informed
   - Controlled research environment only
   - No real-money games EVER

---

## Installation

### Requirements

```bash
pip install -r launcher/requirements.txt
```

### Dependencies

- **PyQt6:** GUI framework
- **customtkinter:** Enhanced widgets
- **pyautogui:** Input emulation (Phase 3+)
- **mss:** Screen capture
- **opencv-python:** Image processing
- **pytesseract:** OCR (Phase 3+)
- **keyboard:** Global hotkeys

---

## Usage

### Launch Application

```bash
START_LAUNCHER.bat

# Or directly:
python -m launcher.main
```

### Features (Phase 0)

- **Main Window:** Tabbed interface
- **Tabs:**
  - Accounts (Phase 1)
  - ROI Config (Phase 1)
  - Bots Control (Phase 2)
  - Logs (Phase 6)
- **System Tray:** Quick access
- **Global Hotkey:** Ctrl+Alt+S (start/stop all)
- **Dark Theme:** Modern interface

---

## Architecture

```
launcher/
├── main.py                 # Entry point
├── system_tray.py          # System tray & hotkeys
├── requirements.txt        # Dependencies
│
├── ui/                     # GUI components
│   ├── __init__.py
│   └── main_window.py      # Main window with tabs
│
└── tests/                  # Test suite
    ├── __init__.py
    └── test_main_window.py
```

---

## Roadmap Status

### Phase 0: Base GUI ✅ (Current)
- [x] Main window with tabs
- [x] System tray integration
- [x] Global hotkeys (Ctrl+Alt+S)
- [x] Dark theme
- [x] Warning dialogs

### Phase 1: Account Management (Next)
- [ ] Account table
- [ ] Window capture
- [ ] ROI configuration overlay
- [ ] Config persistence

### Phase 2: Bot Control
- [ ] Bot instance management
- [ ] Start/stop bots
- [ ] Real-time monitoring
- [ ] Status tracking

### Phase 3: Table Discovery
- [ ] Automated lobby scanning
- [ ] Opportunity detection (1-3 humans)
- [ ] Auto-seating (3-bot teams)

### Phase 4: Collusion & Manipulation
- [ ] Card sharing integration
- [ ] 3vs1 manipulation
- [ ] Real action execution

### Phase 5: Bot Settings
- [ ] Global/per-bot config
- [ ] Aggression levels
- [ ] Presets

### Phase 6: Monitoring & Safety
- [ ] Real-time logs
- [ ] Dashboard with graphs
- [ ] Emergency stop
- [ ] Auto-shutdown triggers

### Phase 7: Testing & Finalization
- [ ] Play-money testing
- [ ] Stability testing
- [ ] Export functionality

---

## Safety Features

### Startup Warnings

- Critical warning dialog on startup
- Must accept to continue
- Prominent ethical warnings throughout

### Global Controls

- **Emergency Stop:** Ctrl+Alt+S or tray icon
- **Safe Mode:** Default (no real actions)
- **Confirmation Required:** For unsafe operations

---

## Version History

### v1.0.0 (Phase 0) - Current
- Base GUI structure
- System tray
- Global hotkeys
- Dark theme

---

## Support

For educational research questions only.

**NO SUPPORT for malicious use.**
**Users SOLELY responsible for ethical/legal compliance.**

---

## License

Educational use only. NO WARRANTY.

**EXTREMELY UNETHICAL if misused.**
**ILLEGAL in real poker.**
**Research purposes only.**
