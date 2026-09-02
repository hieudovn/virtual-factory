# 06 — Hybrid Archetype Execution & ASSY Mapping (Issue #41 §I, §J)

## 6.1 Hybrid archetype composition (conceptual; no one forced engine)

The contract coordinates mixed scopes by treating each scope as an independent
executable that the coordinator advances/exchanges at boundaries — regardless of
internal mechanism:

| Pairing | How it maps under the contract |
|---|---|
| Continuous + Continuous | Two tick scopes, possibly different `dt_s`; synchronized at declared exchange boundaries. |
| Discrete + Discrete | Two event-scheduler scopes; coordinator sequences declared events at coordination points. |
| Continuous + Discrete | Mixed cadences; coordinator uses `common_advance` or `exchange_barrier`; no shared timestep/scheduler required. |
| Batch / state-machine + Continuous | State-machine scope advances phases; continuous scope advances ticks; exchange only at declared boundaries. |

No shared engine implementation is implied. Illustrative examples only; no
site-specific SH WTP process truth is invented.

## 6.2 ASSY reference mapping (demo vs platform distinction)

**Precedent (reusable, from repo):**

- Six isolated `AssyLineRuntime` child contexts under one `AssyDemoComposition`
  = strong precedent for "N executable scopes coordinated by one composition
  context".
- Each context owns its runtime state; composition coordinates via
  `step_context()` without reaching into domain internals.
- `common_advance` policy (`COMMON_DEMO_CLOCK`) with no equal-sim-time assertion
  = evidence for time-invariant #4.

**Demo-only (not frozen plant truth):**

- `ContinuousFeedPolicy` (SSO2/RSO2 replenishment targets) — demo policy.
- `SCENARIO_TARGET_DEFAULTS`, `SCENARIO_QUALITY_OVERRIDES` — demo policy.
- `selected_sub_line_id`, `demo_step_number` — presentation/view state.
- `step_all()` iteration order and fault-exclusion — demo orchestration policy.

**Future fit (not implemented here):** `TIPA Workspace → ASSY Scope →
ASSY-SL01..06 child Scopes` fits the frozen contract without rewriting
`AssyLineRuntime`: each sub-line becomes an executable scope wrapping the same
runtime; the ASSY scope is a parent scope (or coordinator) supplying composition
context. `AssyLineRuntime` is **not rewritten**.

> No TIPA federation implementation is performed in this gate.

## 6.3 Anti-risks checked

- Coordinator as God Engine → prevented (anti-responsibilities §05).
- One workspace = one engine → prevented (ARCH-01/C01 Workspace definition + §K).
- Forcing identical timesteps → prevented (time invariant §04).
- Wall-clock/UI speed vs synchronization → separated (§04).
- Direct cross-scope mutation → prevented (§05.4).
- Ports duplicating PIM semantic authority → prevented (boundary uses structural identity).
- Ports coupled to UI routes/labels → prevented (§05.3).
- Nondeterministic ordering (dict/set/hash/time-of-day) → prevented (§04.2).
- ASSY demo orchestration treated as plant truth → prevented (§06.2).
- Second runtime path diverging from standalone ASSY semantics → prevented (same `AssyLineRuntime`).
- Premature Observation/Monitoring mixing into runtime truth → prevented (§05.2 + data-flow direction preserved).
