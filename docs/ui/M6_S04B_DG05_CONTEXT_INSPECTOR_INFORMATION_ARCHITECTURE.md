# M6-S04B-DG05 — Frame C Context Inspector Information Architecture

> **Status**: DESIGN-ONLY. Frame C information architecture + projection contract.  
> **Baseline**: I05 CLOSED at `ad3d0ad`. DG04 CLOSED.  
> **Purpose**: Freeze the production contract for M6-S04B-I06 (Quality Inspector + Event Interaction).  
> **Rule**: Design only. No implementation. No backend changes in this gate.

---

## 1. Purpose

Freeze the contract for:

`M6-S04B-I06 — Quality Inspector + Event Interaction (Frame C)`

Frame C is a contextual drill-down attached to the currently selected station, WIP, or quality event. The physical Frame B canvas remains the primary spatial context.

---

## 2. Frame C UX Role

```
Frame A Overview = detect        (6 sub-lines simultaneously)
       ↓
Frame B Sub-line Detail = understand  (1 sub-line, physical canvas)
       ↓
Frame C Context Inspector = investigate  (station/WIP/quality drill-down)
```

Frame C is **not** another dashboard. It is a contextual overlay/panel that answers:

1. What is the current state of this station/WIP?
2. What quality decisions have been made for this WIP?
3. What measurements were taken? In range or out?
4. What checklist items were recorded?
5. Where did this MTR come from? (genealogy)
6. What happens when a WIP moves or exits the line?

---

## 3. Current Public Detail Contract

Detail source: `GET /assy-demo/sub-line/{sub_line_id}` → `AssyDemoSnapshot`

### Identity/state fields
`plant_id`, `production_line_id`, `sub_line_id`, `variant`, `simulation_time_s`, `line_state`, `dwell_number`, `nominal_dwell_s`, `scenario`

### `positions[]`
`position_id`, `station_label`, `carrier_id`, `wip_id`, `wip_type`, `manufacturing_status`, `quality_status`, `latest_quality_result`, `attempt_number`, `is_occupied`, `is_quality_hold`, `held_reason`

### `genealogy[]`
`child_wip_id`, `parent_wip_ids`, `component_ids`, `join_time_s`, `join_station`

### `recent_quality_events[]`
`event_type`, `wip_id`, `station_id`, `disposition`, `attempt`, `simulation_time_s`

### `production`
`motors_created`, `motors_released`, `wips_on_line`, `active_quality_holds`, `sso2_buffer`, `rso2_buffer`

---

## 4. Runtime-vs-Projection Analysis

### 4.1 Existing runtime quality data (NOT yet projected)

`AssyLineRuntime.get_quality_history(wip_id)` returns `QualityHistory` containing:

```python
QualityRecord (frozen, slots):
  record_id: str
  wip_id: str
  station_id: str
  check_type: CheckType          # CHECKLIST | MEASUREMENT | TEST | VISUAL_INSPECTION | FINAL_QC
  disposition: str               # PASS | FAIL | NG | HOLD
  attempt_number: int
  simulation_time_s: float
  measurements: tuple[MeasurementValue, ...]
  checklist_items: tuple[str, ...]
  reason_code: str

MeasurementValue (frozen, slots):
  name: str
  value: float
  unit: str
  expected_min: Optional[float]
  expected_max: Optional[float]
  in_range: bool                  # computed property
```

### 4.2 Current snapshot projection

`build_snapshot()` already iterates `qh.records` to populate:

- `positions[].latest_quality_result` (from latest record at that station)
- `positions[].attempt_number`
- `positions[].is_quality_hold`
- `positions[].held_reason`
- `recent_quality_events[]` (flat list, last 20, station-agnostic)

### 4.3 What is NOT projected

| Data | In runtime? | In snapshot? |
|------|------------|-------------|
| Full per-WIP quality record history | Yes (`QualityHistory.records`) | No (only `latest_quality_result` + flat `recent_quality_events`) |
| `check_type` per record | Yes | No (`QualityEventView.event_type` exists but not populated from `rec.check_type.value`) |
| `measurements[]` with name/value/unit/min/max | Yes | No |
| `checklist_items[]` (item names) | Yes | No |
| `reason_code` | Yes | No |
| Per-checklist-item disposition (PASS/FAIL) | **No** — runtime stores item names only, not per-item results | N/A |

### 4.4 Actual runtime quality generation

