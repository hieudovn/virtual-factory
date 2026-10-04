# DDAY-B4-C01 — Unmet Water Conservation + B3 Evidence Restore — SA Review Report

## Status

**IMPLEMENTED — PR OPEN — READY FOR SA REVIEW** (local acceptance complete;
exact-head CI and the canonical task-gate result are recorded in
`.ai-harness/traces/DDAY-B4-C01/` after the evidence commit).

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B4-C01` |
| Authority | SA Issue `#106` (correction only); parent `#105`; SA review on PR `#101` at `0f9606b` |
| Issue #106 access | GitHub Issues API returned 403/404 for this token; contract authored from the SA review comment (2026-10-03T15:35:49Z) plus the explicit user execution order, which name the same two blockers |
| Objective | (a) preserve unmet Filler water demand; (b) restore the two accepted B3 evidence files exactly to `23b6208` |
| Non-deliverables | B5+, merge, starvation/interlock engine, B2/B3 line-semantic rewrite |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-reviewed B4 head / C01 baseline | `0f9606bbc8690e80cfdbf9c4105bcfa998e6e0e8` — match at C01 start |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — not advanced |
| Preflight before first C01 implementation write | `PRECHECK PASSED`, exit 0, clean tree (after the contract commit) |
| PR | `#101` OPEN, base `main` |

---

## Blocker 1 — unmet water demand

Pre-fix (`0f9606b`):

```
drawn = min(pending, tank)
pending = 0.0
```

A starved request was destroyed. Nominal B4-11 never hit the edge.

Fix: `pending -= drawn`. Publish `unmet_water_demand_m3` and
`water_request_total_m3` so `request = draw + unmet` is observable.

Proof (empty tank, request 0.01 m³):

| Step | unmet | draw | request |
|---|---|---|---|
| starve | 0.01 | 0.00 | 0.01 |
| after 0.004 m³ | 0.006 | 0.004 | 0.01 |
| after 0.02 m³ | 0.00 | 0.01 | 0.01 |

No interlock engine. Existing B4-11 identities still hold on the nominal
trajectory and now also assert `unmet == 0` there.

---

## Blocker 2 — B3 evidence restore

Restored exactly to `23b6208266751a8c508b0d96fd7a736dffc5676c`:

| File | blob |
|---|---|
| `evidence/DDAY-B3/generate_evidence.py` | `e3c7de398b7a755d9b5e5deb51be7dbbc1b4ed94` |
| `evidence/DDAY-B3/smoke_bottled_water_ui.py` | `69ce6c62f238bf6faf4d08288f91d7bba61d37b2` |

`git diff 23b6208 --` those two files is empty.

B4-specific `factory_autorun=False` UI smoke now lives only at
`.ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_ui.py`.

---

## Tests and smokes

| Scope | Result |
|---|---|
| C01 tests | 3/3 PASS |
| B4 file | 30/30 PASS |
| Full suite | **1719/1719 PASS**, exit 0 |
| SMOKE-BW-UNMET | PASS |
| SMOKE-BW-FACTORY | PASS |
| SMOKE-BW-UI (B4-owned) | PASS |
| SMOKE-BW | PASS |

Suite: 1716 (B4) → **1719** (C01). No test deleted or weakened.

---

## Scope

C01-scope vs `0f9606b` (implementation, before this evidence pack): 7 files.
Harness allowlist vs `origin/main`: PASS (113 files).
Forbidden paths: none touched.
No merge. No B5.

---

## Governance

- **Merge NOT authorized.** No merge performed.
- **No next slice started.**
- Issue #106 / #105 / PR #101 are the report surfaces requested by SA.

Evidence: `.ai-harness/sa-review/evidence/DDAY-B4-C01/`
Report: `.ai-harness/sa-review/reports/DDAY-B4-C01.md`
