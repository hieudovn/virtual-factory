# VF-ARCH-04 · Evidence 08 — Decisions H, I, J: Capability-driven UI, health/readiness presentation, action authority

## 1. Decision H — Capability-driven UI behavior

**Capability state is the single authority that drives UI visibility,
enablement and transparency. UI composition is never hard-coded by workspace
name, route string, or archetype label.**

### 1.1 State → UI behavior matrix (frozen)

| Capability state | UI composition | Enablement | Transparency |
|---|---|---|---|
| `available` | shown | enabled | normal |
| `not_applicable` | **omitted or N/A** (never a fake empty panel) | disabled/absent | reason shown when N/A |
| `not_ready` | shown | disabled | explicit blocker reason |
| `restricted` | shown | enabled within limits | limits shown |
| `degraded` | shown | enabled | degraded styling + reason |
| `error` | shown | disabled | unavailable + error reason |
| `required-missing` | shown | disabled | **explicit blocker** (never silently omitted) |

### 1.2 Rules

- `not_applicable` ≠ `not_ready`: `not_applicable` is declaratively irrelevant
  (omitted/N/A); `not_ready` is relevant-but-not-usable (visible + blocker).
- `required-missing` is a **derived `not_ready`** (ARCH-03): a required
  capability that is absent is an explicit blocker — the UI must show it, never
  hide it.
- Capability state authority = the **declared provider/contract owner** (ARCH-03
  C01); the UI observes it, never invents or upgrades it.
- No `if workspace_name == "TIPA"` / `"SH WTP"` conditionals anywhere.

## 2. Decision I — Health/readiness presentation contract

**The UI may display readiness and capability state, show blockers, and
navigate to the source of a blocker. It may NOT invent a score, upgrade a
state, hide a blocker, or become an evaluator.**

### 2.1 Allowed

- Display readiness as the **deterministic categorical aggregation** from
  ARCH-03 (e.g., READY / NOT_READY / DEGRADED with the contributing blockers).
- Show **which** capability/binding/runtime/child-scope is blocking.
- Link from a blocker to the object/scope that declares it (navigate to source).
- Show capability state honestly per the H matrix.

### 2.2 Forbidden

- No arbitrary health score (no invented 0–100).
- No UI-side upgrade of readiness or capability state.
- No hiding of `not_ready`/`required-missing` to look better.
- No competing evaluator — readiness remains ARCH-03 aggregation; the UI is a
  faithful projector.
- No "hidden blocker" convenience toggle that suppresses required-missing.

### 2.3 Container scope

A container-only scope shows **structural/composition readiness** (may be READY)
and **execution readiness = `not_applicable`** (ARCH-03 C01). The UI must not
present a container as executable.

## 3. Decision J — Action authority model

**Every user-facing action carries an explicit authority label. Current VF
never implies real plant-control authority.**

### 3.1 Authority classes (frozen)

| Class | Meaning | Current VF examples |
|---|---|---|
| **simulation** | mutates the simulated environment / injected conditions (part of running the simulation) | `/api/fault` (inject simulated fault) |
| **runtime-model** | mutates the run/step/model state of the simulation runtime through ARCH-02 interfaces | `/start`, `/stop`, `/step`, `/reset`; `/assy-demo/station-action`, `/operation-command`, `/jam`, `/recover`, `/run-mode` |
| **plant-operational** | would actuate a real physical plant/equipment | **none today** |

### 3.2 Rules

- Actions are **labeled** by authority class; simulation actions must not look
  like plant control, and runtime-model actions must not look like plant
  actuation.
- No action routes around ARCH-02 declared interfaces; UI/API clients never
  directly mutate another scope's runtime state.
- Plant-operational actions are **not implemented** and must not be implied;
  deciding real plant-control authority is deferred (non-decision).
- Domain process controls (station ops, process setpoints, phase advance) stay
  in the domain content region, not the Floating Control.

## 4. Mapping to current repo

| Frozen concept | Current precedent |
|---|---|
| Capability-driven, no hard-code | `assy_demo.js` OPS-03 "Operation Inspector binding (capability-driven, no AP hard-code)" |
| Simulation vs runtime-model actions | `/api/fault` (simulation) vs `/start`/`/stop`/`/step`/`/reset` + `/assy-demo/*` (runtime-model) |
| No plant control | no plant-control route exists |
| Readiness projection | (new) — consumed from ARCH-03 aggregation |

**Decisions H, I, J are explicit.** No second authority is invented: capability
state comes from the ARCH-03 provider; readiness from the ARCH-03 aggregation;
the UI is a faithful projector (H/I), and actions carry the authority label
that already exists in the repo (J).
