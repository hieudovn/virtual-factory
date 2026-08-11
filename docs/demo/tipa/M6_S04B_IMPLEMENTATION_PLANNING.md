# M6-S04B — Implementation Planning / Technical Mapping

> **Status**: PLANNING — authorized by SA after DG03 closure.  
> **Baseline**: `cf20843` (DG03 visual design frozen)  
> **Purpose**: Map 13 visual design states → current runtime capability → gap → minimal plan.  
> **Rule**: Do NOT invent UI state. Do NOT create fake 6-line data. Do NOT start M6-S05.

---

## 1. Current Runtime Landscape

### 1.1 What Exists (M6-S02 through M6-S04)

| Layer | Module | Capability |
|-------|--------|------------|
| Config | `tipa_assy_demo.yaml` | ONE conveyor, 12 stations (PRE-ASSY..AP11), station durations, quality config |
| Runtime | `AssyLineRuntime` | ONE synchronized indexed line. STOP→OPERATING→READY→INDEX. Multi-WIP concurrent dwell. AP04 genealogy. Quality HOLD/retest. |
| Controller | `DemoController` | RESET/STEP/AUTO/PAUSE/SPEED. 4 scenarios. Single runtime instance. |
| Snapshot | `AssyDemoSnapshot` | Detached read model from 1 runtime. `StationPositionView[]`, `GenealogySummary[]`, `QualityEventView[]`, `ProductionSummary`. |
| API | `/assy-demo/*` | reset/step/snapshot → single snapshot dict. |
| Frontend | `assy_demo.html/js/css` | Single-line visualization. Step/auto/reset controls. Scenario selector. |

### 1.2 Snapshot Data Model (→ API JSON)

Each `/assy-demo/snapshot` returns:
```json
{
  "simulation_time_s": 480.0,
  "line_state": "stopped",
  "dwell_number": 8,
  "nominal_dwell_s": 120.0,
  "positions": [
    {
      "position_id": "AP06",
      "station_label": "AP06 — Electrical / functional test",
      "carrier_id": "PAL-003",
      "wip_id": "MTR-0015",
      "wip_type": "MTR",
      "manufacturing_status": "at_station",
      "quality_status": "retest_pending",
      "latest_quality_result": "FAIL",
      "attempt_number": 1,
      "is_occupied": true,
      "is_quality_hold": true,
      "held_reason": "FAIL (attempt 1)"
    }
  ],
  "genealogy": [...],
  "recent_quality_events": [...],
  "production": {
    "motors_created": 3,
    "motors_released": 1,
    "wips_on_line": 5,
    "active_quality_holds": 1,
    "sso2_buffer": 3,
    "rso2_buffer": 2
  },
  "scenario": "AP06_FAIL_RETEST_PASS"
}
```

**Key observation**: The snapshot is a flat list of positions on ONE line. There is no sub-line ID, no variant tag, no lane grouping.

---

## 2. Design State → Runtime Mapping

### 2.1 Directly Mappable (Runtime Already Supports)

| # | Design State | Runtime Source | Confidence |
|---|-------------|----------------|------------|
| 3 | Normal shared dwell | `line_state: "operating"` + multiple `positions[].is_occupied=true` + all `quality_status: "clear"` | ✅ HIGH |
| 4 | INDEX_SHIFT | `line_state: "indexing"` → `line_state: "stopped"`, carriers advance 1 position | ✅ HIGH |
| 5 | AP04 JOIN | `genealogy[]` entries, `wip_type: "MTR"` at position AP04 | ✅ HIGH |
| 6 | AP06 FAIL/HOLD | `quality_status: "retest_pending"`, `is_quality_hold: true`, `held_reason: "FAIL (attempt 1)"` | ✅ HIGH |
| 7 | AP06 RETEST PASS | After retest dwell: `quality_status: "clear"`, `latest_quality_result: "PASS"` | ✅ HIGH |
| 8 | AP08 NG/REINSPECT | `quality_status: "reinspect_pending"`, `held_reason: "NG (attempt 1)"` | ✅ HIGH |
| 9 | AP11 RELEASED | `manufacturing_status: "released"` at AP11, `production.motors_released += 1` | ✅ HIGH |
| 10 | WIP Inspector | Any occupied position: read `wip_id`, `carrier_id`, `manufacturing_status`, `quality_status`, `genealogy[]` for that WIP, `recent_quality_events[]` filtered by WIP | ✅ MEDIUM (aggregation needed) |
| 11 | Station Inspector | Filter positions by `position_id`, read `wip_id`, `quality_status`, recent events for that station | ✅ MEDIUM (aggregation needed) |
| 12 | Event Selected | `recent_quality_events[]` entry → link to `positions[]` by station_id, link to WIP by wip_id | ✅ MEDIUM (cross-reference needed) |
| 13 | 1366×768 | CSS responsive + SVG viewBox — already proven in Artboard 4 | ✅ HIGH |

