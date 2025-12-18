# POLICY

## Product modes

### REVIEW

- Intended use: post-hand review.
- Poker: analysis output is allowed only after a hand is complete (`meta.hand_complete == True`) or completion can be inferred from hand history.

### TRAIN

- Intended use: internal trainer scenarios.
- External input is blocked.

### LIVE_RESTRICTED

- Intended use: restricted live coaching.
- Poker: only preflop is allowed.

### LIVE_RTA

- Intended use: real-time coaching for simulator environments.
- Hard rule: `mode == LIVE_RTA` is allowed only when `meta.source == "simulator"`.

### INSTANT_REVIEW

**Instant Review** is **post-action coaching**, not real-time assistance.

Semantics:

- The client may track the table in real time (periodic frames / screenshots).
- The server may compute analysis continuously.
- **Recommendations must be revealed only after the user’s action is committed.**

Hard rules:

- If `mode == INSTANT_REVIEW`:
  - If `meta.post_action != True` -> **BLOCK** (`403`, `code=POLICY_BLOCK`, `reason=instant_review_requires_post_action`).
  - If `meta.post_action == True` -> allowed.
- If `meta.source == "poker_room"` and `meta.is_realtime == True`:
  - **Never** allow pre-action disclosure.
  - Post-action disclosure is allowed **only** when `mode == INSTANT_REVIEW` and `meta.post_action == True`.

Security note:

- When policy blocks a request, API responses **must not contain** `decision` or `explanation`.
