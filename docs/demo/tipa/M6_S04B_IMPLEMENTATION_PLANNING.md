# M6-S04B-C02 — Implementation Planning (Single Source of Truth)

> **Status**: PLANNING C02 — single-source-of-truth + detail-consistency review.  
> **Baseline**: DG03 frozen at `cf20843`. C01 at `399e8fe`.  
> **Purpose**: Resolve dual-truth architecture, audit codebase for multi-instance safety, recommend final architecture.  
> **Rule**: Do NOT modify runtime. Do NOT implement UI. Do NOT reopen DG01–DG03. Do NOT start M6-S05.

---

## 1. Executive Recommendation

**Final architecture**: Option A — **6 × `AssyLineRuntime` logical execution contexts**, with a thin `AssyDemoComposition` layer for orchestration and `SubLineSummaryView` projections for overview.

**Why this changed from C01 (Option C → Option A)**:

| Factor | C01 (Option C) | C02 (Option A) |
|--------|---------------|----------------|
| Simulation truth | Two implementations (SubLineEngine + AssyLineRuntime) | **One** (AssyLineRuntime only) |
| Detail any lane | Not resolved — "promotion" undefined | **Immediate** — any sub-line has full runtime |
| Code volume | ~100 lines new engine + ~100 lines composition | ~60 lines composition + ~40 lines projection |
| Duplicate semantics | Yes — second mini-engine duplicates dwell/quality/occupancy | **None** |
| Regression risk | Medium — new engine may diverge | **Low** — tested runtime reused as-is |
| Fallback | Complex — two code paths | **Simple** — disable composition, keep 1 runtime |

---

## 2. Codebase Audit — Multi-Instance Safety

All 10 audit points confirmed safe for 6 × `AssyLineRuntime` instances.

### Audit Point 1 — Construction Cost

`AssyLineRuntime.__post_init__` creates:
- `ConveyorLine(config)` — pure dataclass init, no I/O
- `UpstreamProducer(config)` — pure dataclass init, no I/O

Cost: ~0ms. 6 instances = trivial.

### Audit Point 2 — Module-Level / Global Mutable State

**Result: NONE.**

- `AssyLineRuntime` is a `@dataclass` — all state in instance fields
- `ConveyorLine` — instance-local `_occupancy`, `_carriers`, `_position_complete`
- `UpstreamProducer` — instance-local `_sso2_seq`, `_rso2_seq`
- `GenealogyStore` — instance-local `_records`
- `QualityHistory` — instance-local `_records`, `_current_status`
- `load_assy_config_from_yaml()` — pure function, no caching
- No module-level singletons, no `_instance`, no `global`

### Audit Point 3 — ID Collisions

IDs generated per-instance:
- `MTR-{_motor_seq:04d}` — `_motor_seq` starts at 0 per instance
- `SSO2-{_sso2_seq:04d}` — per `UpstreamProducer` instance
- `RSO2-{_rso2_seq:04d}` — per `UpstreamProducer` instance
- `QR-{_quality_seq:04d}` — `_quality_seq` starts at 0 per instance
- `PAL-{_carrier_seq:03d}` — generated in `DemoController`, will be per-context

**Result**: IDs collide across instances (two runtimes both produce `MTR-0001`). This is a **projection scoping concern**, not a runtime bug.

### Audit Point 4 — ID Scoping

**Decision**: Scope at projection boundary, not runtime internals.

```
Runtime internal:  MTR-0001 (instance-local, valid within runtime)
Projection:        TIPA / ASSY / ASSY-SL03 / MTR-0001
API:               context: { sub_line_id: "ASSY-SL03", wip_id: "MTR-0001" }
```

No runtime ID generation changes needed. `SubLineSummaryView` and `AssyDemoSnapshot` carry `sub_line_id` for scoping. Frontend uses `sub_line_id + wip_id` for uniqueness where needed (event selection, cross-referencing).

### Audit Point 5 — Scenario State Locality

Scenario quality overrides are applied to `AssyLineConfig` BEFORE creating `AssyLineRuntime`. The config is a value object passed to the runtime constructor. Each runtime instance has its own config with its own quality overrides.

**Result**: Instance-local. One runtime with `AP06_FAIL_RETEST_PASS` does not affect another with `HAPPY_PATH`.

### Audit Point 6 — No Global Mutable State (Detailed)

