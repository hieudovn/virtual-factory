# M6-S04B-C01 — Implementation Planning (Revised)

> **Status**: PLANNING C01 — full architecture correction + integrity review.  
> **Baseline**: DG03 frozen at `cf20843`. Original planning at `44185b7`.  
> **Purpose**: Correct architecture assumptions, full planning integrity audit, define minimal implementation path.  
> **Rule**: Do NOT invent UI state. Do NOT create fake 6-line data. Do NOT reopen DG01–DG03. Do NOT start M6-S05.

---

## 1. Executive Recommendation

**Recommended architecture**: Option C (Hybrid) — **1 detailed runtime + 5 lightweight logical state engines**, all sharing the common ASSY process template, producing 6 valid sub-line projections.

**Rationale**:
- 10 of 13 DG03 visual states map directly to existing runtime data — no runtime refactor needed.
- 6 full `AssyLineRuntime` instances (Option A) imply physical assumptions not yet confirmed by TIPA.
- Single-runtime + read-only stubs (Option B) risk fake-data credibility for the overview.
- Hybrid gives realistic overview state from 6 lightweight engines, with one selectable detailed view from the existing full runtime.
- Preserves projection boundary, keeps `AssyLineRuntime` unchanged, and separates demo execution policy from plant truth.

---

## 2. Current Capability

Same as original plan §1. Confirmed and unchanged:

| Layer | Module | Capability |
|-------|--------|------------|
| Config | `tipa_assy_demo.yaml` | ONE conveyor, 12 stations, station durations, quality config |
| Runtime | `AssyLineRuntime` | Synchronized indexed line. STOP→OPERATING→READY→INDEX. Multi-WIP concurrent dwell. AP04 genealogy. Quality HOLD/retest/reinspect. |
| Controller | `DemoController` | RESET/STEP/AUTO/PAUSE/SPEED. 4 scenarios. Single runtime. |
| Snapshot | `AssyDemoSnapshot` | Detached read model: `StationPositionView[]`, `GenealogySummary[]`, `QualityEventView[]`, `ProductionSummary` |
| API | `/assy-demo/*` | reset/step/snapshot → single snapshot dict |
| Frontend | `assy_demo.html/js/css` | Single-line visualization |

**Runtime semantics that must NOT change** (closed under M6-S02/S03/S04):
- Station processing semantics (dwell, concurrent work)
- AP04 JOIN genealogy model
- Quality HOLD/retest/reinspect/FAILED_FINAL lifecycle
- INDEX/conveyor synchronization
- Scenario override mechanism

---

## 3. DG03 State Traceability Matrix

All 13 DG03 visual states → runtime data → projection → API → UI.

| # | DG03 State | Runtime Source | Projection Field | API Contract | UI Component |
|---|-----------|----------------|-------------------|-------------|--------------|
| 1 | ASSY Overview Normal | 6 sub-line summary states | `SubLineSummaryView.line_state` | `GET /assy-demo/overview` | Frame A — 6-lane SVG |
| 2 | ASSY Overview Exception | Target sub-line quality hold + 5 normal | `SubLineSummaryView.active_quality_holds > 0` | `GET /assy-demo/overview` | Frame A — highlighted lane |
| 3 | Normal shared dwell | `line_state: "operating"` + occupied positions + all `quality_status: "clear"` | `positions[]` with filters | `GET /assy-demo/sub-line/{id}` | Frame B Artboard 1 |
| 4 | INDEX_SHIFT | `line_state: "indexing"` → `line_state: "stopped"` | `line_state` transition | `GET /assy-demo/sub-line/{id}` | Frame B Artboard 3 |
| 5 | AP04 JOIN | `genealogy[]` entries, `wip_type: "MTR"` at AP04 | `genealogy[]` | `GET /assy-demo/sub-line/{id}` | Frame B Artboard 3 |
| 6 | AP06 FAIL/HOLD | `quality_status: "retest_pending"`, `is_quality_hold: true` | `positions[AP06].is_quality_hold` | `GET /assy-demo/sub-line/{id}` | Frame B Artboard 2 |
| 7 | AP06 RETEST PASS | `quality_status: "clear"`, `latest_quality_result: "PASS"` | `positions[AP06]` post-retest | `GET /assy-demo/sub-line/{id}` | Frame C §02 |
| 8 | AP08 NG/REINSPECT | `quality_status: "reinspect_pending"` | `positions[AP08].is_quality_hold` | `GET /assy-demo/sub-line/{id}` | Frame C §03 |
| 9 | AP11 RELEASED | `manufacturing_status: "released"` at AP11 | `positions[AP11].manufacturing_status` | `GET /assy-demo/sub-line/{id}` | Frame B Artboard 3 |
| 10 | WIP Inspector | Occupied position + genealogy + quality events | Filtered from `positions[]` + `genealogy[]` + `recent_quality_events[]` | `GET /assy-demo/sub-line/{id}` | Frame B right panel |
| 11 | Station Inspector | Selected position + quality events for that station | Filtered `positions[]` + `recent_quality_events[]` by station | `GET /assy-demo/sub-line/{id}` | Frame C §04 |
| 12 | Event Selected | Event → station linkage → WIP linkage | Cross-reference `recent_quality_events[]` → `positions[]` | `GET /assy-demo/sub-line/{id}` | Frame C §05 |
| 13 | 1366×768 | All of above, CSS responsive + SVG viewBox | N/A (rendering concern) | N/A | CSS media queries |

**No state ends with "frontend can infer" or "hardcode for demo."**

---

