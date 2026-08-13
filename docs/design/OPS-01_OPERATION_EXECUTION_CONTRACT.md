# OPS-01 — Operation Execution & Station Interaction Contract

> **Baseline**: `1b0bbe4`
> **Gate type**: DESIGN/CONTRACT ONLY — no runtime/API/snapshot/UI implementation.
> **Design authority input**: `OPS-01_Operation_Execution_Station_Interaction_Contract_Design_v0.1.md` (SA working baseline).
> **C01 addendum**: `OPS-01-C01_UX_Interaction_Contract_Addendum.md` — Station Interaction Surface (design-only, appended §13).
> **Date**: 2026-08-13

---

## 1. Purpose

Formalize the approved ASSY operation-execution model into repository design/contracts **before** any runtime or UI work. This document:

1. Audits AP01–AP11 against current repo semantics (baseline `1b0bbe4`).
2. Defines the generic station capability schema.
3. Defines the `OperationExecution` state model.
4. Defines MANUAL / AUTO / ASSISTED semantics.
5. Defines the index-eligibility contract.
6. Defines the separation of operation result / quality result / quality status / routing.
7. Defines an additive snapshot projection that does **not** alter `positions[]`.
8. Maps the current ASSY stations to capability contracts.
9. Records unresolved physical synchronization assumptions.

**Audit conclusion: the current repository is consistent with the SA design baseline. No architecture-level contradiction was found; no STOP was required.** All deltas are additive gaps to be closed by OPS-02..OPS-05.

---

## 2. Current repo semantics (audited at `1b0bbe4`)

### 2.1 Conveyor (`assembly/conveyor.py`)
- `ConveyorState`: `INDEXING | STOPPED | OPERATING | READY_TO_INDEX`.
- Single lane, **synchronous stop-and-go** (INV-CONV-01..09).
- Processing occurs **only while STOPPED** (INV-CONV-03).
- Demo config: `index_movement_duration_s: 0` (instantaneous index).
- Positions: `PRE-ASSY, AP01..AP11`.

### 2.2 WIP lifecycle (`assembly/line_runtime.py` `WipLifecycle`)
`CREATED → IN_ASSY → AT_STATION → COMPLETED_STATION → JOINED → RELEASED`.
This is a **WIP-level manufacturing lifecycle**, not an operation-level lifecycle.

### 2.3 Station dispatch (`AssyLineRuntime._execute_station`)
Station behavior is currently **hard-coded by position ID**:

| Station | Current behavior |
|---------|------------------|
| PRE-ASSY | generic complete |
| AP01/AP02/AP05/AP07/AP09/AP10 | generic `DONE` after configurable duration |
| AP03 | quality station — `CHECKLIST` (demo always PASS) |
| AP04 | `_execute_ap04_join` — identity transformation |
| AP06 | quality station — `TEST` (FAIL → RETEST_PENDING, max 2) |
| AP08 | quality station — `VISUAL_INSPECTION` (NG → REINSPECT_PENDING, max 2) |
| AP11 | quality station — `FINAL_QC` (PASS → RELEASED) |

### 2.4 Quality (`assembly/quality_records.py`)
- `QualityStatus`: `CLEAR | HOLD | RETEST_PENDING | REINSPECT_PENDING | FAILED_FINAL`.
  - **Note**: `HOLD` is declared but **never set** by the current runtime; only `CLEAR/RETEST_PENDING/REINSPECT_PENDING/FAILED_FINAL` are written.
- `QualityRecord.disposition`: `PASS | FAIL | NG` (never `HOLD`).
- `CheckType`: `CHECKLIST | MEASUREMENT | TEST | VISUAL_INSPECTION | FINAL_QC`.

### 2.5 AP04 identity boundary (`assembly/genealogy.py`)
- JOIN creates a **new MTR child**; parents are preserved (parent A lifecycle → `JOINED`).
- `GenealogyRecord` is immutable; identity policy is `PROVISIONAL_FOR_DEMO`.

### 2.6 Snapshot (`assembly/demo_snapshot.py`)
- `positions[]` = `StationPositionView`: `position_id, station_label, carrier_id, wip_id, wip_type, manufacturing_status (WipLifecycle), quality_status (QualityStatus), latest_quality_result, attempt_number, is_occupied, is_quality_hold, held_reason`.
- Additive: `genealogy[]`, `recent_quality_events[]`, `quality_records[]`, `production{}`, identity fields.
- **No `active_operations[]` yet.**

