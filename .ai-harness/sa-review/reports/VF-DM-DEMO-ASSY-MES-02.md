# VF-DM-DEMO-ASSY-MES-02 — Six-Sub-line MES Contract Bridge

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `VF-DM-DEMO-ASSY-MES-02` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/dm-demo-assy-mes-02` |
| Baseline (accepted six-sub-line) | `248e70dd4dd327a104e00d200e51608ac017a301` |
| Baseline remote branch | `origin/docs/m6-s01-tipa-baseline` = `248e70dd…` (no newer commit — no discrepancy) |
| Contract version | `tipa-assy-demo-v1` |
| Runtime | authoritative six-sub-line `/assy-demo` (no parallel simulation, no topology rewrite) |
| Production code changed | YES (additive only) |
| Discrete engine / observation core / MQTT / six-sub-line runtime redesigned | NO |

## 2. Objective

Use the authoritative six-sub-line Docker runtime at `/assy-demo` as the VF
source for the customer VF→MES demo, projecting its authoritative facts into
MES-compatible `ProjectedMessage`s via the existing M5 pipeline — without a
parallel simulation and without rewriting the runtime/topology.

## 3. What was built

- `src/virtual_factory/assembly/assy_mes_bridge.py` — additive six-sub-line
  MES contract bridge (`AssyMesBridge` + `build_assy_mes_pipeline`): run_status,
  issue, downtime, LINE_OUT, OEE, WIP_ENTERED + contract provenance; keeps
  M6-INT-01 P0 facts compatible.
- `src/virtual_factory/observation/projections/mes.py` — additive mappings:
  `oee_summary → mes.oee_summary`; `LINE_OUT`/`WIP_ENTERED`/`DOWNTIME_*` →
  `mes.execution_event`.
- `src/virtual_factory/assembly/demo_controller.py` — `attach_mes_bridge`,
  `trigger_jam`, `recover`, `run_to_terminal`, `mes_messages`,
  `mes_outbound_trace`; `reset()` bumps the MES bridge generation.
- `src/virtual_factory/ui/api.py` — `/assy-demo/{jam,recover,run-to-terminal,
  mes-messages,mes-trace,version}`.
- `src/virtual_factory/ui/static/assy_demo.{html,js}` — conveyor-state labels
  never presented as production STOPPED.
- `Dockerfile` + `docker-compose.assy.yml` — source-SHA bake (`SOURCE_SHA`
  build arg → `VF_SOURCE_SHA`) exposed via `/assy-demo/version`.
- `tests/test_assy_mes_bridge_v1.py` — 18 contract tests.
- `docs/deployment/demo-assy-mes-02.md`.

## 4. Findings resolved

1. **Operational state** — `mes.run_status` carries operational
   `line_state` (`running|fault|stopped`) plus a separate raw
   `conveyor_state`; the target sub-line runs RUNNING → FAULT → STOPPED →
   RUNNING; conveyor `stopped` is never projected as production STOPPED.
2. **Exception lifecycle** — deterministic `AP05_JAM` emits
   `EXCEPTION_RAISED` / `EXCEPTION_RESOLVED` under `mes.issue` with shared
   correlation (run, subline, station AP05, reason `AP05_JAM`). Quality HOLD
   never becomes a line fault/downtime (verified by test).
3. **Downtime** — exactly one `DOWNTIME_START` → `DOWNTIME_END` (120 s)
   derived from the authoritative simulation clock; no duplicate record.
4. **LINE_OUT** — `LINE_OUT` (`GOOD` from `RELEASED`, `REJECT` from
   `FAILED_FINAL`) distinct from AP11 final QC and RELEASE; derived from
   authoritative state, not hard-coded in the projection.
5. **OEE** — `mes.oee_summary` per sub-line/run with all required fields;
   `planned=run+downtime`, `actual=good+reject`, A/P/Q/OEE recomputable;
   below 100 % with at least one reject.
6. **Contract/provenance** — `message_key == payload.idempotency_key`,
   `contract_version`, `run_id=ASSY-SLxx:R<n>`, explicit `subline_id`,
   `station_id`, `simulation_time_s`, deterministic non-null `occurred_at`,
   stable source event identity (verified per message).
7. **Control surface** — `/assy-demo` reset bumps generation (no key reuse);
   reset → healthy → jam → recover → run-to-terminal; no new customer page;
   UI labels disambiguate conveyor vs production state.
8. **Docker** — rebuild on exact head; image bakes `SOURCE_SHA`; runtime
   exposes it via `/assy-demo/version`.

## 5. Machine-derived evidence (local, bounded demo)

`message-counts.json` (bounded demo, 13 composition steps, 6 sub-lines, run `R1`):

- **total 521 messages; 521 unique message keys; 0 duplicate keys**
- `mes.execution_event`: 399 (incl. WIP_ENTERED, OPERATION_COMPLETED, LINE_OUT, DOWNTIME_*)
- `mes.quality_result`: 57 · `mes.genealogy_relationship`: 43 · `mes.release`: 5
- `mes.run_status`: 9 · `mes.issue`: 2 · `mes.oee_summary`: 6 (one per sub-line)
- `LINE_OUT`: 5 GOOD + 1 REJECT
- SL03 run_status sequence: `running → fault → stopped → running`
- Evidence integrity: raw JSONL lines == unique message keys == 521 (no duplicate keys)

## 6. Tests

- `tests/test_assy_mes_bridge_v1.py`: **23 passed** (identity, operational
  state incl. conveyor/operational separation, exception lifecycle, downtime,
  LINE_OUT, OEE reconciliation, contract provenance, idempotency, reset
  generation, no-regression, fault-freeze consistency, deferred recovery).
- Full suite: **1595 passed, 0 failed, 0 errors** (green).

## 7. Acceptance criteria

| # | Criterion | Result |
|---|---|---|
| A01 | Six sub-lines with PRE-ASSY/AP01..AP11 | PASS |
| A02 | Distinct run identity per sub-line | PASS |
| A03 | Target RUNNING → FAULT → STOPPED → RUNNING | PASS |
| A04 | One exception raised/resolved | PASS |
| A05 | One confirmed downtime (120 s) | PASS |
| A06 | LINE_OUT GOOD + REJECT | PASS |
| A07 | OEE reconcile + below 100 % + reject | PASS |
| A08 | No regression of quality/retest/reinspection/genealogy/release | PASS |
| A09 | Duplicate poll no new keys; reset new generation | PASS |
| A10 | Full VF suite green | PASS (1595 passed, 0 failed) |

## 8. Open findings

- **PR not opened** — no `gh` CLI / GitHub token in this environment. Proposed
  base `docs/m6-s01-tipa-baseline`, head `feature/dm-demo-assy-mes-02`.
- **Preflight baseline check** compares `expected_base_sha` against
  `origin/main` (harness is main-centric); this gate's authorized baseline is
  `docs/m6-s01-tipa-baseline` = `248e70dd…` (verified exact via
  `git ls-remote`, no newer commit).
- **Two baseline tests were defective pre-existing on the accepted six-sub-line
  baseline and are fixed tests-only in C02 per SA authorization**
  (`test_assy_demo.py::test_scenario_switch_resets_state`,
  `test_ops04_c01.py::test_select_does_not_mutate_runtime_state`). Remote
  `main` does not contain these six-sub-line tests; no main merge/cherry-pick
  was performed and no production code was changed to satisfy the tests.

## 9. Changed files

`assy_mes_bridge.py` (new), `demo_composition.py` (additive selective-step),
`mes.py`, `demo_controller.py`, `ui/api.py`, `ui/static/assy_demo.{html,js}`,
`Dockerfile`, `docker-compose.assy.yml`, `tests/test_assy_mes_bridge_v1.py`
(new), `tests/test_assy_demo.py` (tests-only fix), `tests/test_ops04_c01.py`
(tests-only fix), `docs/deployment/demo-assy-mes-02.md` (new),
`.ai-harness/tasks/VF-DM-DEMO-ASSY-MES-02.json` (new), evidence.

## 10. C02 corrections (final corrective)

- **Runtime-consistent fault/downtime** — while `AP05_JAM` is active, the
  faulted target sub-line is frozen (excluded from `step_all` via the new
  `exclude_sub_line_ids` argument): no sim-time/dwell/WIP/operation/quality/
  genealogy/release/LINE_OUT advance. The five siblings advance normally.
  Recovery is emitted only after the 120 s downtime interval (≥1 excluded
  step); the target resumes afterwards. `line_runtime.py` is untouched.
- **Vacuous test removed** — conveyor-state separation asserted precisely.
- **Bounded demo** — `run_to_terminal` is condition-based (target terminal
  REJECT + each non-target ≥1 GOOD) with a 24-step hard cap; the bounded demo
  emits **521 messages** (< 1,000), 5 GOOD + 1 REJECT, 6 OEE summaries.
- **Clean evidence** — `demo-run.jsonl` regenerated by overwrite; raw lines ==
  unique message keys == 521; 0 duplicate keys.
- **Two defective baseline tests fixed tests-only** (see §8).

## 11. Recommendation

```text
VF-DM-DEMO-ASSY-MES-02-C02 — READY FOR SA REVIEW
Candidate SHA (implementation head): 313bc84
Review head: origin/feature/dm-demo-assy-mes-02 (pushed; exact tip SHA in final SA-ready message)
Tests: 23 bridge tests PASS; full suite 1595 PASS / 0 FAIL
Evidence: 521 messages, 0 duplicate keys, 13 composition steps
```

The PM does not self-certify COMPLETE or CLOSED. Merge and next-slice
authorization remain with the SA.
