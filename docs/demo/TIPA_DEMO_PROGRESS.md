# TIPA ASSY Simulation Demo — Tiến Độ & Trạng Thái

> **Cập nhật**: 2026-08-11  
> **Branch**: `docs/m6-s01-tipa-baseline`  
> **Demo chính thức**: 21-Aug-2026 | **Demo nội bộ**: 17-Aug-2026

---

## 1. Tổng Quan

Dự án mô phỏng dây chuyền lắp ráp (ASSY) động cơ TIPA, phục vụ demo 
nội bộ 17-Aug và demo chính thức 21-Aug-2026.

**Phạm vi chính**: ASSY (Assembly Line) — 12 trạm PRE-ASSY → AP11  
**Hỗ trợ upstream**: SSO2, RSO2 (mức simplified)  
**Test**: 1140+ tests tự động, deterministic

---

## 2. Tiến Độ Tổng Thể

```
M6-S01 ████████████████████ CLOSED ✅  (10-Aug)
M6-S02 ████████████████████ CLOSED ✅  (10-Aug)
M6-S03 ████████████████████ CLOSED ✅  (10-Aug)
M6-S04 ████████████████████ CLOSED ✅  (10-Aug)
M6-S05 ░░░░░░░░░░░░░░░░░░░░ PENDING      MES Observation Integration
```

| Milestone | Trạng thái | Ngày | PR/Head |
|-----------|-----------|------|---------|
| Foundation (M2–M5) | CLOSED | 09-Aug | main @ a21478c |
| M6-S01 Baseline Freeze | CLOSED | 10-Aug | `fe30268` |
| M6-S02 Runtime + WIP + AP04 | CLOSED | 10-Aug | `e0ba672` |
| M6-S03 Quality / Test / Rework | CLOSED | 10-Aug | `58bd958` |
| M6-S04 Visualization + Controls | CLOSED | 10-Aug | `bceeba9` |
| **M6-S05 MES Observation** | **PENDING** | — | — |

---

## 3. Kiến Trúc 4 Lớp (Đã Hoàn Thành)

```
┌─────────────────────────────────────────────────┐
│ M6-S01 — Manufacturing Baseline (frozen v0.9)   │
│  • 12 trạm PRE-ASSY → AP11                      │
│  • WIP genealogy, quality routing                │
│  • Conveyor: single-lane, stop-and-go, 120s dwell│
│  • 13 PTC items, 9 INV-CONV invariants           │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ M6-S02 — Synchronized Indexed ASSY Runtime      │
│  • AssyLineRuntime: dwell/index cycle            │
│  • Multi-WIP concurrent processing per dwell     │
│  • AP04 JOIN: SSO2 + RSO2 → MTR child            │
│  • Genealogy: parent preservation                │
│  • Carrier ≠ WIP identity                        │
│  • Simulated time: actual_dwell formula           │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ M6-S03 — Quality / Test / Rework                 │
│  • AP03: checklist/mechanical prep               │
│  • AP06: electrical test + FAIL/HOLD/RETEST      │
│  • AP08: visual inspection + NG/HOLD/REINSPECT   │
│  • AP11: final QC → RELEASED                     │
│  • FAILED_FINAL: terminal, idempotent             │
│  • Quality history per WIP with attempt tracking  │
└────────────────────┬────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│ M6-S04 — Visualization + Demo Controls           │
│  • FastAPI + HTML/JS SPA (dark theme)            │
│  • Detached snapshot architecture                │
│  • 12 position cards with quality badges          │
│  • RESET / STEP / AUTO / PAUSE / SPEED / SCENARIO│
│  • 4 kịch bản demo                               │
└─────────────────────────────────────────────────┘
```

---

## 4. Chi Tiết Từng Milestone

### M6-S01 — Baseline Freeze v0.9 ✅