Confirmed across all modules:
- `carrier.py` — `CarrierId` (frozen), `CarrierState` (instance)
- `conveyor.py` — `ConveyorLine` (instance), `ConveyorConfig` (value)
- `genealogy.py` — `GenealogyStore` (instance), `GenealogyRecord` (frozen)
- `upstream.py` — `UpstreamProducer` (instance), `UpstreamConfig` (value)
- `quality_records.py` — `QualityHistory` (instance), `QualityRecord` (frozen)
- `line_runtime.py` — `AssyLineRuntime` (instance), `AssyLineConfig` (value)
- `demo_controller.py` — `DemoController` (instance)
- `demo_snapshot.py` — All read models (frozen/detached)

### Audit Point 7 — DemoController Multi-Context

Current `DemoController` manages:
```python
_runtime: Optional[AssyLineRuntime]   # single runtime
_config: Optional[AssyLineConfig]     # single config
```

For 6 contexts, extends to:
```python
_contexts: dict[str, AssyDemoContext]  # sub_line_id → context
_config: AssyLineConfig               # shared process template
```

Where `AssyDemoContext` is a thin holder:
```python
@dataclass
class AssyDemoContext:
    sub_line_id: str
    variant: str
    label: str
    runtime: AssyLineRuntime
    carrier_seq: int
    sso2_ids: list[str]
    sso2_idx: int
```

No modification to `AssyLineRuntime` internals. Controller composition only.

### Audit Point 8 — HOLD / Time Semantics

**Current behavior verified in code**:

During normal dwell (`execute_dwell()`):
```
1. STOPPED → OPERATING (dwell_number +1 on first entry)
2. actual_dwell = max(120.0, max_remaining)
3. All occupied stations accumulate actual_dwell
4. simulation_time_s += actual_dwell
5. If all stations complete → READY_TO_INDEX
```

During HOLD (quality HOLD at AP06):
```
1. State: OPERATING (NOT STOPPED — HOLD prevents READY_TO_INDEX)
2. execute_dwell() is called again
3. dwell_number does NOT increment (only on STOPPED→OPERATING)
4. Held station timer was reset to 0 → remaining = 60.0
5. actual_dwell = max(120.0, 60.0) = 120.0
6. simulation_time_s += 120.0 (time ADVANCES)
7. Retest occurs, if PASS → station complete → READY_TO_INDEX
```

**Key finding**: A held runtime's `simulation_time_s` continues advancing. Under COMMON_DEMO_CLOCK with all 6 runtimes stepped together, their `actual_dwell` values are typically identical (= 120.0 nominal) because:
- Held runtime: max remaining = 60.0 (held station), max(120, 60) = 120
- Normal runtime: max remaining = some station's remaining, typically ≤ 120
- Result: all 6 runtimes advance by ~120.0 per step

Times remain close enough for demo. The overview can report a single global demo time = the first runtime's time, or the max. Individual sub-line snapshots carry their own `simulation_time_s`.

### Audit Point 9 — Public API for Summary Building

`AssyLineRuntime` public API (already used by `build_snapshot()`):

| Public Member | Type | Use |
|--------------|------|-----|
| `simulation_time_s` | property | Summary |
| `conveyor.state` | ConveyorState | Line state badge |
| `conveyor.dwell_number` | int | Dwell counter |
| `conveyor.positions` | tuple[str] | Station list |
| `conveyor.carrier_at(pos)` | CarrierState? | Occupancy |
| `conveyor.wip_at(pos)` | str? | WIP at position |
| `conveyor.occupied_positions()` | list[str] | WIP count |
| `wip_ids` | tuple[str] | WIP enumeration |
| `get_wip(wip_id)` | AssyWipState? | WIP lifecycle |
| `motor_count` | int | Motors created |
| `get_current_quality_status(wip_id)` | QualityStatus | HOLD detection |
| `get_quality_history(wip_id)` | QualityHistory? | Quality details |
| `genealogy.all_records()` | list[GenealogyRecord] | Genealogy |
| `rso2_buffer_size` | int | RSO2 buffer |

**Result**: Sufficient to build both `SubLineSummaryView` (lightweight overview) AND `AssyDemoSnapshot` (detailed). No private field access needed.

### Audit Point 10 — Reset Determinism

Creating `AssyLineRuntime(config)` with identical config:
- `__post_init__` initializes `ConveyorLine` + `UpstreamProducer` identically
- No random, no external state, no timestamp dependency
- `UpstreamProducer._sso2_seq = 0`, `_rso2_seq = 0`
- `_motor_seq = 0`, `_quality_seq = 0`

**Result**: Deterministic. Six instances with same config produce identical initial state.

