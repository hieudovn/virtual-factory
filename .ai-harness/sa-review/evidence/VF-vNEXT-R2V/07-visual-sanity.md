Validation head: (final commit on this branch)
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 07 — Browser / visual sanity (V07)

Environment: live product server `python -m virtual_factory.main serve --host 127.0.0.1
--port 8099` from this branch; integrated browser at an effective viewport of
**652 x 407** (the harness browser does not honour viewport resize requests, so all
browser evidence below is taken at that size).

## Navigation / identity
- `/workspaces` selects `TIPA` (`workspace_id=TIPA`, `run_id=TIPA-0001`,
  `scenario_id=tipa-default`); shell `STEP` x3 -> `step_count=3`, `last_time_s=360`.
- `/assy-demo` opens without resetting or advancing time; the identity bar reads
  `CANONICAL SESSION TIPA - run TIPA-0001 - scenario tipa-default - profile tipa-assy-happy_path`
  and the header reads `CANONICAL STEP 003`, identical to the shell session.

## Frame A (six-line overview)
- Exactly **six** cards: 3 hydraulic (`ASSY-SL01..03`) + 3 thermal (`ASSY-SL04..06`),
  each live (`WIP: 7  OUT: 0  DW: 6  t=720s`, `CONVEYOR PAUSED`) with a 12-dot station
  strip and landmark highlighting.
- Sidebar counters consistent with six live lines: `WIP ON LINE 42` (6 x 7),
  `CREATED 12` (6 x 2), `RELEASED 0`, `HELD 0`.
- No page-level overflow (`documentElement.scrollWidth - clientWidth = 0`); the card
  region `#vf-overview-main` is an `overflow:auto` container (scrollHeight 716 >
  clientHeight 319), i.e. Frame A scrolls inside its frame instead of breaking layout.

## Frame B (2D physical line, sub-line detail)
- Reached by double-clicking a sub-line card (documented affordance
  "Double-click for detail"); Frame A hides, Frame B shows.
- Renders **12 stations** (`PRE-ASSY`, `AP01..AP11`) plus conveyor, context sources
  (`SSO2 INPUT`, `RSO2 ROTOR FEED -> AP04 JOIN`), `PACKED GOODS` zone, legend and
  counters (`Created: 2  Released: 0  On Line: 7  Holds: 0`).
- WIP tokens `SSO2-0003..SSO2-0007`, `MTR-0002`, `MTR-0001` at `t=720s` `DWELL 6`,
  conveyor `stopped (post-index)`, badge `LIVE`; occupancy equals the canonical
  `positions[]` truth at every observed step.
- Repeated `STEP` on the rich page moves the WIPs and advances the SAME canonical
  session (360 -> 480 -> 600 -> 720 s; a new WIP enters each step, `MTR-0001` appears at
  step 5, `MTR-0002` at step 6). Network trace contains only
  `POST /assy-demo/step` (200) and `GET /assy-demo/sub-line/<id>` (200) — no second
  federation/controller.
- Scenario selector disabled (pinned run input); run-mode selector, speed and zoom/fit
  controls usable; live status `LIVE` (never stale during the session).
- Sub-line selection (single click / opening another line's detail) changes the
  monitored line (`fb-sub-line-id`) while run `TIPA-0001`, scenario and step count stay
  unchanged -> presentation-only, no reset.

## Screenshots
- `shot-frame-a.png` — Frame A (six live cards, identity bar, header step).
- `shot-frame-b.png` — Frame B (12 stations, conveyor, WIP tokens, sim panel).

## Defect classification
- **BLOCKER**: none.
- **MAJOR**: none.
- **MINOR — M1**: one unhandled console error on rich-page load:
  `404 GET /vnext/runs/current?workspace=TIPA` (optional vNext run-context fetch). No
  functional impact observed; no legacy/second runtime created. Not corrected here
  (validation-only gate).
- **OBSERVATION — O1**: at the harness viewport (652 x 407) the 1920 x 1080-scale
  Frame B canvas requires pan/zoom to see the whole line and Frame A needs scrolling
  inside its frame; built-in controls exist (fit-to-screen, zoom +/-, frame scroll).
  No layout break, no unusable control.
- **OBSERVATION — O2**: pointer automation reports "element intercepts pointer events"
  when a card is scrolled under the fixed top bar/sidebar in the small harness window;
  real clicks succeed (Frame B was opened with a genuine double-click) and dispatched
  events also succeed. Harness artefact, not a product defect.
- **OBSERVATION — O3**: no JavaScript exception (`pageerror`) was observed.

## Visual sanity verdict
Frame A and Frame B are readable and correctly laid out for the available viewport,
WIP motion is understandable, the selected line is obvious, identity/controls are
usable and not stale, and the inspector/read models are not stale.
**No BLOCKER / MAJOR defect found.**