## 4. Canonical Identity Model

Per SA correction A2:

```
plant_id     = TIPA
line_id      = ASSY
sub_line_id  = ASSY-SL01 .. ASSY-SL06
station_id   = PRE-ASSY, AP01..AP11
wip_id       = MTR-xxxx, SSO2-xxxx, RSO2-xxxx
```

Conceptual fields in implementation:

```python
production_line_id: str   # "ASSY"
sub_line_id: str          # "ASSY-SL01"
variant: str              # "hydraulic" | "thermal"
```

The production hierarchy MUST NOT be flattened. `ASSY` is the production line. `ASSY-SLxx` are sub-lines within it.

---

## 5. Known vs Unknown Physical Topology

Per SA correction A1:

### Confirmed / Required

Six logical execution contexts under `ASSY`:
- `ASSY-SL01` through `ASSY-SL06`
- Each requires its own: sub_line_id, WIP context, genealogy context, quality context, event context, production summary, variant context

### NOT Confirmed (TBD / Out of Scope for S04B)

- Whether each sub-line has an independent indexed conveyor
- Whether control/synchronization is shared across sub-lines
- Whether shared physical transport exists
- ASSY-level production coordination between sub-lines

**Implementation rule**: Model 6 logical execution contexts. Do NOT assert physical independence or shared synchronization. Label all physical assumptions as `DEMO_EXECUTION_POLICY`, not plant truth.

---

## 6. Option A/B/C Comparison

Per SA correction A4:

### Option A — Six Full Runtime Instances

```
6 × AssyLineRuntime (full M6-S02/S03 semantics)
+ sub-line identity wrapper
+ demo composition layer
```

| Criterion | Assessment |
|-----------|------------|
| Implementation effort | MEDIUM — wrapper + multi-controller, but 6× initialization, 6× step |
| Data realism | HIGH — every sub-line has full genealogical/quality state |
| CPU/memory | Low concern (dataclasses + dicts), but 6× test surface |
| Test burden | HIGH — 6× runtime regression, scenario injection into 6 targets |
| Scenario handling | Each scenario must target which sub-line(s) — non-trivial |
| Future productization | Best path if sub-lines are confirmed independent |
| Risk of accidental physical assumptions | HIGH — 6 runtimes implicitly suggests independent conveyors |

### Option B — One Detailed Runtime + 5 Read-Only Overview Projections

```
1 × full AssyLineRuntime (detailed view)
+ 5 × lightweight deterministic summary generators
```

| Criterion | Assessment |
|-----------|------------|
| Speed | HIGH — only one full runtime |
| Simplicity | HIGH — minimal new code |
| Fake-data risk | MEDIUM — 5 summary projections may feel synthetic |
| Credibility | LOW — overview shows 5 sub-lines with no internal state detail |
| Interaction limitations | HIGH — cannot drill into non-detailed sub-lines |
| Demo fit | POOR — only one sub-line is inspectable |

### Option C — Hybrid (RECOMMENDED)

```
6 × lightweight sub-line state engines (shared process template)
+ 1 × selected detailed runtime (reuses existing AssyLineRuntime as projection source)
+ demo composition layer
```

Lightweight engine provides:
- Sub-line identity + variant
- Station occupancy tracking (carrier/WIP positions)
- Quality status summary (HOLD/CLEAR per station)
- Production counters (created, released)
- Dwell number, line state
- Event log (abbreviated — last N events)

Detailed runtime (selected sub-line) reuses existing `AssyLineRuntime`:
- Full genealogy
- Full quality history
- Full trace/event detail
- Inspector-ready data

| Criterion | Assessment |
|-----------|------------|
| Complexity | MEDIUM — new lightweight engine (~100 lines) + composition |
| Realism | HIGH — overview derives from valid state engines, detail from full runtime |
| Demo fit | EXCELLENT — overview shows real state, selection gives full detail |
| Migration path | If TIPA confirms independence → promote lightweight engines to full runtimes. If shared control → lightweight engines reflect that. |
| Test burden | MEDIUM — lightweight engine tests + composition tests |
| Demo risk | LOW — fallback to single detailed runtime always available |

**Recommendation**: Option C. Balanced realism, preserves existing runtime, avoids unconfirmed physical assumptions, good demo fit, clean migration path.

---

## 7. Recommended Demo Architecture

```
┌──────────────────────────────────────────────────┐
│                  DemoController                   │
│  (demo composition + presentation orchestration)  │
├──────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────┐  ┌──────────┐       ┌──────────┐   │
│  │SubLine   │  │SubLine   │  ...  │SubLine   │   │
│  │Engine    │  │Engine    │       │Engine    │   │
│  │ASSY-SL01 │  │ASSY-SL02 │       │ASSY-SL06 │   │
│  │hydraulic │  │hydraulic │       │thermal   │   │
│  └──────────┘  └──────────┘       └──────────┘   │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  AssyLineRuntime (selected sub-line detail)   │ │
│  │  Full M6-S02/S03 semantics, genealogy, QC    │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │            Projection Layer                   │ │
│  │  SubLineSummaryView + AssyDemoSnapshot        │ │
│  │  (detached, no private runtime access)        │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Lightweight Sub-Line State Engine

```python
@dataclass
class SubLineEngine:
    """Lightweight sub-line state engine — manufacturing truth, not fake data."""
    sub_line_id: str          # "ASSY-SL01"
    variant: str              # "hydraulic" | "thermal"
    label: str                # "ASSY-SL01 — Hydraulic"
    
    # Shared process template (reference, not copy)
    process: AssyProcessTemplate
    
    # State
    positions: dict[str, SubLinePositionState]  # station_id → occupancy
    dwell_number: int
    line_state: str           # ConveyorState value
    simulation_time_s: float
    motors_created: int
    motors_released: int
    wips: dict[str, SubLineWipSummary]  # wip_id → summary
    quality_events: list[QualityEventView]  # last ~20
    active_quality_holds: int
