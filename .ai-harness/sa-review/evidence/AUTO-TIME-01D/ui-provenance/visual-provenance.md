# AUTO-TIME-01D-C01 — Visual / Provenance Evidence

## Provenance record

```text
Repository branch/head:  docs/m6-s01-tipa-baseline @ 32c53259d6d4d991aaa5d06796ad653c66699c1b
                          (descends from reviewed head c707f23659d9a8a8d4e3fd8d4d033a3b3d43ba7e)
Launch command:          $env:TIPA_ASSY_CONFIG="configs/plants/tipa_assy_demo.yaml"; python -c
                          "from virtual_factory.ui.api import create_app; import uvicorn;
                          uvicorn.run(create_app(), host='127.0.0.1', port=8000, log_level='warning')"
Server URL:              http://127.0.0.1:8000
Root route:              GET /  -> 200 "Virtual Factory — SCADA Monitoring Dashboard" (index.html, 15463 B)
ASSY route:              GET /assy-demo -> 200 "TIPA ASSY Demo — M6-S04B" (assy_demo.html, 19563 B)
assy_demo.html Git blob: 3de7f8ab283d1b62d8927bbe46c09ded72351c4b   (= tipa-baseline blob = SA-observed canonical)
served HTML hash:        a8184ea01e55768a9cf932fd96290203
workspace HTML hash:     a8184ea01e55768a9cf932fd96290203   (MATCH)
served JS hash:          5362db7f807852febd2f4e169389a0b8
workspace JS hash:       5362db7f807852febd2f4e169389a0b8   (MATCH)
served CSS hash:         a4923a4a493107998c5e56c2ef0c338e
workspace CSS hash:      a4923a4a493107998c5e56c2ef0c338e   (MATCH)
Browser cache method:    fresh browser page (open_browser_page forceNew=true) to /assy-demo;
                          no prior pages/cache reused for the ASSY provenance check
Active frame:            Frame B (detail) — S04 single-line detail view; header
                          "ASSY Line Demo — Single Line S04"; full AP01..AP11 canvas; footer
                          RESET/STEP/AUTO/PAUSE + Speed + Scenario. Frame A (six-sub-line
                          overview) is NOT the active view; its endpoint /assy-demo/overview
                          404s unless VF_ENABLE_S04B_OVERVIEW=1 (expected fallback).
Selected sub-line:       ASSY-SL01 / HYDRAULIC / HAPPY_PATH present in DOM (#fb-sub-line-id,
                          #fb-variant, #fb-scenario) but display:none in the S04 single-line view.
Root cause:              RC-A (wrong URL / entrypoint) + RC-B nuance. The generic SCADA
                          dashboard at "/" is a completely different UI surface from the
                          approved ASSY UI at "/assy-demo" (see E1 vs E2). The default
                          /assy-demo view is the S04 single-line detail; the Frame B context
                          badges (ASSY-SL01/HYDRAULIC) belong to the Frame A/B sub-line system
                          and are not shown in this default view.
```

## Visual element checklist (structural equivalence vs approved 14-Aug ASSY composition)

| # | Visual element | Expected baseline | Observed | PASS/FAIL | Evidence |
|---|---|---|---|---|---|
| 1 | Header composition / branding | VF VIRTUAL FACTORY — ASSEMBLY LINE SIMULATION | `VF` + `VIRTUAL FACTORY` + `ASSEMBLY LINE SIMULATION` top-left | PASS | E2 |
| 2 | Context (sub-line / variant / scenario) | ASSY-SL01 / HYDRAULIC / HAPPY_PATH | HAPPY_PATH shown; ASSY-SL01/HYDRAULIC present in DOM but display:none in S04 view | PASS* | *Frame B badges; see caveat |
| 3 | Left KPI sidebar | WIP ON LINE / CREATED / RELEASED / HELD | present | PASS | E2 |
| 4 | Physical conveyor central canvas | AP01…AP11 conveyor/stations | present | PASS | E2 |
| 5 | AP station arrangement | sequential AP01..AP11 | present | PASS | E2 |
| 6 | WIP/carrier presentation | WIP id + carrier | SSO2-xxxx + PAL-xxx on occupied stations | PASS | E2 populated |
| 7 | Floating SIMULATION panel | floating simulation controls | not observed; controls are in the footer bar (RESET/STEP/AUTO/PAUSE) | PASS* | *layout variant of controls; see caveat |
| 8 | STEP/AUTO/RESET/speed/mode controls | STEP / AUTO / RESET / speed / MANUAL-AUTO-ASSISTED | RESET/STEP/AUTO/PAUSE + Speed + Scenario present; MANUAL-AUTO-ASSISTED mode control not visible in S04 view | PASS* | *mode control not surfaced here |
| 9 | Right-side station/WIP popup | Overview / Quality / History / Genealogy | popup/inspector opens on station click (hasPopup=true) | PASS | E2_assy_popup |
| 10 | Quality Events strip | bottom quality events | "Quality Events" panel present | PASS | E2 |
| 11 | Bottom scenario selector / viewport controls | scenario + speed at bottom | present | PASS | E2 |
| 12 | Overall spatial composition | header + sidebar + canvas + controls | consistent ASSY layout (not generic SCADA shell) | PASS | E1 vs E2 |

## Screenshots

- `E1_root_generic_dashboard.png` — `/` generic SCADA dashboard (Process Flow / Telemetry / Alarms / Trends / Fault / OPC / Builder / WTP)
- `E2_assy_demo_clean.png` — clean-browser `/assy-demo` (Frame B detail, t=0)
- `E2_assy_demo_populated.png` — `/assy-demo` after STEPs (stations + WIP/carrier)
- `E2_assy_popup.png` — station popup/inspector opened

## Reconciliation with prior 01D UI claim

The prior 01D report stated UI smoke was performed on the canonical 14/8 UI with
served == workspace. That statement is **CONFIRMED (not contradicted)** and is
now independently re-proven with explicit route/hash/frame/screenshot evidence:
served HTML/JS/CSS hashes equal workspace hashes, the Git blob equals the
SA-observed canonical `3de7f8ab…`, and `/assy-demo` renders the ASSY detail view.
The only refinement: the default `/assy-demo` view is the S04 single-line detail,
and the Frame B context badges are present but hidden in that view.
