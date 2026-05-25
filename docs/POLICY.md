# POLICY — HIVE Research Use Guidelines

## Purpose

This document defines the acceptable use policies for the HIVE multi-agent poker bot system. HIVE is an **educational research prototype** designed exclusively for studying coordinated AI agents in game theory environments.

---

## Core Principle

> Coordinated AI agents are permitted in **simulated and research environments only**.
> This software must **never** be used for real-money exploitation.

---

## Operating Modes

### SIMULATION

- **Primary mode.** All HIVE features are enabled.
- Live screen capture, card sharing, collusion, and automated actions are allowed.
- Ethical constraints are relaxed for continuous decision loops.
- Intended for: controlled virtual environments, game theory research, multi-agent coordination studies.

### RESEARCH

- Same as SIMULATION but with logging and audit trails enabled.
- All card exchanges, decisions, and actions are recorded for analysis.
- Intended for: academic research, strategy evaluation, A/B profile testing.

### LIVE_AUTOMATION

- Full automation mode: lobby scan → auto-fill → card exchange → 3vs1 play → action execution.
- All safety systems active (kill switch, risk classification, dry-run option).
- Intended for: integration testing against poker client UIs in sandboxed environments.

### DRY_RUN

- Vision pipeline and decision engine run normally.
- **No real mouse/keyboard actions are executed.**
- All actions are logged but not performed.
- Intended for: validation, debugging, pipeline testing.

---

## Coordinated Play (Collusion)

HIVE implements coordinated multi-bot play (collusion) as a research subject:

- **Allowed:** In simulated environments, private tables, research setups, and test accounts.
- **Allowed:** Studying information asymmetry, collective decision-making, and coalition strategies.
- **Allowed:** Academic analysis of how coordination affects game outcomes.
- **NOT allowed:** Real-money poker platforms with real stakes.
- **NOT allowed:** Exploiting other players for financial gain.

---

## Card Sharing

- Hole card exchange between HIVE bots is a core research feature.
- Cards are encrypted in transit (Fernet symmetric encryption).
- All exchanges are logged with timestamps and hand IDs for audit.
- Duplicate card validation prevents data corruption.

---

## Action Execution Safety

| Layer | Protection |
|-------|-----------|
| Kill switch | Immediate halt of all bot actions |
| Risk classification | Actions rated low/medium/high/critical before execution |
| Dry-run mode | Log-only, no real mouse/keyboard |
| Rate limiting | Maximum actions per second to prevent spam |
| Humanization | Bezier mouse curves + think time variance |
| Anti-pattern | Detect and break repetitive click patterns |

---

## Research Ethics

1. **Transparency:** All bot behavior is logged and auditable.
2. **No deception of real players:** HIVE must not be deployed against unsuspecting human players in real-money games.
3. **Academic use:** Results and strategies discovered through HIVE may be published for educational purposes.
4. **Responsible disclosure:** If HIVE reveals exploitable vulnerabilities in poker platform security, responsible disclosure practices should be followed.

---

## Disclaimer

> This software is provided "as is" for educational and research purposes only.
> The authors do not condone or encourage the use of this software for cheating, fraud, or any illegal activity.
> Using coordinated bots in real-money poker violates the terms of service of all major poker platforms and may be illegal in many jurisdictions.
> Users assume all responsibility for how they use this software.

---

## Legacy Modes (Deprecated)

The following modes are retained for backward compatibility with the coach_app engine but are not part of the HIVE workflow:

- `REVIEW` — Post-hand analysis (legacy coach).
- `TRAIN` — Internal trainer scenarios (legacy coach).
- `LIVE_RESTRICTED` — Preflop-only coaching (legacy).
- `INSTANT_REVIEW` — Post-action coaching (legacy). No longer enforced as a gate for HIVE operations.
