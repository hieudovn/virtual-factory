# M6-S04B-I04-C03 — Frame A Visual Evidence

All screenshots captured from live running application at head `50cf8d2`.

## Files

| File | Viewport | Scenario |
|------|----------|----------|
| `A1_1920x1080_happy.png` | 1920x1080 | HAPPY_PATH |
| `A2_1920x1080_ap06_hold.png` | 1920x1080 | AP06_FAIL_RETEST_PASS |
| `A3_1366x768_overview.png` | 1366x768 | AP06_FAIL_RETEST_PASS |

---

## A1 — 1920x1080 HAPPY_PATH

| Field | Value |
|-------|-------|
| Viewport | 1920 x 1080 |
| Scenario | HAPPY_PATH |
| Demo Step | 5 |
| Target Sub-line | (none) |
| Selected Sub-line | ASSY-SL01 |
| Held Station | (none) |
| Total Holds | 0 |
| Motors Created | 6 |

Visual: 6 lanes STOPPED. JOIN/TEST/VISION/FINAL landmarks. LIVE indicator.

---

## A2 — 1920x1080 AP06 HOLD

| Field | Value |
|-------|-------|
| Viewport | 1920 x 1080 |
| Scenario | AP06_FAIL_RETEST_PASS |
| Demo Step | 8 |
| Target Sub-line | ASSY-SL03 |
| Held Station | AP06 |
| Held WIP | MTR-0002 |
| Total Holds | 1 |
| Motors Created | 24 |

Visual: SL03 QUALITY HOLD, AP06/TEST highlighted red, AP06 / MTR-0002.

---

## A3 — 1366x768 Selection Persistence

| Field | Value |
|-------|-------|
| Viewport | 1366 x 768 |
| Scenario | AP06_FAIL_RETEST_PASS |
| Demo Step | 9 |
| Selected Sub-line | ASSY-SL04 (persists after STEP) |
| Total Holds | 0 |
| Motors Created | 30 |

Visual: SL04 cyan outline with cursor:pointer Detail affordance.
Selection persists after STEP refresh. 6 lanes readable.
