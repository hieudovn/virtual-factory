# SA REVIEW INBOX

Task: DDAY-B3 — Bottled Water 2D Target-Line Skin
Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW

Authority:
SA Issue hieudovn/virtual-factory#104 (B3 ONLY)
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA-issued B3 baseline / branch head at B3 start:
f311edeeda595b3bcbc1a53dece5f9812a6435b1 (match)
harness expected_base_sha (== origin/main):
f5261c8ca18cd4e01779c0274b55270ba028b4e5 (unchanged, not advanced)

What was done:
- Dedicated Bottled Water 2D skin, bound to the B2 generic single-line runtime.
- Frozen 8-station route drawn from the runtime route (not a duplicated constant),
  with workspace-specific artwork for all eight machines plus a bottle token.
- Raw-facts strip (run/operating state, sim time, dwell, total/good/reject, on
  line, Inspection verdict), line-event strip, and read-only station/bottle
  inspectors.
- Exactly five operator controls: START / PAUSE / RESUME / STOP / RESET, plus a
  presentation-clock tick; B2 semantics preserved through the UI.
- Reused VF UI mechanics (viewBox canvas, pan/zoom, selection + popup, polling
  clock, reduced-motion interpolation, state highlighting, design tokens) without
  reusing any other line's artwork, icons, layout, labels or APxx vocabulary.
- api.py gained a minimal domain-neutral projection + controls; demo_controller.py
  was NOT needed and is unmodified; line_runtime.py unmodified.

Interaction bugs found and fixed while verifying in a real browser:
1. pan captured the pointer on pointerdown, retargeting mouseup/click to the
   canvas so machines/bottles were unclickable while the line ran;
2. the station layer was rebuilt on every poll, replacing nodes between
   pointerdown and click;
3. the event window default (12) was smaller than one cycle (~20-30 events).

Tests:
  B3 acceptance 23/23 | UI/API/runtime regression 141/141 | full suite 1689/1689
  (1647 baseline, +17 B2, +2 B2-C01, +23 B3)

Visual evidence (8 screenshots + 10 captured states):
.ai-harness/sa-review/evidence/DDAY-B3/screenshots/
  running, paused, stopped, after-reset, inspection inspector, bottle inspector,
  reject running, reject inspection
Workspace isolation: 2241 rendered strings scanned across all captured states,
0 hits for assy/tipa/pre-assy/sso2/rso2/ap05_jam/APxx.

Evidence:
.ai-harness/sa-review/evidence/DDAY-B3/ (01..04, machine-evidence.json,
browser-evidence.json, implementation.patch, smokes, JUnit XMLs,
flaky-reset-disclosure.txt)
Report:
.ai-harness/sa-review/reports/DDAY-B3.md

Verification commands:
python .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
python -m pytest -q
python .ai-harness/scripts/run_task_gate.py --task .ai-harness/tasks/DDAY-B3.json --token <token>
  (do not set PYTHONIOENCODING=utf-8 on Windows for the gate invocation)

Governance:
- Merge NOT authorized. No next slice authorized (B4+ not started).
- No forbidden path modified; allowlist checks PASS (60 files vs origin/main,
  exactly 6 B3 files vs the B3 baseline).
- No KPI/OEE calculation, no manual decision surface, no later-slice scope.
- Disclosed: pre-existing flaky reset test (id() reuse) left untouched per
  Issue #104; full suite and exact-head CI green.
