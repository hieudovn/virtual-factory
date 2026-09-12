# VF-vNEXT-R1 — Canonical TIPA Same-Session Production Semantics

Gate: `VF-vNEXT-R1` (implementation only)
Issue: #79 (`https://github.com/hieudovn/virtual-factory/issues/79`)
Architecture authority: R0 / Issue #78 (CLOSED — frozen; not reinterpreted)
Model: DeepSeek V4.1 Flash (task reasoning class HIGH)
Status: READY FOR SA REVIEW

---

## 0. Identity

| Item | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `feature/vf-vnext-r1` |
| Exact technical base SHA (branch point) | `ed217c867dff048ee3774d139e53b8cfb1130251` (G26 accepted head) |
| Harness `expected_base_sha` (origin/main) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (inspected; **not** merged, **not** rebased) |
| Gate head | see §7 (pushed gate head) |

No rebase onto repository `main` was performed. The default branch is not the
accepted vNext technical baseline and was used only for the harness preflight
comparison.

## 1. Objective (implementation only)

The selected canonical vNext TIPA `RuntimeSession` must execute the
already-accepted six-sub-line ASSY production semantics instead of advancing six
empty clocks, through the frozen truth chain:

```
TIPA RuntimeSession
 -> explicit immutable ASSY run profile / simulation inputs
 -> TipaAssyFederation
 -> exactly six isolated AssyLineRuntime instances
 -> G4 participant/coordinator execution
```

R1 is runtime/domain-run semantics only: **no** rich UI migration (R2), **no**
Observation/MES reintegration (R3), **no** SH-WTP/gateway work, **no**
`AssyLineRuntime` rewrite, **no** second runtime/controller/engine/lifecycle
authority.

## 2. Changed-file inventory

| File | Change |
|---|---|
| `src/virtual_factory/assembly/assy_run_profile.py` | **NEW** — immutable `AssyRunProfile` run INPUT, shared pure scenario/config helpers, shared `AssySubLineRunState`, shared production driver `step_prepared_line()` |
| `src/virtual_factory/assembly/demo_composition.py` | legacy accepted demo now delegates scenario mapping / config transforms / feed preparation / step driver to the shared helpers (public API and behaviour preserved) |
| `src/virtual_factory/assembly/__init__.py` | additive exports of the R1 profile seam |
| `src/virtual_factory/federation/assy_host.py` | `initialize(run_profile=...)` per-line preparation before runtime construction; `reset_sub_line()` profile-consistent re-preparation; run-state/scenario accessors |
| `src/virtual_factory/federation/assy_participant.py` | opt-in prepared-production step through the shared helper; unprepared mode keeps the frozen G5 structural step |
| `src/virtual_factory/runcontrol/assy_bridge.py` | ASSY-domain hold/freeze seam (held sub-lines excluded from the coordination window); profile-consistent reset; fail-closed all-held advance |
| `src/virtual_factory/runcontrol/session.py` | session `scenario_id` resolved to a pinned immutable ASSY run profile; profile id pinned in the run context |
| `tests/test_vnext_r1_production_semantics.py` | **NEW** — 39 focused R1 tests |
| `.ai-harness/tasks/VF-vNEXT-R1.json` | gate task contract |
| `.ai-harness/regression/vnext_baseline_manifest.json` | R1 gate context + `r1_production_semantics` group |
| `.ai-harness/sa-review/evidence/VF-vNEXT-R1/` | deterministic evidence generator + 8 JSON proof artefacts |
| `.ai-harness/sa-review/CURRENT.md` | SA review inbox → R1 |
| `.ai-harness/sa-review/reports/VF-vNEXT-R1.md` | this report |

No file outside the task-contract allowlist was modified; no forbidden path was
touched (`line_runtime.py`, `demo_controller.py`, `composition/`, `workspace/`,
`provenance/`, `shwtp/`, `ui/`, `configs/`, `docs/`, `deploy/`, `examples/` all
untouched).

## 3. Architecture-conformance note (no new design)

- The platform chain `WorkspaceRuntimeRegistry -> RuntimeSession ->
  RunLifecycleService -> ExecutionBridge -> G4 Coordinator -> participant
  adapter -> domain runtime` is unchanged. `RunLifecycleService`,
  `AssySubLineAdapter` (G4 participant seam), `TipaAssyFederation` and the G1
  structural workspace identity are reused as-is.
- `AssyLineRuntime` remains the authoritative ASSY domain truth and was **not**
  modified; all domain driving uses existing public operations only
  (`produce_sso2_wip`, `produce_rso2_wip`, `introduce_to_assy`,
  `execute_dwell`, `index_line`, `reset`).
- The run profile is run **INPUT**: immutable, re-resolved deterministically from
  the session `scenario_id`, owning no mutable truth and no lifecycle.
