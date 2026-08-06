# C02 Correction Mapping — V2 Findings → V3 Files

**Date:** 2026-08-05

| SA Finding | Correction | v3 File(s) | Key Change |
|-------------|-----------|------------|------------|
| V2-F01 (bootstrap undefined) | C02-01 | `05-v3` §3, `15-v3` §4.1 | `initialize(initial_events)` explicit |
| V2-F02 (dispatcher receives run_state) | C02-02 | `06-v3` §1, `04-v3` §1 | `dispatch(event)` — no run_state |
| V2-F02 (HandlerOutcome mutable) | C02-03 | `06-v3` §2, `15-v3` §4.4 | `tuple` not `list` |
| V2-F03 (slice ownership duplicate) | C02-04 | `04-v3` §4, `14-v3`, `15-v3` | M2-S01 owns protocol + outcome |
| V2-F04 (message_sequence in engine) | C02-05 | `04-v3` §3, `08-v3` §1–§2 | Moved to M4 SnapshotMessage |
| V2-F05 (safe-point order) | C02-06 | `05-v3` §5–§6 | Commands BEFORE event |
| V2-F06 (state authority) | C02-07 | `05-v3` §4 | Engine owns status; controller requests |
| V2-F07 (contract refs wrong) | C02-08 | `07-v3` §4 | Corrected edge binding example |
| V2-F08 (audit reduced) | C02-09 | `08-v3` §7, `09-v3` §7 | CommandAuditEntry restored |
| V2-F09 (snapshot truncation) | C02-10 | `08-v3` §5, `09-v3` §6, `10-v3` §1 | Never truncate; error envelope |
| V2-F10 (TIPA too early) | C02-11 | `11-v3` M3/M4/M5 | TIPA config begins M5-S01 |
| V2-F11 (test requirements) | C02-12 | `15-v3` §4, §6 | Explicit step semantics + acceptance |
| V2-F12 (acceptance criteria) | C02-13 | `15-v3` §6 | Baseline SHA, actual counts, CI |

---

## v3 File Inventory (14 files)

| File | Replaces |
|------|----------|
| `04-...-architecture-v3.md` | v2 |
| `05-...-control-modes-v3.md` | v2 |
| `06-...-state-contracts-v3.md` | v2 |
| `07-...-contracts-v3.md` | v2 |
| `08-...-snapshot-command-v3.md` | v2 |
| `09-...-api-plan-v3.md` | v2 |
| `10-...-performance-strategy-v3.md` | v2 |
| `11-...-roadmap-v3.md` | v2 |
| `12-decision-register-v3.md` | v2 |
| `13-risk-register-v3.md` | v2 |
| `14-...-slice-matrix-v3.md` | v2 |
| `15-prompt-vf-dm-m2-s01-v3.md` | v2 |
| `16-executive-summary-v3.md` | v2 |
| `c02-correction-mapping.md` | new |
