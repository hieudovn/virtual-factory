# DDAY-B2-C01 — Semantic Isolation + Harness Gate Correction — SA Review Report

## Status

**IMPLEMENTED — PR OPEN — READY FOR SA REVIEW**

Machine-derived by the full canonical task gate for this exact head:

```
Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW
Gate: ready_for_sa_review | Satisfied: True | Exit: 0
```

Pipeline P01–P24: all 24 executed, all 24 PASS (including **P22**, which
previously aborted every run). Acceptance: **14 PASS, 0 FAIL, 0 UNKNOWN**.

The PM does not self-certify `COMPLETE`, `CLOSED` or `SA APPROVED`.

---

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-B2-C01` |
| Authority | SA Issue `#103` (correction only), parent `#102`, PR `#101` |
| Objective | (a) remove legacy `ASSY` lifecycle semantics from Bottled Water outward facts while preserving legacy behaviour; (b) repair the P21/P22 harness inconsistency so the gate can validate its own provisional report |
| Non-deliverables | B3+ scope, any file outside the allowlist, lifecycle/domain API redesign, weakening `validate_report_consistency.py`, relaxing exact-head invariants or acceptance criteria |
| Authorization | `may_open_pr: true`, `may_merge: false`, `may_start_next_task: false` |

---

## Repository State

