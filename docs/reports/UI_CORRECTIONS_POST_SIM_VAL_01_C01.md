# Báo cáo thay đổi UI — ASSY Demo (post SIM-VAL-01-C01)

> **Ngày**: 2026-08-13  
> **Baseline trước thay đổi**: `deeccf4` (SIM-VAL-01-C01)  
> **Head hiện tại**: `b9df954`  
> **Loại thay đổi**: UI / Frontend correction — **KHÔNG đổi backend/runtime/API/semantics**  
> **Người thực hiện**: PM (AI coding agent) — theo yêu cầu trực tiếp của user

---

## 1. Tổng quan

Sau gate SIM-VAL-01-C01, user phát hiện 3 nhóm vấn đề UI trên Frame B (Sub-line Detail). Đã sửa qua 3 commit riêng lẻ:

| Commit | Nội dung |
|--------|----------|
| `0063322` | Nút điều khiển top-bar (RESET/STEP/AUTO/PAUSE) không hoạt động đúng khi ở Frame B |
| `51e22a6` | Nhãn RSO2/SSO2 bị lặp/gây hiểu nhầm + chữ mờ, đè lên đối tượng |
| `b9df954` | Canvas chỉ chiếm nửa trên màn hình + click WIP không hiện popup |

---

## 2. Chi tiết từng thay đổi

### 2.1 Frame-aware top-bar controls (`0063322`)

**Vấn đề**: Nút RESET/STEP/AUTO/PAUSE luôn gọi `ctrl.*` (Frame A) kể cả khi đang mở Frame B. Kết quả: RESET ở Frame B không refresh view (trông như "không có tác dụng"), STEP/AUTO không cập nhật Frame B.

**Sửa**:
- Thêm router nhận biết frame: `uiReset()`, `uiStep()`, `uiToggleAuto()`, `uiPause()` — tự chọn `ctrlB.*` khi Frame B đang mở, `ctrl.*` khi ở Frame A.
- Cập nhật `onclick` các nút top-bar sang router mới.
- Thêm tốc độ chậm `0.1x` và `0.25x` vào cả 2 speed select (để quan sát dễ hơn).

**Files**: `assy_demo.html` (+12/-4), `assy_demo.js` (+28)

### 2.2 RSO2/SSO2 label + font readability (`51e22a6`)

**Vấn đề**: (a) nhãn `RSO2 ROTOR` lặp 2 chỗ gây cảm giác "nhiều rotor xếp hàng chờ JOIN"; (b) chữ nhỏ/mờ/đè lên thân máy và pallet.

**Sửa**:
| Vị trí | Trước | Sau |
|--------|-------|-----|
| Nhánh AP04 | `RSO2 ROTOR` | `RSO2` |
| Vùng raw — stator | `SSO2 STATOR` | `SSO2 LINE — source` |
| Vùng raw — rotor | `RSO2 ROTOR` | `RSO2 LINE — buffer` |
| Vùng off-line | `CONCEPTUAL — Inspect...` | `CONCEPTUAL — WIP FAIL/NG only · Inspect...` |

**Font/vị trí**:
- AP badge: 13→14px, box 44×20→48×22, nâng lên tránh đè.
- Tên op: 12→13px, màu `--vf-text-secondary`→`--vf-text` (đậm hơn).
- Landmark (JOIN/TEST/VISION/FINAL): 11→12px, y+56→y+64 (thoát khỏi thân máy).
- WIP ID: 9→10px, `--vf-text-muted`→`--vf-text-secondary`.
- Zone label: 11→12px; sub-label: 9→10px.
- LINE OUT/IN: 10→11px.

**File**: `assy_demo.js` (+24/-27)

### 2.3 SVG canvas fill + WIP click popup (`b9df954`)

**Vấn đề 1**: Canvas chỉ hiển thị ở nửa trên màn hình. Nguyên nhân: CSS chỉ có rule `#vf-canvas-svg` (ID cũ), SVG thực tế là `#fb-canvas-svg` → không có `height:100%`, chỉ bị flex kéo ngang (1044px) và tự tính chiều cao theo tỉ lệ (446px), bỏ trống ~280px phía dưới.

**Vấn đề 2**: Click WIP không hiện popup. Nguyên nhân: sau refactor motion (I07), WIP tách sang nhóm `#fb-wips`, nhưng `_bindWipClicks()` vẫn truy vấn `#fb-stations .vf-wip-group`.

**Sửa**:
- CSS: `#vf-canvas-svg, #fb-canvas-svg { width:100%; height:100%; }`
- JS: `_bindWipClicks()` selector → `#fb-wips .vf-wip-group`

**File**: `assy_demo.css` (+2/-2), `assy_demo.js` (+1/-1)

---

## 3. Kiểm chứng

| Hạng mục | Kết quả |
|----------|---------|
| SVG chiều cao | 724.9px = đúng chiều cao Frame B ✅ |
| STEP ở Frame B | DWELL tăng đúng ✅ |
| RESET ở Frame B | về DWELL 0, WIP 1 ✅ |
| Click WIP | popup `PRE-ASSY — SSO2-0002` ✅ |
| Click AP | popup `AP06 — Empty` ✅ |
| Speed 0.1x | mỗi bước 10 giây ✅ |
| Regression tests | **38 passed** (`test_runtime_service`, `test_api`, `test_quality`, `test_sim_val_01_feed`) |

---

## 4. Scope — KHÔNG thay đổi

| Mục | Thay đổi? |
|-----|-----------|
| Backend | ❌ KHÔNG |
| Runtime semantics | ❌ KHÔNG |
| API | ❌ KHÔNG |
| Quality semantics | ❌ KHÔNG |
| Motion semantics | ❌ KHÔNG |
| LINE OUT/IN active routing | ❌ KHÔNG |
| REWORK | ❌ KHÔNG |
| Physical Composition | ❌ KHÔNG (chỉ font/label/nút) |
| I09-P04/P05 | ❌ CHƯA bắt đầu |

---

## 5. Vấn đề còn mở (chờ SA)

1. **LINE OUT semantics**: User từng đề xuất LINE OUT dùng cho "thành phẩm đang Hold cần Rework". Đã thống nhất **giữ nguyên frozen contract** (LINE OUT = WIP exception FAIL/NG), tạm bỏ qua ý kiến đó, sẽ chốt với SA ở phase sau.
2. **Icon RSO2/SSO2**: User thấy "nhiều rotor/stator xếp hàng". Đã chỉ đổi nhãn chữ. Việc bỏ/gom các pallet contextual (icon) đang chờ user trao đổi với SA trước khi sửa tiếp.

---

## 6. Git history

```
b9df954 fix: SVG canvas fills container + restore WIP click popup
51e22a6 ui: clarify RSO2/SSO2 source labels + readable fonts + fix text overlap
0063322 fix: frame-aware top-bar controls (reset/step/auto/pause) + slower speed options
deeccf4 SIM-VAL-01-C01 (baseline)
```

> **STOP — Báo cáo chỉ để SA review. Chưa có yêu cầu sửa thêm.**
