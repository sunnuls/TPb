## Changelog

### 0.1.0

- **Poker `/analyze/poker` end-to-end (MVP)**: HH parsing → state validation → deterministic decision engine → RU explanation.
- **Hand history parsers**: PokerStars parser + generic fallback + dispatch selection + structured `ParseReport`.
- **No-hallucinations**: explanation templates only render fields that exist in `Decision.key_facts`.
- **Tests**: end-to-end API tests + parser tests with real-ish PokerStars cash + tournament fixtures.

## Changelog

### 0.1.0

- Added deterministic end-to-end `/analyze/poker` pipeline (HH parse → validate → engine → RU explanation).
- Added PokerStars + generic fallback hand-history parsing with `ParseReport`.
- Added MVP poker engine (preflop heuristic + postflop made-hand/draw + pot-odds when available).
- Added pytest coverage for parsing + API response shape + “no invented facts” basic guard.

## Changes

### 0.1.0

- Added end-to-end `/analyze/poker` pipeline: HH ingest → validation → deterministic MVP engine → RU explanation → parse_report.
- Added PokerStars HH parser improvements (total pot line capture) + generic fallback parser + parser dispatch.
- Added pytest coverage for parser extraction and API response + “no extra card facts” guard.