| Tài liệu | Nội dung |
|----------|---------|
| `TIPA_ASSY_DEMO_BASELINE_v0.9.md` | Topo 12 trạm, conveyor single-lane stop-and-go, 9 INV-CONV |
| `TIPA_DEMO_WIP_GENEALOGY_v0.9.md` | 10 WIP states, AP04 parent_A + parent_B → child |
| `TIPA_DEMO_QUALITY_ROUTING_v0.9.md` | AP03/06/08/11 quality state machines |
| `TIPA_DEMO_OBSERVATION_MATRIX_v0.9.md` | 16 observation points, 7 semantic types |
| `TIPA_DEMO_PENDING_CONFIRMATIONS.md` | 13 PTC items (9 CONFIG_ONLY, 2 SMALL_LOGIC, 1 STRUCTURAL) |

**Corrections**: C01 (Source Alignment), C02 (Conveyor Clarification), C02.1 (Runtime Semantics)

---

### M6-S02 — Runtime + WIP + AP04 Join/Genealogy ✅

| Module | Chức năng |
|--------|----------|
| `assembly/carrier.py` | CarrierId, CarrierState (WIP ≠ carrier) |
| `assembly/conveyor.py` | ConveyorState, ConveyorLine (INDEXING→STOPPED→OPERATING→READY) |
| `assembly/genealogy.py` | GenealogyRecord (frozen), GenealogyStore |
| `assembly/upstream.py` | SSO2/RSO2 simplified production |
| `assembly/line_runtime.py` | AssyLineRuntime — dwell, index, AP04 join, YAML loader |
| `configs/plants/tipa_assy_demo.yaml` | Authoritative demo config |

**Công thức timing**: `actual_dwell = max(nominal_dwell, max(remaining_station_time))`  
**Corrections**: C01 (Runtime Semantics), C02 (Config & Evidence)

---

### M6-S03 — Quality / Test / Rework ✅

| Module | Chức năng |
|--------|----------|
| `assembly/quality_records.py` | QualityStatus, QualityRecord, QualityHistory, MeasurementValue, scenario resolver |

| Trạm | Hành vi |
|------|--------|
| AP03 | CHECKLIST → PASS → AP04 |
| AP06 | TEST → FAIL/HOLD → RETEST (max 2) → PASS hoặc FAILED_FINAL |
| AP08 | VISUAL_INSPECTION → NG/HOLD → REINSPECT (max 2) → PASS hoặc FAILED_FINAL |
| AP11 | FINAL_QC → PASS → RELEASED |

**Corrections**: C01 (Terminal Quality Hold), C01.1 (Terminal Idempotency)

---

### M6-S04 — Visualization + Demo Controls ✅

| Layer | Chi tiết |
|-------|---------|
| `demo_snapshot.py` | AssyDemoSnapshot — detached read model, 12 StationPositionView |
| `demo_controller.py` | RESET / STEP / AUTO / PAUSE / SPEED / 4 scenarios |
| `ui/static/assy_demo.html` | SPA với ASSY line cards ngang |
| `ui/static/assy_demo.js` | JS controller + DOM renderer |
| `ui/static/assy_demo.css` | Dark theme, quality badges (PASS/FAIL/NG/HOLD/RELEASED) |
| `ui/api.py` | `/assy-demo` endpoints |

**Kịch bản demo**:
- `HAPPY_PATH` — tất cả PASS
- `AP06_FAIL_RETEST_PASS` — motor 2: AP06 FAIL → RETEST → PASS
- `AP08_NG_REINSPECT_PASS` — motor 2: AP08 NG → REINSPECT → PASS
- `FAILED_FINAL` — AP06 max attempts exhausted

**Khởi động**: `uvicorn virtual_factory.ui.api:create_app --factory` → `http://localhost:8000/assy-demo`

**Corrections**: C01 (Projection Boundary & Demo Semantics)

---

## 5. Test Suite

| Suite | Count | Status |
|-------|-------|--------|
| M2–M5 regression | 1067 | ✅ |
| M6-S02 focused | 33 | ✅ |
| M6-S03 quality | 21 | ✅ |
| M6-S04 visualization | 21 | ✅ |
| **TOTAL** | **1142** | ✅ |

---

## 6. Cấu Trúc Thư Mục Dự Án