- The legacy `DemoController`/`AssyDemoComposition` were **not** made the runtime
  authority and were **not** deleted; they now delegate their pure
  domain-run-preparation semantics to the shared module so the two paths cannot
  diverge. No new controller/engine/session/scheduler/lifecycle was introduced.
- G4 stays domain-ignorant: the production driver lives behind the ASSY
  participant adapter; no SSO2/RSO2/AP/scenario logic was added to the
  coordinator.

## 4. Profile / input contract summary

`AssyRunProfile` (frozen dataclass, `version = "1"`,
`provenance = simulation_synthetic_profile_input`):

| Field | Meaning |
|---|---|
| `profile_id` | deterministic id, e.g. `tipa-assy-happy_path`, pinned in the run context |
| `session_scenario_id` | the canonical session `scenario_id` it resolved from (`tipa-default`) |
| `scenario` | accepted run scenario value (`HAPPY_PATH`, `AP06_FAIL_RETEST_PASS`, `AP08_NG_REINSPECT_PASS`, `FAILED_FINAL`) |
| `target_sub_line_id` | deterministic synthetic exception target (`""`, `ASSY-SL03`, `ASSY-SL02`) |
| `initial_sso2_inventory` / `initial_rso2_inventory` | explicit initial upstream preparation (7 / 7) |
| `continuous_feed_enabled`, `feed_policy` | bounded feed/replenishment settings (`sso2_target=10`, `sso2_low_watermark=3`, `rso2_target=6`) |
| `provenance` | simulation/synthetic marking — never site truth |

Resolution: canonical aliases (`tipa-default`, `tipa-happy-path`,
`tipa-ap06-retest`, `tipa-ap08-reinspect`, `tipa-failed-final`) or the raw
accepted scenario values (case-insensitive). **Unknown scenario ids fail closed
before any runtime construction.** `tipa-default` resolves to the accepted
HAPPY_PATH-style production profile — never an empty federation.

Per-line application (before runtime construction, into that line's own
deep-copied config): effective scenario (only the target line receives the
synthetic exception), accepted quality/config transforms, stable ordinal seed,
own run state (inventory + carrier/feed sequencing), own adapter.

Production driver (single shared implementation, used by both paths):
**replenish/prepare feed → on-demand RSO2 for AP04 → `execute_dwell()` →
`index_line()` only when `READY_TO_INDEX` → introduce next SSO2 through the
existing public entry.**

## 5. Proofs (evidence artefacts)

All artefacts are regenerated deterministically by
`.ai-harness/sa-review/evidence/VF-vNEXT-R1/generate_evidence.py`.

### 5.1 Non-empty production (A)

`02-production-progression.json` — canonical `tipa-default` session, all six
lines:

| step | sim time | dwell | wip count | motors | rso2 | occupied positions |
|---|---|---|---|---|---|---|
| 1 | 120 | 1 | 7 | 0 | 7 | PRE-ASSY=SSO2-0002, AP01=SSO2-0001 |
| 5 | 600 | 5 | 16 | 1 | 6 | PRE-ASSY…AP04 + AP05=MTR-0001 |

Hard guard satisfied: **no line is empty from the first meaningful step**
(`wip_count == 0` after meaningful stepping would be FAIL).

### 5.2 AP04 / genealogy (A)

Reached at **step 5 / t=600 s** through the selected session path:
`AP05 = MTR-0001`, genealogy `MTR-0001 <- (SSO2-0001, RSO2-0001)`, RSO2 buffer
7 → 6 (consumed by the join). Bounded run continues to release/LINE_OUT
(`MTR-0001`, `MTR-0002` released, `motor_count = 10` at step 16).

### 5.3 Six isolated runtimes (B)

`03-isolation.json`: 6 distinct runtime objects, 6 distinct config objects,
6 distinct run-state holders, 6 distinct adapters, 6 distinct seeds
(`base + ordinal`, identical across two independent initializations),
runtime type is exactly `AssyLineRuntime`; advancing one sub-line leaves the
other five byte-identical (`others_unchanged = true`).

### 5.4 Scenario targeting (C)

`04-scenario-targeting.json` (20 steps):

| session scenario | target | runtime evidence on the target line | non-target lines |
|---|---|---|---|
| `tipa-default` | — | all six: AP06/AP08 single PASS, released motors | identical |
| `tipa-ap06-retest` | ASSY-SL03 | `MTR-0002` AP06 = FAIL → PASS (2 attempts) | single PASS, unchanged |
| `tipa-ap08-reinspect` | ASSY-SL02 | `MTR-0002` AP08 = NG → PASS (2 attempts) | single PASS, unchanged |
| `tipa-failed-final` | ASSY-SL03 | `MTR-0001` AP06 = FAIL, FAIL → `failed_final`, no AP08/AP11, **no release** | normal release route |

Targeting is effective, not metadata-only: the per-line config carries the
transform and the runtime behaviour changes only on the accepted target line.

