# VF-DM-DEMO-ASSY-MES-01 — TIPA ASSY Customer Demo Scenario v1

> C02 corrective cycle applied on review head `4db8d60` (see §12).

## 1. Baseline / Head

| Field | Value |
|---|---|
| Task ID | `VF-DM-DEMO-ASSY-MES-01` |
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/dm-demo-assy-mes-01` |
| Baseline (origin/main) | `17a1d9ecafb170fa94e8d01a1f12d84e79982773` |
| Candidate SHA | `3b70688f6c6bcb342e9186a762727ff6e639b799` (C02 implementation head) |
| Review head | `origin/feature/dm-demo-assy-mes-01` (pushed; exact tip SHA in final SA-ready message) |
| Contract version | `tipa-assy-demo-v1` |
| Production code changed | YES (additive only) |
| Simulation engine redesigned | NO |
| Observation pipeline core redesigned | NO |
| MQTT gateway redesigned | NO |

## 2. Objective

Deterministic, resettable single-sub-line (`ASSY-SL01`) VF→MES demo:
`SSO2+RSO2 → PRE-ASSY → AP01..AP11 → LINE_OUT`, with 4 deterministic WIPs,
independent line-state/exception/downtime/LINE_OUT/quality/genealogy events,
and a reconciled OEE summary, routed through the existing M5 pipeline
(`RealityInput → ObservationService → ObservationRouter → MESProjection →
JSONL/MQTT gateways`).

## 3. What was built

New package `src/virtual_factory/assembly/demo_assy_mes/`:

- `model.py` — domain vocabulary (`LineState`, `LineOutDisposition`, `Station`,
  `FactKind`, `DemoFact`, `ScenarioSpec`).
- `oee.py` — `OeeSummary` + `compute_oee` (A/P/Q reconciliation).
- `scenario.py` — `build_scenario_facts()` (deterministic fact script).
- `bridge.py` — `build_observation_points()`, `build_demo_pipeline()`,
  `fact_to_reality()` (DemoFact → M5 RealityInput).
- `runner.py` — `DemoRunner` (reset/start/pause/step/jam/recover, OEE, snapshot).
- `controller.py` — `DemoController` (control surface).
- `fixtures.py` — `build_fixtures()` (pure, from real messages).
- `__main__.py` — one-command end-to-end demo runner.

Additive projection change `observation/projections/mes.py`:
- `mes.oee_summary` semantic type; `LINE_OUT`/`WIP_ENTERED`/`DOWNTIME_*`
  event types → `mes.execution_event`.

Minimal control surface in `ui/api.py`:
- `GET /demo-assy-mes` (customer-facing demo page)
- `POST /demo-assy-mes/{reset,start,pause,step,jam,recover}`
- `GET /demo-assy-mes/{snapshot,messages}`

`src/virtual_factory/ui/static/demo_assy_mes.html` — customer page
(SSO2+RSO2 → AP04 join → PRE-ASSY..AP11 → LINE_OUT, WIP tokens, line state,
event log, OEE, control buttons).

## 4. The four deterministic WIPs

| WIP | Journey | LINE_OUT |
|---|---|---|
| `MTR-DEMO-001` | happy: AP04 join, AP06/AP08/AP11 PASS | GOOD |
| `MTR-DEMO-002` | AP06 FAIL a1 → rework → PASS a2 | GOOD |
| `MTR-DEMO-003` | AP05 jam → FAULT → STOPPED → recover → RUNNING | GOOD |
| `MTR-DEMO-004` | AP11 final-QC FAIL (terminal) | REJECT |

## 5. OEE reconciliation (verified)

```text
planned=1200  downtime=120  run=1080  ideal_cycle=240
actual=4  good=3  reject=1
A = 1080/1200 = 0.9
P = 240×4/1080 = 0.888889
Q = 3/4 = 0.75
OEE = 0.9 × 0.888889 × 0.75 = 0.6 (60%)
```

Computed from simulated data (LINE_OUT counts + downtime interval), not
hard-coded. `run + downtime == planned`, `good + reject == actual`.

## 6. Message contract

Every message carries: stable idempotency key, `contract_version`
(`tipa-assy-demo-v1`), `run_id` (`ASSY-SL01:R<n>`), `subline_id`, station
identity, WIP identity, `simulation_time_s`, and a deterministic ISO-8601
`occurred_at` (fixed demo epoch `2026-01-01T00:00:00+00:00` +
`simulation_time_s`).

Quality facts carry finality markers: `is_terminal` (false except the
terminal AP11 final-QC FAIL) and `terminal_state` (`"failed_final"` for the
terminal reject, `""` otherwise). FAULT and STOPPED have distinct simulated
timestamps (590s / 600s), preserving RUNNING → FAULT → STOPPED → RUNNING.

Emitted types (63 messages/run): `mes.run_status` ×4, `mes.issue` ×2,
`mes.execution_event` ×39, `mes.quality_result` ×13,
`mes.genealogy_relationship` ×4, `mes.oee_summary` ×1.

## 7. Tests

- `tests/test_demo_assy_mes_v1.py`: **32 passed** (topology, four WIPs,
  fault/recovery, LINE_OUT, OEE reconciliation, determinism, reset,
  idempotency, projection, JSONL serialization, control surface, quality
  finality markers, state ordering, deterministic `occurred_at`, customer
  page route).
- Full suite: **1099 passed** (no failures, no regression).

### C02 control semantics (verified)

`start` only enables stepping (does NOT process the timeline synchronously);
`pause` blocks the next `step`; `step` emits exactly one fact while running;
`trigger_jam` deterministically emits facts up to and including
FAULT → STOPPED; `recover` only resumes after the jam and emits recovery
facts until RUNNING.

## 8. Acceptance criteria

| # | Criterion | Result |
|---|---|---|
| A01 | Deterministic repeated runs (same output/order) | PASS |
| A02 | Reset leaves no runtime state | PASS |
| A03 | No duplicate events on retry (stable keys) | PASS |
| A04 | JSONL / MQTT serialization compatible | PASS |
| A05 | OEE + counters reconcile | PASS |
| A06 | Existing VF suite no regression | PASS |
| A07 | Tests for topology, 4 units, fault/recovery, LINE_OUT, fixtures | PASS |
| A08 | Demo command / guide | PASS (`python -m virtual_factory.assembly.demo_assy_mes`) |

## 9. Evidence

`.ai-harness/sa-review/evidence/VF-DM-DEMO-ASSY-MES-01/`:
`preflight.json`, `demo-run.jsonl` (63 real messages), `fixtures/` (9 fixture
files), `regression-full.txt`.

## 10. Machine-derived gate status

Harness gate (`run_task_gate.py --report-only`), executed on C02 head
`3b70688f6c6bcb342e9186a762727ff6e639b799`:

| Step | Name | Result |
|---|---|---|
| P01 | Load contract | PASS |
| P02 | Validate contract | PASS |
| P03 | Preflight | PASS (baseline match, clean tree, correct branch) |
| P04 | Changed files | PASS (29 files) |
| P05 | Local evidence | PASS |
| P06 | Tests | PASS (1099 passed, 0 failed) |
| P07 | Smoke checks | PASS (SMOKE-DEMO) |
| P08 | Remote state | FAIL (no GitHub token / gh CLI — authenticated remote verification unavailable) |
| P09 | PR metadata | FAIL (no PR; token required) |
| P10 | Exact-head CI | FAIL (no CI trigger; token required) |
| P11 | Merge CI smoke | PASS (N/A) |

`requested_gate_satisfied: false` — remote steps fail closed solely because no
GitHub token / `gh` CLI is present in this environment. The branch **is**
pushed: `git ls-remote origin feature/dm-demo-assy-mes-01` =
`3b70688f6c6bcb342e9186a762727ff6e639b799`.

Open findings (remote verification blocked in this environment):

- P08/P09/P10 (authenticated remote state, PR metadata, exact-head CI):
  **UNVERIFIED** — no GitHub token and `gh` CLI not authenticated. A PR could
  not be opened programmatically and CI could not be triggered/verified.
  SA/operator credentials are required.

Machine-derived status: **IMPLEMENTED (pushed, local gate green);
NOT READY — PR/CI UNVERIFIED** (requires SA/operator credentials to open the
PR and run CI on the exact head).

## 11. Changed files

- `src/virtual_factory/assembly/demo_assy_mes/` (new package: model, scenario, oee, bridge, runner, controller, fixtures, __main__)
- `src/virtual_factory/observation/projections/mes.py` (additive: `mes.oee_summary` + LINE_OUT/WIP_ENTERED/DOWNTIME_* event mappings)
- `src/virtual_factory/ui/api.py` (control surface + `GET /demo-assy-mes` page route)
- `src/virtual_factory/ui/static/demo_assy_mes.html` (new customer page)
- `tests/test_demo_assy_mes_v1.py` (new, 32 tests)
- `docs/deployment/demo-assy-mes.md` (demo guide, updated control semantics)
- `.ai-harness/tasks/VF-DM-DEMO-ASSY-MES-01.json` (task contract)
- `.ai-harness/sa-review/` (report, inbox, evidence, fixtures)

No change to `discrete/`, observation pipeline core (`envelope/point/service/router/policy`), or gateways.

## 12. C02 corrective cycle

Applied on review head `4db8d60`; fixed the 5 blocking findings without
redesigning the discrete engine, observation pipeline, MQTT gateway, or OEE:

1. **Quality finality markers** — `is_terminal`/`terminal_state` on every
   quality fact (non-terminal `false`/`""`; terminal AP11 final-QC FAIL
   `true`/`"failed_final"`).
2. **Deterministic `occurred_at`** — fixed demo epoch + `simulation_time_s`
   (ISO-8601 UTC), independent of ingest wall-clock.
3. **Distinct FAULT/STOPPED timestamps** — FAULT@590s, STOPPED@600s
   (downtime 600→720 = 120s preserved); RUNNING → FAULT → STOPPED → RUNNING.
4. **Real control semantics** — `start` enables stepping only; `pause` blocks
   `step`; `trigger_jam` → FAULT → STOPPED; `recover` only after fault.
5. **Customer page** — `GET /demo-assy-mes` renders the static demo page.

## 13. Recommendation

```text
VF-DM-DEMO-ASSY-MES-01-C02 — READY FOR SA REVIEW
Candidate SHA (implementation head): 3b70688f6c6bcb342e9186a762727ff6e639b799
Review head: origin/feature/dm-demo-assy-mes-01 (pushed; exact tip SHA in final SA-ready message)
Tests: 32 demo tests; 1099 full suite (0 failed)
Open findings: PR not opened / CI not run (no GitHub credentials in environment)
```

The PM does not self-certify COMPLETE or CLOSED. Merge and next-slice
authorization remain with the SA.
