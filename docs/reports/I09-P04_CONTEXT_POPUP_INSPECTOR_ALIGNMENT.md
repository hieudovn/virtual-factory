# I09-P04 — Context Popup / Inspector Alignment

> **Baseline**: `e46d2a8`
> **Head triển khai**: `58f4a75`
> **Commit chain**: `e46d2a8 → 7e6e0a7 → 58f4a75`
> **Ngày**: 2026-08-13
> **Loại**: UI interaction alignment — **KHÔNG đổi backend/runtime/API/snapshot/positions[]/motion**
> **C01**: reset stale-popup defect fix (được SA authorize) — chỉ `ctrlB.reset()` cleanup

---

## 1. Mục tiêu

Căn chỉnh tương tác giữa context source (SSO2 / RSO2 / line-out) và popup/inspector, tách bạch
**contextual sources** khỏi **authoritative WIP inspector**, và xử lý **AP04 identity boundary**
(không chuyển identity ngầm khi SSO2 bị tiêu thụ thành MTR).

---

## 2. Changes

| File | Nội dung |
|------|----------|
| `src/virtual_factory/ui/static/assy_demo.js` | `_bindContextClicks()`, `selectContext(type)`, `_renderContextPopup()`, line_state wording, AP04 boundary trong `_renderPopup`, selected-WIP highlight, genealogy parent links clickable |
| `src/virtual_factory/ui/static/assy_demo.css` | `pointer-events` cho context groups, `.vf-context-note/tag`, `.vf-popup-sep`, `.vf-insp-link`, selected WIP halo |
| `src/virtual_factory/ui/static/assy_demo.js` **(C01)** | `ctrlB.reset()`: `this.closePopup(); this._renderInspector(null);` ngay sau khi clear interaction state, trước API round-trip |

---

## 3. Context source clickable

- **SSO2 INPUT**: nhóm `<g data-context="sso2">` → popup "SSO2 INPUT — Upstream stator + shield source feeding ASSY start / PRE-ASSY." + tag "Context source — upstream line not simulated".
- **RSO2 ROTOR FEED**: nhóm `<g data-context="rso2">` → popup "RSO2 ROTOR FEED — Rotor source feeding AP04 JOIN." + row "Feeds → AP04 JOIN".
- **LINE-OUT / OFF-LINE**: nhóm `<g data-context="offline">` → popup "LINE-OUT / OFF-LINE CONTEXT — Representative items shown are context-only, not live WIP".
- `pointer-events: bounding-box` để toàn bộ vùng group (kể cả khoảng trống) bắt click.
- Tabs (Overview/Quality/History/Genealogy) bị ẩn khi hiển thị context; được phục hồi khi mở station/WIP inspector.

---

## 4. Inspector fields (station / WIP)

Popup WIP/station giữ nguyên các field: Station, WIP, Product, Carrier, Status, Quality, Hold,
và thêm **Joined** row cho MTR child (← SSO2-xxxx + RSO2-xxxx @ AP04).

---

## 5. AP04 Identity Boundary

- Chọn một SSO2 đã bị tiêu thụ (không còn on-line) → popup hiển thị:
  `Consumed at AP04 — this identity is now the parent of a new motor.`
  + row `Child MTR → MTR-xxxx ↗` (clickable, không chuyển identity ngầm).
- Click "MTR-xxxx ↗" → quay lại inspector của MTR child.
- Genealogy panel (inspector + context strip) render parent ids dạng **clickable link** (`ctrlB.selectWip`).

---

## 6. line_state presentation

| Giá trị | Hiển thị |
|---------|----------|
| `stopped` | Conveyor: stopped (post-index) |
| `operating` | Conveyor: station work |
| `ready_to_index` | Conveyor: ready to index |
| `indexing` | Conveyor: indexing |

Ánh xạ khớp `ConveyorState` enum (`indexing`/`stopped`/`operating`/`ready_to_index`).

---

## 7. Selected-WIP highlight

- `_applyHighlights()` toggle class `selected` trên `#fb-wips .vf-wip-group` khớp `_selectedWipId`.
- CSS halo (`drop-shadow`) đánh dấu WIP đang được chọn; clear khi close/reset/sub-line switch.

---

## 7b. C01 — Reset stale-popup correction

- **Defect**: `reset()` chỉ xóa interaction state nội bộ, không đóng DOM popup → stale truth hiển thị sau RESET.
- **Fix**: `this.closePopup(); this._renderInspector(null);` chạy **trước** `call('reset')`/`refresh()`.
- **Verify 4+1 trường hợp** (before → after):
  | Case | popup | inspector | halo |
  |------|:---:|:---:|:---:|
  | station → RESET | closed | closed | — |
  | WIP → RESET | closed | closed | cleared |
  | SSO2 context → RESET | closed | closed | — |
  | RSO2 context → RESET | closed | closed | — |
  | off-line context → RESET | closed | closed | — |

---

## 8. Responsive

| Viewport | Kết quả |
|----------|---------|
| 1920×1080 | ✅ |
| 1600×900 | ✅ |
| 1366×768 | ✅ |

SVG `#fb-canvas-svg` fill container (kiểm chứng 1172×650 tại viewport test).

---

## 9. Evidence matrix

`docs/ui/evidence/i09-p04/`:

| Criterion | Evidence | Result |
|-----------|----------|:---:|
| Context source clickable | EV2 (SSO2), EV3 (RSO2), EV4 (offline) | PASS |
| WIP inspector + tabs restored | EV5 | PASS |
| Selected-WIP highlight follows identity | EV5a (PRE-ASSY, before), EV5b (AP01, after) — same `SSO2-0001`, no duplicate | PASS |
| Selected highlight present | EV6 | PASS |
| AP04 identity boundary (consumed SSO2 → child MTR) | EV7, EV8 | PASS |
| Genealogy parent links clickable | EV9 | PASS |
| 1366×768 popup fit | EV11 (popup rect fully in viewport, controls usable) | PASS |
| Reset clears popup/context (C01) | EV13 (before RESET), EV14 (after RESET) | PASS |
| Frame B context sources + line_state | EV1 | PASS |

---

## 10. Tests

```
27 passed (gate suites: test_runtime_service, test_api, test_sensor_quality, test_scenario_loader, test_sim_val_01_feed)
```
Toàn bộ suite: `1278 passed, 2 failed` — 2 failure là **pre-existing** ngoài phạm vi gate
(`test_assy_demo.py::TestVScenarioSwitch::test_scenario_switch_resets_state`,
`test_demo_composition.py::TestReset::test_reset_creates_fresh_configs`), không liên quan
thay đổi UI (JS/CSS-only).

Browser smoke: context click SSO2/RSO2/offline, WIP click, selected highlight, AP04 boundary,
selected WIP before/after STEP, 1366 popup fit, reset clears popup/selection/context, console 0 errors.

---

## 11. Scope

| Concern | Changed? |
|---------|----------|
| Backend | NO |
| Runtime (AssyLineRuntime) | NO |
| API | NO |
| Snapshot contract | NO |
| `positions[]` semantics | NO |
| Motion semantics | NO |
| LINE OUT/IN active routing | NO |
| REWORK runtime | NO |
| Quality semantics | NO |
| Continuous feed policy | NO |
| I09-P05 | NOT STARTED |

C01 correction (authorized): chỉ thêm `closePopup()` + `_renderInspector(null)` trong `ctrlB.reset()`.
Không đổi runtime/API/snapshot/motion; không refactor popup architecture.

---

> **I09-P04-C01 — READY FOR SA REVIEW.**