| Station | Check type | Measurements generated | Checklist items generated |
|---------|-----------|----------------------|--------------------------|
| AP03 | CHECKLIST | — | `mechanical_prep_ok`, `visual_check_ok`, `measurement_subset_ok` |
| AP06 | TEST | `R_U-V`, `R_V-W`, `R_W-U` (Ω, with expected ranges) | — |
| AP08 | VISUAL_INSPECTION | — | `surface_quality`, `label_presence`, `assembly_alignment` |
| AP11 | FINAL_QC | — | `packaging_integrity`, `label_correct`, `documentation_complete` |

All measurement and checklist data is existing simulation truth — no fabrication needed.

---

## 5. Architecture Decision: Option A vs Option B

### Option A — Frontend-only (existing snapshot only)

**What Frame C could show**:
- Station/WIP summary from `positions[]` ✓
- Genealogy from `genealogy[]` ✓
- Flat event list from `recent_quality_events[]` ✓
- Production counters ✓

**What Frame C could NOT show**:
- Per-record `check_type` (TEST vs CHECKLIST vs VISUAL_INSPECTION vs FINAL_QC)
- Measurement values with expected ranges (AP06 electricals)
- Checklist item names (AP03, AP08, AP11)
- `reason_code`
- Per-WIP attempt history grouped by station

**Verdict**: Technically feasible but would produce a shallow Inspector that doesn't meaningfully differentiate from the existing Frame B right-panel event strip + station hover. The Frame C value proposition — "investigate" — requires the detail that exists in runtime but isn't projected.

### Option B — Narrow additive projection (embedded in existing snapshot)

**Add one field to `AssyDemoSnapshot`**:

```
quality_records: list[QualityRecordView]
```

Where `QualityRecordView` is a **detached, serializable read model** built from `QualityRecord`:

```
record_id, wip_id, station_id, check_type, disposition,
attempt_number, simulation_time_s,
measurements[], checklist_items[], reason_code
```

**Constraints**:
- Projection only — no runtime mutation
- Built from `runtime.get_quality_history(wip_id).records` (public API)
- Detached — no mutable runtime references
- Backward compatible — additive field, existing S04/S04B fields unchanged
- No new API endpoint — single `/sub-line/{id}` refresh

**Payload estimate**: Typical demo has ~20 quality records across all WIPs. Each record with measurements/checklist adds ~200-500 bytes. Total additive payload: ~4-10KB. Acceptable for a single-refresh detail endpoint.

### RECOMMENDATION: **Option B — embedded additive field**

**Rationale**:
1. Simplest for frontend: single `refresh()` call, all data available
2. `build_snapshot()` already iterates `qh.records` — projection is additive, not restructured
3. No new route, no new error handling, no new failure modes
4. Payload increase is modest (≤10KB)
5. Makes Frame C genuinely useful: measurements, checklists, attempt history
6. No runtime/domain changes — data already exists

---

## 6. Frozen Projection Contract for I06

### 6.1 Additive field: `quality_records[]`

Add to `AssyDemoSnapshot`:

```python
@dataclass
class QualityRecordView:
    """Detached read model of one quality record. Built from QualityRecord only."""
    record_id: str = ""
    wip_id: str = ""
    station_id: str = ""
    check_type: str = ""          # "CHECKLIST" | "MEASUREMENT" | "TEST" | "VISUAL_INSPECTION" | "FINAL_QC"
    disposition: str = ""         # "PASS" | "FAIL" | "NG" | "HOLD"
    attempt_number: int = 0
    simulation_time_s: float = 0.0
    measurements: list[dict] = field(default_factory=list)   # [{name, value, unit, expected_min?, expected_max?}]
    checklist_items: list[str] = field(default_factory=list)
    reason_code: str = ""

    def to_dict(self) -> dict: ...
```

Add to `AssyDemoSnapshot`:

```python
quality_records: list[QualityRecordView] = field(default_factory=list)
```

### 6.2 Build logic (in `build_snapshot`)

For each `wip_id` in `runtime.wip_ids`:
1. `qh = runtime.get_quality_history(wip_id)`
2. If `qh`, iterate `qh.records`
3. For each `QualityRecord`, construct `QualityRecordView` with all fields projected

Existing `recent_quality_events[]` and `positions[]` quality fields remain unchanged.

### 6.3 Backend scope for I06

**Files allowed to change**:
- `src/virtual_factory/assembly/demo_snapshot.py` — add `QualityRecordView`, add field to `AssyDemoSnapshot`, update `build_snapshot()`
- `tests/` — add quality record projection tests

