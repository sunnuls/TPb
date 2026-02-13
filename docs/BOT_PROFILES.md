# Bot Profiles Guide

> Complete guide to configuring, assigning, and testing bot behavior profiles.
>
> ⚠️ **EDUCATIONAL RESEARCH ONLY.**

---

## Table of Contents

1. [Overview](#overview)
2. [Profile System Architecture](#architecture)
3. [Preset Profiles](#preset-profiles)
4. [Profile JSON Format](#json-format)
5. [Profile Manager API](#profile-manager)
6. [Per-Bot Configuration](#per-bot-config)
7. [Hot-Reload & Live Changes](#hot-reload)
8. [Creating Custom Profiles](#custom-profiles)
9. [A/B Testing Framework](#ab-testing)
10. [Behavioral Variance Integration](#behavioral-variance)

---

## Overview

The HIVE Launcher uses a JSON-based profile system to control bot behavior.
Each bot is assigned a **profile** that defines:

- **Aggression level** (1–10)
- **Equity thresholds** (when to open, call, bet, bluff)
- **Bet sizing** (open raise, c-bet, turn, river fractions)
- **Timing** (delay ranges per action type)
- **Mouse dynamics** (curve intensity, speed, jitter, overshoot)
- **Session parameters** (max time, auto-rejoin, table selection)
- **Behavior style** (aggressive, passive, balanced, erratic)

---

## Architecture

```
config/bot_profiles.json          ← Profile definitions (5 presets)
config/bot_assignments.json       ← Bot → Profile mapping + overrides
        │
        ▼
┌──────────────────────┐
│  BotProfileManager   │  Loads & validates profiles from JSON
│  (bot_profile_manager)│  CRUD operations, profile→BotSettings
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   BotConfigLoader    │  Per-bot assignment + overrides
│  (bot_config_loader) │  Hot-reload, startup loading
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    BotInstance        │  Receives BotSettings
│  (bot_instance)      │  → Vision → Decision → Action
└──────────────────────┘
```

---

## Preset Profiles

Five built-in profiles in `config/bot_profiles.json`:

### Shark (Tight-Aggressive)

| Parameter | Value | Notes |
|---|---|---|
| Aggression | 8/10 | Very aggressive |
| Preflop open equity | 0.60 | Selective, but not ultra-tight |
| C-bet pot fraction | 0.65 | Standard 2/3 pot |
| Open raise | 3.0 BB | Standard |
| Delay range | 0.3–2.0s | Fast, decisive |
| Mouse intensity | 3 | Nearly straight cursor path |
| Max session | 150 min | Long sessions |
| Behavior style | `aggressive` | |

**Best for:** Profitable, winning-style play. Mimics a skilled regular.

### Rock (Tight-Passive)

| Parameter | Value | Notes |
|---|---|---|
| Aggression | 2/10 | Very passive |
| Preflop open equity | 0.78 | Premium hands only |
| C-bet pot fraction | 0.50 | Small bets |
| Open raise | 2.5 BB | Modest |
| Delay range | 0.8–4.0s | Slow, deliberate |
| Mouse intensity | 7 | Wobbly cursor |
| Max session | 90 min | Short sessions |
| Behavior style | `passive` | |

**Best for:** Ultra-conservative play. Folds almost everything.

### TAG — Tight-Aggressive Balanced (Default)

| Parameter | Value | Notes |
|---|---|---|
| Aggression | 6/10 | Balanced |
| Preflop open equity | 0.65 | Solid range |
| C-bet pot fraction | 0.60 | Balanced sizing |
| Open raise | 2.8 BB | Standard |
| Delay range | 0.4–3.0s | Normal pace |
| Mouse intensity | 5 | Moderate curves |
| Max session | 120 min | 2-hour sessions |
| Behavior style | `balanced` | |

**Best for:** Default recommendation. Solid, unremarkable play.

### LAG — Loose-Aggressive

| Parameter | Value | Notes |
|---|---|---|
| Aggression | 9/10 | Maximum pressure |
| Preflop open equity | 0.48 | Very wide range |
| C-bet pot fraction | 0.75 | Large bets |
| Open raise | 3.5 BB | Oversized |
| Delay range | 0.2–1.8s | Very fast |
| Mouse intensity | 2 | Straight, fast clicks |
| Max session | 180 min | Long grind |
| Behavior style | `aggressive` | |

**Best for:** Exploiting tight tables. High variance, high reward.

### Fish — Loose-Passive

| Parameter | Value | Notes |
|---|---|---|
| Aggression | 4/10 | Passive |
| Preflop open equity | 0.50 | Wide calling range |
| C-bet pot fraction | 0.40 | Small, weak bets |
| Open raise | 2.0 BB | Min-raise style |
| Delay range | 0.6–4.5s | Slow, inconsistent |
| Mouse intensity | 8 | Erratic, overshooting |
| Max session | 60 min | Short, casual sessions |
| Behavior style | `erratic` | |

**Best for:** Mimicking a recreational player to avoid detection.

---

## JSON Format

```json
{
  "_meta": {
    "version": "1.0.0",
    "description": "Bot behavior profiles"
  },
  "profiles": {
    "profile_name": {
      "display_name": "Human-Readable Name",
      "description": "One-line description",
      "aggression_level": 6,
      "equity_thresholds": {
        "preflop_open": 0.65,
        "preflop_call": 0.58,
        "postflop_bet": 0.52,
        "postflop_call": 0.48,
        "river_bluff": 0.25
      },
      "bet_sizing": {
        "open_raise_bb": 2.8,
        "cbet_pot_fraction": 0.60,
        "turn_pot_fraction": 0.55,
        "river_pot_fraction": 0.65,
        "max_bet_multiplier": 3.5
      },
      "timing": {
        "delay_min": 0.4,
        "delay_max": 3.0,
        "think_time_fold": [0.3, 1.0],
        "think_time_call": [0.5, 2.0],
        "think_time_raise": [0.6, 2.5],
        "think_time_allin": [1.0, 3.5]
      },
      "mouse": {
        "curve_intensity": 5,
        "speed_mult": 1.0,
        "jitter": 0.8,
        "overshoot_prob": 0.5
      },
      "session": {
        "max_session_time": 120,
        "auto_rejoin": true,
        "table_select_min_vpip": 28
      },
      "behavior_style": "balanced"
    }
  }
}
```

### Field reference

| Section | Field | Type | Range | Description |
|---|---|---|---|---|
| root | `aggression_level` | int | 1–10 | Overall aggression multiplier |
| equity | `preflop_open` | float | 0.0–1.0 | Min equity to open-raise preflop |
| equity | `preflop_call` | float | 0.0–1.0 | Min equity to call a preflop raise |
| equity | `postflop_bet` | float | 0.0–1.0 | Min equity to bet postflop |
| equity | `postflop_call` | float | 0.0–1.0 | Min equity to call postflop |
| equity | `river_bluff` | float | 0.0–1.0 | Bluff threshold on river |
| bet | `open_raise_bb` | float | 2.0–5.0 | Open-raise size in big blinds |
| bet | `cbet_pot_fraction` | float | 0.25–1.0 | C-bet as fraction of pot |
| bet | `turn_pot_fraction` | float | 0.25–1.0 | Turn bet as fraction of pot |
| bet | `river_pot_fraction` | float | 0.25–1.0 | River bet as fraction of pot |
| bet | `max_bet_multiplier` | float | 1.0–10.0 | Max bet relative to pot |
| timing | `delay_min` | float | 0.1–5.0 | Min action delay (seconds) |
| timing | `delay_max` | float | 0.5–10.0 | Max action delay (seconds) |
| timing | `think_time_*` | [min, max] | | Per-action think time range |
| mouse | `curve_intensity` | int | 1–10 | Bézier curve curvature |
| mouse | `speed_mult` | float | 0.5–2.0 | Mouse speed multiplier |
| mouse | `jitter` | float | 0.0–3.0 | Random movement noise |
| mouse | `overshoot_prob` | float | 0.0–1.0 | Probability of overshooting target |
| session | `max_session_time` | int | 10–360 | Max session length (minutes) |
| session | `auto_rejoin` | bool | | Rejoin table on disconnect |
| session | `table_select_min_vpip` | int | 0–100 | Min table VPIP for selection |
| root | `behavior_style` | str | `aggressive` / `passive` / `balanced` / `erratic` | Humanization behavior |

---

## Profile Manager

### Load profiles

```python
from launcher.bot_profile_manager import BotProfileManager

mgr = BotProfileManager()  # loads from config/bot_profiles.json
print(mgr.list_profiles())  # ['shark', 'rock', 'tag', 'lag', 'fish']
```

### Get a profile

```python
profile = mgr.get_profile("shark")
print(profile.display_name)       # "Shark"
print(profile.aggression_level)   # 8
print(profile.equity.preflop_open)  # 0.60
```

### Convert to BotSettings

```python
settings = mgr.profile_to_settings("tag")
# settings is a BotSettings instance, ready for BotInstance
print(settings.delay_min)     # 0.4
print(settings.delay_max)     # 3.0
print(settings.aggression_level)  # 6
```

### CRUD operations

```python
# Add a new profile
mgr.add_profile("custom_shark", {
    "display_name": "Custom Shark",
    "aggression_level": 7,
    "equity_thresholds": {"preflop_open": 0.62, ...},
    ...
})

# Update an existing profile
mgr.update_profile("tag", {"aggression_level": 7})

# Delete a profile
mgr.delete_profile("custom_shark")

# Save to disk
mgr.save()
```

### Validation

```python
from launcher.bot_profile_manager import ProfileValidator

errors = ProfileValidator.validate(profile)
if errors:
    for err in errors:
        print(f"  ✗ {err}")
else:
    print("Profile is valid")
```

The validator checks:
- Aggression in range [1, 10]
- All equity thresholds in [0.0, 1.0]
- Preflop open > preflop call
- Timing: delay_min < delay_max
- Valid behavior style

---

## Per-Bot Configuration

### Assign profiles to bots

```python
from launcher.bot_config_loader import BotConfigLoader

loader = BotConfigLoader()

# Assign profiles
loader.assign("bot_1", "shark")
loader.assign("bot_2", "fish")
loader.assign("bot_3", "tag")

# Load settings for a specific bot
settings = loader.load_for_bot("bot_1")  # → shark's BotSettings
```

### Per-bot overrides

Override specific fields without creating a new profile:

```python
loader.assign("bot_4", "tag", overrides={
    "aggression_level": 8,       # more aggressive than standard TAG
    "delay_min": 0.2,            # faster
    "max_session_time": 180,     # longer sessions
})

settings = loader.load_for_bot("bot_4")
print(settings.aggression_level)  # 8 (overridden from 6)
```

### Startup loading

Apply all assignments when the bot manager starts:

```python
from launcher.bot_manager import BotManager

bot_manager = BotManager()
loader.startup_load_all(bot_manager)
# All bots in bot_manager.bots receive their assigned settings
```

### Persistence

Assignments are saved to `config/bot_assignments.json`:

```json
{
  "bot_1": {"profile_name": "shark", "overrides": {}, "assigned_at": 1707523200},
  "bot_2": {"profile_name": "fish", "overrides": {}, "assigned_at": 1707523200},
  "bot_4": {"profile_name": "tag", "overrides": {"aggression_level": 8}, "assigned_at": 1707523200}
}
```

---

## Hot-Reload

Change a bot's profile without restarting:

```python
# Swap profile entirely
loader.hot_swap("bot_1", "rock")
# bot_1 now plays Rock style (if BotInstance is linked)

# Override a single field mid-session
loader.hot_override("bot_1", {"delay_max": 5.0})

# View change history
for entry in loader.changelog:
    print(f"{entry['timestamp']}: {entry['bot_id']} → {entry['action']}")
```

---

## Custom Profiles

### Method 1: JSON file

Edit `config/bot_profiles.json` directly:

```json
{
  "profiles": {
    "nit_grinder": {
      "display_name": "Nit Grinder",
      "description": "Ultra-tight, exploits loose tables",
      "aggression_level": 5,
      "equity_thresholds": {
        "preflop_open": 0.75,
        "preflop_call": 0.70,
        "postflop_bet": 0.60,
        "postflop_call": 0.55,
        "river_bluff": 0.10
      },
      "bet_sizing": {
        "open_raise_bb": 2.5,
        "cbet_pot_fraction": 0.50,
        "turn_pot_fraction": 0.50,
        "river_pot_fraction": 0.50,
        "max_bet_multiplier": 2.0
      },
      "timing": {
        "delay_min": 0.5,
        "delay_max": 3.5,
        "think_time_fold": [0.2, 0.8],
        "think_time_call": [0.5, 2.5],
        "think_time_raise": [0.8, 3.0],
        "think_time_allin": [1.5, 4.0]
      },
      "mouse": {
        "curve_intensity": 6,
        "speed_mult": 1.1,
        "jitter": 1.0,
        "overshoot_prob": 0.4
      },
      "session": {
        "max_session_time": 240,
        "auto_rejoin": true,
        "table_select_min_vpip": 35
      },
      "behavior_style": "balanced"
    }
  }
}
```

### Method 2: Programmatic

```python
mgr.add_profile("nit_grinder", {
    "display_name": "Nit Grinder",
    "aggression_level": 5,
    # ... all fields
})
mgr.save()
```

---

## A/B Testing

Compare profiles statistically to find the most profitable strategy.

### Quick test

```python
from launcher.ab_testing import ABTestRunner

runner = ABTestRunner()
runner.add_all_profiles()  # loads all 5 presets

result = runner.run(hands_per_session=1000, sessions_per_profile=50)
print(result.report())
```

### Example output

```
═══════════════════════════════════════════════
         A/B Test Report
═══════════════════════════════════════════════
 Profiles tested: 5
 Hands per session: 1000
 Sessions per profile: 50
───────────────────────────────────────────────
 #1  shark    profit=+14.2 ±3.1 bb/100  VPIP=22% PFR=18% AF=3.2
 #2  tag      profit=+8.7  ±2.8 bb/100  VPIP=25% PFR=20% AF=2.5
 #3  lag      profit=+5.3  ±5.2 bb/100  VPIP=38% PFR=32% AF=4.1
 #4  rock     profit=+2.1  ±1.5 bb/100  VPIP=12% PFR=9%  AF=1.3
 #5  fish     profit=-8.4  ±4.7 bb/100  VPIP=42% PFR=15% AF=1.1
───────────────────────────────────────────────
 Best: shark (95% CI: [11.1, 17.3])
═══════════════════════════════════════════════
```

### Custom comparison

```python
runner = ABTestRunner()
runner.add_profile("shark")
runner.add_profile("tag")

result = runner.run(hands_per_session=5000, sessions_per_profile=100)

shark_stats = result.profiles["shark"]
tag_stats = result.profiles["tag"]

print(f"Shark mean profit: {shark_stats.mean_profit_bb100:.1f} bb/100")
print(f"TAG mean profit:   {tag_stats.mean_profit_bb100:.1f} bb/100")
print(f"Shark 95% CI:      [{shark_stats.ci_lower:.1f}, {shark_stats.ci_upper:.1f}]")
```

---

## Behavioral Variance Integration

Profiles integrate with the humanization layer via `behavior_style`:

```python
from launcher.vision import BehaviorProfile, BehaviorSampler

# Profile's behavior_style determines the base behavior
profile = mgr.get_profile("shark")  # behavior_style = "aggressive"

# Create a sampler from the style
bp = getattr(BehaviorProfile, profile.behavior_style)()
sampler = BehaviorSampler(bp)

# Sample human-like parameters for each action
think = sampler.sample_think_time("raise")     # 0.4–2.0s for shark
mouse = sampler.sample_mouse_config()           # intensity=3, fast
offset = sampler.sample_click_offset()          # small jitter
```

The `AntiPatternExecutor` uses these samples automatically when executing
actions, ensuring that each profile produces a distinct but human-like
behavioral signature.
