# Bridge Mode - Educational HCI Research Prototype

## ⚠️ CRITICAL WARNINGS

**EDUCATIONAL USE ONLY**

This software is developed EXCLUSIVELY for Human-Computer Interaction (HCI) research purposes. It is designed to study external desktop applications and multi-agent coordination in simulated environments.

### Legal & Ethical Restrictions

1. **NO REAL-MONEY POKER:**
   - This software MUST NOT be used for real-money online poker
   - Violates Terms of Service of all poker sites
   - May be illegal in many jurisdictions
   - Can result in permanent account bans

2. **RESEARCH ONLY:**
   - Use ONLY in controlled academic research settings
   - Play-money testing ONLY for demonstration purposes
   - All data collection must comply with research ethics protocols

3. **NO WARRANTY:**
   - Provided "AS IS" without any warranties
   - Authors assume NO liability for misuse
   - Users are SOLELY responsible for compliance with laws and ToS

---

## Overview

Bridge Mode connects the poker simulation engine to external desktop applications for HCI research.

### Architecture

```
Screenshot → Vision Layer → State Extraction → Decision Engine → Action Layer → Monitoring
```

### Key Components

1. **Vision Layer** (`bridge/vision/`)
   - Card extraction
   - Numeric parsing (pot, stacks, bets)
   - Metadata detection (street, table type)

2. **State Bridge** (`bridge/state_bridge.py`)
   - Orchestrates vision components
   - Produces unified TableState

3. **Action Layer** (`bridge/action/`)
   - Action translation (decision → command)
   - Simulation mode (logging only)
   - Real execution (UNSAFE mode)

4. **Monitoring** (`bridge/monitoring.py`)
   - UI change detection
   - Anomaly detection
   - Auto-shutdown on issues

5. **Safety Framework** (`bridge/safety.py`)
   - Global kill-switch
   - Mode restrictions (dry-run/safe/unsafe)
   - Session limits (time, hands, vision errors)

---

## Operational Modes

### 1. DRY-RUN Mode (Default)

**Status:** Safe - No real actions executed

```bash
python -m bridge.bridge_main --mode dry-run --hands 100
```

**Behavior:**
- Full simulation
- All actions logged but NOT executed
- Complete state extraction and decision making
- Safe for testing and development

**Use Cases:**
- Algorithm testing
- Vision pipeline validation
- Decision quality analysis
- Performance benchmarking

---

### 2. SAFE Mode

**Status:** Low Risk - Conservative actions only

```bash
python -m bridge.bridge_main --mode safe --hands 50
```

**Behavior:**
- Real actions LIMITED to: fold, check, call
- Raise/bet actions BLOCKED (fallback to call)
- Full monitoring active
- Auto-shutdown on anomalies

**Restrictions:**
- No aggressive actions
- No risk of significant losses
- Minimal impact on game state

**Use Cases:**
- Initial live testing in play-money
- Action execution validation
- UI interaction verification

---

### 3. UNSAFE Mode

**Status:** HIGH RISK - All actions enabled

```bash
python -m bridge.bridge_main --mode unsafe --hands 10
```

**Behavior:**
- ALL actions allowed (fold/check/call/raise/bet/allin)
- Real mouse clicks and keyboard input
- Requires explicit confirmation
- Full logging with screenshots

**Safety Measures:**
- Risk level classification (LOW/MEDIUM/HIGH)
- Configurable max risk level
- Emergency shutdown on any anomaly
- Session time limit (default: 30 minutes)
- Hand limit (default: 500 hands)
- Vision error limit (default: 3 consecutive errors)

**CRITICAL:**
- Use ONLY in play-money environments
- Requires careful monitoring
- Can cause real financial loss if misused
- Authors NOT responsible for any losses

---

## Safety Features

### Automatic Shutdown Triggers

The system will automatically shut down on:

1. **Vision Errors:** 3 consecutive vision extraction failures
2. **Session Timeout:** 30 minutes elapsed (configurable)
3. **Hand Limit:** 500 hands played (configurable)
4. **UI Changes:** Unexpected UI changes detected
5. **Anomalies:** Invalid game state, disconnections, popups
6. **Kill Switch:** Manual emergency stop (Ctrl+C or kill switch file)

### Session Limits (Phase 4 Enhanced Safety)

```python
SafetyConfig(
    max_runtime_seconds=1800,     # 30 minutes
    max_vision_errors=3,           # 3 consecutive errors
    max_hands_per_session=500      # 500 hands max
)
```

### Real-Time Monitoring

```python
# Get session info
session_info = safety.get_session_info()
# Returns:
# - elapsed_seconds
# - remaining_seconds
# - hands_played
# - hands_remaining
# - consecutive_vision_errors
# - vision_errors_until_shutdown
```

---

## Multi-Room Support (Phase 2)

Bridge supports multiple poker rooms with custom configurations:

### Supported Rooms