**Files forbidden to change**:
- `line_runtime.py` — no behavior changes
- `quality_records.py` — no domain model changes
- `demo_controller.py` — no orchestration changes
- `api.py` — no route changes (existing `/sub-line/{id}` already returns full snapshot)
- `demo_composition.py` — no composition changes
- conveyor, WIP lifecycle, simulation timing — no changes

---

## 7. Frame C Inspector Information Architecture

### 7.1 Inspector Views

| View | Content | Source |
|------|---------|--------|
| **Summary** | Station ID/label, WIP ID/type, carrier, manufacturing status, quality status, latest disposition, attempt, held reason | `positions[]` |
| **Quality History** | Chronological quality records for selected WIP: check type, station, disposition, attempt, time, reason_code | `quality_records[]` (filtered by `wip_id`) |
| **Measurements** | Name, actual value, unit, expected min/max, in/out-of-range indicator | `quality_records[].measurements[]` |
| **Checklist** | Item names from `checklist_items[]` under overall record disposition | `quality_records[].checklist_items[]` |
| **Genealogy** | Parent SSO2 + RSO2 → child MTR, join station, join time | `genealogy[]` |
| **Events** | Filtered quality events/records, click-to-highlight in Frame B | `quality_records[]` + `recent_quality_events[]` |

### 7.2 Visual Layout (1920×1080)

```
┌──────────────────────────────────────────────────────────┐
│ Frame B header + controls (unchanged)                    │
├──────────────────────────────────────┬───────────────────┤
│                                      │ INSPECTOR         │
│   Physical Canvas (Frame B)          │ ┌───────────────┐ │
│   (slightly reduced width when       │ │ Summary       │ │
│    Inspector is open)                │ │ AP06 / TEST   │ │
│                                      │ │ MTR-0003      │ │
│                                      │ │ PASS #1       │ │
│                                      │ └───────────────┘ │
│                                      │ ┌───────────────┐ │
│                                      │ │ Quality Hist  │ │
│                                      │ │ AP06 TEST     │ │
│                                      │ │ PASS t=420s   │ │
│                                      │ └───────────────┘ │
│                                      │ ┌───────────────┐ │
│                                      │ │ Measurements  │ │
│                                      │ │ R_U-V 1.23 Ω  │ │
│                                      │ │ [0.8–1.5] ✓   │ │
│                                      │ └───────────────┘ │
│                                      │ ┌───────────────┐ │
│                                      │ │ Genealogy     │ │
│                                      │ │ SSO2+RSO2→MTR │ │
│                                      │ └───────────────┘ │
├──────────────────────────────────────┴───────────────────┤
│ Event strip + zoom controls (unchanged)                  │
└──────────────────────────────────────────────────────────┘
```

### 7.3 Inspector Sections (Priority Order)

1. **Summary** — always visible, collapsible
2. **Quality History** — chronological, collapsible, filtered to selected WIP
3. **Measurements** — shown only when records have `measurements[]` (AP06)
4. **Checklist** — shown only when records have `checklist_items[]` (AP03, AP08, AP11)
5. **Genealogy** — shown for MTR WIPs, collapsible

### 7.4 Checklist Truthfulness Rule

Runtime stores checklist item **names** but does **not** store per-item PASS/FAIL status. The overall record `disposition` (PASS/FAIL/NG) applies to the entire check.

**I06 rendering rule**:
- Show checklist items as a list of **recorded item names**
- Show the **overall record disposition** as the check result
- Do **NOT** invent individual PASS/FAIL checkmarks per item
- Do **NOT** fabricate per-item results

Example (AP03 CHECKLIST, disposition=PASS):
```
✓ CHECKLIST — PASS (attempt 1, t=180s)
  Recorded items: mechanical_prep_ok, visual_check_ok, measurement_subset_ok
```

Not:
```
✓ mechanical_prep_ok  ← FAKE (not in data model)
✓ visual_check_ok     ← FAKE
✓ measurement_subset_ok ← FAKE
```

### 7.5 Measurements Rendering

Example (AP06 TEST, disposition=PASS):
```
📏 TEST Measurements — t=420s
  R_U-V  1.23 Ω  [0.8 – 1.5]  ✓ IN RANGE
  R_V-W  1.18 Ω  [0.8 – 1.5]  ✓ IN RANGE
  R_W-U  0.72 Ω  [0.8 – 1.5]  ✗ OUT OF RANGE
```

