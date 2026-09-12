# VF-vNEXT-R5 — Single Simulation System Consolidation + Shared VF Shell

**Machine-derived status: `BLOCKED FOR SA`**
(not READY, not COMPLETE, not CLOSED, not SA APPROVED, no next slice authorized)

| Field | Value |
| --- | --- |
| Gate | VF-vNEXT-R5 (Issue #84) |
| Gate type | IMPLEMENTATION gate; executed as **audit-level gate** — the consolidation could not be completed without an SA decision, so **no product code was changed** |
| Branch | `feature/vf-vnext-r5` |
| Branch point (technical base) | `989deac2fe189e7e66c89d2c33218004e2b7d08c` (R4 head) |
| `expected_base_sha` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (= `origin/main`) |
| Task contract | `.ai-harness/tasks/VF-vNEXT-R5.json` |
| Harness preflight | PASSED (see execution log) |
| Changed files | `.ai-harness/**` only (contract, evidence, report, status); **`src/` and `tests/` untouched** |
| Verdict | `BLOCKED FOR SA` — two stop conditions of the R5 contract were triggered by measurement |

---

## 1. Why this gate is BLOCKED rather than READY

The R5 contract requires that **no active product route may create simulation state except
through the canonical Workspace / RuntimeSession path**, and it defines an explicit STOP
condition: *if de-authorizing a competing authority would lose a proven capability that has
no canonical equivalent, or if consolidation requires a product-surface decision beyond a
bounded correction → `VF-vNEXT-R5 — BLOCKED FOR SA`.*

Measurement shows **two live competing authorities that cannot be de-authorized inside a
bounded R5 correction**:

| # | Authority | Construction site | Active product surface | Canonical replacement today |
| --- | --- | --- | --- | --- |
| 1 | `ROOT_DASHBOARD_RUNTIME_SERVICE` | `src/virtual_factory/ui/api.py:29` (eager, at `create_app()`) | 19 routes (`/`, `/status`, `/telemetry/*`, `/alarms`, `/step`, `/run-steps`, `/start`, `/stop`, `/reset`, `/ws/telemetry`, `/api/plant-graph`, `/api/model-types`, `/api/fault`, `/api/opcua/status`, `/api/ai/*`, `/api/config/*`, `/api/ui/*`) | **NONE** |
| 2 | `LEGACY_G7_RUN_CONTROL_SERVICE` | `api.py:813` (TIPA) and `api.py:846` (continuous), plus a second per-attempt `RuntimeService` at `api.py:829` | 11 `/vnext/runs*` routes | **Partial** (TIPA has one; continuous has none) |
| 3 | `LEGACY_DEMO_ASSY_MES_CONTROLLER` | `api.py:245` (`DemoController(DemoRunner())`) | 9 `/demo-assy-mes*` routes | **YES** (canonical rich ASSY `/assy-demo/*`) → this one is de-authorizable and is **not** a blocker |

### Blocker 1 — continuous-process dashboard authority (no canonical equivalent)

Measured: `build_platform_registry()` exposes exactly **two** workspaces — `["TIPA", "shwtp"]`;
`continuous_workspace_registered = false`. The capability behind the dashboard routes (plant
config load/switch, continuous run/step/reset, telemetry history, alarms, websocket streaming,
MQTT/OPC-UA status, AI endpoints, UI context) therefore has **no canonical Workspace /
RuntimeSession home**. The authority is an app-level singleton created before any request and
reused by every dashboard route, so it owns simulation state independently of any run-id
authority.

Consequences (pick one, they are mutually exclusive):
- de-authorize the dashboard → the entire MVP-01 continuous-process interactive product
  surface stops working (proven capability, no canonical replacement) → **capability loss**;
- consolidate the dashboard onto the canonical path → a **third canonical workspace
  (`continuous`) must be registered and exposed as user-selectable**, `create_app` /
  `WorkspaceMonitor` must carry the continuous config/dt/mqtt/opcua inputs, and accepted
  G23/G24/G25 + root-dashboard expectations must be migrated → **product-surface decision
  beyond a bounded correction**.

### Blocker 2 — legacy G7 run-control family (split authority, one safe half, one unsafe half)

The 11 `/vnext/runs*` routes funnel through `_vnext_service()` → `_get_run_control_service()`,
which builds **its own** `RunLifecycleService` per discriminator (measured: 2 services
constructed on first touch, `TIPA` + `continuous`):

- **TIPA discriminator (duplicate authority, unsafe-in-the-opposite-sense):** it calls
  `TipaAssyFederation.initialize()` **without a run profile**. It can therefore never be
  equivalent to the canonical prepared TIPA authority; it is a second, *semantically
  divergent* TIPA lifecycle authority. De-authorizing it loses nothing proven →
  **de-authorizable** (recommended split, see §5).
- **continuous discriminator:** it is the *only* run/replay orchestration surface of the
  continuous product, and it is itself a second continuous authority next to Blocker 1.
  It cannot be de-authorized before the continuous-workspace decision is made.

### Finding D — the R5 attempt-binding requirement is currently VIOLATED (measured)

`build_tipa_scenario_run_factory` (`src/virtual_factory/runcontrol/session.py`) mutates a
single module-closure `holder["profile"]` in `factory()` while the **zero-arg**
`bridge_factory()` reads it, and `RunLifecycleService._bridge_for()` calls that zero-arg
factory. The binding is therefore **order-dependent, not attempt-bound**.

Measured, on the canonical seam, with a legal lifecycle sequence:

```
A = factory("tipa-default")       # profile tipa-assy-happy_path
A.advance(); A.stop()
B = factory("tipa-failed-final")  # profile tipa-assy-failed_final
B.advance(); B.stop()
A.replay(); A.advance()
  -> session_a.profile_id (canonical context)   = tipa-assy-happy_path
  -> TipaAssyFederation.initialize(run_profile) = tipa-assy-failed_final   <<< CONTAMINATION
```

**Proof: a replayed attempt of the `tipa-default` run builds its federation from the
`tipa-failed-final` profile** (`violations: 1`, `verdict: ATTEMPT_BINDING_UNBOUND`). The
ordinary *select → run* flow is accidentally correct because the shared
`RunLifecycleService` admits at most one nonterminal run
(`RunLifecycleError: cannot create a new run while active run ... is nonterminal`), so the
most recently created session happens to agree with the holder. This contradicts the R4
factory contract ("using that run's pinned scenario profile … no hidden state carry-over")
and the R5 requirement to prove **no cross-run profile contamination**.

---

## 2. Evidence produced (all machine-generated, repo-native)

Generator: `.ai-harness/sa-review/evidence/VF-vNEXT-R5/generate_evidence.py`
(static scan of `src/**` + `tests/**`, route→authority parse of `ui/api.py`, instrumented
construction counters over live FastAPI routes, and the attempt-binding probe).

| Artefact | Content |
| --- | --- |
| `01-architecture-inventory.json` | 21 production construction sites, four-way classified; 6 of them on the active product path (all in `ui/api.py`); 589 test/reference construction sites recorded as counts only; full 67-route → authority map; registry inventory |
| `02-product-path-construction-proof.json` | per-phase construction counters + request statuses; attempt-binding scenes |
| `03-blocker-analysis.json` | blockers, options, unblocked subset, authority statements |

### Classification summary (deliverable A)

| Classification | Sites (production) | Examples |
| --- | --- | --- |
| `CANONICAL_SESSION_REGISTRY_AUTHORITY_KEEP` | 9 | `runcontrol/session.py` (session + scenario-run factories), `shwtp/session.py`, `ui/workspace_monitor.py` registry factories |
| `KEEP_AS_EXECUTION_KERNEL_OR_DOMAIN_LIBRARY` | 3 | `core/engine_factory.py:83`, `discrete/run_service.py:107` (engine construction inside the execution kernel) |
| `KEEP_AS_TEST_REFERENCE_ONLY` | 3 | `assembly/demo_controller.py:86`, `assembly/assy_mes_bridge.py:1481` demo smoke, `demo_assy_mes/__main__.py:36` CLI |
| `DEPRECATE_REMOVE_ACTIVE_PRODUCT_REACHABILITY` | 6 | `ui/api.py:29` (root dashboard `RuntimeService`), `:245` (`DemoController` + `DemoRunner`), `:813`/`:829`/`:846` (legacy G7 TIPA + per-attempt continuous `RuntimeService` + legacy G7 continuous) |
| `DELETE_ONLY_IF_PROVEN_REDUNDANT` | 0 | nothing is deleted or proposed for deletion in this gate |

Total: 21 production sites; 589 test/reference construction sites recorded as counts only.

Route→authority map (67 non-static routes): canonical ASSY experience **20**,
root dashboard **19**, static page / no state **16**,
legacy demo ASSY-MES **9**, canonical workspace monitor **6**, legacy G7 run-control **11**
(3 direct + 8 via `_vnext_mutate`; the static parser attributes 3 to handlers, the rest to the shared helper).

### Product-path construction proof (deliverable B)

Driving every canonical route family on a fresh app
(`/workspaces`, `/vnext/workspaces`, `/vnext/workspaces/{TIPA,shwtp}/view`,
`/assy-demo/reset|step×2|overview|sub-lines|identity|oee|snapshot|mes-messages`, all HTTP 200):

```
RuntimeSession        = 2   (TIPA = 1, shwtp = 1)
RunLifecycleService   = 2   (one per canonical workspace)
TipaAssyFederation    = 1
DemoController        = 0
RuntimeService        = 0
verdict: CANONICAL_PRODUCT_PATH_IS_SINGLE_AUTHORITY
```

`create_app()` itself constructs `RuntimeService = 1` (eager, blocker 1). Touching the
non-canonical families constructs exactly what the audit claims: legacy demo → 1
`DemoController` + 1 `DemoRunner`; legacy G7 → 2 `RunLifecycleService` (TIPA + continuous).

---

## 3. What was NOT executed (and is not claimed)

- **No consolidation code was written.** A partial migration would leave an unreviewable
  half-migrated product path; the decisive blocker is a scope/product-surface decision, so
  the gate stops at the audit per the contract's STOP clause.
- **No `src/` or `tests/` file was modified** — the changed-file set is `.ai-harness/**`
  (contract, evidence, report, status/manifest).
- Deliberately not started: SH-WTP functional/whole-plant expansion (I2 explicitly not
  authorized), gateway/OPC/MQTT/Kafka production work, PIM/MES repo changes, generic
  G4/coupling redesign, broad G22 run-identity redesign, ASSY visual simplification,
  `AssyLineRuntime` rewrite, any deletion of proven domain capability.
- No merge, no push to `main`. PR is opened for review only.

---

## 4. Recommended unblocked subset (ready to execute once SA decides)

| ID | Work | Risk |
| --- | --- | --- |
| R5a-1 | **Attempt-binding fix:** make the lifecycle bridge construction context-aware (`_bridge_for()` passes the attempt's `RunContextV2`; TIPA factory resolves the profile from `record.context.scenario_id` instead of the mutable holder), removing cross-run profile contamination. Add regression: A→B→replay/new_attempt must use each attempt's own profile. | low, bounded |
| R5a-2 | **De-authorize `/demo-assy-mes/*`** (9 routes): fail closed with an explicit deprecation response; keep the module as reference/test-only. | low |
| R5a-3 | **De-authorize the duplicate TIPA discriminator** of `/vnext/runs*` (fail closed with canonical guidance: the canonical TIPA authority is `/assy-demo/*` + `/vnext/workspaces/TIPA/*`). Keep the continuous discriminator pending Blocker 1. | low/medium (public API split needs SA ratification) |
| R5a-4 | **Bounded shared-shell convergence:** I1 (scenario/new-run control on the canonical `WorkspaceMonitor.new_run` seam), I3 (responsive scope table), I4 (single unavailable-action convention), I5 (compact shared glossary), I6 (remove the unused G7 `run_control_context.js` include from the canonical ASSY page). | low |
| R5a-5 | **Single-system firewall test module:** static import scan of active product UI for legacy authorities + dynamic per-route construction counters (one session per workspace, TIPA = 1 session/1 federation/6 runtimes, zero legacy constructions). | low |
| R5a-6 | **Regression:** focused R5 suite + R1–R4 + canonical baseline + full suite at the pushed head. | as usual |

---

## 5. SA decision required

**Question:** how must the continuous-process product (MVP-01 plant dashboard) be
consolidated onto the canonical Workspace/RuntimeSession path?

1. **OPTION 1 (recommended) — register `continuous` as a third canonical workspace.**
   Canonical session factory (`RunLifecycleService` + `ContinuousExecutionBridge` over a
   per-attempt `RuntimeService`, reusing the accepted C03 attempt-isolation pattern); root
   dashboard routes rewired to that canonical session; the G7 continuous discriminator
   retired; new run-id authority shared with the registry. *No capability lost.* Requires
   SA authorization because it changes the product surface (3 workspaces, shell selector,
   `create_app`/`WorkspaceMonitor` inputs, migration of accepted G23/G24/G25 and
   root-dashboard expectations).
2. **OPTION 2 — deprecate the dashboard state routes.** Bounded, but the MVP-01 continuous
   interactive surface (run/step/reset + live telemetry/alarms/websocket) is lost with no
   canonical replacement.
3. **OPTION 3 — governance scope amendment.** The SA explicitly scopes the R5 firewall to
   workspace-platform product paths and classifies the continuous dashboard + legacy G7
   run-control as frozen non-workspace legacy surfaces. *No capability lost*, but the
   "no competing authority behind any active product route" requirement must be amended.

R5a-1 (proven contamination) and R5a-2/R5a-3-TIPA/R5a-4/R5a-5/R5a-6 are independent of this
decision and can be authorized immediately in a bounded follow-up gate.

---

## 6. Regression at this head

- No executable source changed → all R1–R4 behaviour carries over unchanged from the R4 head
  `989deac` (42/42 baseline groups, full suite **2625 passed**).
- R5-head canonical baseline (42 groups; `gate.task_contract = .ai-harness/tasks/VF-vNEXT-R5.json`,
  `gate.changed_files_base = 989deac…`): **PASSED** — see `CURRENT.md` for the machine-derived
  line (`BASELINE PASSED: all required groups green`, `failed_groups: []`), including
  `checks_preflight` and `checks_changed_files`.
- No new baseline group is added in this gate (no new pytest module exists; audit-only gate).

---

## 7. Authority (unchanged, restated)

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

Nothing in this gate authorizes runtime execution against a real site, physical assets,
OPC-UA/MQTT production endpoints, or whole-plant scope. The SA AI remains the sole authority
for COMPLETE / CLOSED / SA APPROVED / NEXT SLICE AUTHORIZED statements.

**STOP — awaiting SA decision on §5 before any consolidation code is written.**
