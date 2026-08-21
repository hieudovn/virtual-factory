# VF-DM-DEMO-ASSY-MES-03 — Detailed Operation Evidence Contract

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `VF-DM-DEMO-ASSY-MES-03` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/dm-demo-assy-mes-03-evidence` |
| Baseline (accepted six-sub-line) | `c3c8bb60e587f2ef4464975ab359362100fa7730` |
| Baseline remote branch | `origin/docs/m6-s01-tipa-baseline` = `c3c8bb6…` (no newer commit — no discrepancy) |
| Contract version | `tipa-assy-demo-v1.1` |
| Runtime | authoritative six-sub-line `/assy-demo` (no parallel simulation, no topology rewrite) |
| Production code changed | YES (additive only, incl. two justified additive runtime fields) |
| Discrete engine / observation core / MQTT / six-sub-line runtime redesigned | NO |

## 2. Objective

Complete the one-way VF→MES contract with detailed operation evidence:
AP03 checklist evidence (`mes.checklist_result`), AP06 numerical measurement
evidence (`mes.measurement_result`), and AP08/AP11 structured inspection
observations (`observations[]` on `mes.quality_result`) — all derived from
authoritative runtime/operation-execution data without fabrication. Bump the
contract to `tipa-assy-demo-v1.1`. No MES implementation in this gate.

## 3. What was built

- `src/virtual_factory/assembly/assy_mes_bridge.py` — additive evidence facts:
  `CHECKLIST_CONFIRMED` (AP03, checklist ≠ quality), `MEASUREMENT_RESULT`
  (AP06 per-attempt R_U-V/R_V-W/R_W-U with value/unit/limits/in_spec),
  `observations[]` + `proposed_quality_result` + `proposed_quality_reason` on
  `QUALITY_RESULT` and `AP11_FINAL_QC_*`; contract version `tipa-assy-demo-v1.1`.
- `src/virtual_factory/observation/projections/mes.py` — additive mappings
  `CHECKLIST_CONFIRMED → mes.checklist_result`,
  `measurement_result → mes.measurement_result`.
- `src/virtual_factory/ui/api.py` — `/assy-demo/version` returns
  `contract_version: tipa-assy-demo-v1.1`.
- **Justified additive runtime change** (see §4):
  - `src/virtual_factory/assembly/quality_records.py` — `QualityRecord` gains
    default-valued frozen fields `observations`, `proposed_quality_result`,
    `proposed_quality_reason`.
  - `src/virtual_factory/assembly/line_runtime.py` — one additive constructor
    call in `_apply_quality_decision` freezes the already-observed values into
    the record at decision time.
- `tests/test_assy_mes_03_evidence.py` — 16 focused contract tests.
- `tests/test_assy_mes_bridge_v1.py` — contract version updated to v1.1.
- `docs/deployment/demo-assy-mes-03.md`.
- Evidence under `.ai-harness/sa-review/evidence/VF-DM-DEMO-ASSY-MES-03/`.

## 4. Justified additive runtime change (data not otherwise exposed)

The gate requires observations to be immutable after the decision is recorded.
The authoritative per-attempt observation result and machine proposal were
previously not exposed in a stable form:

- `QualityRecord.checklist_items` stored only observation-id strings (no
  result), and
- `op.observations` / `op.proposed_quality_result` are overwritten on every
  re-observation, so a retested attempt's NG evidence was lost.

Minimal additive fix (no behavior/transition/scheduling change):

- `QualityRecord` gains `observations: tuple[dict, ...] = ()`,
  `proposed_quality_result: str = ""`,
  `proposed_quality_reason: Optional[dict] = None`.
- `line_runtime._apply_quality_decision` passes the already-observed values
  into the frozen record (one additive constructor call).

The bridge reads the frozen record fields first, so a retested NG attempt keeps
its `anomaly` observation and `NG` proposal even after a later PASS
(proven by `ap08-ng-observation.json`).

## 5. Machine-derived evidence (bounded demo)

`message-counts.json` (bounded demo, 13 composition steps, 6 sub-lines, run `R1`):

- **total 666 messages; 666 unique message keys; 0 duplicate keys;
  raw JSONL lines == unique keys == total**
- `mes.execution_event`: 399 (WIP_ENTERED, OPERATION_COMPLETED, LINE_OUT, DOWNTIME_*)
- `mes.checklist_result`: 49 (AP03 confirmed checklist; no fabricated disposition)
- `mes.measurement_result`: 96 (AP06: 32 attempts × 3 points R_U-V/R_V-W/R_W-U)
- `mes.quality_result`: 57 (52 QUALITY_RESULT + 5 AP11_FINAL_QC_*)
  - QUALITY_RESULT with `observations[]`: 20 (AP08 VISUAL_INSPECTION)
  - AP11 FINAL_QC with `observations[]`: 5 (FINAL_QC, 3 observations each)
- `mes.genealogy_relationship`: 43 · `mes.release`: 5
- `mes.run_status`: 9 · `mes.issue`: 2 · `mes.oee_summary`: 6
- AP06 FAIL attempt: R_U-V = 0.29 Ω, lower_limit 0.30, `in_spec=false`
  (preserved after retest)
- AP08 NG → reinspect PASS (focused harness): NG attempt keeps
  `demo_visual_observation_1 = anomaly`, proposal `NG`; the later PASS attempt
  has `ok`/`PASS` — per-attempt immutability proven.
- Contract version `tipa-assy-demo-v1.1` stamped on every message.

## 6. Tests

- `tests/test_assy_mes_03_evidence.py`: **16 passed** (AP03 checklist ×4,
  AP06 measurement ×4, observations ×2, contract/idempotency ×3, no-regression ×3).
- `tests/test_assy_mes_bridge_v1.py`: contract version updated to v1.1.
- Full suite: **1611 passed, 0 failed, 0 errors** (green).

## 7. Acceptance criteria

| # | Criterion | Result |
|---|---|---|
| A01 | AP03 confirmed → exactly one checklist_result, no disposition | PASS |
| A02 | AP03 incomplete → no checklist_result | PASS |
| A03 | Checklist item ids/counts match station contract | PASS |
| A04 | AP06: 3 measurements per attempt (R_U-V/R_V-W/R_W-U) | PASS |
| A05 | AP06 value/unit/limits/in_spec (inclusive) | PASS |
| A06 | AP06 FAIL value preserved after retest | PASS |
| A07 | AP06 measurement linked to execution/record/attempt | PASS |
| A08 | AP08 observations + proposal separate from disposition; NG → anomaly | PASS |
| A09 | AP11 observations emitted; not conflated with release/line-out | PASS |
| A10 | Contract v1.1 on every message | PASS |
| A11 | Duplicate poll no new keys; reset new generation | PASS |
| A12 | Full VF suite green | PASS (1611 passed, 0 failed) |
| A13 | MES-02 facts (run_status/issue/downtime/LINE_OUT/OEE) no regression | PASS |

## 8. Open findings

- **PR not opened yet** — no `gh` CLI / GitHub token in this environment;
  proposed base `docs/m6-s01-tipa-baseline`, head
  `feature/dm-demo-assy-mes-03-evidence`.
- **Preflight baseline check is main-centric** — the harness compares
  `expected_base_sha` against `origin/main` (`fda1db4…`), but this gate's
  authorized baseline is `docs/m6-s01-tipa-baseline` = `c3c8bb6…` (verified
  exact via `git rev-parse origin/docs/m6-s01-tipa-baseline`, no newer commit).
  Same documented limitation as MES-02.
- **Docker exact-head smoke** — DONE: image rebuilt on `05d0154`,
  `/health` ok, `/assy-demo` 200, `/assy-demo/version.source_sha == 05d0154`,
  `contract_version == tipa-assy-demo-v1.1`, 6 sub-lines,
  reset→jam→recover→run-to-terminal→mes-messages produces the evidence surface
  (checklist_result 49, measurement_result 96, quality_result 57) with 0
  duplicate keys (see `docker-smoke.md`).
- **Exact-head CI** pending (see SA-ready message for CI URL).

## 9. Changed files

`assy_mes_bridge.py`, `quality_records.py` (justified additive),
`line_runtime.py` (justified additive, one constructor call), `mes.py`,
`ui/api.py`, `tests/test_assy_mes_bridge_v1.py`,
`tests/test_assy_mes_03_evidence.py` (new),
`docs/deployment/demo-assy-mes-03.md` (new),
`.ai-harness/tasks/VF-DM-DEMO-ASSY-MES-03.json` (new), evidence.

## 10. Recommendation

```text
VF-DM-DEMO-ASSY-MES-03 — READY FOR SA REVIEW
Candidate SHA (implementation head): 05d0154
Review head: origin/feature/dm-demo-assy-mes-03-evidence (pushed; exact tip SHA in final SA-ready message)
Tests: 16 focused PASS; full suite 1611 PASS / 0 FAIL
Evidence: 666 messages, 0 duplicate keys, checklist_result 49, measurement_result 96, quality_result 57 (observations on AP08/AP11)
Docker: exact-head image smoke PASS (source_sha == 05d0154, contract v1.1)
Contract: tipa-assy-demo-v1.1
```

The PM does not self-certify COMPLETE or CLOSED. Merge and next-slice
authorization remain with the SA.
