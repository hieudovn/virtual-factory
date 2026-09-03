# VF-ARCH-04 · Evidence 04 — Decision C: Floating Simulation Control

## 1. Decision statement

**The Floating Simulation Control is the one shared, minimal, context-aware
run-control primitive. It exposes only run control; it never hosts scenario
editing, replay, domain process controls, or plant-control actions.**

## 2. Baseline control set (minimal, frozen)

| Control | Semantics (from ARCH-02) | State visibility |
|---|---|---|
| Time | current simulation time of the active run | always visible when a run is selected |
| Run / Pause | start or pause the active run in the active scope | enabled only when permitted by scope/run state |
| Step | advance exactly one discrete step | enabled only when the runtime supports stepping |
| Reset | reset the active scope's run state to baseline | enabled only when permitted |
| Speed | run-time rate factor (where supported) | enabled only when supported by the runtime |
| (optional) compact run/scenario context | read-mostly label of selected run/scenario + its state | always |

Hard boundary — the Floating Control **must never** contain:
- scenario editor,
- replay/checkpoint editor,
- domain process controls (e.g., jam a station, run-to-terminal, station-action),
- plant-control / operational actions.

Those belong to the **domain content region** (Domain UX) or are deferred.

## 3. Context-awareness

The Floating Control is **bound to the active scope and active run**:

- It operates on the **selected scope** (the scope in the current structural
  context), never on an unspecified "global" runtime.
- The target context is always visible in the control (which scope/run the
  buttons act on).
- Switching scope re-binds the control to the new scope's runtime; it does not
  leak commands across scopes.
- All commands route through **ARCH-02 declared interfaces** — the UI never
  mutates another scope's runtime state directly.

## 4. State-driven enablement (from ARCH-02/ARCH-03)

| Runtime/scope state | Control behavior |
|---|---|
| `running` | Run→Pause enabled; Step/Reset disabled or confirm-gated |
| `paused` | Run/Step/Reset enabled |
| `stopped` / `idle` | Run/Step enabled; Reset enabled |
| `not_ready` / `required-missing` | controls disabled with explicit blocker reason (never silently hidden) |
| `restricted` | controls visible within permitted limits (e.g., Step only) |
| container-only scope (`not_applicable` execution) | control hidden or shown inert with "container scope — no executable runtime" |
| no run selected | control shows "no run selected"; Run disabled until a run/scenario is selected |

## 5. What it is NOT

- Not a scenario manager (selecting a run/scenario is context, editing is not).
- Not a replay/checkpoint editor.
- Not a global "God control" over all scopes at once.
- Not the place for domain station operations (`jam`, `recover`,
  `run-to-terminal`, `station-action` remain domain UX, evidence 08).

## 6. Mapping to current repo

| Frozen concept | Current precedent | Classification |
|---|---|---|
| Run/Pause/Step/Reset/Speed | `index.html` `/start`, `/stop`, `/step`, `/reset`, `/run-steps` | **G → R** (today unscoped; vNext scoped) |
| Step/reset in domain UX | `assy_demo.html` reset/step; `/assy-demo/step`, `/assy-demo/reset`, `/assy-demo/run-to-terminal` | **D** — domain run actions stay in the ASSY content region |
| Compact run/scenario context | `assy_demo.html` `demo-step` + `HAPPY_PATH` badge | **X → R concept** (context strip, not demo values) |
| Domain controls excluded from shell | `/assy-demo/jam`, `/recover`, `/station-action`, `/operation-command` | **D** — proof that domain controls exist and must stay out of the Floating Control |

The existing separation (generic run controls vs ASSY domain controls) is the
concrete precedent for the frozen boundary: **run control is a platform
primitive; domain operation is domain UX.**

## 7. Minimality test

- Contains only run-control primitives + compact context: **yes**.
- Contains no editor/domain/plant controls: **yes** (explicitly excluded).
- Bound to one scope/run with visible target: **yes**.

**Decision C is explicit and minimal.**
