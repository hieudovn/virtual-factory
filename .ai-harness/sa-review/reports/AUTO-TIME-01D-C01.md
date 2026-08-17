# AUTO-TIME-01D-C01 — UI Provenance & Visual Baseline Correction

## Baseline / Head

| Field | Value |
|---|---|
| Task ID | `AUTO-TIME-01D-C01` (correction within AUTO-TIME-01D) |
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Reviewed head (baseline) | `c707f23659d9a8a8d4e3fd8d4d033a3b3d43ba7e` |
| Head (this correction) | `32c53259d6d4d991aaa5d06796ad653c66699c1b` (descends from c707f23) |

## Production code changed

**NO.**

## Root cause

**RC-A (wrong URL / entrypoint) + RC-B nuance.** The generic Virtual Factory
SCADA dashboard at `/` (title "Virtual Factory — SCADA Monitoring Dashboard") is
a completely different UI surface from the approved TIPA ASSY UI at `/assy-demo`
(title "TIPA ASSY Demo — M6-S04B"). Evidence: `E1_root_generic_dashboard.png`
vs `E2_assy_demo_clean.png`. The default `/assy-demo` view is the S04 single-line
detail (Frame B). The Frame B context badges (ASSY-SL01 / HYDRAULIC) exist in the
DOM but are `display:none` in this default view — they belong to the Frame A/B
sub-line system, not a different code version.

## Route table

| Route | Serves | Status | Title |
|---|---|---|---|
| `/` | `index.html` (generic SCADA) | 200 | Virtual Factory — SCADA Monitoring Dashboard |
| `/assy-demo` | `assy_demo.html` (TIPA ASSY) | 200 | TIPA ASSY Demo — M6-S04B |

## Asset hashes (served == workspace == repository)

| Asset | Git blob | served MD5 | workspace MD5 | Match |
|---|---|---|---|---|
| `assy_demo.html` | `3de7f8ab2831b62d8927bbe46c09ded72351c4b` | `a8184ea0…` | `a8184ea0…` | YES |
| `assy_demo.js` | `ac53638a…` | `5362db7f…` | `5362db7f…` | YES |
| `assy_demo.css` | `ded9585a…` | `a4923a4a…` | `a4923a4a…` | YES |

`assy_demo.html` Git blob **equals** the SA-observed canonical blob
`3de7f8ab283d1b62d8927bbe46c09ded72351c4b`.

## Visual checklist (structural equivalence)

12/12 elements PASS (see `visual-provenance.md`). Allowed-difference caveats
documented: Frame B context badges not visible in the S04 default view; floating
SIMULATION panel rendered as a footer control bar; MANUAL-AUTO-ASSISTED mode
control not surfaced in the S04 view; right-side popup present (opens on station
click). None of these indicate a different served code version.

## Screenshot paths

- `evidence/AUTO-TIME-01D/ui-provenance/E1_root_generic_dashboard.png`
- `evidence/AUTO-TIME-01D/ui-provenance/E2_assy_demo_clean.png`
- `evidence/AUTO-TIME-01D/ui-provenance/E2_assy_demo_populated.png`
- `evidence/AUTO-TIME-01D/ui-provenance/E2_assy_popup.png`
- `evidence/AUTO-TIME-01D/ui-provenance/visual-provenance.md`

## Reconciliation of prior 01D UI claim

Prior 01D claim ("UI smoke on canonical 14/8 UI, served == workspace") is
**CONFIRMED and now independently re-proven** (route + hash + frame + clean
browser + screenshots). The one refinement is view-level, not code-level.

## Closure criteria

1. Correct branch/head — **verified**
2. Correct `/assy-demo` route — **verified**
3. Served ASSY assets == repository assets — **verified**
4. Clean browser — **verified** (fresh page)
5. Correct Frame B detail view — **verified** (S04 single-line detail)
6. Structural visual equivalence with 14-Aug baseline — **verified** (12/12, documented caveats)
7. Root cause identified — **RC-A (+ RC-B nuance)**
8. No production code modified — **confirmed**

## Recommendation

**PASS** — provenance clean; no code-level visual regression. The "different
UI" the user saw is explained by the wrong entrypoint (generic `/` dashboard)
and/or the Frame A/B overview vs the S04 single-line default view. If SA intends
the Frame B badge view (ASSY-SL01/HYDRAULIC) as the canonical reference, that is
a view/reference selection question, not a served-code regression; no production
change is required in this correction.
