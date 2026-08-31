# I09-P05 — Demo Visual / Interaction Polish

> **Baseline**: `06b1b38`
> **Head triển khai**: `6a93af5`
> **Commit chain**: `e46d2a8 → 7e6e0a7 → 58f4a75 → 06b1b38 → 6a93af5`
> **Ngày**: 2026-08-13
> **Loại**: POLISH-ONLY — **KHÔNG đổi backend/runtime/API/snapshot/positions[]/motion/quality/genealogy/feed**

---

## 1. Mục tiêu

Cải thiện độ rõ, cân bằng thị giác và khả năng demo của Frame B trước Integrated Demo Validation.
Không thêm capability, không đổi semantics.

---

## 2. Changes (chỉ visual/interaction)

| File | Nội dung |
|------|----------|
| `src/virtual_factory/ui/static/assy_demo.css` | Thay selected-WIP `drop-shadow` toàn bộ children bằng **dedicated selection ring** `.vf-wip-sel-halo` |
| `src/virtual_factory/ui/static/assy_demo.js` | (1) render halo ring trong `_renderWips`; (2) WIP ID 10→11px; (3) flow cue opacity 0.09→0.14; (4) SSO2/RSO2 context icons opacity 0.78→0.5; (5) off-line labels/watermark 8→9px |

Không đổi file backend/runtime/API/snapshot.

---

## 3. Visual changes (material)

1. **Selected WIP** — ring `stroke-dasharray 5,3` + fill nhẹ thay cho glow mờ toàn bộ children:
   - không còn nhìn như error/hold
   - text WIP ID sắc nét khi di chuyển
   - halo đi theo group trong motion (identity follow giữ nguyên)
2. **Flow cue** — RIGHT→LEFT arrow dễ nhận biết hơn (0.09→0.14), vẫn dưới WIP/stations.
3. **Context cues (SSO2/RSO2)** — opacity 0.78→0.5, rõ ràng là contextual, không cạnh tranh với live WIP.
4. **Off-line tray** — label ghost + watermark `CONTEXT — not live WIP` tăng 8→9px, đọc được hơn.
5. **WIP ID** — 10→11px, đọc rõ hơn ở 1366.

---

## 4. Interaction changes (polish-level only)

- Không thêm/đổi field, không thêm handler mới.
- Selection ring chỉ là styling của `.selected` (reuse existing state `_selectedWipId`).

---

## 5. Before/after rationale

| Vấn đề (before 06b1b38) | Sau I09-P05 |
|-------------------------|-------------|
| Selected WIP glow làm text mờ, dễ nhầm lỗi | Ring rõ ràng, text sắc, không giống lỗi |
| Flow direction gần như vô hình (0.09) | Arrow RIGHT→LEFT nhận biết được, vẫn tinh tế |
| Context cues quá "sống" (0.78) | Rõ là context-only (0.5), live WIP chiếm ưu thế thị giác |
| WIP ID 10px khó đọc ở 1366 | 11px dễ đọc hơn |

---

## 6. Frozen P04 invariants — confirmed unchanged

1. Context source ≠ authoritative WIP — **giữ** (càng mờ hơn)
2. SSO2/RSO2 popup không bịa upstream data — **giữ**
3. Off-line tray không bịa live exception — **giữ**
4. Selected WIP follow by identity — **giữ** (ring đi theo group)
5. AP04 không silent identity transfer — **giữ** (verified lại)
6. `STOPPED` = conveyor state — **giữ**
7. RESET atomic clear — **giữ** (smoke pass)

---

## 7. Responsive

| Viewport | Kết quả |
|----------|---------|
| 1920×1080 | ✅ EV1 |
| 1600×900 | ✅ EV2 |
| 1366×768 | ✅ EV3 (popup fit, controls usable, main line readable) |

---

## 8. Evidence

`docs/ui/evidence/i09-p05/`:
- EV1 1920 full Frame B
- EV2 1600 full Frame B
- EV3 1366 full Frame B
- EV4 steady-state 12 WIPs
- EV5 selected WIP during movement (MTR-0013, AP10→AP11)
- EV6 AP04 JOIN composition
- EV7 SSO2 / PRE-ASSY composition
- EV8 RSO2 / AP04 composition
- EV9 Line-Out tray composition
- EV10 WIP popup/inspector
- EV11 context popup
- EV12 final demo-ready full frame

---

## 9. Tests

```
27 passed (gate suites: test_runtime_service, test_api, test_sensor_quality, test_scenario_loader, test_sim_val_01_feed)
```

Browser smoke (tất cả PASS, console 0 errors):
RESET, STEP, AUTO, PAUSE, speed 0.1x/0.25x, Frame A→B→A, station click, WIP click,
selected WIP follow (halo theo identity), AP04 identity boundary, SSO2/RSO2/off-line context click,
popup close, reset cleanup, sub-line switch, zoom/pan/fit.

---

## 10. PM Self-Review

1. Production semantic change? **NO**
2. Runtime/API/snapshot file change? **NO**
3. `positions[]` meaning change? **NO**
4. MotionEngine rules change? **NO**
5. AP04 identity behavior change? **NO**
6. Context source became authoritative? **NO**
7. Off-line tray showing fake live state? **NO**
8. New feature sneaked in? **NO**
9. 1366 still usable? **YES**
10. Final frame clearer than `06b1b38`? **YES**

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
- LINE OUT/IN routing: NO
- REWORK runtime: NO
- Production Context backlog: NOT STARTED

---

> **I09-P05 — READY FOR SA REVIEW.**