### 2.2 Partially Mappable (Single-Line Runtime → Multi-Line UI Gap)

| # | Design State | Gap |
|---|-------------|-----|
| 1 | ASSY Line Overview — Normal (6 lanes) | Runtime has 1 line. No sub-line identity. No variant tag. No per-lane production counters. |
| 2 | ASSY Line Overview — Exception (6 lanes, 1 hold) | Same as above + need per-lane quality status aggregation. |

---

## 3. Gap Analysis — Single Line → 6 Sub-Lines

### 3.1 Structural Gaps

| Gap ID | Description | Severity |
|--------|-------------|----------|
| G-01 | **No sub-line identity**: `AssyLineRuntime` has no `line_id`, no variant tag (Hydraulic vs Thermal). | 🔴 Blocker for 6-lane UI |
| G-02 | **Single runtime**: `DemoController` holds ONE `AssyLineRuntime`. 6 sub-lines would need 6 runtimes or a multi-line runtime. | 🔴 Blocker for 6-lane UI |
| G-03 | **Single snapshot**: `/assy-demo/snapshot` returns 1 flat `positions[]`. No per-line grouping. | 🔴 Blocker for per-lane rendering |
| G-04 | **Single config**: `tipa_assy_demo.yaml` describes 1 line. No sub-line array. | 🟡 Medium |
| G-05 | **No variant distinction in runtime**: Both Hydraulic and Thermal sub-lines use identical station setup. Only input source differs (SSO2(H) vs SSO2(T)). | 🟡 Medium |
| G-06 | **Frontend single-lane**: `assy_demo.html` renders 1 line topology. | 🔴 Blocker for 6-lane UI |

### 3.2 What Does NOT Need Changing

