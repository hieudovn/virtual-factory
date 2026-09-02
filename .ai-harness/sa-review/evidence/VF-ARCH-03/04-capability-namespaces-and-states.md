# 04 — Capability Namespaces & State Model (Issue #42 §E, §F)

## 4.1 Capability namespace model (conceptual; no workspace-name routing)

Three separated namespaces; examples are **illustrative**, not frozen product
routing:

| Namespace | Meaning | Illustrative examples |
|---|---|---|
| **Platform capability** | Cross-workspace platform services/contracts | `runtime.control`, `scenario`, `monitoring`, `events`, `provenance` |
| **Execution / domain capability** | Archetype/mechanism-level domain capability | `continuous.balance`, `discrete.routing`, `batch.recipe` |
| **Workspace / domain feature** | Workspace- or domain-specific feature | `shw.water_quality`, `tipa.ap06_retest` |

Anti-coupling rules:

1. Capability-driven behavior must **never** be hard-coded by workspace name.
   Repo precedent: ASSY station dispatch is capability-driven (station
   `Capabilities` flags + `line_runtime` C01-01 dispatch), **not** an
   `if workspace == "TIPA"` branch.
2. Namespaces are separated conceptually; a feature never masquerades as a
   platform capability and vice versa.
3. Capability identity is structural (namespace + capability key), independent of
   UI labels and workspace names.

## 4.2 Capability state model (frozen baseline)

| State | Meaning |
|---|---|
| `available` | Capability is present and usable for the current scope/run. |
| `not_applicable` | Capability does not apply to this scope/domain/archetype (not a failure). |
| `not_ready` | Capability is applicable but missing prerequisites (config/params/binding/readiness gap). |
| `restricted` | Capability is applicable but constrained (e.g. fidelity ceiling, policy, resource) — usable within declared limits. |
| `error/degraded` | Capability is applicable but currently failing or operating in degraded mode. |

### 4.2.1 `error` vs `degraded` (C01-style clarification)

`error` and `degraded` are **two distinguishable operational substates** of one
combined baseline class `error/degraded`:

- `error` = capability is failing / not usable (fault).
- `degraded` = capability is usable but at reduced capacity/fidelity.

Both map to the frozen baseline state `error/degraded`; distinguishing them is a
contract-level operational substate, not a new top-level capability state.

### 4.2.2 State semantics (explicit)

1. **Authority/owner:** each state is owned by the component that can observe it
   — platform capability states by the platform/runtime layer; execution/domain
   capability states by the scope runtime; workspace feature states by the
   workspace/domain configuration (all aggregated, never independently invented).
2. **Absent vs not-applicable vs not-ready:**
   - absent capability = not declared for the scope (no state to aggregate);
   - `not_applicable` = declared but irrelevant to this scope/domain;
   - `not_ready` = declared, applicable, but prerequisites missing.
3. **Failure/error vs configuration/readiness gap:** `error/degraded` is an
   operational fault; `not_ready` is a configuration/readiness gap. They are
   distinct and never conflated.
4. **No fabricated availability:** `available` is never claimed unless the
   prerequisites are actually satisfied. `not_ready`/missing capability is shown
   transparently; there is no silent fallback.