### 2.7 Completion / index eligibility
- `ConveyorLine._position_complete` + `check_ready()` → **implicit** index eligibility.
- Quality hold (`RETEST/REINSPECT/FAILED_FINAL`) prevents `mark_position_complete` → line does **not** index. `STAY_AT_STATION` is implicit.

### 2.8 What does NOT exist today
- No station capability schema.
- No `OperationExecution` / completion-mode model.
- No MANUAL/AUTO/ASSISTED distinction (execution is fully automatic, dwell-synchronized).
- No routing axis (`LINE_OUT`/`LINE_IN` are frozen conceptual UI cues only).
- No user-facing exception affordance (HOLD / LINE OUT / note).

---

## 3. Station capability model (generic schema)

A station exposes only the decisions that physically/business-wise belong to that operation. A generic `DONE | HOLD | LINE OUT` toolbar must **not** be applied uniformly.

```yaml
station_contract:
  station_id: AP03
  capabilities:
    execution: true
    checklist: true
    measurement: false
    quality_decision: true
    exception: true
    identity_transformation: false
    final_disposition: false
```

Supported capability flags (additive in future):

| Capability | Meaning |
|-----------|---------|
| `execution` | station performs a physical/manufacturing operation |
| `checklist` | operation requires checklist item confirmation |
| `measurement` | operation produces measurable values |
| `quality_decision` | operation yields a PASS/FAIL/NG quality decision |
| `exception` | operation may raise HOLD / LINE OUT / note |
| `identity_transformation` | operation transforms WIP identity (e.g. AP04 JOIN) |
| `final_disposition` | operation disposes the WIP (release/hold/reject) |

Machine-readable schema: `.ai-harness/schemas/station-contract.schema.json`.
Machine-readable example: `docs/design/station-contracts.example.yaml`.

---

## 4. OperationExecution state model

Generic lifecycle, **per WIP per station**, orthogonal to physical position, quality status, exception case, WIP identity, and line state:

```text
ARRIVED
  ↓
READY
  ↓
WORKING
  ↓
AWAITING_COMPLETION   (execution stations)
AWAITING_DECISION     (quality-decision stations)
  ↓
COMPLETED | HELD | FAILED | EXCEPTION_PENDING
  ↓
ELIGIBLE_TO_INDEX
```

```yaml
operation_execution:
  execution_id: EXEC-...
  station_id: AP05
  wip_id: MTR-0042
  state: WORKING
  started_at_sim_s: 1840
  completed_at_sim_s: null
  work_duration_s: 35
  completion_mode: MANUAL | AUTO | ASSISTED
  inputs: {}
  checklist: []
  measurements: []
  operation_result: null
  quality_result: null
  routing_action: null
  source: { type: simulated | manual | imported }
```

`operation_result`, `quality_result`, and `routing_action` are **separate fields** — never overloaded.

---

## 5. MANUAL / AUTO / ASSISTED semantics

- **MANUAL**: operation info shown; user presses the station-appropriate action (`DONE`, `CONFIRM & COMPLETE`, `CONFIRM`). Station is not complete and the WIP is not index-eligible until the action completes.
- **AUTO**: simulation execution advances automatically. AUTO does **not** force PASS.
  - Pure execution: operation starts, waits configurable simulated work time, performs the same `DONE` transition automatically.
  - Quality/test: synthetic/scenario/rule-driven inputs produce PASS/FAIL/NG per the existing scenario resolver; quality semantics unchanged.
- **ASSISTED**: system prepares data/default decision; user confirms or overrides where the station contract allows.

**Invariant**: MANUAL, AUTO, and ASSISTED share **one** lifecycle and one state model — they differ only in who/what supplies the completion action, never in separate logic trees.

Demo timing guidance: nominal visual wait ~1–2 s for simple stations, scaled by simulation speed; actual `work_duration_s` remains configurable and independent of visual animation timing.

---

## 6. Index-eligibility contract

A WIP is `ELIGIBLE_TO_INDEX` only when the **current station contract** is satisfied:

| Station | Eligible when |
|---------|---------------|
| AP01/AP02/AP05/AP07/AP09/AP10 | `DONE` |
| AP03 | required checklist complete **and** confirmed |
| AP04 | `JOIN_COMPLETE` (child created) |
| AP06 | `TEST_COMPLETE` **and** `PASS` |
| AP08 | `INSPECTION_COMPLETE` **and** `PASS` |
| AP11 | `RELEASE` (exit/released) |

Non-eligible states keep the WIP at the station (`routing_action: STAY_AT_STATION`).

