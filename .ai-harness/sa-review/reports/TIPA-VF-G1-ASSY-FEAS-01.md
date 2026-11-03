# TIPA-VF-G1-ASSY-FEAS-01 — SA review summary

**Issue:** #126  
**Task contract:** `.ai-harness/tasks/TIPA-VF-G1-ASSY-FEAS-01.json`  
**Full report:** `docs/reports/TIPA_VF_G1_ASSY_EXTERNAL_INPUT_FEASIBILITY.md`  
**Evidence:** `.ai-harness/sa-review/evidence/TIPA-VF-G1-ASSY-FEAS-01/`  
**Baseline:** `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe`  
**Design input:** PR #132 head `ff485d5bb50e55e91b90008465e4cc87ab7a9f22` (unmerged)  
**Production code changed:** NO

## Decision

```text
NEEDS_LOCAL_EXTENSION — bounded G3-A adapter required
```

The current six-sub-line ASSY runtime does **not** already support an integrated
external feed or an exact factory clock. It can be extended additively without
rewriting core, but not by using the current API as-is.

## Key findings

1. **Four local production paths** exist: `initialize` seeds 7 SSO2 + 7 RSO2 per
   context; `ContinuousFeedPolicy.replenish` tops up both; `step_context`
   produces RSO2 on demand; `produce_sso2_wip`/`produce_rso2_wip` are public
   local producers. The on-demand path is **not** disabled by
   `continuous_feed_enabled=False`.
2. **No external injection API**: unregistered external IDs are rejected; RSO2
   buffer is private and AP04 pops the first key.
3. **No exact-time/event-boundary API**: `execute_dwell` and `index_line` are the
   only time advances; six contexts are explicitly independent; no global
   lockstep. `DiscreteClock`/`FutureEventScheduler` exist but are not wired.
4. **No reservation/all-or-nothing join**: AP04 has no eligibility, version,
   reservation or rollback; missing Rotor raises `AssyLineError` rather than a
   deterministic wait state.
5. **Snapshot/reset/C4 are stable**: reset moves `R1 → R2`, trace fingerprint is
   identical, duplicate poll adds zero keys, C4 remains `tipa-assy-demo-v1.1`
   with 9 types / 666 messages.

## Seam classification

| Seam | Classification |
|---|---|
| Suppress all local seed/replenish | `SAFE_ADDITIVE` |
| External SSO2 registration at PRE-ASSY | `NEEDS_LOCAL_EXTENSION` |
| External RSO2 registration at AP04 | `NEEDS_LOCAL_EXTENSION` |
| Exact factory clock / six-line lockstep | `BLOCKED_REDESIGN` for the same-time claim |
| Reservation / all-or-nothing AP04 join | `NEEDS_LOCAL_EXTENSION` |
| Snapshot/reset/run-id/C4 | `SAFE_ADDITIVE` |
| Late WIP / wait state | `NEEDS_LOCAL_EXTENSION` |
| Buffer capacity/FIFO/qualification | `BLOCKED_REDESIGN` outside ASSY; G2 ledger |

## Oracle summary

| Oracle | Current |
|---|---|
| OR-01 zero external input | FAIL (local seed; raises at AP04) |
| OR-02 two sub-lines / one Rotor | NO MECHANISM (independent buffers) |
| OR-03 late external WIP | NO SUPPORT (unknown WIP) |
| OR-04 replay/reset | PASS |
| OR-05 AP06 FAIL→PASS | PASS |

## Tests executed

- 109 passed: SIM-VAL-01 feed, demo composition, C4 bridge, MES-03 evidence,
  contract finality.
- 110 passed: Bottled Water line, ASSY line, demo ASSY MES v1, M6 integration.
- C4 smoke: 666 messages, 9 types, 666 unique keys, 6 sub-lines.
- No test deleted/skipped; no production/config/test file modified.

## Acceptance

All report/evidence acceptance items PASS. Exact-head PR/CI is recorded in the
task gate and PR/issue comment. The PM does not certify COMPLETE/CLOSED and does
not authorize G3-A, merge or the next slice.