### 5.5 Held-one / five-continue (D)

`05-hold-freeze.json`: holding `ASSY-SL03` leaves it **identical** (t=120,
dwell=1, wip=7, no motors) across 5 parent advances, while `ASSY-SL01/02/04/05/06`
advance to t=720 with motors and remain mutually equivalent; releasing the line
lets it advance again (t=840 after the next window). No shared-state corruption.
The seam is a domain bridge capability only — no generic coordinator or
synchronization policy was added, and no AP05/UI/MES fault workflow was built.

### 5.6 Reset / new-attempt / replay (F)

`06-lifecycle.json`:

- **reset** — same `run_id`, profile-consistent re-prepared state (t=0, dwell=0,
  wip=7, rso2=7, no genealogy, run state re-seeded), and re-stepping 5 windows
  reproduces the pre-reset production state exactly.
- **new_attempt** — fresh `run_id`, same pinned profile, first step equal to a
  fresh session's first step (no hidden carry-over).
- **replay** — fresh `run_id`, bounded production state equivalent to the
  baseline after the same steps.

### 5.7 Determinism (E)

`07-determinism.json`: two fresh canonical sessions with identical profile/
config/scenario produce equivalent bounded domain summaries after the same 15
authorized steps (`equivalent = true`).

### 5.8 Shared semantics, no divergence

`08-parity-vs-accepted-demo.json`: the canonical session and the accepted legacy
demo composition produce **identical per-step domain state for 16/16 steps**
(simulation time, dwell, WIP count, motors, RSO2, physical occupancy), because
both now call the same shared helpers.

### 5.9 Frozen-invariant guards

- G4 exact-boundary/no-fractional-dwell unchanged (arbitrary/fractional targets
  still fail closed; natural boundaries land exactly on 120 s multiples).
- The plain production host contract is unchanged: `TipaAssyFederation(...)
  .initialize()` still yields six **unseeded** runtimes and exposes no demo-policy
  authority (existing G5-C01 guards remain green).
- No `AssyLineRuntime` rewrite; no second runtime authority under the session
  (no `DemoController`/`AssyDemoComposition` instance is created or hosted).

## 6. Regression (exact commands / results)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider tests/test_vnext_r1_production_semantics.py` | **39 passed** |
| `python -m pytest -q -p no:cacheprovider tests` (full repository suite) | **2528 passed** (2489 pre-R1 + 39 R1) |
| `python .ai-harness/regression/run_vnext_baseline.py` (complete canonical baseline) | **PASS at the pushed head** — all groups green including the new `r1_production_semantics`, `full_suite`, `checks_compile`, `checks_static_lint_type`, `checks_changed_files`, `checks_preflight` |

Targeted suites re-verified green during implementation include the G5 ASSY
federation/parity suite, G7 run control + ASSY bridge, demo composition, and the
G22/G23/G24/G25/G26 session/registry/shell/acceptance suites, plus the full ASSY
domain/demo regression oracle (part of the full suite).

The one transient issue found during development (legacy callers passing the
plain-string scenario value to `AssyDemoComposition`) was fixed by keeping the
accepted `str`-enum tolerance in the delegating helpers; the full suite is green.

## 7. Gate head / push status

Gate head SHA, remote branch head and working-tree state are reported in the
final status message (the baseline was run at the committed head; the same head
was pushed to `origin/feature/vf-vnext-r1` and verified equal to local HEAD).

## 8. Explicit non-work statement

**No R2, R3, SH-WTP or gateway work was started.** Specifically: no rich Frame A/B
UI migration, no `/assy-demo` repointing, no observation/MES/output
reintegration, no gateway/OPC/MQTT/Kafka/REST expansion, no SH-WTP domain or
runtime work, no legacy simulator consolidation or deletion, no new
architecture/roadmap, and no rebase onto repository `main`.

## 9. Authority (unchanged)

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

All scenario/quality/inventory values exercised here are simulation/synthetic
demo-scale inputs — **not** TIPA site truth.

## 10. Evidence index

```
.ai-harness/sa-review/evidence/VF-vNEXT-R1/
  01-run-profile.json              profile/input contract + accepted aliases
  02-production-progression.json   non-empty production + AP04/genealogy + release
  03-isolation.json                six isolated runtimes/configs/run-states/seeds
  04-scenario-targeting.json       effective per-line scenario + runtime evidence
  05-hold-freeze.json              held line unchanged, five continue
  06-lifecycle.json                reset / new-attempt / replay
  07-determinism.json              two fresh sessions equivalence
  08-parity-vs-accepted-demo.json  canonical vs legacy accepted demo equivalence
  generate_evidence.py             deterministic generator (re-runnable)
```

## 11. Gate status

`VF-vNEXT-R1 — READY FOR SA REVIEW`. No PR opened, nothing merged, no next gate
started. Awaiting SA disposition.
