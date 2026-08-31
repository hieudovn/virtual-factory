# UI-CTX-02 — Báo cáo triển khai Contextual Source & Line-Out (kèm correction)

> **Baseline**: `77e61a2`  
> **Head hiện tại**: `e46d2a8`  
> **Ngày**: 2026-08-13  
> **Loại**: UI implementation — **KHÔNG đổi backend/runtime/API/snapshot/motion**

---

## 1. Commits

| Commit | Nội dung |
|--------|----------|
| `f0246c7` | UI-CTX-02: SSO2/RSO2 source cues + line-out context tray |
| `e46d2a8` | Correction: rotor feed xếp dọc + stator spacing không chồng |

---

## 2. SSO2 Input Source

- **Vị trí**: gần ASSY INPUT / PRE-ASSY (bên phải)
- **Primitive**: `statorAssy` (không pallet, không conveyor)
- **Bố cục**: 3 icon xếp **dọc**, khoảng cách **58px** (đường kính stator 56px → không chồng)
- **Labels**: `SSO2 INPUT` + `STATOR + SHIELD SOURCE`
- **Connector**: 1 mũi tên nét đứt nhẹ hướng vào PRE-ASSY (flow RIGHT→LEFT)
- **Context-only**: ✅ không wip_id, không `#fb-wips`, không occupancy

---

## 3. RSO2 Rotor Feed

- **Vị trí**: ngay phía trên AP04 JOIN (đã xoá khỏi ASSY INPUT)
- **Primitive**: `rotor` (không pallet)
- **Bố cục**: 3 icon xếp **dọc** (x=1240), khoảng cách **26px** (rotor cao 16px → không chồng)
- **Labels**: `RSO2 ROTOR FEED` + `TO AP04 JOIN`
- **Connector**: 1 mũi tên nét đứt nhẹ vào AP04
- **Context-only**: ✅

---

## 4. ASSY INPUT Zone Cleanup

- Đã xoá pallet rotor (`RSO2 LINE — buffer`) khỏi ASSY INPUT.
- ASSY INPUT giờ chỉ còn: `ASSY INPUT / LINE START` + SSO2 source cue.
- Không còn nhãn nào gợi ý rotor vào đầu line.

---

## 5. Line-Out / Off-Line Context Tray

- **Title**: `LINE-OUT / OFF-LINE ITEMS`
- **Subtitle**: `INSPECT · VERIFY · OPTIONAL REWORK · CONTEXT`
- **Items**: 3 ghost card đại diện — `WIP` (stator) / `MTR` / `PACKED`
  - opacity 0.45, viền nét đứt, **không wip_id / carrier / status / station binding / motion**
  - watermark `CONTEXT — not live WIP`
- **Future-ready**: sẽ populate bằng additive `offline_wips[]` / `exception_cases[]` (không đụng `positions[]`)

---

## 6. Authoritative vs Contextual Separation

| UI element | Authoritative? | Contextual? |
|------------|:---:|:---:|
| `positions[]` (main-line WIP) | ✅ | ❌ |
| AP04 JOIN | ✅ | ❌ |
| SSO2 source (3 icons) | ❌ | ✅ |
| RSO2 rotor feed (3 icons) | ❌ | ✅ |
| Line-out tray items | ❌ | ✅ |
| LINE OUT / LINE IN connectors | ❌ (routing concept) | ✅ |

Layer riêng: `fb-context-sources` (SSO2/RSO2) và `fb-context-offline` (tray). Contextual items **không** vào `#fb-wips`, MotionEngine, station occupancy, runtime counters.

---

## 7. Responsive

| Viewport | Kết quả |
|----------|---------|
| 1920×1080 | ✅ |
| 1600×900 | ✅ |
| 1366×768 | ✅ icon compact, không đè PRE-ASSY/AP04 |

---

## 8. Evidence

`docs/ui/evidence/ui-ctx-02/`:
- EV1 1920 full, EV2 1600 full, EV3 1366 full
- EV4 SSO2 input close-up, EV5 RSO2/AP04 close-up, EV6 off-line tray close-up
- EV7 steady-state 12 WIPs, EV8 AP04 JOIN frame

---

## 9. Tests

```
38 passed in 1.37s
```
Suites: `test_runtime_service`, `test_api`, `test_quality`, `test_sim_val_01_feed`

Browser smoke: RESET/STEP/AUTO/PAUSE, 0.1x/0.25x, Frame A→B→A, station/WIP click, zoom/pan/fit, continuous feed, console 0 errors.

---

## 10. Scope

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
| I09-P04 | NOT STARTED |
| I09-P05 | NOT STARTED |

---

> **STOP — chờ SA duyệt UI-CTX-02 trước khi mở I09-P04.**