The `in_range` property (computed from `expected_min`/`expected_max`) is truthfully projected from `MeasurementValue.in_range`.

---

## 8. Selection Model

### 8.1 Station Selection (primary)

Click station node in Frame B → Inspector opens with:
- Station context: station ID, label, current occupant (if any)
- If occupied: WIP becomes associated context, quality/genealogy sections populate
- If empty: station context only, quality/genealogy sections hidden

### 8.2 WIP Selection (secondary)

Click WIP token/carrier in Frame B → Inspector opens with:
- WIP context: WIP ID, type, carrier, manufacturing status
- Quality history filtered to that WIP
- Measurements/checklist for that WIP
- Genealogy for MTR WIPs

### 8.3 Event Selection (tertiary)

Click event in event strip or quality history → Inspector:
- Selects/highlights linked station in Frame B canvas
- Selects linked WIP
- Opens Inspector to the relevant quality record section

### 8.4 Selection Precedence

1. If station is clicked → station selection with associated WIP
2. If WIP token is clicked → WIP selection, station is spatial context
3. If event is clicked → highlight station + select WIP + Inspector shows quality context

Only one selection active at a time. Clicking empty canvas area clears selection.

---

## 9. Refresh / Selection Persistence

### 9.1 STEP/AUTO behavior

| Scenario | Behavior |
|----------|----------|
| Selected WIP remains on line | Preserve WIP identity selection; update physical highlight to current `positions[]` |
| Selected WIP in HOLD | Preserve context; show latest quality record; physical highlight stays at held station |
| Selected WIP moves to next station | Physical highlight follows from `positions[]` |
| Selected WIP leaves line / released | Physical highlight disappears; Inspector shows historical context with "Not on line" indicator |
| Selected station becomes empty | Inspector station context remains valid; occupancy section shows "Empty" |

### 9.2 Inspector state across steps

- Inspector open/collapsed state: preserved across STEP/AUTO
- Selected WIP/station identity: preserved if still on line
- Quality data: refreshed from latest snapshot on each step
- Inspector does NOT close automatically on step

### 9.3 Inspector state across navigation

- Frame B → Frame A → Frame B: Inspector resets to collapsed/closed
- Switching sub-lines within Frame B (future): Inspector resets

---

## 10. Responsive Behavior

### 1920×1080
- Inspector panel: 320px right side
- Physical canvas: remaining width (~1600px)
- All Inspector sections visible with scrolling
- Station/WIP labels remain readable

### 1366×768
- Inspector: overlay or narrow panel (240px)
- Physical canvas: fills width when Inspector closed
- Inspector sections: collapsible, scrollable
- Operational text: 11px minimum

---

## 11. Truthfulness Invariants

1. `positions[]` = sole source for current physical occupancy
2. `genealogy[]` = relationship/history truth; never implies current position
3. `quality_records[]` = quality decision/history truth
4. Historical data must not be converted into current physical occupancy
5. Overall record disposition must not be expanded into fake per-item checklist dispositions
6. Measurement limits shown only when actual `expected_min`/`expected_max` exist
7. No station progress percentage (no data source)
8. Simulation time only — no wall-clock timestamps
9. Demo data identified as synthetic where appropriate
10. `in_range` computed from actual min/max, not fabricated

---

## 12. DATA GAP Matrix

| Desired Inspector Element | Runtime? | Snapshot (post-I06)? | Classification |
|---|---|---|---|
| WIP current state | Yes | Yes (`positions[]`) | EXISTING / USE DIRECTLY |
| Station current state | Yes | Yes (`positions[]`) | EXISTING / USE DIRECTLY |
| Genealogy | Yes | Yes (`genealogy[]`) | EXISTING / USE DIRECTLY |
| Quality record history (flat) | Yes | Yes (`quality_records[]`) | ADDITIVE PROJECTION |
| Quality record history (per-WIP) | Yes | Yes (filter `quality_records[]` by `wip_id`) | ADDITIVE PROJECTION |
| `check_type` per record | Yes | Yes | ADDITIVE PROJECTION |
| Measurements (name/value/unit/min/max) | Yes | Yes | ADDITIVE PROJECTION |
| Expected min/max | Yes | Yes | ADDITIVE PROJECTION |
| `in_range` computation | Yes | Yes (project from `MeasurementValue.in_range`) | ADDITIVE PROJECTION |
| Checklist item names | Yes | Yes | ADDITIVE PROJECTION |
| Per-checklist-item disposition | **No** — runtime stores names only | **No** | DATA GAP / DEFER |
| `reason_code` | Yes | Yes | ADDITIVE PROJECTION |
| Test attempt history (AP06) | Yes | Yes (filter by station) | ADDITIVE PROJECTION |
| Visual inspection attempt history (AP08) | Yes | Yes | ADDITIVE PROJECTION |
| Final QC history (AP11) | Yes | Yes | ADDITIVE PROJECTION |
| Per-station elapsed/progress | **No** | **No** | DATA GAP / DEFER |
| Wall-clock timestamps | **No** | **No** | OUT OF SCOPE |
| Operator identity | **No** | **No** | OUT OF SCOPE / M6-S05+ |
| Equipment/sensor raw data | **No** | **No** | OUT OF SCOPE / M6-S05+ |
| MES work order/order context | **No** | **No** | OUT OF SCOPE / M6-S05+ |