---

## 3. Core Finding Resolution — Single Source of Truth

### The C01 Problem

Option C proposed:
```
6 × SubLineEngine (lightweight, new code)
+ 1 × AssyLineRuntime (full, existing code)
```

This creates **two different simulation implementations** for the same ASSY sub-line concept. `SubLineEngine` independently simulates dwell, occupancy, quality, counters — duplicating semantics already in `AssyLineRuntime`.

The "promotion" from lightweight engine to full runtime was never technically defined. A lightweight engine lacks genealogy, quality history, and runtime internals needed to reconstruct an `AssyLineRuntime`. "Promotion" would require event replay or shadow-running — neither implemented.

### The C02 Solution

Option A — all 6 sub-lines backed by the **same tested `AssyLineRuntime`**:

```
6 × AssyLineRuntime (logical execution contexts)
→ SubLineSummaryView (projection, not simulation)
→ AssyOverviewSnapshot
→ UI
```

One manufacturing behavior = one implementation. Overview derives from runtime public state via projection — not from a parallel mini-simulation.

---

## 4. Revised Option Scorecard

| Criterion | A: 6 × Runtime | B: 1 Runtime + Static | C: Dual Engine |
|---|:---:|:---:|:---:|
| Single source of truth | ✅ One implementation | ✅ One implementation | ❌ Two implementations |
| Full detail any lane | ✅ Immediate | ❌ Only 1 lane | ❌ "Promotion" undefined |
| New code volume | 🟡 ~100 lines (composition + projection) | ✅ ~30 lines | ❌ ~200 lines (engine + composition) |
| Duplicate semantics | ✅ None | ✅ None | ❌ Dwell, occupancy, quality duplicated |
| Regression risk | ✅ None (runtime unchanged) | ✅ None | 🟡 New engine may diverge |
| Scenario targeting | ✅ Per-instance config | ❌ Only 1 target lane | 🟡 Per-engine config |
| Identity handling | ✅ Sub_line_id at projection | ✅ Sub_line_id at projection | 🟡 Two identity models |
| Demo deadline fit | ✅ Simple composition | ✅ Trivial | 🟡 New engine needs testing |
| Future product path | ✅ Runtime instances = logical contexts | ❌ Static summaries not product-grade | 🟡 Engine must be replaced or promoted |
| Rollback simplicity | ✅ Disable composition, keep 1 runtime | ✅ Always works | 🟡 Remove engine + composition |

**Winner**: Option A. Single truth, full detail for any lane, minimal new code, zero runtime changes, clean rollback.

---

## 5. Final Architecture

```
                         AssyDemoComposition
                                │
                ┌───────────────┼───────────────┐
                │               │               │
         AssyDemoContext   AssyDemoContext   ... ×6
         ASSY-SL01         ASSY-SL02
         hydraulic         hydraulic
                │               │
         AssyLineRuntime  AssyLineRuntime    ← ONE implementation
         (HAPPY_PATH)     (HAPPY_PATH)         reused 6 times
                │               │
                └─── public API ─┘
                        │
                Projection Layer
            ┌───────────┴───────────┐
            │                       │
    SubLineSummaryView      AssyDemoSnapshot
    (6 × for overview)      (selected detail)
            │                       │
            └─────── UI ────────────┘
```

### Key Interpretation

- Six `AssyLineRuntime` instances are **logical demo execution contexts** — NOT claims about physical conveyor independence
- One tested runtime implementation = single source of manufacturing truth
- Overview = projection from runtime public state (no second simulation engine)
- Detail for any sub-line = immediately available from its runtime
- Common step/clock = `DEMO_EXECUTION_POLICY`, not plant truth

### AssyDemoContext

```python
@dataclass
class AssyDemoContext:
    """One logical ASSY sub-line execution context for demo."""
    sub_line_id: str          # "ASSY-SL01"
    variant: str              # "hydraulic" | "thermal"
    label: str                # "ASSY-SL01 — Hydraulic"
    runtime: AssyLineRuntime  # the ONE execution implementation
    carrier_seq: int = 1
    sso2_ids: list[str] = field(default_factory=list)
    sso2_idx: int = 0
```

### AssyDemoComposition

