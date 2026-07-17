# POLICY — HIVE Product Guidelines

## Purpose

HIVE is a multi-bot poker automation platform for coordinating AI agents at poker tables.
This document describes operating modes, safety controls, and product expectations.

---

## Core Principle

> HIVE is a tool for automated multi-agent poker play and coordination.
> The operator is responsible for how the software is used and for compliance with
> applicable laws and the rules of any poker room or platform they connect to.

---

## Operating Modes

### SIMULATION
- Full HIVE features against simulated tables.
- No real client capture/clicks required.

### RESEARCH / LOGGING
- Same capabilities with full audit logs (card shares, decisions, actions).

### LIVE_AUTOMATION
- Full cycle against a real poker client UI:
  lobby scan → seating → card exchange → coordinated play → action execution.
- Safety systems remain available (kill switch, risk levels, dry-run).

### DRY_RUN
- Vision and decision engines run normally.
- No real mouse/keyboard or ADB input is sent.
- Use for pipeline validation and debugging.

---

## Coordinated Play

HIVE supports multi-bot coordination (shared hole cards, collective equity, team strategies):

- Teams of bots can exchange information and act jointly.
- Card exchange is encrypted in transit when using CentralHub (Fernet).
- All exchanges can be logged with timestamps and hand IDs.

---

## Action Execution Safety

| Layer | Protection |
|-------|------------|
| Kill switch | Immediate halt of all bot actions |
| Risk classification | Actions rated before execution |
| Dry-run mode | Log-only, no real input |
| Rate limiting | Cap actions per second |
| Humanization | Timing variance and mouse curves |
| Anti-pattern | Break repetitive click patterns |

---

## Operator Responsibility

1. Configure accounts, proxies, and clients correctly.
2. Keep logs when debugging multi-bot sessions.
3. Follow the rules of the poker rooms and jurisdictions you operate in.
4. Use kill switch / emergency stop if something goes wrong.

---

## Disclaimer

> Software is provided "as is".
> Authors are not responsible for account bans, losses, or rule violations
> arising from operator use of the product.
