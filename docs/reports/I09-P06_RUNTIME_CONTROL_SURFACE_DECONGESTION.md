# I09-P06 — Runtime Control Surface / Header Decongestion

> **Baseline**: `182287d`
> **Head triển khai**: `6fddf97`
> **Commit chain**: `e46d2a8 → 7e6e0a7 → 58f4a75 → 06b1b38 → 6a93af5 → 182287d → 6fddf97`
> **Ngày**: 2026-08-13
> **Loại**: UI INFORMATION-ARCHITECTURE CORRECTION — FRONTEND ONLY

---

## 1. Mục tiêu

Tách biệt các mối quan tâm trong Frame B:
- Top header = global context / navigation
- Floating Simulation Control = execution / clock / conveyor state
- Left sidebar = production outcome / KPI
- Center canvas = physical production reality
- Popup/inspector = object knowledge

---

## 2. Header before/after

**Move OUT (top bar)**:
- `t=…`, `DWELL`, conveyor state (`fb-line-state`), LIVE (`fb-live-status`)
- RESET / STEP / AUTO / PAUSE
- speed selector (`fb-speed-select`)
- dead `line-state-display` span

**Remain (top bar)**:
- VF logo (TIPA plant / ASSY line)
- `fb-sub-line-id`, `fb-variant`, `fb-scenario` (global context badges)
- Frame A `live-status` + `demo-step` (hidden in Frame B)
- navigation (⊞ ⚙ ?)

---

## 3. Floating Simulation Control

- Vị trí: bottom-left của central canvas (`#vf-sim-panel`, absolute, không draggable, không persistence).
- Nội dung: `Simulation` title, `● LIVE`, `t=…`, `DWELL`, conveyor state, `[RESET][STEP][AUTO][PAUSE]` + speed select.
- Không chồng lấn conveyor/stations/Line-Out tray/popup/KPI sidebar. Event strip dời `left` sang phải panel.

---

## 4. Control routing

- Reuse nguyên `uiReset / uiStep / uiToggleAuto / uiPause` + `ctrlB.setSpeed`.
- Button giữ nguyên ID `btn-reset/btn-step/btn-auto/btn-pause` → `ctrl.startAuto/stopAuto` + `ctrlB.startAuto/stopAuto` sync trạng thái AUTO/PAUSE không đổi.
- Không tạo control path thứ hai. Frame A routing giữ nguyên (button giờ nằm trong panel Frame B).

---

## 5. KPI separation

Created / Released / On Line / Holds vẫn ở left sidebar. Không đưa KPI vào Simulation Control.

---

## 6. Frozen invariants — confirmed

1. context ≠ authoritative WIP — giữ
2. không bịa SSO2/RSO2 upstream — giữ
3. không fake live off-line — giữ
4. selected WIP follow by identity — giữ (halo)
5. AP04 không silent identity transfer — giữ
6. STOPPED = conveyor-specific — giữ
7. RESET atomic clear — giữ
8. Motion rules — giữ
9. scenario/sub-line switch clear stale state — giữ

---

## 7. Responsive

| Viewport | Kết quả |
|----------|---------|
| 1920×1080 | ✅ EV1 |
| 1600×900 | ✅ EV2 |
| 1366×768 | ✅ EV3 (header breathes, panel không che WIP/stations, popup fit, sidebar usable) |

---

## 8. Evidence

`docs/ui/evidence/i09-p06/`:
- EV1 1920 decongested Frame B
- EV2 1600 Frame B
- EV3 1366 Frame B
- EV4 top header close-up (global context only)
- EV5 floating simulation panel close-up
- EV6 AUTO active state
- EV7 PAUSE state
- EV8 speed 0.1x control
- EV9 selected WIP + panel coexist
- EV10 popup + panel coexist
- EV11 AP04/RSO2 composition unaffected
- EV12 final demo-ready full frame

---

## 9. Tests

```
27 passed (gate suites: test_runtime_service, test_api, test_sensor_quality, test_scenario_loader, test_sim_val_01_feed)
```

Browser smoke (tất cả PASS, console 0 errors):
RESET, STEP, AUTO, PAUSE, speed 0.1x/0.25x, Frame A→B→A, scenario switch, sub-line switch,
selected WIP follow, AP04 identity boundary, SSO2/RSO2/off-line context click, popup close,
reset cleanup, zoom/pan/fit.

---

## 10. PM Self-Review

1. Top header materially less crowded? **YES**
2. Runtime controls visually inside Simulation Zone? **YES**
3. Scenario/Sub-line still global context? **YES**
4. KPIs separate from runtime controls? **YES**
5. Runtime behavior changed? **NO**
6. API/snapshot/state model changed? **NO**
7. Control handlers remain single-source? **YES**
8. P04/P05 invariants intact? **YES**
9. 1366 cleaner than baseline? **YES**
10. Overall UI easier to explain? **YES**

---

## 11. Scope

- Backend: NO
- Runtime: NO
- API: NO
- Snapshot: NO
- positions[]: NO
- Motion semantics: NO
- Quality semantics: NO
- Genealogy semantics: NO
- LINE OUT/IN runtime: NO
- REWORK runtime: NO
- Production Context backlog: NOT STARTED

---

> **I09-P06 — READY FOR SA REVIEW.**