```

Key design: The lightweight engine tracks **real manufacturing state** but at reduced fidelity. It does NOT simulate full genealogy, full quality history, or per-station elapsed time. It tracks what the overview needs: which stations are occupied, what the quality status is, what the production counters are.

The detailed runtime (`AssyLineRuntime`) provides the rich view when a sub-line is selected.

---

## 8. Demo Execution Policy

Per SA corrections A3 and A9:

### DEMO_EXECUTION_POLICY (not plant truth)

```
Policy: COMMON_DEMO_CLOCK
- All 6 sub-line engines + 1 detailed runtime advance in lockstep
  under a single step() call.
- simulation_time_s is identical across all contexts.
- This is a DEMO PRESENTATION CONVENIENCE.
- It does NOT assert TIPA sub-lines share a physical clock,
  conveyor, or control cadence.
```

**Why**: Simplifies demo presentation. Overview shows all sub-lines at the same simulation time. No divergence to explain.

**What it does NOT claim**: Real TIPA sub-lines are synchronized. Real TIPA has shared control.

### Detail Selection Policy

```
Policy: SELECTED_DETAIL_SWAP
- One sub-line at a time provides the detailed AssyLineRuntime view.
- Switching selection swaps which sub-line's lightweight engine
  is promoted to full detail (or creates a new full runtime snapshot).
- The detailed view always comes from AssyLineRuntime public API.
- No synthetic detail data.
```

---

## 9. Scenario Targeting Policy

Per SA correction and requirement for "5 normal + 1 exception" overview:

### Policy: SINGLE_TARGET_EXCEPTION

```
- Global scenario applies to ONE designated target sub-line.
- Remaining 5 sub-lines run HAPPY_PATH.
- Target sub-line is configurable (default: ASSY-SL03, matching DG03 design).
```

**Why**: The DG03 visual design shows exactly this: 5 normal lanes + 1 exception lane (SL03 HOLD in Frame A). This must be achievable with real runtime state, not hardcoded CSS.

### Scenario → Target Mapping

| Global Scenario | Target Sub-Line | Other 5 Sub-Lines |
|----------------|-----------------|-------------------|
| HAPPY_PATH | (none — all normal) | HAPPY_PATH |
| AP06_FAIL_RETEST_PASS | ASSY-SL03 | HAPPY_PATH |
| AP08_NG_REINSPECT_PASS | ASSY-SL02 (configurable) | HAPPY_PATH |
| FAILED_FINAL | ASSY-SL03 | HAPPY_PATH |

### How "5 normal + 1 HOLD" is achieved

1. DemoController initializes 6 SubLineEngine instances.
2. Scenario quality overrides applied ONLY to target sub-line engine.
3. All 6 engines step under common clock.
4. At the dwell where target engine's AP06 produces FAIL → HOLD, the other 5 engines continue normal processing.
5. `GET /assy-demo/overview` returns 6 `SubLineSummaryView` — one has `active_quality_holds: 1`, five have `active_quality_holds: 0`.
6. Frontend renders 5 green lanes + 1 red lane.

**All state comes from valid runtime engines. No fake data.**

---

## 10. Projection Contracts

Per SA correction A6: preserve projection boundary. No frontend access to private runtime state.

### Existing (Preserved)

```
AssyDemoSnapshot        — detailed single-sub-line projection
StationPositionView     — one station in the detailed view
GenealogySummary        — AP04 join record
QualityEventView        — quality event for activity panel
ProductionSummary       — counters
```

These remain unchanged. They serve the selected-sub-line detail view.

### New (Additive)

```
SubLineSummaryView      — lightweight overview projection for one sub-line
AssyOverviewSnapshot    — composition: 6 × SubLineSummaryView + demo metadata
```

```python
@dataclass
class SubLineSummaryView:
    """Lightweight overview of one sub-line. Detached from runtime."""
    sub_line_id: str
    variant: str
    label: str
    line_state: str           # ConveyorState value
    dwell_number: int
    simulation_time_s: float
    motors_created: int
    motors_released: int
    wips_on_line: int
    active_quality_holds: int
    held_station: str          # e.g. "AP06" if HOLD, else ""
    held_wip_id: str           # e.g. "MTR-0015" if HOLD, else ""
    is_exception: bool         # True if this sub-line has active quality hold

@dataclass
class AssyOverviewSnapshot:
    """Complete ASSY overview. Detached from all runtimes."""
    simulation_time_s: float
    sub_lines: list[SubLineSummaryView]
    total_motors_created: int
    total_motors_released: int
    total_active_holds: int
    scenario: str
    target_sub_line_id: str    # which sub-line is the exception target
