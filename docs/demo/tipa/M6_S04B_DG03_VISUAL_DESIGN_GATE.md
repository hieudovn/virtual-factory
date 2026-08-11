# M6-S04B-DG03-C02 — Visual Design Gate (Final)

> **Status**: Visual design gate — final. Ready for SA review.  
> **Corrections**: C01 (4 blockers), C02 (evidence cleanup)  
> **Design tool**: SVG/HTML mockups (Figma-ready specification)  
> **Date**: 2026-08-11  
> **Design Authority**: `docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md` v1.1

---

## 1. Visual Evidence Matrix

All artifacts in `docs/demo/tipa/ui/`. Open `.html` in browser at 1920×1080.

| # | State | File | Section | Status |
|---|-------|------|---------|--------|
| 1 | ASSY Line Overview — Normal | `frame_a_assy_overview.html` | Full | ✅ |
| 2 | ASSY Line Overview — Exception | `frame_a_assy_overview.html` | SL03 HOLD lane | ✅ |
| 3 | Sub-line Detail — Normal shared dwell | `frame_b_states_detail.html` | Artboard 1 (view all stations) | ✅ |
| 4 | INDEX_SHIFT (before/transition/after) | `frame_b_states_detail.html` | Artboard 2 (top) | ✅ |
| 5 | AP04 JOIN (parents → child) | `frame_b_states_detail.html` | Artboard 2 (bottom-right) | ✅ |
| 6 | AP06 FAIL/HOLD | `frame_b_states_detail.html` | Artboard 1 | ✅ |
| 7 | AP06 RETEST PASS / READY | `frame_c_states_quality.html` | Section 02 | ✅ |
| 8 | AP08 NG / REINSPECT | `frame_c_states_quality.html` | Section 03 | ✅ |
| 9 | AP11 RELEASED / LINE_OUT | `frame_b_states_detail.html` | Artboard 2 (bottom-left) | ✅ |
| 10 | WIP Inspector | `frame_b_states_detail.html` | Artboard 1 (right panel) | ✅ |
| 11 | Station Inspector | `frame_c_states_quality.html` | Section 04 | ✅ |
| 12 | Event Selected (event ↔ station/WIP) | `frame_c_states_quality.html` | Section 05 | ✅ |
| 13 | 1366×768 readability | `frame_b_states_detail.html` | Artboard 3 | ✅ |

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

---

## 4. Scope Check

- ✅ Design artifacts/documentation only
- ✅ No runtime changes
- ✅ No production UI implementation
- ✅ No MES / M6-S05
- ✅ Canonical UI/UX guide complied with

---

> **M6-S04B-DG03-C02 is READY FOR SA REVIEW.**