**Frozen**: `positions[]` remains the sole source of truth for main-line physical occupancy. Eligibility is an operation-layer concept; it does not add occupancy fields to `positions[]`.

---

## 7. Orthogonal semantics

Four separate axes — must never be conflated:

| Axis | Examples |
|------|----------|
| **operation_result** | `DONE`, `JOIN_COMPLETE`, `TEST_COMPLETE`, `INSPECTION_COMPLETE`, `CONFIRMED` |
| **quality_result** | `PASS`, `FAIL`, `NG` |
| **quality_status** | `CLEAR`, `RETEST_PENDING`, `REINSPECT_PENDING`, `FAILED_FINAL` |
| **routing** | `CONTINUE`, `STAY_AT_STATION`, `LINE_OUT`, `LINE_IN` |

**Sharpening note (current repo)**: today AP06/AP08 conflate "test operation complete" with "station complete". On FAIL/NG the runtime leaves the station incomplete (quality hold), which is behaviorally correct for retest, but does not expose the conceptual fact that the *test operation itself completed with a FAIL quality result*. OPS-02 must model `operation_result=TEST_COMPLETE` + `quality_result=FAIL` + `quality_status=RETEST_PENDING` + `routing=STAY_AT_STATION` as distinct facts.

`QualityStatus.HOLD` is declared but currently unused; OPS-02 should either give it a precise meaning (user-initiated exception hold) or retire it.

---

## 8. Additive snapshot projection

Frozen invariant:

> `positions[]` remains the sole source of truth for current main-line physical occupancy.

Proposed additive projection (OPS-02), built from runtime public API only:

```yaml
active_operations:
  - station_id: AP05
    wip_id: MTR-0042
    state: AWAITING_COMPLETION
    required_action: DONE
```

Full operation history belongs in an execution registry, not in `positions[]`. This mirrors the existing additive pattern of `quality_records[]` / `genealogy[]`.

---

## 9. Station contract mapping (current ASSY baseline)

| Station | capabilities | normal action | failure / alternate | eligibility |
|---------|--------------|---------------|---------------------|-------------|
| PRE-ASSY | execution (prep/buffer) | auto DONE | — | DONE |
| AP01 | execution | DONE | — | DONE |
| AP02 | execution | DONE | — | DONE |
| AP03 | execution, checklist, quality_decision, exception | CONFIRM & COMPLETE | HOLD | checklist + confirm |
| AP04 | execution, identity_transformation | JOIN COMPLETE | — (requires RSO2) | JOIN_COMPLETE |
| AP05 | execution | DONE | — | DONE |
| AP06 | execution, measurement, quality_decision | CONFIRM (PASS/FAIL) | FAIL → retest → FAILED_FINAL | TEST_COMPLETE + PASS |
| AP07 | execution | DONE | — | DONE |
| AP08 | execution, quality_decision | CONFIRM (PASS/NG) | NG → reinspect → FAILED_FINAL | INSPECTION_COMPLETE + PASS |
| AP09 | execution (boxing) | DONE | — | DONE |
| AP10 | execution (packaging) | DONE | — | DONE |
| AP11 | execution, checklist, quality_decision, final_disposition | RELEASE | HOLD / REJECT (pending confirmed semantics) | RELEASE |

**AP03 pre-join gate invariant** (explicit contract for OPS-04):

> AP04 must not JOIN before the AP03 prerequisite is satisfied.

Today this is enforced **implicitly** by the synchronous blocked conveyor (a WIP cannot reach AP04 while held at AP03). OPS-04 makes this an explicit, configurable prerequisite check.

---

## 10. Gap & assumption table

| # | Item | Repo state | Classification | Target |
|---|------|-----------|----------------|--------|
| G1 | Station capability schema | hard-coded dispatch | GAP (additive) | OPS-02 |
| G2 | `OperationExecution` state model | WIP lifecycle only | GAP (additive) | OPS-02 |
| G3 | MANUAL/AUTO/ASSISTED modes | fully auto only | GAP (additive) | OPS-02 |
| G4 | operation_result vs quality_result separation | conflated at AP06/AP08 | GAP (sharpening) | OPS-02 |
| G5 | `QualityStatus.HOLD` unused | declared, never set | GAP (define or retire) | OPS-02 |
| G6 | routing axis (CONTINUE/STAY/LINE_OUT/LINE_IN) | implicit STAY only | GAP (frozen not-implemented) | OPS-03/04 |
| G7 | additive `active_operations[]` | absent | GAP (additive) | OPS-02 |
| G8 | AP03 pre-join gate invariant | implicit only | GAP (explicit contract) | OPS-04 |
| G9 | exception affordance UI | absent | GAP | OPS-03 |
| G10 | per-station index eligibility | implicit `_position_complete` | GAP (formalize) | OPS-02 |

