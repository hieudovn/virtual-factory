# VF-vNEXT-R2 — Canonical Same-Session Rich ASSY 2D Experience

Gate: `VF-vNEXT-R2` (implementation gate; SA amendment on Issue #80)
Issue: #80 (`https://github.com/hieudovn/virtual-factory/issues/80`) · SA amendment comment `5629686166`
Architecture authority: R0 / Issue #78 (CLOSED — frozen, not reinterpreted)
Status: READY FOR SA REVIEW

---

## 1. Identity

| Item | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/vf-vnext-r2` |
| Exact technical base SHA (branch point) | `4f866323fc73a1f73f6d513d5c91220d14a997b3` (R1-C01 head) |
| Harness `expected_base_sha` (origin/main) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (unchanged; no rebase) |
| Gate head | reported in the final status message (pushed head) |
| Task contract | `.ai-harness/tasks/VF-vNEXT-R2.json` |
| Harness preflight | PASSED |

## 2. What was implemented (one product-path TIPA authority)

| File | Change |
|---|---|
| `ui/assy_experience.py` | **NEW** `CanonicalAssyExperience`: same-session rich projection/control adapter. Frame A overview (six canonical sub-lines via the accepted `build_summary`/`AssyOverviewSnapshot` view models), Frame B detached `build_snapshot` projections with a canonical identity envelope, presentation-only sub-line selection, THIN same-session OPS-03/OPS-04 bindings (`submit_operation_command`, `submit_station_action`, per-line `global_run_mode`), explicit deferred seam, hold/freeze read model |
| `ui/workspace_monitor.py` | public `live_session(workspace_id)` seam (the ONE live session, shared with `/workspaces`), `tipa_config_path` property, and `_tipa_view_extra` corrected to same-session semantics (`shares_session: true`, `shares_identity: true`, canonical note) |
| `ui/api.py` | `/assy-demo` endpoints now served by the canonical experience; `_get_assy_controller()` / legacy controller authority **removed**; `/reset`, `/step`, `/snapshot`, `/select`, `/overview`, `/sub-lines`, `/sub-line/{id}`, `/identity` canonicalized (overview/sub-lines/sub-line now always registered); OPS-03/OPS-04 command + run-mode are thin same-session bindings; observation/MES/jam/recover/run-to-terminal/scenario-change fail closed as explicit deferred |
| `ui/static/assy_demo.js` | binding-only edits: canonical identity bar rendering, **no reset on page open**, reset/step send no scenario mutation, scenario selectors disabled as pinned run input, deferred responses surfaced (no fabricated state) |
| `ui/static/assy_demo.html` | canonical identity element added; scenario selectors statically disabled (pinned run input) |
| `tests/test_vnext_r2_same_session_rich_assy.py` | **NEW** 27 focused R2 tests |
| `tests/test_vnext_g24_workspace_ui.py`, `tests/test_vnext_g25_acceptance.py`, `tests/test_demo_overview.py` | legacy **ownership** assertions retired/migrated to the canonical same-session contract (SA amendment); accepted domain capability untouched |
| `.ai-harness/regression/vnext_baseline_manifest.json` | R2 gate context + `r2_same_session_rich_assy` group |

**Not touched:** `AssyLineRuntime`, federation/R1 production semantics, generic coordinator,
runcontrol lifecycle, SH-WTP, gateway, observation/MES bridges, PIM, continuous engine,
Frame A/B visual design/layout.

## 3. Acceptance evidence (deterministic artefacts in `evidence/VF-vNEXT-R2/`)

### A. Same-session identity — `01-same-session-identity.json`
Rich identity and shell view share `run_id`, `workspace_id`, `scenario_id`
(`tipa-default`), pinned `profile_id = tipa-assy-happy_path`;
`authority = canonical_tipa_runtime_session`.

### B. Frame A — `02-frame-a-overview.json`
Exactly `ASSY-SL01..ASSY-SL06` with scopes `TIPA/ASSY/<id>`; after five canonical
steps every row is live (`t = 600 s`, 6 WIPs on line, 1 motor each), totals
`6 created / 0 released`, `demo_step_number = 5` (canonical step count),
`scenario = tipa-default`.

### C. Frame B physical truth — `03-frame-b-movement.json`
Accepted 12-position list in every frame; successive snapshots
`PRE-ASSY=SSO2-0002 / AP01=SSO2-0001` → `AP02` → `AP03` → `AP04` → `AP05=MTR-0001`
with genealogy `MTR-0001 ← (SSO2-0001, RSO2-0001)`; each rendered WIP id equals
`conveyor.wip_at(position)` on the canonical runtime.

### D. Inspector / quality / genealogy — `04-inspector-read-models.json`
23 snapshot read-model keys, 12 station contracts, active-operation and
quality-event read models present (detached projections of the same runtime).

### E. Control coherence — `05-selection-and-control.json`
Selection changes nothing but presentation (same run id, step count, totals);
rich STEP advances the shell session (both report the same time); rich RESET
keeps the same run id and returns all six lines to the fresh profile baseline
(`t = 0`, 0 motors).

### F. Held-one / five-continue on the UI — `06-held-one-five-continue.json`
`ASSY-SL03` held: overview row frozen at `t = 120 s`, 0 motors, 2D projection
still the 120 s frame; the other five at `t = 720 s` with motors; hold read model
reports `held_sub_line_ids = ["ASSY-SL03"]`.

### G. Deferred fail-closed — `07-deferred-fail-closed.json`
`/observations`, `/mes-messages`, `/mes-trace` → **503** (`deferred_to: R3`);
`/jam`, `/recover`, `/run-to-terminal`, scenario-changing `/reset` → **409**
(`deferred_to: R4`); every payload states `legacy_runtime_authority: false`.

### H. No second runtime / no legacy authority — `08-no-second-runtime.json`
Across the whole rich path (overview, reset, step, snapshot, select, sub-lines,
run-mode, deferred): **1** canonical federation constructed, **0**
`DemoController` instantiations.

### I. Static binding facts — `09-static-ui-binding.json`
Rich page 200; canonical identity element present; three scenario selectors
disabled; no on-load reset remains in the JavaScript; deferred responses handled
in the UI.

### J. Migration of the legacy product-path suites
The accepted OPS-03/OPS-04 API behaviour suites now run against the canonical
session through thin same-session bindings and remain green;
`tests/test_ops03_interaction.py` and `tests/test_ops04_c01.py` pass **without
modification**, which is direct evidence that accepted domain capability was
preserved while ownership moved. Only the superseded *ownership* assertions were
retired per the SA amendment (separate-legacy-runtime metadata in G24/G25;
feature-flag-gated Frame A/B route registration in `test_demo_overview.py`).

## 4. Regression (exact results)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests/test_vnext_r2_same_session_rich_assy.py` | **27 passed** |
| `python -m pytest -q -p no:cacheprovider tests` (full repository suite) | **2556 passed** (2529 pre-R2 + 27 R2) |
| `python .ai-harness/regression/run_vnext_baseline.py` (complete canonical baseline) | **PASS at the pushed head** (39 groups incl. `r2_same_session_rich_assy`, `r1_production_semantics`, `g22_session_replay`, `g25_acceptance`, `full_suite`, `checks_*`) |

R1 production/profile/scenario/isolation/lifecycle tests remain green, as does
the ASSY domain/demo oracle inside the full suite.

## 5. Explicit non-work statement

No R3 Observation/MES/output reintegration (the endpoints are deferred, not
rewired), no gateway/OPC/MQTT/Kafka/REST work, no SH-WTP work, no
`AssyLineRuntime` rewrite, no scenario/lifecycle redesign, no general legacy
simulator consolidation or deletion, no broad visual redesign, no rebase onto
repository `main`. **R3 was not started.**

## 6. Authority (unchanged)

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## 7. Evidence index

```
.ai-harness/sa-review/evidence/VF-vNEXT-R2/
  01-same-session-identity.json      rich UI == shell canonical session
  02-frame-a-overview.json           six canonical sub-lines, live
  03-frame-b-movement.json           2D positions[] + WIP movement + AP04 genealogy
  04-inspector-read-models.json      station/operation/quality read models
  05-selection-and-control.json      selection presentation-only; STEP/RESET coherence
  06-held-one-five-continue.json     frozen line + five continuing (UI projection)
  07-deferred-fail-closed.json       R3/R4 deferred endpoints (failed closed)
  08-no-second-runtime.json          one federation, zero legacy controllers
  09-static-ui-binding.json          HTML/JS binding facts
  generate_evidence.py               deterministic generator (re-runnable)
```

## 8. Gate status

`VF-vNEXT-R2 — READY FOR SA REVIEW`. No PR opened, nothing merged, no next gate
started.
