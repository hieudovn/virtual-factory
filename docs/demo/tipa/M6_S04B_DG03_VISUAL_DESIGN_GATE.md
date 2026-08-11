# M6-S04B-DG03-C03 — Visual Design Gate (Final)

> **Status**: Visual design gate — final. Ready for SA review.  
> **Corrections**: C01 (4 blockers), C02 (evidence cleanup), C03 (evidence mapping + normal shared-dwell)  
> **Design tool**: SVG/HTML mockups (Figma-ready specification)  
> **Date**: 2026-08-11  
> **Design Authority**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` v1.1

---

## 1. Visual Evidence Matrix

All artifacts in `docs/demo/tipa/ui/`. Open `.html` in browser at 1920×1080.

| # | State | File | Section | Status |
|---|-------|------|---------|--------|
| 1 | ASSY Line Overview — Normal | `frame_c_states_quality.html` | Section 01 (HAPPY_PATH) | ✅ |
| 2 | ASSY Line Overview — Exception | `frame_a_assy_overview.html` | SL03 QUALITY HOLD lane | ✅ |
| 3 | Sub-line Detail — Normal shared dwell | `frame_b_states_detail.html` | Artboard 1 (STOP/WORK, concurrent) | ✅ |
| 4 | INDEX_SHIFT (before/transition/after) | `frame_b_states_detail.html` | Artboard 3 (top) | ✅ |
| 5 | AP04 JOIN (parents → child) | `frame_b_states_detail.html` | Artboard 3 (bottom-right) | ✅ |
| 6 | AP06 FAIL/HOLD | `frame_b_states_detail.html` | Artboard 2 | ✅ |
| 7 | AP06 RETEST PASS / READY | `frame_c_states_quality.html` | Section 02 | ✅ |
| 8 | AP08 NG / REINSPECT | `frame_c_states_quality.html` | Section 03 | ✅ |
| 9 | AP11 RELEASED / LINE_OUT | `frame_b_states_detail.html` | Artboard 3 (bottom-left) | ✅ |
| 10 | WIP Inspector | `frame_b_states_detail.html` | Artboard 2 (right panel) | ✅ |
| 11 | Station Inspector | `frame_c_states_quality.html` | Section 04 | ✅ |
| 12 | Event Selected (event ↔ station/WIP) | `frame_c_states_quality.html` | Section 05 | ✅ |
| 13 | 1366×768 readability | `frame_b_states_detail.html` | Artboard 4 | ✅ |

**All 13 states have explicit visual evidence.**

---

## 2. Design Style — Industrial Operations Cockpit

Dark control-room theme (#0d1117), physical-first hierarchy, semantic colors preserved:
- PASS/active: #4ecca3 | FAIL/NG: #e94560 | HOLD/warning: #ffc107 | RELEASED: #17a2b8
- Variant distinction: labels + grouping (#111d30 hydraulic, #141028 thermal) — NOT semantic colors
- Typography: 11-16px for projector-critical labels; monospace for IDs/timestamps

---

## 3. Semantic Consistency Check

- ✅ No HAPPY_PATH + FAIL/HOLD contradiction (exception frame uses AP06_FAIL_RETEST_PASS)
- ✅ No OPERATING + blocking HOLD contradiction (header shows QUALITY HOLD)
- ✅ No same-WIP impossible simultaneous state
- ✅ No forward INDEX while HOLD active
- ✅ No unconfirmed cross-sub-line physical/control independence asserted
- ✅ DEMO/SYNTHETIC DATA labeled in inspector
- ✅ Normal shared-dwell (Artboard 1): conveyor stationary, 6 stations active concurrently, no HOLD, no INDEX, no sequential execution implied

**Artifact structure:**
- `frame_a_assy_overview.html`: Exception-oriented physical overview (6 lanes, SL03 HOLD)
- `frame_b_states_detail.html`: 4 artboards — (1) Normal shared dwell, (2) AP06 HOLD, (3) INDEX_SHIFT + JOIN + RELEASE, (4) 1366×768
- `frame_c_states_quality.html`: 5 sections — (01) Normal overview, (02) RETEST PASS, (03) NG/REINSPECT, (04) Station Inspector, (05) Event Selected

---

## 4. Scope Check

- ✅ Design artifacts/documentation only
- ✅ No runtime changes
- ✅ No production UI implementation
- ✅ No MES / M6-S05
- ✅ Canonical UI/UX guide complied with

---

> **M6-S04B-DG03-C03 is READY FOR SA REVIEW.**
