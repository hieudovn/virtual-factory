# UI-CTX-01 — Contextual SSO2 / RSO2 / Line-Out Representation Design Review

> **Gate**: UI-CTX-01 (REVIEW + ANALYSIS ONLY — no implementation)  
> **Baseline**: `b9df954`  
> **Date**: 2026-08-13  
> **Status**: DESIGN REVIEW READY FOR SA

---

## A. Current-State Audit (b9df954)

| Element | Current state |
|---------|---------------|
| Canvas / viewBox | `1920 × 820`, `preserveAspectRatio="xMidYMid meet"`, SVG fills container (`#fb-canvas-svg` 100%×100%) |
| ASSY INPUT zone (right) | Dashed box `ASSY INPUT / LINE START` + 2 contextual pallets: `SSO2 LINE — source` (stator) + `RSO2 LINE — buffer` (rotor) |
| ASSY OUTPUT zone (left) | Dashed box `ASSY OUTPUT / LINE END` + 1 contextual pallet `PACKED GOODS` |
| AP04 rotor cue | Single `rotor` icon above AP04 + label `RSO2`, dashed connector into AP04 |
| Off-line zone (bottom) | Dashed box `OFF-LINE EXCEPTION HANDLING — CONCEPTUAL — WIP FAIL/NG only · Inspect / Diagnose / Optional Rework / Verify` |
| LINE OUT connector | Dashed arrow down at x=1050 (right side, near AP06 region) |
| LINE IN connector | Dashed arrow up at x=650 (left side, near AP08 region) |
| WIP group | `#fb-wips` (separate layer for motion) |
| Station geometry | 12 stations, 96×68 body, uniform Y=330, gaps 115–130px |
| Popup | Works on station + WIP click (restored in b9df954) |
| Readability | Fonts enlarged in 51e22a6; labels clarified |

### Audit screenshot evidence
- `docs/ui/evidence/ui-ctx-01-review/current_state_1366.png`
- `docs/ui/evidence/ui-ctx-01-review/current_state_1600.png`
- `docs/ui/evidence/ui-ctx-01-review/ap04_rso2_context.png`
- `docs/ui/evidence/ui-ctx-01-review/assy_input_sso2_context.png`
- `docs/ui/evidence/ui-ctx-01-review/offline_zone_context.png`

---

## B. Semantic Conflicts (current vs desired)

| # | Conflict | Detail |
|---|----------|--------|
| 1 | **RSO2 rotor at ASSY INPUT is semantically wrong** | RSO2 rotor feeds **AP04 JOIN**, not the general ASSY INPUT. Current arrangement implies rotor enters at PRE-ASSY/AP01. |
| 2 | **No "source queue" semantics** | Current shows single static pallets, not a waiting/source queue of ~3 icons. |
| 3 | **Off-line zone is label-only** | Zone has no items/silhouettes; does not communicate "items may exist outside main line". |
| 4 | **LINE OUT/IN connectors are generic** | No explicit take-off/return semantics; correct per frozen contract (not hardcoded to AP06/AP08), but visually weak. |

---

## C. Proposed Design

### C.1 SSO2 source cue — near ASSY INPUT / PRE-ASSY
```
[ ASSY INPUT ]                    (right side)
    ↑
[ SSO2 INPUT — stator+shield ]
  [ stator ][ stator ][ stator ]   ← ~3 icons, vertical stack, no pallet, no conveyor
```
- Label: `FROM SSO2` or `SSO2 INPUT` (recommend `SSO2 INPUT`).
- Icons: reuse `statorAssy` primitive (ring + shield), NOT pallet, NOT completed MTR.
- One light connector into PRE-ASSY (RIGHT→LEFT flow entry).
- **Recommendation: context-only representative queue (Option A).** Runtime has `sso2_buffer` counter but no per-item upstream occupancy; do not invent counts.