- ✅ Station processing semantics (dwell, concurrent work, quality)
- ✅ AP04 JOIN genealogy model
- ✅ Quality HOLD / retest / reinspect / FAILED_FINAL lifecycle
- ✅ INDEX / conveyor synchronization
- ✅ Scenario override mechanism
- ✅ Control actions (RESET/STEP/AUTO/PAUSE/SPEED)
- ✅ AssyDemoSnapshot data fields (they're correct, just need grouping)
- ✅ API endpoint structure (can be extended, not rewritten)

---

## 4. Minimal Implementation Plan

### 4.1 Principle: Extend, Don't Rewrite

The 6 sub-lines are **independent, identically-structured** lines with different input variant labels. They do not interact. This means we can model them as 6 instances of the same runtime, not a fundamentally different architecture.

### 4.2 Phase 1 — Backend Multi-Line Foundation (MINIMAL)

#### P1.1 — Config: Sub-line Array
Extend `tipa_assy_demo.yaml`:
```yaml
sub_lines:
  - id: ASSY-SL01
    variant: hydraulic
    label: "ASSY-SL01 — Hydraulic"
  - id: ASSY-SL02
    variant: hydraulic
    ...
  - id: ASSY-SL04
    variant: thermal
    ...
```
Shared: conveyor positions, station durations, quality config, upstream config.
Per-sub-line: id, variant, label.

#### P1.2 — Runtime: `AssySubLine` Wrapper
Thin wrapper that pairs an `AssyLineRuntime` with its sub-line identity:
```python
@dataclass
class AssySubLine:
    line_id: str       # "ASSY-SL01"
    variant: str       # "hydraulic" | "thermal"
    label: str
    runtime: AssyLineRuntime
```
No change to `AssyLineRuntime` internals. The runtime doesn't need to know it's a sub-line.

#### P1.3 — Controller: Multi-Line Management
Extend `DemoController`:
- `_sub_lines: dict[str, AssySubLine]` — 6 sub-lines
- `initialize()` creates all 6
- `step()` steps all 6 (or only active ones)
- `reset()` resets all 6
- Scenario applies uniformly (all sub-lines same scenario for demo)
- (Optional later): per-sub-line scenario injection

#### P1.4 — Snapshot: Multi-Line Aggregation
Extend `AssyDemoSnapshot`:
```python
@dataclass
class AssyMultiLineSnapshot:
    simulation_time_s: float
    sub_lines: list[SubLineSnapshot]  # one per sub-line
    production: ProductionSummary     # aggregated

@dataclass  
class SubLineSnapshot:
    line_id: str
    variant: str
    label: str
    line_state: str
    dwell_number: int
    positions: list[StationPositionView]
    genealogy: list[GenealogySummary]
    recent_quality_events: list[QualityEventView]
    production: ProductionSummary
```

#### P1.5 — API: Extended Endpoints
- `POST /assy-demo/step` → returns `AssyMultiLineSnapshot`
- `POST /assy-demo/snapshot` → returns `AssyMultiLineSnapshot`
- `POST /assy-demo/reset` → returns `AssyMultiLineSnapshot`
- (NEW) `GET /assy-demo/sub-line/{line_id}` → returns `SubLineSnapshot` for detail view

Backward compatible: existing endpoints return new shape; frontend update handles it.

### 4.3 Phase 2 — Frontend Multi-Lane Rendering (After P1 Backend)

#### P2.1 — Frame A: 6-Lane Overview
- Render 6 horizontal lanes, grouped by variant (3 Hydraulic + 3 Thermal)
- Per lane: `line_state`, `dwell_number`, `production.motors_created`, `production.motors_released`
- Exception highlighting: any lane with `production.active_quality_holds > 0` → red border
- Color scheme: Hydraulic lanes #111d30, Thermal lanes #141028 (from design guide)

#### P2.2 — Frame B: Sub-Line Detail (Selected Lane)
- Click a lane in Frame A → navigate to detail view
- Detail = current `positions[]` rendered as the 12-station physical flow
- States: STOP/WORK, INDEX_SHIFT, HOLD — driven by snapshot data, not invented
- Right panel: WIP Inspector (selected WIP from clicked station)

#### P2.3 — Frame C: Quality States + Inspector
- Quality event log from `recent_quality_events[]`
- Station Inspector: click a station → show station detail
- Event Selected: click an event → highlight station + WIP

### 4.4 What We Do NOT Build (Yet)

- ❌ Per-sub-line independent scenarios (all 6 share scenario for demo)
- ❌ Inter-sub-line WIP transfer (sub-lines are independent)
- ❌ Different station layouts per sub-line (identical topology)
- ❌ Per-sub-line timing variations (shared config)
- ❌ MES integration (M6-S05 — NOT AUTHORIZED)
- ❌ Production database / persistence

---

## 5. Phase Execution Order

```
P1.1 Config sub-line array          [1 file, ~30 lines YAML]
  ↓
P1.2 AssySubLine wrapper            [1 new file, ~40 lines]
  ↓
P1.3 DemoController multi-line      [1 file edit, ~60 lines changed]
  ↓
P1.4 MultiLineSnapshot + builder    [1 file edit, ~80 lines added]
  ↓
P1.5 API extended endpoints         [1 file edit, ~30 lines changed]
  ↓
  ═══ BACKEND GATE — verify all 6 sub-lines respond ═══
  ↓
P2.1 Frame A: 6-lane overview       [assy_demo.html/js/css — major update]
  ↓
P2.2 Frame B: sub-line detail       [same files — detail view routing]
  ↓
P2.3 Frame C: quality + inspector   [same files — event/inspector panels]
```

---

## 6. Design State → API Data Mapping (Reference)

This is the authoritative mapping for frontend implementation:

| Visual Element | Snapshot Field | Condition |
|----------------|---------------|-----------|
| Lane status badge (OPERATING/STOPPED/HOLD) | `sub_line.line_state` | Map `operating`→OPERATING, `stopped`→STOPPED, HOLD if `active_quality_holds > 0` |
| Variant label (HYDRAULIC/THERMAL) | `sub_line.variant` | `hydraulic`→"SSO2(H)", `thermal`→"SSO2(T)" |
| Station occupied (dot filled) | `position.is_occupied` | `true` → filled dot |
| Station active (WORK indicator) | `position.is_occupied && line_state == "operating" && !position.is_quality_hold` | Station doing work |
| Station HOLD (red border) | `position.is_quality_hold` | `true` → red stroke |
| Station PASS (green) | `position.latest_quality_result == "PASS"` | Green check |
| Station FAIL (red) | `position.latest_quality_result == "FAIL"` | Red X |
| WIP token on conveyor | `position.wip_id` | Display token badge |
| AP04 JOIN indicator | `position.position_id == "AP04" && position.wip_type == "MTR"` | Show parents |
| AP11 RELEASED | `position.manufacturing_status == "released"` | Cyan arrow out |
| Production counters | `production.motors_created`, `production.motors_released` | Per-lane stats |
| Quality events feed | `recent_quality_events[]` | Filterable by station/WIP |

---

## 7. Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| 6 runtimes = 6× memory/CPU | Runtime is lightweight dataclasses + dicts. 6 instances ≈ trivial overhead. |
| Independent sub-lines diverge in simulation time | All 6 share same `step()` → same `simulation_time_s`. Controller ensures sync. |
| Frontend 6-lane SVG complexity | Reuse existing single-lane rendering. Wrap in a loop over sub-lines. |
| "Fake" 6-line data (SA concern) | Every data point comes from actual runtime state. No hardcoded mock data in frontend. |

---

## 8. Scope

- ✅ M6-S04B implementation planning only
- ✅ Maps design states → runtime capabilities → gaps
- ✅ Proposes minimal extension path (extend, don't rewrite)
- ✅ No runtime changes until plan is SA-approved
- ❌ No M6-S05 (MES)
- ❌ No production UI implementation
- ❌ No code changes in this phase

---

> **M6-S04B Implementation Planning is READY FOR SA REVIEW.**  
> Next: SA approval → P1.1 backend multi-line foundation.