1. **PokerStars** (`config/rooms/pokerstars.yaml`)
2. **Ignition Casino** (`config/rooms/ignition.yaml`)
3. **GGPoker** (`config/rooms/ggpoker.yaml`)
4. **888poker** (`config/rooms/888poker.yaml`)
5. **partypoker** (`config/rooms/partypoker.yaml`)

### Room Configuration

Each room has:
- **ROI Definitions:** Coordinates for cards, pot, stacks, buttons
- **Color Profiles:** Table felt, card backs, button colors
- **OCR Settings:** Text prefixes, separators
- **Card Recognition:** Rank/suit dimensions and offsets

### Using Different Rooms

```bash
python -m bridge.bridge_main --mode dry-run --room ignition
```

---

## Live Testing Pipeline (Phase 3)

### Safe Testing Protocol

```python
from bridge.live_test_runner import LiveTestRunner

runner = LiveTestRunner(
    room="pokerstars",
    dataset_dir="live_test_data"
)

# Run full test sequence
report = await runner.run_full_test(
    dry_run_hands=100,    # Phase 1: Simulation
    safe_hands=50,        # Phase 2: fold/check/call only
    medium_unsafe_hands=10 # Phase 3: small bet/raise
)
```

### Test Metrics

- **Success Rate:** Hands completed successfully
- **Vision Accuracy:** Correct state extractions
- **Latency:** Screenshot → Decision time
- **Error Rate:** Failed operations

### Performance Targets

- **Vision Accuracy:** ≥96% on cards, ≥92% on numbers
- **Success Rate:** ≥95% hands completed
- **Latency:** <500ms average

---

## Demo Mode (Phase 4)

### Web Interface

```bash
python -m bridge.demo_mode
```

Opens browser interface at `http://127.0.0.1:7860`

### Features

- **Screenshot Upload:** Analyze any poker table screenshot
- **State Extraction:** Display TableState components
- **HIVE Recommendations:** Show 3vs1 coordination strategy
- **Risk Assessment:** Evaluate action safety

### Demo Safety

- **NO REAL ACTIONS:** Demonstration only
- **Dry-run mode:** All operations simulated
- **Safe exploration:** No risk of execution

---

## Training Data Collection

### Collecting Screenshots

```python
from bridge.vision.training_data_collector import TrainingDataCollector

collector = TrainingDataCollector(
    dataset_dir="dataset",
    capture_interval=5.0,  # Every 5 seconds
    room="pokerstars"
)

# Manual capture
screenshot_id = collector.capture_screenshot(manual=True)

# Load annotation template
annotation = collector.load_annotation(screenshot_id)

# Add annotations
annotation.cards.append(CardAnnotation('A', 's', 100, 200, 50, 70))
annotation.numerics.append(NumericAnnotation('pot', 150.0, 500, 300, 100, 30))

# Save
collector.save_annotation(annotation)
```

### Annotation Workflow

1. Auto-capture screenshots (every 5 seconds)
2. Generate JSON annotation templates
3. Manual annotation (external tool or script)
4. Validate annotations
5. Export for model training

---

## Installation & Setup

### Prerequisites

```bash
pip install numpy pillow pyyaml
pip install mss  # For screen capture
pip install pyautogui  # For unsafe mode (optional)
pip install gradio  # For demo mode (optional)
```

### Quick Start

1. **Test in Dry-Run:**
   ```bash
   python -m bridge.bridge_main --mode dry-run --hands 10
   ```

2. **Launch Demo:**
   ```bash
   python -m bridge.demo_mode
   ```

3. **Run Tests:**
   ```bash
   pytest bridge/tests/ -v
   ```

---

## File Structure

```
bridge/
├── safety.py                    # Global safety framework
├── state_bridge.py              # Main state extraction orchestrator
├── bridge_main.py               # Main integration module
├── live_test_runner.py          # Controlled testing pipeline
├── demo_mode.py                 # Web interface demo
├── monitoring.py                # Anomaly detection & auto-shutdown
│
├── vision/                      # Vision layer
│   ├── card_extractor.py
│   ├── numeric_parser.py
│   ├── metadata.py
│   └── training_data_collector.py
│
├── action/                      # Action layer
│   ├── real_executor.py         # UNSAFE: Real action execution
│   └── tests/
│
├── screen_capture.py            # Screenshot capture
├── roi_manager.py               # ROI management
├── lobby_scanner.py             # Lobby scanning
├── opportunity_detector.py      # Table selection
├── bot_identification.py        # Bot identity & HIVE groups
├── external_hub_client.py       # Multi-bot coordination
├── action_translator.py         # Decision → ActionCommand
├── action_simulator.py          # Action simulation (logging)
├── humanization_sim.py          # Human-like behavior
│
└── tests/                       # Comprehensive test suite

config/
└── rooms/                       # Multi-room configurations
    ├── pokerstars.yaml
    ├── ignition.yaml
    ├── ggpoker.yaml
    ├── 888poker.yaml
    └── partypoker.yaml
```

---

## Testing

### Run All Tests

```bash
pytest bridge/ -v
pytest config/rooms/tests/ -v
```

### Test Coverage