### C.2 RSO2 source cue — directly above AP04 JOIN
```
[ RSO2 ROTOR FEED ]
  [ rotor ][ rotor ][ rotor ]      ← ~3 icons, horizontal row above AP04
          │
          v  (one light connector)
        AP04 JOIN
```
- Label: `FROM RSO2` or `RSO2 ROTOR FEED` (recommend `RSO2 ROTOR FEED`).
- Icons: reuse `rotor` primitive.
- **Move rotor OUT of ASSY INPUT zone** (fixes conflict B-1).
- **Recommendation: context-only representative queue (Option A).** `rso2_buffer` exists but is a buffer count, not per-icon authoritative occupancy.

### C.3 LINE OUT / off-line area — below main conveyor
```
        LINE OUT ↓
  ┌─────────────────────────────────┐
  │ OFF-LINE / LINE-OUT ITEMS AREA  │
  │  [ ] [ ] [ ]                    │  ← future-ready empty slots
  │  No active off-line items       │  ← explicit empty state today
  │  in current scenario             │
  └─────────────────────────────────┘
        ↑ LINE IN
```
- **Recommendation: Hybrid / future-ready tray (Option 3).**
  - Today: explicit empty state + 3 "empty slots" marked `CONTEXT` / `empty`.
  - Future: populate additively via `exception_cases[]` / `offline_wips[]` (does NOT touch `positions[]`).
  - Visually differentiate conceptual slots from real WIP (dashed outline, low opacity, `CONTEXT` watermark).

---

## D. Authoritative vs Conceptual Matrix

| UI element | Authoritative today? | Runtime-backed? | Conceptual? | Future-ready? |
|------------|:---:|:---:|:---:|:---:|
| `positions[]` | ✅ YES | ✅ YES | ❌ | ✅ |
| SSO2 source queue | ❌ NO | ❌ (buffer count only) | ✅ | PARTIAL (`sso2_buffer`) |
| RSO2 source queue | ❌ NO | ❌ (buffer count only) | ✅ | PARTIAL (`rso2_buffer`) |
| AP04 JOIN | ✅ YES | ✅ YES | ❌ | ✅ |
| LINE OUT | ❌ NO (routing concept only) | ❌ NO active routing | ✅ | ✅ (EXH-ROUTE-01) |
| LINE IN | ❌ NO | ❌ NO active routing | ✅ | ✅ (EXH-ROUTE-01) |
| Off-line items | ❌ NO | ❌ NO occupancy contract | ✅ (empty state) | ✅ (additive `offline_wips[]`) |
| REWORK | ❌ NO | ❌ NO | ✅ (label only) | ✅ (EXH-ROUTE-01) |

---

## E. Layout Proposal (ASCII)

```
                 [ RSO2 ROTOR FEED ]
                 [rotor][rotor][rotor]
                          │
                          v
AP11 ← AP10 ← AP09 ← AP08 ← AP07 ← AP06 ← AP05 ← AP04 JOIN ← AP03 ← AP02 ← AP01 ← PRE-ASSY
                                                                                        ↑
                                                                            [ SSO2 INPUT ]
                                                                            [st][st][st]

══════════════════ MAIN CONVEYOR (RIGHT → LEFT) ══════════════════

                    LINE OUT ↓
   ┌─────────────────────────────────────────────────────────┐
   │ OFF-LINE / LINE-OUT ITEMS AREA  ·  CONTEXT               │
   │  [ empty ] [ empty ] [ empty ]                          │
   │  No active off-line items in current scenario            │
   └─────────────────────────────────────────────────────────┘
                    ↑ LINE IN
```

Visual hierarchy (strongest → weakest):
1. Main conveyor + active WIP
2. Station sequence
3. AP04 JOIN
4. SSO2/RSO2 source cues (clearly "source", not stations)
5. Off-line context (clearly "context", not active)
6. Labels/grid

---

## F. Responsive Assessment

| Viewport | Verdict |
|----------|---------|
| 1920×1080 | ✅ Source cues + off-line tray fit without collision |
| 1600×900 | ✅ Mild tightening acceptable |
| 1366×768 | ⚠️ Must keep source cues compact (3 small icons, ≤36px each); off-line tray single row; no new vertical bands |

