# 13-v3 — Risk Register (Final)

**Date:** 2026-08-05  
**Replaces:** `13-...-v2.md`

Key v3 changes: Added risks for bootstrap ownership (R26), dispatcher state leakage (R27), snapshot truncation (R28), TIPA prematurity (R29), command loss at completion (R30).

| # | Risk | Mitigation | Gate |
|---|------|-----------|------|
| R01–R22 | (unchanged from v2) | — | — |
| R23 | Engine receives handler scheduler | Resolved: C02-02 | M2-S01 |
| R24 | Routing conditions use eval() | Resolved: closed vocabulary | M3 |
| R25 | Continuous files renamed | Resolved: C-008 | M4 |
| R26 | Bootstrap behavior undefined at implementation | `initialize(initial_events)` explicit | M2-S01 |
| R27 | Handler leaks run_state mutations | Dispatcher does not receive run_state | M2-S01 |
| R28 | JSON truncated on overflow | 200KB hard limit, error envelope, never truncate | M4 |
| R29 | TIPA integration before config exists | TIPA begins M5-S01 | M3/M4 |
| R30 | Queued commands lost at completion | Commands applied before event, also before final broadcast | M2-S04 |