```python
@dataclass
class AssyDemoComposition:
    """Demo orchestration — presentation layer, not manufacturing control."""
    contexts: dict[str, AssyDemoContext]  # sub_line_id → context
    config: AssyLineConfig                # shared process template
    scenario: DemoScenario
    target_sub_line_id: str               # exception target
    selected_sub_line_id: str             # current detail selection
    global_demo_time_s: float             # presentation clock
    
    def step_all(self) -> None:
        """DEMO_EXECUTION_POLICY: step all contexts under common clock."""
        for ctx in self.contexts.values():
            self._step_context(ctx)
        # Global demo time = first context time (all close enough)
        first = next(iter(self.contexts.values()))
        self.global_demo_time_s = first.runtime.simulation_time_s
    
    def overview(self) -> AssyOverviewSnapshot:
        """Build overview from all 6 context runtimes (projection only)."""
        ...
    
    def detail(self, sub_line_id: str) -> AssyDemoSnapshot:
        """Build detailed snapshot from selected context runtime."""
        ...
```

---

## 6. Detail Selection Guarantee

**Guarantee A**: Any of 6 sub-lines can return a full valid `AssyDemoSnapshot` at its current state.

```
GET /assy-demo/sub-line/ASSY-SL01 → AssyDemoSnapshot (from SL01 runtime)
GET /assy-demo/sub-line/ASSY-SL03 → AssyDemoSnapshot (from SL03 runtime)
GET /assy-demo/sub-line/ASSY-SL06 → AssyDemoSnapshot (from SL06 runtime)
```

All 6 runtimes run concurrently. Selection simply chooses which runtime to build the detailed snapshot from. No "promotion", no reconstruction, no event replay.

---

## 7. Identity Scoping

**Contextual uniqueness via projection, not runtime ID changes**:

```
Runtime internal:      MTR-0001 (unique within one AssyLineRuntime instance)
Projection context:    sub_line_id = "ASSY-SL03"
API representation:    { sub_line_id: "ASSY-SL03", wip_id: "MTR-0001" }
UI uniqueness key:     "ASSY-SL03::MTR-0001"
```

- No runtime ID generation changes needed
- `SubLineSummaryView` carries `sub_line_id` for scoping
- `AssyDemoSnapshot` carries `sub_line_id` (additive field to existing model)
- Frontend combines `sub_line_id + wip_id` for cross-referencing (event → station → WIP)

---

## 8. Demo Clock / Time Semantics

### Three Time Concepts

| Concept | Source | Use |
|---------|--------|-----|
| Global demo time | `AssyDemoComposition.global_demo_time_s` | Header display, "t=480s" |
| Sub-line local time | `runtime.simulation_time_s` (per context) | Per-sub-line snapshot detail |
| Plant truth | TBD (TIPA unconfirmed) | Not modeled in demo |

### Time Under HOLD