Source cues must NOT add new horizontal conveyor lanes. Keep icons small and grouped.

---

## G. Interaction Proposal (future I09-P04, not now)

| Click target | Future popup content |
|--------------|---------------------|
| SSO2 source | upstream buffer count, source context |
| RSO2 source | rotor buffer, relation to AP04 JOIN |
| Off-line zone/items | WIP identity, quality status, reason/event, treatment/verification (if known) |

**Canvas text stays minimal.** Data belongs in popup/inspector (frozen principle: shape tells story on canvas, data in popup).

---

## H. Risks

| Risk | Mitigation |
|------|-----------|
| Source queues imply fabricated inventory | Label `CONTEXT`, no exact count (`+N` only if authoritative) |
| Off-line tray implies active routing | Explicit empty state + `CONTEXT` watermark + dashed slots |
| Rotor at ASSY INPUT (current bug) misleads JOIN semantics | Move rotor to AP04 feed (fixes B-1) |
| Extra icons crowd 1366 | Compact icons, no pallets, single row |
| Reopening Physical Composition Freeze | **Not required** — these are additive contextual cues, not main-line geometry changes |

---

## I. Recommendation Summary

1. **SSO2**: context-only representative queue (~3 stator icons, no pallet, no conveyor) near PRE-ASSY / ASSY INPUT. Label `SSO2 INPUT`.
2. **RSO2**: context-only representative queue (~3 rotor icons) directly above AP04 JOIN. Label `RSO2 ROTOR FEED`. **Remove rotor from ASSY INPUT.**
3. **Off-line**: hybrid future-ready tray with explicit empty state + 3 `CONTEXT` slots, populating later via additive `offline_wips[]`.
4. **Interaction**: defer to I09-P04. Canvas stays minimal.
5. **Frozen design impact**: `NO REOPEN REQUIRED` — contextual cues are additive; main-line geometry, station sequence, `positions[]`, motion, and EXH semantics remain frozen.

---

## Q&A — Questions PM Must Answer

| # | Question | Answer |
|---|----------|--------|
| 1 | SSO2 queue context-only or runtime-backed? | **Context-only** (runtime has only `sso2_buffer` count) |
| 2 | RSO2 queue context-only or runtime-backed? | **Context-only** (runtime has only `rso2_buffer` count) |
| 3 | RSO2 cue directly above AP04 or offset? | **Directly above AP04** (single light connector) |
| 4 | SSO2 cue inside ASSY INPUT or separate panel? | **Inside/adjacent ASSY INPUT zone** (near PRE-ASSY) |
| 5 | Source items include pallets? | **No** — use stator/rotor primitives directly, not pallets |
| 6 | Off-line area representative items or empty state? | **Explicit empty state now** + 3 future-ready `CONTEXT` slots |
| 7 | Can future off-line items populate additively without changing `positions[]`? | **Yes** — via `offline_wips[]` / `exception_cases[]` |
| 8 | Should LINE OUT/IN connectors move? | **No** — keep generic, not hardcoded to AP06/AP08 |
| 9 | Reopen Physical Composition Freeze? | **NO REOPEN REQUIRED** |
| 10 | Next gate vs deferred? | Implement source cues + off-line tray in a dedicated correction gate; popup interaction deferred to I09-P04 |

---

## Scope Confirmation

| Concern | Changed? |
|---------|----------|
| Backend | ❌ NO CHANGE |
| AssyLineRuntime | ❌ NO CHANGE |
| API | ❌ NO CHANGE |
| Snapshot contract | ❌ NO CHANGE |
| Motion | ❌ NO CHANGE |
| `positions[]` semantics | ❌ NO CHANGE |
| LINE OUT/IN runtime | ❌ NO CHANGE |
| REWORK runtime | ❌ NO CHANGE |
| I09-P04 | ❌ NOT STARTED |
| I09-P05 | ❌ NOT STARTED |
| Production UI code | ❌ NO CHANGE (this task) |