- **Unit Tests:** Individual components
- **Integration Tests:** Multi-component workflows
- **Safety Tests:** Mode restrictions and limits
- **Configuration Tests:** Room config validation

### Test Results (Phase 3-4)

- Total tests: 170+
- Coverage: Vision, Action, Safety, Monitoring, Integration
- All tests passing in dry-run mode

---

## Troubleshooting

### Common Issues

**1. "mss not available"**
```bash
pip install mss
```

**2. "pyautogui not available"**
- Only needed for UNSAFE mode
- Install: `pip install pyautogui`
- Can skip if only using dry-run/safe modes

**3. "Vision extraction failed"**
- Check if poker client is running
- Verify window title matches expected pattern
- Check ROI configuration for your room
- Use training data collector to debug

**4. "Emergency shutdown triggered"**
- Review logs in `bridge/monitoring_logs/`
- Check `SHUTDOWN_*.log` for reason
- Common causes: vision errors, UI changes, invalid state

---

## Best Practices

### For Safe Research

1. **Always start with dry-run:**
   - Test full pipeline before any real actions
   - Validate vision accuracy
   - Check decision quality

2. **Use play-money ONLY:**
   - Never use real-money accounts
   - Treat as pure research environment
   - Expect ToS violations even in play-money

3. **Monitor actively:**
   - Check logs regularly
   - Watch for vision errors
   - Review decision quality

4. **Respect limits:**
   - Keep sessions short (<30 minutes)
   - Limit hands per session (<500)
   - Stop immediately on any issues

### For Development

1. **Test extensively:**
   - Run full test suite before changes
   - Validate in dry-run mode first
   - Use demo mode for visual verification

2. **Collect training data:**
   - Gather diverse screenshots
   - Annotate accurately
   - Test on multiple room skins

3. **Document changes:**
   - Update configs when ROIs change
   - Log vision accuracy metrics
   - Track decision quality

---

## Performance Metrics

### Target Performance (Phase 3)

- **Vision Accuracy:**
  - Cards: ≥96%
  - Numbers: ≥92%

- **System Performance:**
  - Success Rate: ≥95%
  - Latency: <500ms average
  - Error Rate: <5%

### Monitoring Metrics

- Hands played per session
- Vision extraction success rate
- Action execution success rate
- Anomalies detected
- Average decision latency

---

## Research Ethics

### Ethical Guidelines

1. **Transparency:**
   - Clearly identify research purpose
   - Disclose use of automated systems
   - Do not deceive other players

2. **Harm Prevention:**
   - Use only play-money environments
   - Do not disrupt real games
   - Respect poker room policies

3. **Data Privacy:**
   - Do not collect data on other players
   - Anonymize all research data
   - Secure all collected information

4. **Academic Integrity:**
   - Cite this work appropriately
   - Share findings openly
   - Report limitations honestly

---

## Citation

If you use this software in research, please cite:

```
Bridge Mode - Educational HCI Research Prototype
Multi-Agent Coordination Framework for Desktop Application Research
2026
```

---

## Support & Contributions

### Reporting Issues

- Report bugs via GitHub Issues
- Include logs from `bridge/monitoring_logs/`
- Provide reproduction steps

### Contributing

- Follow existing code style
- Add tests for new features
- Update documentation
- Ensure safety checks remain intact

---

## License

Educational use only. See LICENSE file for details.

---

## Version History

### Roadmap 3 (Complete)
- Phase 0: Project structure
- Phase 1: Screen capture + ROI
- Phase 2: Vision layer
- Phase 3: Lobby & opportunity detection
- Phase 4: Hub communication
- Phase 5: Action layer (simulation)
- Phase 6: Monitoring & safety
- Phase 7: Integration & testing

### Roadmap 4 (Complete)
- Phase 1: Unsafe action executor
- Phase 2: Vision enhancement + multi-room support
- Phase 3: Live testing pipeline
- Phase 4: Final safety & demo mode

---

## FAQ

**Q: Can I use this for real poker?**
A: NO. Absolutely not. Educational research only.

**Q: Is this legal?**
A: In most jurisdictions, automated poker play violates Terms of Service and may be illegal. This is for RESEARCH ONLY in controlled environments.

**Q: Will I get banned?**
A: Yes, if you use this on any poker site, even play-money. Sites actively detect and ban automated play.

**Q: What about play-money testing?**
A: Still violates ToS. Use for demonstration purposes only, understanding account ban risk.

**Q: How accurate is the vision layer?**
A: Target: 96%+ for cards, 92%+ for numbers. Actual accuracy depends on training data quality.

**Q: Can I add more poker rooms?**
A: Yes, create new YAML config in `config/rooms/` following existing format.

**Q: How do I contribute training data?**
A: Use `TrainingDataCollector` to capture and annotate screenshots. Follow annotation guidelines.

---

## Contact

For research collaboration or questions:
- GitHub Issues for technical questions
- Follow academic ethics guidelines
- Respect legal and ToS restrictions

---

**Remember: This is a research prototype, not a production system.**

**Use responsibly. Play responsibly. Research ethically.**