---

## 13. I06 Acceptance Matrix

| # | Criterion | Source |
|---|-----------|--------|
| 1 | Inspector opens on station click in Frame B | Selection |
| 2 | Inspector opens on WIP/carrier click in Frame B | Selection |
| 3 | Inspector opens on event click in event strip | Selection |
| 4 | Summary view: station ID/label, WIP ID/type, carrier, status, disposition, attempt, held reason | `positions[]` |
| 5 | Quality history: chronological records for selected WIP with check_type, station, disposition, attempt, time | `quality_records[]` |
| 6 | Measurements: name, value, unit, expected min/max, in-range indicator (AP06) | `quality_records[].measurements[]` |
| 7 | Checklist: item names with overall record disposition, no fake per-item checkmarks | `quality_records[].checklist_items[]` |
| 8 | Genealogy: parent→child, join station, join time (MTR WIPs) | `genealogy[]` |
| 9 | AP06 retest history visible (multiple attempts) | `quality_records[]` |
| 10 | AP08 reinspect history visible | `quality_records[]` |
| 11 | AP11 FINAL_QC context visible | `quality_records[]` |
| 12 | Failed-final state: terminal quality record + status | `quality_records[]` + `positions[]` |
| 13 | Event click → physical highlight in Frame B canvas | Selection |
| 14 | Selection persists across STEP (WIP still on line) | Refresh model |
| 15 | Released/exited WIP: Inspector shows historical context with "Not on line" | Refresh model |
| 16 | Empty station: summary shows station, occupancy empty | `positions[]` |
| 17 | 1920×1080: Inspector panel 320px, all sections scrollable | Responsive |
| 18 | 1366×768: Inspector narrow/overlay, text ≥11px | Responsive |
| 19 | No fake progress percentages | Truth |
| 20 | No fake per-checklist-item dispositions | Truth |
| 21 | No fake measurement values | Truth |
| 22 | S04 fallback unaffected | Regression |
| 23 | Frame A overview unaffected | Regression |
| 24 | Frame B detail unaffected (except Inspector panel addition) | Regression |
| 25 | `quality_records[]` field backward compatible (additive only) | Contract |
| 26 | No I07 animation | Scope |
| 27 | No MES panels | Scope |

---

## 14. Forbidden Scope

- ❌ No runtime/domain model changes (`line_runtime.py`, `quality_records.py`)
- ❌ No new API endpoints (existing `/sub-line/{id}` serves Inspector data)
- ❌ No controller/composition changes
- ❌ No conveyor/WIP lifecycle/timing changes
- ❌ No per-checklist-item disposition fabrication
- ❌ No fake measurements or expected ranges
- ❌ No station progress percentages
- ❌ No wall-clock timestamps
- ❌ No operator identity
- ❌ No MES/IIoT panels
- ❌ No animation/motion (I07)
- ❌ No separate Inspector page/screen

---

## 15. Test / Evidence Plan

### Backend tests (I06)
- `QualityRecordView` round-trip serialization
- `build_snapshot` includes `quality_records[]`
- Measurements with min/max projected correctly
- Checklist items projected as list
- `reason_code` projected
- Backward compatibility: existing snapshot fields unchanged
- Empty quality history produces empty `quality_records[]`

### UI evidence (I06)
- Inspector opens from station/WIP/event click
- AP06 measurements with in-range/out-of-range
- AP08 checklist items
- AP11 FINAL_QC context
- Selection survives STEP
- Released WIP historical context
- 1920 + 1366 responsive

---

> **DG05-01 is READY FOR SA REVIEW.**
>
> Next: SA approval → I06 Context Inspector implementation.