**Assumptions (unresolved physical coordination — do not invent):**

| # | Assumption | Status |
|---|-----------|--------|
| A1 | One blocked station blocks the whole indexed conveyor (synchronous line) | Preserve current demo behavior until separately authorized |
| A2 | Stations may not continue independently while the line is blocked | Preserve current demo behavior |
| A3 | No inter-station buffering | Preserve current demo behavior |
| A4 | `index_movement_duration_s = 0` (instantaneous index) | Demo-only; configurable |
| A5 | Exact TIPA AP11 REJECT routing (to where) | Unconfirmed — do not implement |

**No contradictions found.** The SA §12 ("preserve existing conveyor semantics until separately authorized") is satisfied by the current synchronous model.

---

## 11. Implementation slices

1. **OPS-02 — Runtime OperationExecution Engine**
   - Station contracts (load from config, not position-ID dispatch)
   - `OperationExecution` state machine
   - MANUAL / AUTO / ASSISTED completion (one lifecycle)
   - Index-eligibility gating
   - Additive `active_operations` projection (no `positions[]` change)

2. **OPS-03 — Station Interaction UI**
   - Generic popup rendering driven by capabilities
   - DONE / checklist / test / vision / final-QC forms
   - `[DONE] [⋯ Exception]` pattern; exception drawer only where `exception: true`

3. **OPS-04 — AP03 / AP06 / AP08 / AP11 Deep Behavior**
   - AP03 checklist + explicit pre-join gate
   - AP06 measurement/test, AP08 inspection, AP11 release/hold
   - Retest / reinspect / FAILED_FINAL preserved

4. **OPS-05 — Configurable Templates**
   - Extract station types for reuse across other lines/factories

---

## 12. Frozen invariants preserved

1. `positions[]` = sole main-line occupancy truth.
2. AP04 identity boundary (child created only after completion; parents preserved).
3. Current quality-status semantics (`RETEST_PENDING`, `REINSPECT_PENDING`, `FAILED_FINAL`).
4. Same-station retest/reinspect baseline unless exception routing is separately implemented.
5. No fake Line-Out / Line-In runtime.
6. No invented physical conveyor synchronization.
7. MANUAL/AUTO/ASSISTED share one lifecycle, not separate logic trees.

---

## 13. Station Interaction Surface (OPS-01-C01 addendum)

Design-only. OPS-03 remains the implementation slice. This section pins the UI/interaction architecture so later OPS-03 cannot fork it.

1. **Single interaction surface** — reuse the existing top-right Context Inspector / popup as the future Station/WIP Operation Interaction surface. No persistent per-AP control window. Clicking a station or its current WIP must resolve to the same underlying `OperationExecution`.

2. **Station click vs WIP click** — station click = station-first context (“what is happening at this station?”); WIP click = WIP-first context (“what does this WIP currently need?”). Both reference the same active operation state and must not create duplicate control state.

3. **Capability-driven renderer** — UI generated from station capabilities, never hard-coded `if AP03 / if AP06`:
   - `execution` → DONE
   - `checklist` → checklist + confirm
   - `measurement` + `quality_decision` → measurement fields + PASS/FAIL
   - `final_disposition` → RELEASE/HOLD/REJECT as allowed by the contract
   Exact field definitions may be station configuration; renderer architecture must be generic.

4. **Manual mode** — when a station reaches an action-required state, the station/WIP becomes visually marked `ACTION REQUIRED`. User clicks station/WIP to open the inspector and execute the required action. Do **not** auto-open popups. Simple execution stations in a globally MANUAL run wait for user `DONE`.

5. **Auto mode** — inspector remains available as a monitor/view surface. The simulator performs the same completion transition automatically after configured work time. AUTO is **not** auto-PASS for quality gates.

6. **Simulation panel separation** — the floating Simulation Control Panel is responsible only for runtime controls (RESET/STEP/AUTO/PAUSE/speed/runtime status). Operation forms (checklist / PASS/FAIL / DONE) belong in the Station/WIP Inspector, not in the Simulation Control Panel. A future aggregate cue such as `N actions required` may be shown in the Simulation Panel, but it must not duplicate station control logic.

7. **No implementation in C01** — this addendum is contract only. OPS-03 implements the capability-driven station interaction UI.

---

> **OPS-01-C01 — READY FOR SA REVIEW.**