When target sub-line (e.g., ASSY-SL03) enters HOLD:
- SL03 runtime: `execute_dwell()` advances time normally (~120s per step). dwell_number does NOT increment while state stays OPERATING. Held station timer resets each dwell.
- Other 5 runtimes: `execute_dwell()` advances time normally (~120s per step). Stations complete → READY_TO_INDEX → index → dwell_number increments.
- Global demo time: reports one context's time (all close enough). Or reports `max()`.
- Per-sub-line `dwell_number` naturally diverges (held sub-line dwells don't increment)

**This is demo-realistic**: The held sub-line experiences time passing (operators waiting, retesting) while other sub-lines continue productive cycles.

### COMMON_DEMO_CLOCK Implementation

```python
def step_all(self):
    """Step all contexts. Each calls its own execute_dwell()."""
    for ctx in self.contexts.values():
        if ctx.runtime.conveyor.state in (STOPPED, OPERATING):
            ctx.runtime.execute_dwell()
            if ctx.runtime.conveyor.state == READY_TO_INDEX:
                ctx.runtime.index_line()
                self._introduce_next_sso2(ctx)
    # Global time = first context (all nominally identical)
    self.global_demo_time_s = next(iter(self.contexts.values())).runtime.simulation_time_s
```

---

## 9. Config Decision

**Process config extraction: DEFER (P2).**

Rationale:
- Existing `tipa_assy_demo.yaml` already contains the complete process definition and is validated by M6-S02/S03/S04 tests
- Extracting a separate `tipa_assy_process.yaml` risks breaking existing config loading
- One shared `AssyLineConfig` instance can be passed to all 6 runtimes — no duplication needed
- For S04B P0/P1, extending the existing YAML with a `sub_lines` array is sufficient
- Separate process config is architectural cleanliness, not demo necessity before 17-Aug

**What we DO change** (minimal):
```yaml
# tipa_assy_demo.yaml — ADD at end
production_line:
  id: ASSY
  sub_lines:
    - { id: ASSY-SL01, variant: hydraulic, label: "ASSY-SL01 — Hydraulic" }
    - { id: ASSY-SL02, variant: hydraulic, label: "ASSY-SL02 — Hydraulic" }
    - { id: ASSY-SL03, variant: hydraulic, label: "ASSY-SL03 — Hydraulic" }
    - { id: ASSY-SL04, variant: thermal,  label: "ASSY-SL04 — Thermal" }
    - { id: ASSY-SL05, variant: thermal,  label: "ASSY-SL05 — Thermal" }
    - { id: ASSY-SL06, variant: thermal,  label: "ASSY-SL06 — Thermal" }
  demo:
    target_sub_line_for_exception: ASSY-SL03
```

Existing config structure preserved. Existing tests unaffected.

---

## 10. G-ENGINE Reassessment

**G-ENGINE (lightweight sub-line state engines): REMOVED.**

Replaced by:
- `G-CONTEXT`: 6 × `AssyLineRuntime` as logical execution contexts (reuses existing tested implementation)
- `G-OVERVIEW`: `SubLineSummaryView` projection from runtime public API (no second simulation)

---

## 11. DG03 Traceability Matrix (Unchanged from C01)

All 13 DG03 states trace end-to-end through the new architecture. Same projection fields, same API contracts. Only the source changes: `SubLineEngine` → `AssyLineRuntime` public API.

---

## 12. API Contracts (Unchanged from C01)

```
POST /assy-demo/reset                    → AssyDemoSnapshot (existing, backward compat)
POST /assy-demo/step                      → AssyDemoSnapshot (existing, backward compat)
POST /assy-demo/snapshot                  → AssyDemoSnapshot (existing, backward compat)
GET  /assy-demo/overview                  → AssyOverviewSnapshot (NEW)
GET  /assy-demo/sub-lines                 → list[SubLineSummaryView] (NEW)
GET  /assy-demo/sub-line/{sub_line_id}    → AssyDemoSnapshot (NEW, existing shape)
```

---

## 13. Revised Implementation Gates

```
S04B-I01 — Context Identity + Config Extension
  ↓
S04B-I02 — AssyDemoComposition + Multi-Runtime Management
  ↓
S04B-I03 — Overview Projection + Additive API
  ↓
  ═══ BACKEND GATE — 6 contexts respond, scenario targeting, any-lane detail ═══
  ↓
S04B-I04 — ASSY Overview UI (Frame A)
  ↓
S04B-I05 — Sub-line Detail + Selection Routing (Frame B)
  ↓
S04B-I06 — Quality Inspector + Event Interaction (Frame C)
  ↓
S04B-I07 — Motion / Transition Animation
  ↓
S04B-I08 — Demo Hardening
```

### S04B-I01 — Context Identity + Config Extension

**Objective**: Define identity model and extend config with sub-line array. No runtime changes.

**Files**:
- `configs/plants/tipa_assy_demo.yaml` — add `production_line.sub_lines[]` array
- `src/virtual_factory/assembly/sub_line_identity.py` — NEW, identity dataclasses + config parsing

**Invariants**:
- `production_line_id == "ASSY"`, `sub_line_id == "ASSY-SLxx"`
- Config change is additive — existing fields unchanged
- Existing `AssyLineConfig` loading from YAML unaffected

**Tests**: Identity model parsing, config round-trip, existing M6-S02 regression unaffected.

### S04B-I02 — AssyDemoComposition + Multi-Runtime Management

**Objective**: Create `AssyDemoComposition` managing 6 `AssyLineRuntime` contexts.

**Files**:
- `src/virtual_factory/assembly/demo_composition.py` — NEW, `AssyDemoComposition` + `AssyDemoContext`
- `src/virtual_factory/assembly/demo_controller.py` — refactor to use composition internally
- No changes to `AssyLineRuntime`, `ConveyorLine`, or any M6-S02/S03/S04 code

**Invariants**:
- All 6 contexts use the same `AssyLineRuntime` implementation
- Scenario quality overrides applied to target context only
- `DEMO_EXECUTION_POLICY: COMMON_DEMO_CLOCK` via `step_all()`
- No runtime internals modified
- Existing `DemoController` public API preserved (reset/step/snapshot route to selected context)

**Tests**: 6 contexts initialize deterministically, scenario targeting (5 HAPPY_PATH + 1 exception), step_all advances all contexts, ID isolation per context, reset determinism.

### S04B-I03 through S04B-I08

Unchanged from C01 plan — same objectives, invariants, and test strategies. Only the backend source changes from `SubLineEngine` to `AssyLineRuntime`.

---

## 14. Test Strategy (Revised)

### Unit Tests

| Layer | What | Count (est.) |
|-------|------|-------------|
| Identity | Config parsing, validation | 8 |
| Composition | `AssyDemoContext` creation, `AssyDemoComposition` init | 8 |
| Projection | `SubLineSummaryView` from runtime public API | 10 |
| Scenario | Targeting, override application | 8 |

### Integration Tests

| Scope | What | Count (est.) |
|-------|------|-------------|
| Multi-context | 6 runtimes coexist, no ID interference, deterministic init | 6 |
| Step-all | Common clock, time near-identical, HOLD behavior | 5 |
| API | `/overview`, `/sub-line/{id}` for all 6, error paths | 8 |
| Scenario | 5 normal + 1 exception verified via API | 6 |
| Detail any lane | `GET /sub-line/{id}` returns valid snapshot for all 6 | 3 |

### Regression Tests

| Scope | What |
|-------|------|
| M6-S02/S03/S04 | All 75 tests — `AssyLineRuntime` unchanged |
| M2–M5 | 1067 tests — no core changes |

### UI Acceptance + Demo Rehearsal

Unchanged from C01.

---

## 15. Fallback Plan

### Fallback A — Single Runtime (ALWAYS AVAILABLE)

```
- Disable composition initialization → create 1 runtime as before
- Overview endpoint returns single-entry list or 404
- Existing /assy-demo/reset|step|snapshot work identically to S04
- 100% backward compatible
```

### Fallback B — Composition with Limited UI

```
- Backend composition works (6 contexts, overview API)
- UI renders single detail view (existing S04 renderer)
- Overview shown as simple text/table if SVG not ready
```

---

## 16. P0 / P1 / P2 Schedule (Unchanged from C01)

- **P0** (17-Aug): I01–I05 (identity, composition, overview API, Frame A, Frame B)
- **P1** (21-Aug): I06–I08 (inspector, animation, hardening)
- **P2** (Defer): Process config extraction, per-variant overrides, MES

---

## 17. Risks (Revised After Audit)

| Risk | C01 Severity | C02 Severity | Change |
|------|:---:|:---:|--------|
| Dual simulation truth | — | **ELIMINATED** | Option A = single implementation |
| Lightweight engine divergence | MEDIUM | **ELIMINATED** | No second engine |
| "Promotion" undefined | — | **ELIMINATED** | Any lane has full runtime |
| ID collision across instances | — | **LOW** | Scoped at projection boundary |
| Time divergence under HOLD | — | **LOW** | Close enough for demo (~120s per step) |
| Frontend 6-lane SVG complexity | MEDIUM | MEDIUM | Unchanged |
| Demo deadline | MEDIUM | MEDIUM | Unchanged |

---

## 18. Planning Self-Review (C02 Addendum)

### What changed from C01 to C02?
- Architecture: Option C (dual engine) → Option A (6 × existing runtime)
- `SubLineEngine` removed — no second simulation implementation
- "Promotion" concept removed — any sub-line has full runtime immediately
- Config extraction deferred to P2
- G-ENGINE reclassified from MUST to REMOVED, G-CONTEXT added

### Why is Option A now safe?
- Codebase audit confirms: no global state, no singletons, instance-local IDs, deterministic init
- 6 runtime instances are ~0ms construction cost, ~trivial memory
- All state is instance fields — no shared mutable state
- Existing tests (1067 + 75) validate runtime semantics once, not 6 times

### What remains unresolved?
- Physical topology (independent vs shared conveyors) — TBD by TIPA
- Architecture explicitly separates logical execution context from plant physical truth

---

## 19. Scope

- ✅ M6-S04B implementation planning C02 — single-source-of-truth + codebase audit
- ✅ 10-point codebase audit complete — all points confirm multi-instance safety
- ✅ Option A recommended with evidence
- ✅ Guarantee A for detail selection
- ❌ No runtime code changes
- ❌ No production UI implementation
- ❌ No MES / M6-S05
- ❌ DG01–DG03 remain closed

---

> **M6-S04B Implementation Planning C02 is READY FOR SA REVIEW.**
>
> **Status Summary**:
> ```
> DG01–DG03               ALL CLOSED ✅
> M6-S04B Planning C02     READY FOR SA
> M6-S05 MES               NOT AUTHORIZED
> ```