```
virtual-factory/
├── configs/plants/
│   └── tipa_assy_demo.yaml          ← Authoritative demo config (YAML single source)
├── docs/demo/
│   ├── TIPA_SIMULATION_DEMO_TIMELINE_2026-08.md
│   ├── TIPA_DEMO_PROGRESS.md        ← File này
│   └── tipa/
│       ├── TIPA_ASSY_DEMO_BASELINE_v0.9.md
│       ├── TIPA_DEMO_WIP_GENEALOGY_v0.9.md
│       ├── TIPA_DEMO_QUALITY_ROUTING_v0.9.md
│       ├── TIPA_DEMO_OBSERVATION_MATRIX_v0.9.md
│       └── TIPA_DEMO_PENDING_CONFIRMATIONS.md
├── src/virtual_factory/assembly/
│   ├── carrier.py                   ← M6-S02
│   ├── conveyor.py                  ← M6-S02
│   ├── genealogy.py                 ← M6-S02
│   ├── upstream.py                  ← M6-S02
│   ├── line_runtime.py              ← M6-S02 (main runtime)
│   ├── quality_records.py           ← M6-S03
│   ├── demo_snapshot.py             ← M6-S04
│   ├── demo_controller.py           ← M6-S04
│   └── primitives/wip/quality/...   ← M3/M4 (preserved)
├── src/virtual_factory/ui/
│   ├── api.py                       ← M6-S04 (extended)
│   └── static/
│       ├── assy_demo.html           ← M6-S04
│       ├── assy_demo.js             ← M6-S04
│       └── assy_demo.css            ← M6-S04
└── tests/
    ├── test_assy_line.py            ← M6-S02 (33 tests)
    ├── test_quality.py              ← M6-S03 (21 tests)
    ├── test_assy_demo.py            ← M6-S04 (21 tests)
    └── demo_assy.py                 ← CLI demo fixture
```

---

## 7. Demo Readiness

| Hạng mục | Mức độ |
|----------|--------|
| Process model / runtime | 🟢 100% — indexed line hoàn chỉnh |
| WIP + genealogy | 🟢 100% — AP04 join, carrier separation |
| Quality / test / rework | 🟢 100% — PASS/HOLD/RETEST/REINSPECT/FAILED_FINAL |
| Visualization | 🟢 100% — web-based SPA, 4 scenarios |
| MES integration | 🔴 0% — M6-S05 pending |
| Stability / regression | 🟢 1142 tests passed |
| Demo script / readiness | 🟡 70% — cần M6-S05 |

**Overall Demo Readiness**: ~70%

---

## 8. Pending TIPA Confirmations (13 items)

| Impact | Count | Items |
|--------|-------|-------|
| CONFIG_ONLY | 9 | PTC-01,02,03,04,05,07,08,09,11 |
| SMALL_LOGIC | 2 | PTC-06 (AP04 join), PTC-10 (overrun rule) |
| STRUCTURAL | 1 | PTC-12 (multi-product) |
| CARRIER | 1 | PTC-13 (carrier reuse) |

Tất cả đều có provisional demo values. Không item nào block implementation.

---

## 9. INV-CONV Invariants (9 items — Authoritative)

| ID | Nội dung |
|----|---------|
| INV-CONV-01 | ASSY uses ONE conveyor lane |
| INV-CONV-02 | Conveyor is stop-and-go / indexed |
| INV-CONV-03 | Processing occurs ONLY while conveyor is stopped |
| INV-CONV-04 | Nominal dwell is configuration-driven (120s baseline) |
| INV-CONV-05 | Line dwell and station operation duration are separate |
| INV-CONV-06 | Incomplete work prevents WIP from advancing |
| INV-CONV-07 | WIP identity ≠ carrier/pallet identity |
| INV-CONV-08 | No conveyor physics required for demo |
| INV-CONV-09 | Multi-WIP concurrent processing per dwell; INDEX is line-level sync boundary |

---

## 10. Lịch Trình Còn Lại

| Ngày | Milestone |
|------|-----------|
| **11-Aug** | M6-S05 MES Observation Integration |
| **12–16 Aug** | Hardening, full rehearsal, demo script |
| **17-Aug** | Internal integrated demo |
| **18–20 Aug** | Correction / stabilization window |
| **21-Aug** | 🎯 Official TIPA demo |