```

### Derivation Rules (Deterministic)

All derivation rules are pure functions of runtime/public state:

| Derived Value | Rule |
|---------------|------|
| `is_exception` | `active_quality_holds > 0` |
| `held_station` | First station where `is_quality_hold == true` |
| `held_wip_id` | `wip_id` at `held_station` |
| `total_motors_created` | `sum(sub_line.motors_created)` |
| `total_active_holds` | `count(sub_line.is_exception)` |

---

## 11. API Contracts

Per SA correction A5: additive API. Preserve existing S04 contracts.

### Preserved (Unchanged Response Shape)

```
POST /assy-demo/reset      → AssyDemoSnapshot (existing detailed shape)
POST /assy-demo/step        → AssyDemoSnapshot (existing detailed shape)
POST /assy-demo/snapshot    → AssyDemoSnapshot (existing detailed shape)
GET  /assy-demo             → assy_demo.html (unchanged)
GET  /assy-demo/static/*    → static files (unchanged)
```

These endpoints continue to return the existing single-sub-line detailed snapshot. The S04 frontend continues to work. This is the fallback.

### New (Additive for S04B)

```
GET  /assy-demo/overview               → AssyOverviewSnapshot
GET  /assy-demo/sub-lines              → list[SubLineSummaryView]  (alias)
GET  /assy-demo/sub-line/{sub_line_id} → AssyDemoSnapshot (detailed, existing shape)
```

**Principle**:
- `/assy-demo/reset|step|snapshot` remain backward compatible — they serve the currently-selected detailed sub-line.
- `/assy-demo/overview` is the new 6-lane overview contract.
- `/assy-demo/sub-line/{sub_line_id}` returns the existing detailed snapshot shape for any sub-line.

No existing endpoint changes response shape. No silent repurposing.

---

## 12. Config Composition

Per SA correction A7: separate process definition from deployment.

### Process Definition (Shared)

```yaml
# configs/plants/tipa_assy_process.yaml (NEW — shared template)
process:
  name: "TIPA ASSY Process"
  conveyor:
    nominal_line_dwell_time_s: 120.0
    index_movement_duration_s: 0.0
    positions:
      - PRE-ASSY
      - AP01 .. AP11
  station_durations:
    PRE-ASSY: 30.0
    AP01: 60.0
    # ... same as current
  quality:
    ap03: { max_attempts: 1, scenario: PASS }
    ap06: { max_attempts: 2, scenario: PASS }
    ap08: { max_attempts: 2, scenario: PASS }
    ap11: { max_attempts: 1, scenario: PASS }
  ap04:
    required_parent_sources: [SSO2, RSO2]
```

### Deployment / TIPA Composition

```yaml
# configs/plants/tipa_assy_demo.yaml (EXTENDED)
plant:
  id: TIPA
  name: "TIPA Motor Production"

production_line:
  id: ASSY
  name: "ASSY Line"
  process_ref: "tipa_assy_process.yaml"   # or inline

  sub_lines:
    - id: ASSY-SL01
      variant: hydraulic
      label: "ASSY-SL01 — Hydraulic"
    - id: ASSY-SL02
      variant: hydraulic
      label: "ASSY-SL02 — Hydraulic"
    - id: ASSY-SL03
      variant: hydraulic
      label: "ASSY-SL03 — Hydraulic"
    - id: ASSY-SL04
      variant: thermal
      label: "ASSY-SL04 — Thermal"
    - id: ASSY-SL05
      variant: thermal
      label: "ASSY-SL05 — Thermal"
    - id: ASSY-SL06
      variant: thermal
      label: "ASSY-SL06 — Thermal"

  demo:
    target_sub_line_for_exception: ASSY-SL03
    execution_policy: COMMON_DEMO_CLOCK
```

No duplication of station model. Process definition is referenced once.

---

## 13. UI Component / Data Mapping

| Visual Element | Data Source | Condition |
|----------------|------------|-----------|
| Lane status OPERATING | `SubLineSummaryView.line_state == "operating"` | Green badge |
| Lane status STOPPED | `SubLineSummaryView.line_state == "stopped"` | Gray badge |
| Lane status HOLD | `SubLineSummaryView.is_exception == true` | Red badge, red lane border |
| Variant label | `SubLineSummaryView.variant` | `hydraulic` → "HYDRAULIC SSO2", `thermal` → "THERMAL SSO2" |
| Lane WIP/OUT/DW counters | `SubLineSummaryView.wips_on_line`, `motors_released`, `dwell_number` | Numeric |
| Exception detail in lane | `SubLineSummaryView.held_station`, `held_wip_id` | "⏸ AP06 / MTR-0015 / FAIL #1" |
| Station occupied (detail) | `StationPositionView.is_occupied` | Filled dot or token |
| Station quality hold (detail) | `StationPositionView.is_quality_hold` | Red border |
| Station PASS/FAIL (detail) | `StationPositionView.latest_quality_result` | Green check / Red X |
| WIP token | `StationPositionView.wip_id` | Token badge with ID |
| Genealogy in inspector | `GenealogySummary[]` filtered by selected WIP | Parent→child tree |
| Quality events | `QualityEventView[]` | Filterable feed |
| Production counters | `ProductionSummary` | Aggregate or per-sub-line |

---

## 14. Animation / Motion Derivation Model

Per SA correction B8: distinguish runtime truth from visual interpolation.

### Runtime Truth (Discrete Snapshots)

- `step()` returns post-step state.
- Snapshot is a point-in-time read model.
- No continuous motion data exists in runtime.

### Visual Interpolation (Frontend Only)

```
previous_snapshot ────→ next_snapshot
                         │
              ┌──────────┴──────────┐
              │  Transition Interp  │
              │  (frontend only)    │
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │  Transient Animation│
              │  ~500ms             │
              └─────────────────────┘
```

Allowed transitions (no manufacturing truth invented):
- **INDEX_SHIFT**: previous snapshot positions → next snapshot positions. Frontend interpolates carrier movement along conveyor bar. Duration: configurable (~500ms).
- **LINE_IN**: New WIP appears at PRE-ASSY. Simple fade-in.
- **LINE_OUT**: WIP at AP11 with `manufacturing_status: "released"`. Simple fade-out.
- **JOIN**: RSO2 appears at AP04, MTR child appears. Fade + highlight.
- **HOLD**: Station border turns red. No motion — conveyor stationary per runtime truth.

**Rule**: Frontend may animate BETWEEN two valid snapshots. Frontend may NOT invent manufacturing events not present in snapshot data.

---

## 15. Gap Classification: MUST / SHOULD / DEFER / REMOVE

Per SA correction A10:

### MUST HAVE (Required for S04B Demo)

| Gap | Description | Rationale |
|-----|-------------|-----------|
| G-SL-ID | Sub-line identity model (`ASSY` line, `ASSY-SLxx` sub-lines) | DG03 shows 6 named lanes |
| G-OVERVIEW | Overview projection (`SubLineSummaryView` × 6) | Frame A requires per-lane summary |
| G-ENGINE | Lightweight sub-line state engines (6×) | Must produce valid overview state, not fake data |
| G-SCENARIO | Scenario targeting (1 exception + 5 normal) | DG03 Frame A shows 5 normal + 1 HOLD |
| G-API-OV | `GET /assy-demo/overview` endpoint | New contract for 6-lane data |
| G-API-DETAIL | `GET /assy-demo/sub-line/{id}` endpoint | Drill-down to selected sub-line |
| G-UI-FRAMEA | 6-lane overview SVG renderer | Frame A from DG03 |
| G-UI-FRAMEB | Sub-line detail view (reuse existing single-line renderer) | Frame B from DG03 |
| G-UI-FRAMEC | Quality inspector + event interaction | Frame C from DG03 |
| G-ANIM | INDEX_SHIFT + LINE_IN/OUT animation | DG03 shows motion transitions |
| G-1366 | 1366×768 responsive layout | DG03 Artboard 4 |

### SHOULD HAVE (If Stable Before 21-Aug)

| Gap | Description | Rationale |
|-----|-------------|-----------|
| G-PERF | Config-driven per-variant station duration overrides | Future Thermal/Hydraulic differences |
| G-DEMO-HARD | Auto-run polish, scenario switching UX | Demo readiness |

### DEFER (Not Required for S04B)

| Gap | Description | Rationale |
|-----|-------------|-----------|
| G-PHYS-CTRL | Real cross-sub-line synchronization semantics | TIPA physical topology unconfirmed |
| G-PHYS-CONV | Shared physical conveyor model | TIPA unconfirmed |
| G-FULL-VARIANT | Full variant-specific process behavior | Incomplete TIPA data |
| G-INDEP-SCHED | Independent sub-line scheduling | Not needed for demo |
| G-MES | MES integration | M6-S05 — NOT AUTHORIZED |

### REMOVE (From Original Plan)

| Original Item | Reason for Removal |
|---------------|-------------------|
| "6 independent, identically-structured lines" | A1: unconfirmed physical independence |
| "all six share same step so simulation_time_s is synchronized" (as plant truth) | A9: must label as DEMO_EXECUTION_POLICY |
| `AssySubLine` wrapper with `line_id = "ASSY-SL01"` (flattened) | A2: must use `production_line_id=ASSY, sub_line_id=ASSY-SLxx` |
| Changing existing `/assy-demo/step` response shape | A5: must preserve backward compatibility |
| 6 × full `AssyLineRuntime` as default plan | A4: Option C recommended after comparison |

---

## 16. Sequential Implementation Gates

```
S04B-I01 — Identity + Config + Engine Contract
  ↓
S04B-I02 — Lightweight SubLineEngine + Scenario Targeting
  ↓
S04B-I03 — Overview Projection + Additive API
  ↓
  ═══ BACKEND GATE — verify 6 sub-lines respond, 5 normal + 1 exception ═══
  ↓
S04B-I04 — ASSY Overview UI (Frame A)
  ↓
S04B-I05 — Sub-line Detail + Selection Routing (Frame B)
  ↓
S04B-I06 — Quality Inspector + Event Interaction (Frame C)
  ↓
S04B-I07 — Motion / Transition Animation
  ↓
S04B-I08 — Demo Hardening (1366×768, auto-run, scenario polish)
```

### S04B-I01 — Identity + Config + Engine Contract

**Objective**: Define the canonical identity model and shared process template. No runtime code changes.

**Files**:
- `configs/plants/tipa_assy_demo.yaml` — extend with `production_line` + `sub_lines` array
- `configs/plants/tipa_assy_process.yaml` — NEW, shared process template (extracted from existing config)
- `src/virtual_factory/assembly/sub_line_identity.py` — NEW, identity dataclasses only

**Invariants**:
- `production_line_id == "ASSY"`, `sub_line_id == "ASSY-SLxx"`
- Process template referenced once, not duplicated 6 times
- Variant is a configuration field (`hydraulic` | `thermal`), not a UI label only

**Tests**: Unit tests for identity model, config parsing, process template validation.

**Out of scope**: Runtime changes, engine implementation, API.

### S04B-I02 — Lightweight SubLineEngine + Scenario Targeting

**Objective**: Implement the 6 lightweight sub-line state engines + scenario targeting.

**Files**:
- `src/virtual_factory/assembly/sub_line_engine.py` — NEW, `SubLineEngine` dataclass + step logic
- `src/virtual_factory/assembly/demo_controller.py` — extend with multi-engine management
- `src/virtual_factory/assembly/demo_snapshot.py` — add `SubLineSummaryView` builder

**Invariants**:
- Each engine produces valid manufacturing state (not fake data)
- Scenario quality overrides applied ONLY to target sub-line
- Common demo clock — all engines step together
- `SubLineEngine` does NOT subclass or wrap `AssyLineRuntime`
- No change to `AssyLineRuntime` internals

**Tests**: Unit tests for engine state transitions, scenario targeting (5 normal + 1 exception), quality HOLD propagation, production counters.

**Out of scope**: Full genealogy in lightweight engine, API endpoints, frontend.

### S04B-I03 — Overview Projection + Additive API

**Objective**: Build `AssyOverviewSnapshot`, `SubLineSummaryView`, and add API endpoints.

**Files**:
- `src/virtual_factory/assembly/demo_snapshot.py` — add `AssyOverviewSnapshot`, `SubLineSummaryView`, `build_overview()`
- `src/virtual_factory/ui/api.py` — add `GET /assy-demo/overview`, `GET /assy-demo/sub-line/{sub_line_id}`
- Existing endpoints unchanged

**Invariants**:
- `AssyOverviewSnapshot` is fully detached — no runtime references
- `GET /assy-demo/overview` returns 6 `SubLineSummaryView` entries
- `GET /assy-demo/sub-line/{sub_line_id}` returns existing `AssyDemoSnapshot` shape
- Existing `/assy-demo/reset|step|snapshot` response shape unchanged

**Tests**: Integration tests for API contracts, overview consistency (6 sub-lines, correct counters), sub-line detail retrieval for all 6 IDs, error for invalid sub_line_id.

**Out of scope**: Frontend rendering.

### S04B-I04 — ASSY Overview UI (Frame A)

**Objective**: Render the 6-lane ASSY overview matching DG03 Frame A.

**Files**:
- `src/virtual_factory/ui/static/assy_demo.html` — add overview layout
- `src/virtual_factory/ui/static/assy_demo.js` — fetch overview, render 6 lanes
- `src/virtual_factory/ui/static/assy_demo.css` — lane styles, variant colors

**Invariants**:
- All lane data from `GET /assy-demo/overview` API
- 5 normal lanes (green/OPERATING) + 1 exception lane (red/HOLD) during exception scenario
- Hydraulic lanes grouped, Thermal lanes grouped
- Variant labels from API, not hardcoded
- Click a lane → S04B-I05 detail view

**Tests**: UI acceptance: Frame A renders at 1920×1080, lane states match API data, hover/click targets work, no hardcoded lane data.

**Out of scope**: Detail view, inspector, animation.

### S04B-I05 — Sub-line Detail + Selection Routing (Frame B)

**Objective**: Render selected sub-line detail matching DG03 Frame B artboards.

**Files**:
- `src/virtual_factory/ui/static/assy_demo.html` — detail view area
- `src/virtual_factory/ui/static/assy_demo.js` — detail fetch, station rendering, WIP inspector
- `src/virtual_factory/ui/static/assy_demo.css` — detail styles

**Invariants**:
- Detail data from `GET /assy-demo/sub-line/{selected_id}`
- Reuse existing single-line SVG renderer logic where possible
- WIP Inspector populates from snapshot data (not invented)
- STOP/WORK, HOLD, INDEX_SHIFT states derived from `line_state` + `positions[].is_quality_hold`
- Back button to overview

**Tests**: UI acceptance: Frame B renders all 12 stations, WIP inspector shows correct data, state badges match runtime state, back navigation works.

**Out of scope**: Animation, quality inspector panels.

### S04B-I06 — Quality Inspector + Event Interaction (Frame C)

**Objective**: Station Inspector and Event Selected interaction.

**Files**:
- `src/virtual_factory/ui/static/assy_demo.js` — inspector panels, event click handlers
- `src/virtual_factory/ui/static/assy_demo.css` — inspector styles

**Invariants**:
- Station Inspector populates from `positions[]` + filtered `recent_quality_events[]`
- Event Selected highlights linked station + WIP
- All data from existing API snapshot fields
- No fake quality events

**Tests**: UI acceptance: inspector panels populate correctly, event selection highlights correct station/WIP, multiple events selectable, inspector closes cleanly.

**Out of scope**: New API endpoints (uses existing snapshot data).

### S04B-I07 — Motion / Transition Animation

**Objective**: INDEX_SHIFT, LINE_IN, LINE_OUT, JOIN animations.

**Files**:
- `src/virtual_factory/ui/static/assy_demo.js` — animation engine
- `src/virtual_factory/ui/static/assy_demo.css` — transition styles

**Invariants**:
- Animation interpolates between two valid snapshots only
- No manufacturing events invented
- ~500ms INDEX_SHIFT transition
- LINE_IN/LINE_OUT as simple fade
- JOIN as fade + highlight pulse

**Tests**: UI acceptance: INDEX_SHIFT shows pallet movement, no state corruption between transitions, animation respects HOLD (no forward motion during HOLD).

**Out of scope**: Continuous physics simulation, real-time conveyor movement.

### S04B-I08 — Demo Hardening

**Objective**: 1366×768, auto-run polish, scenario switching UX, fallback verified.

**Files**: Same UI files — polish pass.

**Invariants**:
- 1366×768 renders all critical labels legible
- Auto-run cycle works with 6-sub-line overview + detail routing
- Scenario switching resets all engines correctly
- Fallback to single-sub-line S04 demo verified
- All 13 DG03 states demonstrable

**Tests**: Demo rehearsal: HAPPY_PATH full auto-run, AP06_FAIL_RETEST_PASS (5 normal + 1 HOLD → resolution), AP08_NG_REINSPECT, FAILED_FINAL, reset/repeatability, 1366×768 verification, fallback verification.

**Out of scope**: MES, production database, deployment automation.

---

## 17. Test Strategy

### Unit Tests

| Layer | What | Count (est.) |
|-------|------|-------------|
| Identity | `SubLineIdentity` creation, validation, config parsing | 8 |
| Engine | `SubLineEngine` state transitions, occupancy, quality summary | 15 |
| Projection | `SubLineSummaryView` derivation, `AssyOverviewSnapshot` aggregation | 10 |
| Scenario | Targeting logic, override application, 5-normal+1-exception | 8 |
| Status derivation | `is_exception`, `held_station`, line state mapping | 6 |

### Integration Tests

| Scope | What | Count (est.) |
|-------|------|-------------|
| Multi-engine | 6 engines step together, common clock, no divergence | 5 |
| API | `/overview` contract, `/sub-line/{id}` contract, error paths | 8 |
| Scenario | HAPPY_PATH, AP06_FAIL, AP08_NG, FAILED_FINAL across 6 engines | 6 |
| Reset | Full reset, all engines reinitialize, scenario re-applied | 3 |

### Regression Tests

| Scope | What |
|-------|------|
| M6-S02 | All 33 existing tests — no `AssyLineRuntime` changes |
| M6-S03 | All 21 existing tests — no quality engine changes |
| M6-S04 | All 21 existing tests — snapshot shape preserved |
| M2–M5 | 1067 tests — no core changes |

### UI Acceptance Tests

| Scope | What |
|-------|------|
| Frame A | 6 lanes, 5 normal + 1 exception, variant labels, counters |
| Frame B | 12 stations, WIP inspector, state badges |
| Frame C | Station inspector, event selection, linkage highlighting |
| 1920×1080 | All labels readable, no overflow |
| 1366×768 | Compressed layout, critical labels legible |
| Semantic | No fake state, no HAPPY_PATH + HOLD contradiction, no forward INDEX during HOLD |

### Demo Rehearsal

| Scenario | Steps |
|----------|-------|
| HAPPY_PATH | RESET → AUTO run 10 cycles → verify 6 lanes all OPERATING, motors releasing |
| AP06_FAIL_RETEST_PASS | RESET → STEP to HOLD → verify 5 normal + 1 HOLD → continue to RETEST → verify HOLD clears → all 6 OPERATING |
| AP08_NG_REINSPECT | RESET → STEP to NG → verify REINSPECT → continue → verify clear |
| FAILED_FINAL | RESET → STEP to FAILED_FINAL → verify terminal state |
| Reset/repeat | Full reset mid-scenario, verify clean state |

---

## 18. Failure / Rollback Plan

Per SA correction B10:

### Fallback A — Single Detailed Runtime Only (ALWAYS AVAILABLE)

```
- Disable overview API endpoint → return 404 or empty
- Disable multi-engine initialization
- Frontend falls back to single-sub-line S04 demo
- Existing /assy-demo/reset|step|snapshot work unchanged
- 100% backward compatible with S04 closed state
```

**Trigger**: Multi-engine unstable before 17-Aug internal demo.

### Fallback B — Overview as Static + Single Detail

```
- Overview shows static 6-lane layout (hardcoded labels, no live data)
- Single selected sub-line detail works (existing S04 runtime)
- "Live overview coming soon" indicator
```

**Trigger**: Overview API works but frontend 6-lane rendering incomplete.

### Fallback C — Per-Gate Rollback

```
Each S04B-Ixx gate is independently revertible:
- I01 config → revert config file only
- I02 engine → delete sub_line_engine.py, revert controller
- I03 API → delete new endpoints, keep old
- I04-I08 UI → delete new HTML sections, keep old
```

Existing S04 demo always works. New S04B features are additive.

---

## 19. P0 / P1 / P2 Schedule

Per SA correction B11:

### P0 — Required for Internal Demo (17-Aug)

| Item | Gate | Est. Effort |
|------|------|-------------|
| Identity + Config | S04B-I01 | Small (config only) |
| SubLineEngine × 6 | S04B-I02 | Medium |
| Overview Projection + API | S04B-I03 | Medium |
| Frame A: 6-lane overview | S04B-I04 | Medium-Large |
| Frame B: Sub-line detail | S04B-I05 | Medium |
| Fallback verification | Cross-cutting | Small |

### P1 — Required for Official Demo (21-Aug, if P0 Stable)

| Item | Gate | Est. Effort |
|------|------|-------------|
| Frame C: Quality Inspector | S04B-I06 | Medium |
| Motion/Transition Animation | S04B-I07 | Medium |
| 1366×768 Hardening | S04B-I08 | Small |
| Auto-run Polish | S04B-I08 | Small |
| Demo Rehearsal | S04B-I08 | Medium |

### P2 — Defer

| Item | Rationale |
|------|-----------|
| Per-variant station duration overrides | Not needed for demo |
| Full variant-specific process behavior | Incomplete TIPA data |
| Inter-sub-line WIP transfer | No TIPA confirmation |
| MES integration | M6-S05 NOT AUTHORIZED |

---

## 20. Risks / Open Questions

| Risk | Severity | Mitigation |
|------|----------|------------|
| Lightweight engine has subtle state divergence from full runtime | MEDIUM | Use shared process template. Validate engine against full runtime for equivalent scenarios. |
| 6 engines + 1 runtime = initialization time | LOW | All are dataclasses + dicts. Initialization < 100ms. |
| Frontend 6-lane SVG complexity | MEDIUM | Reuse existing single-lane SVG. Loop over sub-lines with vertical offset. |
| Scenario targeting ambiguity (which sub-line gets exception?) | LOW | Configurable default. Demo script controls it. |
| TIPA confirms different physical topology mid-sprint | LOW | Option C architecture accommodates: lightweight engines can be promoted or replaced. |
| Demo time runs out before P1 complete | MEDIUM | Fallback A always available. P0 covers core demo story. |

### Open Questions (for TIPA / Future)

- Are ASSY sub-lines physically independent conveyors? (TBD)
- Do Thermal and Hydraulic variants have different station durations? (TBD)
- Is there shared ASSY-level production coordination? (TBD)
- What is the exact SSO2(H) vs SSO2(T) test/profile difference? (TBD)

These are explicitly NOT blocking S04B. They are deferred to later milestones.

---

## 21. Explicit Implementation Authorization Boundary

```
✅ AUTHORIZED: M6-S04B implementation planning (this document)
✅ AUTHORIZED: After SA closes planning → S04B-I01 through S04B-I08
❌ NOT AUTHORIZED: M6-S05 (MES integration)
❌ NOT AUTHORIZED: Production UI (non-demo)
❌ NOT AUTHORIZED: Runtime semantic changes to M6-S02/S03/S04
❌ NOT AUTHORIZED: Changes to closed DG01–DG03 design
❌ NOT AUTHORIZED: Direct push to main
❌ NOT AUTHORIZED: Merge without SA explicit approval
```

---

## Planning Self-Review

### Completeness
- **What was missing from the original plan?**
  - Canonical identity hierarchy (plant_id → line_id → sub_line_id)
  - Known vs unknown physical topology distinction
  - Option comparison (A/B/C)
  - Demo execution policy separation
  - Scenario targeting policy (5 normal + 1 exception)
  - Animation derivation model
  - Additive API principle
  - Config composition (process vs deployment)
  - Full DG03 traceability matrix
  - Test strategy by layer
  - Fallback/rollback plan
  - P0/P1/P2 prioritization
  - Implementation gates with invariants
- **What is still intentionally deferred?**
  - Physical topology confirmation (TIPA)
  - Full variant-specific process behavior (TIPA)
  - MES integration (M6-S05)

### Consistency
- **What contradictions were found and removed?**
  - "Independent sub-lines" vs TIPA unconfirmed physical topology → removed, replaced with logical execution contexts
  - `line_id = "ASSY-SL01"` vs canonical `production_line_id = ASSY, sub_line_id = ASSY-SLxx` → corrected
  - "Step all six runtimes" as implicit synchronization → labeled as DEMO_EXECUTION_POLICY
  - Changing existing API response shape vs backward compatibility → additive API design
  - 6 full runtimes as default vs unconfirmed independence → Option C hybrid recommended

### Necessity
- **What originally proposed work was removed as unnecessary?**
  - 6 × full `AssyLineRuntime` instances (→ lightweight engines for 5, full for 1 selected)
  - `AssySubLine` wrapper with flattened identity (→ proper hierarchy)
  - Changing existing endpoint response shapes (→ additive API)
  - "Independent" conveyor/physical claims (→ logical execution contexts)

### Architecture
- **What assumptions were downgraded to TBD/demo policy?**
  - Sub-line physical independence → downgraded to TBD
  - Shared synchronization → downgraded to TBD
  - Common clock as plant truth → DEMO_EXECUTION_POLICY
  - Variant as UI label → configuration dimension with incomplete data

### Sequence
- **Why is the new implementation order safe?**
  - I01 (identity + config) has zero runtime impact — pure definition
  - I02 (engines) is self-contained — no existing code modified
  - I03 (API) is additive — existing endpoints unchanged
  - Backend gate before any UI work
  - Each UI gate builds on the previous, no circular dependencies

### Demo Risk
- **What is the minimum fallback if time runs out?**
  - Fallback A: existing S04 single-sub-line demo works unchanged
  - All new endpoints are additive — disabling them doesn't break S04
  - P0 (overview + detail) is the core demo story; P1 is polish

### Confidence

```
Architecture confidence:    HIGH
  - Identity model is unambiguous
  - Option C is well-scoped and reversible
  - No runtime semantics changed
  - Additive API preserves existing contracts

Demo feasibility confidence: MEDIUM
  - P0 (overview + detail) is achievable before 17-Aug
  - P1 (inspector + animation) depends on P0 stability
  - Frontend 6-lane SVG complexity is the main unknown
  - Fallback A eliminates all demo risk

Known unresolved risks:
  - Frontend SVG 6-lane rendering complexity (not yet proven in code)
  - Lightweight engine state fidelity vs full runtime (needs validation)
  - 17-Aug deadline pressure on P1 scope
```

---

## Scope

- ✅ M6-S04B implementation planning C01 — full architecture correction + integrity review
- ✅ DG03 traceability complete (all 13 states)
- ✅ Option comparison + recommendation (Option C)
- ✅ Implementation gates defined with invariants and tests
- ✅ Fallback plan defined
- ✅ P0/P1/P2 schedule
- ❌ No runtime code changes
- ❌ No production UI implementation
- ❌ No MES / M6-S05
- ❌ DG01–DG03 remain closed

---

> **M6-S04B Implementation Planning C01 is READY FOR SA REVIEW.**
>
> Next: SA approval → S04B-I01 (Identity + Config + Engine Contract).
