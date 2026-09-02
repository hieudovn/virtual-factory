# VF-ARCH-01 — Freeze platform structural model

> **C01 revision (Issue #40 correction):** (1) `Simulation Scope` semantics made
> consistent — every scope is a structural/addressable boundary; `executability`
> is a capability, not a type default; container-only scopes are valid; the
> standalone/federated contract applies only to executable-capable scopes.
> (2) `Workspace` no longer implies a single engine — deployment/identity/config/
> composition boundary; legacy `runtime.engine` is a compatibility/default/profile
> field. (3) `AssyDemoComposition` downgraded to a reusable composition
> pattern/precedent (vNext TIPA→ASSY federation remains an implementation
> target). (4) Migration dispositions are candidate directions only; final
> disposition deferred to later gates.

| Field | Value |
|---|---|
| Task ID | `VF-ARCH-01` (GitHub Issue #40) + C01 |
| Parent | Issue #39 `VF-vNEXT-ARCH` (umbrella architecture program) |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Architecture / design gate — documentation & evidence only (no production implementation) |
| Canonical baseline | `main` @ `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Production code changed | **NO** (only `.ai-harness/`) |
| ARCH-02 started | **NO** |

## 1. Objective

Freeze the structural model for all later vNext work:

```
VF Platform → Workspace → Simulation Scope → Simulation Object
```

with tree-like management/navigation hierarchy, graph-based connectivity, and
standalone/federated execution of a scope.

## 2. Repo-first discovery (evidence 01)

Verified at baseline:

- **TIPA ASSY identity hierarchy** (`assembly/sub_line_identity.py`): TIPA
  Plant → ASSY Production Line → ASSY-SL01..06 (hydraulic/thermal). Anti-flattening
  language already frozen.
- **`AssyDemoComposition`** (`assembly/demo_composition.py`): six
  `AssyDemoContext`s, each wrapping one `AssyLineRuntime`; isolated per-context
  state; `selected_sub_line_id`; demo feed policy only.
- **Generic runtime/config abstractions** (`core/`, `discrete/`): flat
  `PlantConfig` + `PlantGraph` + `RuntimeAssembly` + `SimulationEngine`;
  discrete-event kernel. **No production Workspace/Scope/`workspace_id` exists**
  (only PH00 §06 proposal) → no competing hierarchy abstraction.
- **UI context/sub-line selection** (`ui/static/assy_demo.js`, `ui/api.py`):
  presentation selector over the composition, not identity authority.
- **Accepted evidence/docs**: PH00 §06 (workspace fields + 3-distinct-identity
  invariant), PH00 §13 (target architecture), PIM handoff (canonical semantic
  identity), `ARCHITECTURE.md` / `docs/design-principles.md` (config-driven,
  graph-based, port-based).

## 3. Frozen structural model (evidence 03–05)

Definitions are mutually exclusive with anti-definitions (evidence 02):

- **Platform** — the product: shared kernels + domain models + gateways + the
  structural contract.
- **Workspace** — top-level deployment/identity/configuration/composition
  boundary (TIPA, SH-WTP, …); no single-engine implication (child scopes may
  use different mechanisms; legacy `runtime.engine` = compatibility/default/profile).
- **Simulation Scope** — nested structural/addressable simulation boundary; may
  be **executable** (runtime/execution boundary) or **container-only** (groups
  child scopes/objects); executability is a capability, not a default.
- **Simulation Object** — leaf runtime entity (station, WIP, carrier, pump,
  valve, tank, …).
- **Archetype** (`continuous`/`batch`/`discrete`) is a label, not an engine;
  **execution mechanisms** (tick solver, discrete-event, state-machine) are
  composable.

Identity invariants (evidence 03): `workspace_id` / `scope_id` / scope path /
object identity are VF structural identity, **separate** from `outputs.namespace`
and from PIM canonical ids. Child scope id is unique within its parent boundary.

Hierarchy vs graph (evidence 04): containment is a **tree** (one parent);
connectivity/dependency is a **graph** (many edges). A scope has one containment
parent and many graph relationships.

Standalone vs federated (evidence 04): for **executable scopes**, same domain
runtime in both modes; parent supplies host/composition context only; child
keeps its own runtime/config boundary; parent is not child domain authority.
`AssyLineRuntime` is **not redesigned**. `AssyDemoComposition` is a reusable
composition pattern/precedent, not a completed vNext TIPA→ASSY federation.

## 4. Reference mappings (evidence 05)

- **TIPA (verified, lossless):** TIPA Workspace → ASSY Scope → ASSY-SL01..06
  child Scopes → AP01..06 / SSO2 / RSO2 / carrier / WIP / sink Objects.
- **SH WTP (conceptual, no invented topology):** SH-WTP Workspace → process
  area/unit Scopes (illustrative) → equipment Objects. Same structural model,
  no special-case architecture.

## 5. Migration impact (evidence 06)

Candidate directions only (final disposition deferred): `AssyLineRuntime` is a
reuse target (not redesigned — frozen intent); `sub_line_identity` + `core/` +
`discrete/` are candidates for reuse; `AssyDemoComposition` is a reference
pattern/precedent; `build_tipa_topology()` and `simulators/wtp`/`vf2` are
retained as legacy/reference. No refactor here.

## 6. STOP-condition assessment

| Stop condition | Result |
|---|---|
| ASSY semantics cannot map without breaking domain behavior | NOT triggered (lossless) |
| Competing generic hierarchy abstraction in repo | NOT triggered (none in `src/`) |
| Scope identity not separable from PIM id / output namespace | NOT triggered (3 axes) |
| Standalone/federated requires domain-runtime rewrite | NOT triggered (reusable composition pattern exists; no rewrite required) |
| Requires ARCH-02 runtime sync/port semantics prematurely | NOT triggered (deferred) |

**Conclusion: no STOP condition triggered.**

## 7. Acceptance

| Criterion | Result |
|---|---|
| Definitions mutually exclusive and sufficient | PASS (evidence 02) |
| TIPA/ASSY maps cleanly without flattening/rewrite | PASS (evidence 05) |
| SH WTP maps conceptually, no special-case rules | PASS (evidence 05) |
| Hierarchy vs graph explicit | PASS (evidence 04) |
| Standalone/federated explicit | PASS (evidence 04) |
| Identity boundaries explicit | PASS (evidence 03) |
| Archetype vs execution mechanism explicit | PASS (evidence 05) |
| Later-gate implementation deferred | PASS (evidence 06 §6.3) |
| No production code changed | PASS (only `.ai-harness/`) |

## 8. Evidence

`.ai-harness/sa-review/evidence/VF-ARCH-01/` — 6 files (01…06).

## 9. Final status

```text
VF-ARCH-01-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. ARCH-02 is NOT started; all
implementation non-decisions remain deferred.