| Field | Value |
|---|---|
| Branch | `sa/dday-track-b-20261003` |
| SA-issued C01 baseline (Issue #103) | `0a1d18e42b5a28009ae05a6e916f9e942a857b38` — branch head at C01 start, **match** |
| Expected base SHA (harness semantics = `origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` — **not advanced** |
| Preflight before first C01 write | `PRECHECK PASSED`, exit 0, clean tree |

---

## Implementation (complete change set)

```
A  .ai-harness/tasks/DDAY-B2-C01.json
A  .ai-harness/tests/test_gate_report_provisional.py
A  .ai-harness/sa-review/evidence/DDAY-B2-C01/  (pack, smoke, scope contract)
M  .ai-harness/scripts/run_task_gate.py
M  src/virtual_factory/assembly/line_runtime.py
M  tests/test_dday_b2_bottled_water_line.py
```

987 insertions / 21 deletions. Nothing else changed; in particular
`demo_controller.py`, `station_contracts.py`, `quality_records.py`,
`conveyor.py`, `demo_snapshot.py`, `validate_report_consistency.py` and
`derive_status.py` are untouched.

### C01-A — semantic isolation

Verified pre-fix defect, reproduced through public API before any change:

```
manufacturing_status: 'in_assy'      leaks 'assy' (case-insensitive): True
entry-facts hits: ["in_assy"]
```

Fix: `WipLifecycle` gains `IN_LINE = "in_line"`; the generic `introduce_unit()`
assigns it. The legacy value is neither removed nor renamed, and the legacy
profile still assigns `in_assy` via `introduce_to_assy()`.

Post-fix, every stage of the generic route publishes a domain-neutral status:

| Stage | Status |
|---|---|
| entry | `in_line` |
| in progress (station not complete) | `in_line` |
| station completion | `completed_station` |
| route completion | `released` |
| reject | `rejected` |

Case-insensitive leak sweep (patterns `assy`, `tipa`, `sso2`, `rso2`,
`ap05_jam`, `\bap\d{2}\b`) over raw facts, trace, contracts, unit ids and every
station status: **0 findings** across 139 / 143 / 290 / 372 strings for the four
states.

T12 was strengthened from exact uppercase literals to case-insensitive semantic
matching, so `in_assy` now fails the test — the regression guard the SA asked for.

### C01-B — harness gate repair

**Defect 1 (P21/P22).** P21 wrote its provisional report without the
implementation SHA while P22 requires it, so the gate could never validate its
own artefact; every task aborted at P22 with exit 5 and P23/P24 were unreachable
(reproduced at two different heads). Fix: a single `_write_gate_report(...)`
writer now always states `**Implementation SHA**`; P21 and P24 both use it.
`validate_report_consistency.py` is unmodified and still fail-closed (negative
control: a report without the SHA fails).

**Defect 2 (PR state representation), found during verification.** With a token,
`verify_remote_state.py` stores the REST value `"open"` while `derive_status.py`
and the harness fixtures use `"OPEN"`. The gate consequently completed P01–P24
with every step PASS and every acceptance item PASS yet derived
`NOT READY — GOVERNANCE FAILURE` purely on representation. Fix: `run_task_gate.py`
normalizes the PR state to the canonical form before status derivation. This is a
representation alignment, not a relaxation: a **closed** PR still derives
`NOT READY — GOVERNANCE FAILURE` (proven in the evidence and by a focused test).

---

## Evidence

| Item | File |
|---|---|
| 01 semantic isolation (pre/post fix, all states, legacy preserved) | [01-semantic-isolation.md](../evidence/DDAY-B2-C01/01-semantic-isolation.md) |
| 02 harness gate repair (root causes, before/after, tests) | [02-harness-gate-repair.md](../evidence/DDAY-B2-C01/02-harness-gate-repair.md) |
| 03 full task-gate result (P01–P24, acceptance, invariants) | [03-task-gate-result.md](../evidence/DDAY-B2-C01/03-task-gate-result.md) |
| 04 tests and regression | [04-tests-and-regression.md](../evidence/DDAY-B2-C01/04-tests-and-regression.md) |
| 05 scope audit | [05-scope-audit.md](../evidence/DDAY-B2-C01/05-scope-audit.md) |
| raw machine record | [machine-evidence.json](../evidence/DDAY-B2-C01/machine-evidence.json) |
| pre-fix / post-fix transcripts | [prefix-reproduction.txt](../evidence/DDAY-B2-C01/prefix-reproduction.txt), [postfix-proof.txt](../evidence/DDAY-B2-C01/postfix-proof.txt) |
| runtime smokes | [smoke_semantic_isolation.py](../evidence/DDAY-B2-C01/smoke_semantic_isolation.py), [../DDAY-B2/smoke_bottled_water.py](../evidence/DDAY-B2/smoke_bottled_water.py) |

### Tests

| Suite | Collected | Passed | Failed | Result |
|---|---|---|---|---|
| B2 + C01 tests | 19 | 19 | 0 | PASS |
| Harness tests | 9 | 9 | 0 | PASS |
| Legacy regression | 575 | 575 | 0 | PASS |
| Full suite | 1666 | 1666 | 0 | PASS |

### Required verification (Issue #103)

| # | Requirement | Result |
|---|---|---|
| 1 | Reproduce pre-fix `in_assy` leakage / code-path proof | **done** — public-API reproduction + transcript |
| 2 | No legacy semantics at entry / in-progress / completion / reject | **PASS** — 0 findings in 4 states, 944 strings scanned |
| 3 | Legacy regression unchanged/green | **PASS** — 575/575, unmodified |
| 4 | P21 provisional report contains the exact implementation SHA | **PASS** — full SHA and 12-char prefix present |
| 5 | `validate_report_consistency.py` succeeds on the generated provisional report | **PASS** — "Report is consistent with evidence.", 0 issues |
| 6 | Full task gate successfully through P24 for the new exact head | **PASS** — exit 0, P01–P24 all PASS, READY |
| 7 | Targeted B2 tests + full repository suite | **PASS** — 19/19 and 1666/1666 |
| 8 | remote HEAD = PR #101 head = CI head = reported SHA | **PASS** — all three invariants `true` |

---

## Acceptance Matrix

| ID | Criterion | Result |
|---|---|---|
| A01 | Baseline match | PASS |
| A02 | Clean working tree at preflight | PASS |
| A03 | Full suite passes | PASS |
| A04 | Required smoke checks effective PASS | PASS (SMOKE-BW, SMOKE-BW-ISO) |
| A05 | No blocking issues | PASS |
| A06 | No tool failures (P22 no longer fails) | PASS |
| A07 | No contradictions | PASS |
| A08 | All canonical gate steps executed | PASS |
| A09 | All canonical gate steps PASS, including P22 | PASS |
| A10 | Commit exists remotely | PASS |
| A11 | Remote branch head reported | PASS |
| A12 | PR #101 resolved | PASS |
| A13 | Exact-head CI success | PASS |
| A14 | Authorization boundaries preserved | PASS |

---

## Issues

| Type | Details |
|---|---|
| Tool failures | none |
| Unknown evidence | none |
| Contradictions | none |
| Residual (disclosed) | The PR-state root cause remains in `verify_remote_state.py`, which is outside the C01 allowlist; the orchestrator aligns the representation instead. A one-line normalization at the source would make the shim removable — SA decision requested. |
| Invocation note | Do not force `PYTHONIOENCODING=utf-8` when invoking the gate on Windows (subprocess encoding round-trip). Does not affect CI. |

---

## Derived Status

| Field | Value |
|---|---|
| Derived status | `IMPLEMENTED — PR OPEN — READY FOR SA REVIEW` |
| Derivation | full canonical task gate, P01–P24, exit 0 |
| Requested gate | `ready_for_sa_review` — **satisfied** |
| Requested human decision | SA review of the exact head diff, tests and evidence; optional decision on fixing `verify_remote_state.py` at the source |
| Merge authorization | **not granted** |
| Next-slice authorization | **not granted** |
