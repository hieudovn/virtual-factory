# DDAY-B3 — 03. Visual evidence

**Machine record:** [`browser-evidence.json`](./browser-evidence.json) — produced
by [`capture_visual_evidence.py`](./capture_visual_evidence.py), which drives the
real page in a real Chromium against the real app and records what the browser
actually rendered.

Screenshots: [`screenshots/`](./screenshots)

| # | File | What it shows |
|---|---|---|
| 01 | `01-target-line-running.png` | full target line in normal operation: all 8 machines, bottles on the conveyor, live counts |
| 02 | `02-paused.png` | paused state (progression frozen, state preserved) |
| 03 | `03-stopped.png` | controlled stop |
| 03b | `03b-after-reset.png` | known initial state after RESET (empty line, zeroed counts) |
| 04 | `04-inspection-station.png` | Inspection machine selected — station inspector open with the PASS badge |
| 05 | `05-bottle-inspector.png` | bottle selected — read-only unit context with its quality record |
| 06 | `06-reject-running.png` | failing-inspection configuration: reject counter rising, Inspection showing `NG — rejected` |
| 07 | `07-reject-inspection.png` | Inspection machine selected during a reject |

## Captured states

| State | run | total | good | reject | Inspection | stations | bottles |
|---|---|---|---|---|---|---|---|
| running | RUNNING | 15 | 8 | 0 | PASS — continues | 8 | 7 |
| paused | PAUSED | 16 | 9 | 0 | PASS — continues | 8 | 7 |
| paused (after 2.2 s) | PAUSED | 16 | 9 | 0 | PASS — continues | 8 | 7 |
| inspection inspector | PAUSED | 16 | 9 | 0 | PASS — continues | 8 | 7 |
| unit inspector | PAUSED | 16 | 9 | 0 | PASS — continues | 8 | 7 |
| stopped | STOPPED | 16 | 9 | 0 | PASS — continues | 8 | 7 |
| reset | STOPPED | 0 | 0 | 0 | no result yet | 8 | 0 |
| resumed | RUNNING | 2 | 0 | 0 | no result yet | 8 | 2 |
| reject running | RUNNING | 19 | 0 | 15 | NG — rejected | 8 | 4 |
| reject inspector | PAUSED | 19 | 0 | 15 | NG — rejected | 8 | 4 |

*PAUSE proof:* the paused facts are byte-identical after a 2.2 s wait with the
clock still polling (`paused frozen: True`), and the paused count in one capture
(16) vs running (15) reflects the one cycle completed between the two captures.

*RESET proof:* after RESET the counters are zero, nothing is on the line, and the
Inspection indicator returns to "no result yet"; a subsequent START resumes
production (total 2 after two cycles).

## Click proofs (the click actually landed on the drawn element)

| Target | `elementFromPoint` at the click point | Matched |
|---|---|---|
| Inspection machine | `rect.bw-hit` | ✅ `.bw-station` |
| a bottle | `rect.bw-bottle-hit` | ✅ `.bw-bottle` |
| Inspection machine (reject page) | `rect.bw-hit` | ✅ `.bw-station` |

Selection is read-only: the station popup shows station/step/occupancy/bottle plus
the inspection result, and the unit popup shows identity, status, station,
stations completed, rejected, counted-good, quality status and its quality
records — with the explicit note *"This panel is read-only."* and no action
control.

## Workspace-isolation proof (as rendered)

The vocabulary scan runs over the **fully rendered page** (all visible text, all
SVG text, all asset references and the open popup body) for the patterns `assy`,
`tipa`, `pre-assy`, `sso2`, `rso2`, `ap05_jam` and `\bAP\d{2}\b`:

| State | strings scanned | hits |
|---|---|---|
| running | 233 | 0 |
| paused | 232 | 0 |
| paused (after wait) | 232 | 0 |
| inspection inspector | 244 | 0 |
| unit inspector | 253 | 0 |
| stopped | 253 | 0 |
| reset | 137 | 0 |
| resumed | 180 | 0 |
| reject running | 233 | 0 |
| reject inspector | 244 | 0 |

**2241 strings scanned, 0 hits.** The page also references only its own assets
(`bottled_water_demo.css` / `.js`; no other skin).

The eight machine drawings are workspace-specific bottling symbols
(blower/hopper, spray rinser, filler manifold, capper head, camera + light cone,
label roll, case packer, palletizer). Verified rendered geometry per station
(non-empty, distinct bounding boxes):

| Station | shapes | artwork box |
|---|---|---|
| BW-FP-BLW01 | 10 | 120×67 |
| BW-FP-RIN01 | 13 | 108×90 |
| BW-FP-FIL01 | 9 | 112×98 |
| BW-FP-CAP01 | 8 | 100×100 |
| BW-FP-INS01 | 8 | 90×102 |
| BW-FP-LAB01 | 8 | 101×104 |
| BW-FP-CPK01 | 12 | 112×100 |
| BW-FP-PAL01 | 12 | 116×110 |

## Reproducing

```
python -m uvicorn --factory ...              # or the two helper servers (see below)
python .ai-harness/sa-review/evidence/DDAY-B3/capture_visual_evidence.py --port 8123 --fail-port 8124
python .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py
```

The visual capture needs two live servers: one on the shipped configuration and
one whose Inspection checkpoint is set to fail
(`BOTTLED_WATER_CONFIG=<derived line.yaml>`). The reject screenshots come from the
second server.
