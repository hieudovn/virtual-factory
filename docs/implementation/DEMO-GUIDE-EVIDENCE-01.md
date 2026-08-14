# DEMO-GUIDE-EVIDENCE-01 — Current UI Operation Guide Evidence

Status: **DEMO-GUIDE-EVIDENCE-01 — READY FOR SA REVIEW**

Baseline: `59e7ff8` (documentation/evidence only — no production-code change).

This report describes the **exact current UI behavior** at the authorized baseline,
so the official DOCX demo guide can be generated without opening the source code.
All labels/behaviors below were verified against the live browser UI and the
static HTML/JS at `59e7ff8`.

---

## 1. Startup / reset procedure

| Item | Value |
|---|---|
| Start backend | `python src/virtual_factory/main.py serve --port 8091` (env `VF_ENABLE_S04B_OVERVIEW=1`) |
| URL to open | `http://127.0.0.1:8091/assy-demo` |
| Initial page | **Frame A — "ASSY LINE — 6 PARALLEL SUB-LINES"** overview (HYDRAULIC: ASSY-SL01..03, THERMAL: ASSY-SL04..06) |
| Browser refresh safe? | **Yes** — a page reload re-initializes the demo to HAPPY_PATH / fresh state |
| RESET (Frame A) | Sidebar button **"↻ Reset Line"** |
| RESET (Frame B) | Sim panel button **"↻ RESET"** |
| Scenario values | **Happy Path**, **AP06 Fail → Retest → Pass**, **AP08 NG → Reinspect → Pass**, **Failed Final** |
| Default selected sub-line | **ASSY-SL01** |
| Choose sub-line | Frame A: **single-click** a card = select; **double-click** = open detail (Frame B) |
| Default run mode | **AUTO** (Mode selector) |
| Switch mode | Frame B Mode selector: **AUTO / MANUAL / ASSISTED** |
| `STEP` | Advances simulation one dwell+index cycle (all sub-lines step; selected sub-line is shown) |
| `AUTO` button | Starts continuous auto-run (repeated STEP at speed); label changes to **"⏹ STOP"** |
| `PAUSE` | Stops the continuous auto-run timer (enabled only while AUTO is running) |
| Speed selector | **0.1x / 0.25x / 0.5x / 1x / 2x / 5x / 10x** (default **1x**); presentation pacing only |

Evidence: `docs/ui/evidence/demo-guide-evidence-01/01_initial_overview.png`,
`02_frame_b_detail.png`.

---

## 2. Control inventory (verified)

| UI area | Visible label | Exact action | Preconditions | Expected effect | Notes / restrictions |
|---|---|---|---|---|---|
| Sidebar | **↻ Reset Line** | `ctrl.reset()` | any | Rebuilds all 6 sub-lines to HAPPY_PATH | Full reset |
| Sidebar | **⚠ Clear Alarms** | `ctrl.reset()` | any | Same as Reset Line | **Mislabeled** — no separate alarm-clear exists; it just resets |
| Sidebar | **⬇ Export** | `console.log('Export')` | any | Nothing visible | **Placeholder, non-functional** |
| Top bar | **⊞** (Overview) | close Frame B + refresh overview | in Frame B | Returns to 6-sub-line overview | |
| Top bar | **⚙** (Settings) | none | any | nothing | **Inert** (no handler) |
| Top bar | **?** (Help) | none | any | nothing | **Inert** (no handler) |
| Frame A | sub-line card | click select / dbl-click detail | overview | highlight / open Frame B | |
| Sim panel | **↻ RESET** | `uiReset()` | Frame B | Rebuild all sub-lines, close inspector | |
| Sim panel | **▶ STEP** | `uiStep()` | Frame B | one dwell+index cycle | |
| Sim panel | **▶▶ AUTO** | `uiToggleAuto()` | Frame B | start/stop continuous stepping | becomes **⏹ STOP** while running |
| Sim panel | **⏸ PAUSE** | `uiPause()` | AUTO running | stop auto timer | disabled otherwise |
| Sim panel | Speed select | `setSpeed()` | Frame B | pacing only | no runtime semantic change |
| Sim panel | Mode select | `setRunMode()` | Frame B | AUTO/MANUAL/ASSISTED completion mode | affects all sub-lines |
| Footer | Scenario select | `setScenario()` | any | reset with scenario | AP06→SL03, AP08→SL02, Failed Final→SL03 |
| Footer | Speed select (A) | `setSpeed()` | Frame A | pacing only | |
| Footer | **🔍+ / 🔍− / ⊡** | zoom in/out/reset | Frame B | SVG zoom | 100% label |
| Canvas | station | click | Frame B | open inspector + popup | |
| Canvas | WIP | click | Frame B | select WIP, open inspector | |
| Popup | **×** | close popup | popup open | close | |
| Popup tabs | **Overview / Quality / History / Genealogy** | switch tab | popup open | show station/WIP sections | |
| Operation block | **DONE / CONFIRM & COMPLETE / JOIN COMPLETE / PASS / FAIL / NG / RELEASE** | submit command | op AWAITING_*, MANUAL/ASSISTED | authoritative result + refresh | fail-closed on invalid |
| Operation block | checklist checkboxes | toggle item | AP03 gated | enable/disable CONFIRM | |
| Exception drawer | **⋯ Exception → HOLD** | `submitStationAction HOLD` | contract `exception` | HELD + STAY_AT_STATION | AP03, AP11 only |
| Exception drawer | **RESUME** | `submitStationAction RESUME` | op HELD | restore pre-hold state | |
| Event strip | **Quality Events** | click to expand | any | list quality events | bottom-left |

Evidence: `02_frame_b_detail.png`, `03_inspector_popup_tabs.png`.

---

## 3. STEP demo — exact operator script (Happy Path)

Primary target: **SSO2-0001 → AP04 JOIN → MTR-0001 → AP11 RELEASE** (carrier PAL-001).

| Step | State before action | Exact action | Button/control | Expected immediate UI result | Expected production result | Presenter explanation |
|---|---|---|---|---|---|---|
| 1 | Overview | RESET | **↻ Reset Line** | "WIP ON LINE 0" | fresh HAPPY_PATH | "Six parallel sub-lines; we open ASSY-SL01" |
| 2 | Overview | open detail | double-click **ASSY-SL01** | Frame B, SSO2-0001 at PRE-ASSY | target sub-line selected | |
| 3 | Sim panel | set MANUAL | Mode → **MANUAL** | Mode shows MANUAL | decisions wait for operator | "MANUAL proves the operator actually resolves each station" |
| 4 | t=0 | advance | **▶ STEP** | "1 action required", PRE-ASSY AWAITING | PRE-ASSY work done, not complete | "time advanced; station now needs a decision" |
| 5 | inspector | open station | click **PRE-ASSY** | popup + operation block with **DONE** | | |
| 6 | operation | execute | **DONE** | "actions required" clears | operation_result DONE, CONTINUE, eligible | "DONE releases the station" |
| 7 | | index | **▶ STEP** | SSO2-0001 moves to AP01 | physical index | "the line indexes only when all stations are resolved" |
| 8 | AP01 | execute | click AP01 → **DONE** | | DONE/CONTINUE | |
| 9 | AP02 | execute | click AP02 → **DONE** | | DONE/CONTINUE | |
| 10 | AP03 | checklist gate | click AP03 | checklist shown, **CONFIRM & COMPLETE** disabled | | "AP03 is a gated checklist — cannot complete incomplete" |
| 11 | AP03 | check all 3 items | demo_item_1/2/3 checkboxes | button enabled | | |
| 12 | AP03 | execute | **CONFIRM & COMPLETE** | | CONFIRMED, quality null, CONTINUE | |
| 13 | AP04 | JOIN | click AP04 → **JOIN COMPLETE** | inspector WIP changes to **MTR-0001** | JOIN_COMPLETE, child created | "identity handoff: SSO2 + RSO2 → MTR" |
| 14 | AP05 | execute | click AP05 → **DONE** | MTR-0001 remains target | DONE | |
| 15 | AP06 | evidence | click AP06 | measurements + proposal + reason + **PASS/FAIL** | AWAITING_DECISION | "evidence is generated BEFORE the decision" |
| 16 | AP06 | decide | **PASS** | Quality PASS #1 | TEST_COMPLETE, PASS, CLEAR, CONTINUE | |
| 17 | AP07 | execute | click AP07 → **DONE** | | DONE | |
| 18 | AP08 | evidence | click AP08 | vision observations + proposal + **PASS/NG** | | |
| 19 | AP08 | decide | **PASS** | Quality PASS | INSPECTION_COMPLETE, PASS, CLEAR | |
| 20 | AP09/AP10 | execute | click each → **DONE** | | DONE | |
| 21 | AP11 | QC stage | click AP11 | observations + proposal + **PASS** | AWAITING_DECISION | "final QC first — no release yet" |
| 22 | AP11 | QC PASS | **PASS** | State AWAITING_COMPLETION, Result CONFIRMED | quality CLEAR; **not released** | "QC passed but product is NOT yet released" |
| 23 | AP11 | RELEASE | **RELEASE** | Status **released**, RELEASED count +1 | RELEASED, CONTINUE, output | "RELEASE only after QC PASS" |

Notes:
- **Identity change** is visible at AP04 (step 13): the inspector WIP changes from `SSO2-0001` to `MTR-0001`.
- **Other occupied stations** also raise "actions required" (continuous feed fills the line); resolve them all before indexing.
- "actions required" badge = count of operations in `AWAITING_*` with mode ≠ AUTO.
- Simulation time advances (t=…) independently of operation completion — STEP advances time; the operator action completes the station.

Evidence: `docs/ui/evidence/manual-e2e-01/` (full per-station screenshots 01–18) and
`demo-guide-evidence-01/04_ap03_checklist_incomplete.png` … `10_ap11_released.png`.

---

## 4. Station interaction matrix (verified)

| Station | UI label | Inspector state | Interaction | Button(s) | Result | Eligible when |
|---|---|---|---|---|---|---|
| PRE-ASSY | Prep | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP01 | Stator Assy | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP02 | Term. Box | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP03 | Mech. Check | AWAITING_COMPLETION | checklist + confirm | **CONFIRM & COMPLETE** (gated) | CONFIRMED / quality null / CONTINUE | after gate + index |
| AP04 | JOIN | AWAITING_COMPLETION | JOIN | **JOIN COMPLETE** | JOIN_COMPLETE + child | after JOIN + index |
| AP05 | Mech. Assy | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP06 | EOL Test / TEST | AWAITING_DECISION | evidence + decide | **PASS** / **FAIL** | TEST_COMPLETE / PASS / CLEAR / CONTINUE | after PASS + index |
| AP07 | Finish | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP08 | Vision / VISION | AWAITING_DECISION | observation + decide | **PASS** / **NG** | INSPECTION_COMPLETE / PASS / CLEAR / CONTINUE | after PASS + index |
| AP09 | Boxing | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP10 | Pack / Label | AWAITING_COMPLETION | DONE | **DONE** | DONE / CONTINUE | after DONE + index |
| AP11 Stage 1 | Final QC / FINAL | AWAITING_DECISION | QC decide | **PASS** (only) | CONFIRMED / PASS / CLEAR / AWAITING_COMPLETION | **not yet** |
| AP11 Stage 2 | Final QC / FINAL | AWAITING_COMPLETION | release | **RELEASE** | RELEASED / CONTINUE | after RELEASE + index |
| AP03 / AP11 | — | AWAITING_* | HOLD | **⋯ Exception → HOLD** | HELD / STAY_AT_STATION | **never until RESUME** |

HOLD/RESUME is available only at contract-authorized stations (AP03, AP11). FAIL is
**intentionally not exposed** at AP11 (negative final-QC routing is unconfirmed).

---

## 5. AP03 checklist — detailed evidence

- Item labels: **demo_item_1**, **demo_item_2**, **demo_item_3** (intentionally DEMO_SYNTHETIC, neutral).
- Completion button: **"CONFIRM & COMPLETE"** — **disabled** until all three items are checked.
- HOLD entry: **"⋯ Exception"** drawer → **HOLD**.
- After completion: operation_result **CONFIRMED**, quality_result **null** (no fabricated PASS/FAIL), routing **CONTINUE**.

Screenshots: `04_ap03_checklist_incomplete.png` (disabled button),
`05_ap03_checklist_complete.png` (all checked, button enabled).

---

## 6. AP04 JOIN — detailed evidence

- Click AP04 station → inspector shows parent **SSO2-0001** → click **"JOIN COMPLETE"**.
- Immediately after: inspector WIP becomes **MTR-0001**; genealogy row
  `MTR-0001 ← SSO2-0001 + RSO2-0001 @ AP04`.
- Genealogy is viewable in the popup **Genealogy** tab (and the inspector Genealogy section).
- Carrier **PAL-001** is reused (the child is loaded onto the same carrier).
- No automatic index occurs on JOIN — indexing happens only on the next STEP once all stations are eligible.

Screenshots: `manual-e2e-01/06_AP04_JOIN_BEFORE.png`, `07_AP04_JOIN_AFTER.png`.

---

## 7. AP06 electrical test — detailed evidence

Happy Path (PASS):
- Measurements: **R_U-V 0.46Ω [0.30, 0.60] IN RANGE**, **R_V-W 0.48Ω**, **R_W-U 0.45Ω**.
- Proposal row: **PASS**; Reason row: **DEMO_IN_RANGE**.
- Controls: **PASS** / **FAIL**.
- After PASS: **Quality PASS #1**, Quality Events strip gains `PASS MTR-0001 @ AP06`, routing CONTINUE.

FAIL → RETEST → PASS (scenario **"AP06 Fail → Retest → Pass"**):
- Attempt #1: proposal **FAIL**, Reason **DEMO_OUT_OF_RANGE**, first measurement out of range (e.g. R_U-V 0.29Ω OUT).
- Click **FAIL** → Quality **FAIL (attempt 1)**, Hold indicator, Routing **STAY_AT_STATION**; WIP physically stays at AP06.
- Next STEP regenerates a **fresh attempt #2 observation** (proposal PASS) — the evidence belongs to attempt #2.
- Click **PASS** → CLEAR, CONTINUE, eligible. Attempt numbers differ; no duplicate records.

Screenshots: `06_ap06_evidence.png`, `14_ap06_fail_attempt1.png`,
`manual-e2e-01/Q02_AP06_RETEST_PASS_ATTEMPT2.png`.

---

## 8. AP08 Vision — detailed evidence

- Observation basis: neutral IDs **demo_visual_observation_1..3** (ok/anomaly),
  Reason **demo_visual_rule_1**, Proposal **PASS** or **NG**.
- Controls: **PASS** / **NG**.
- Happy Path PASS → **INSPECTION_COMPLETE**, PASS, CLEAR, CONTINUE.
- NG → REINSPECT → PASS (scenario **"AP08 NG → Reinspect → Pass"**): NG → **REINSPECT_PENDING**,
  STAY_AT_STATION, WIP stays AP08; next STEP fresh observation; PASS → CLEAR.

Screenshots: `07_ap08_evidence.png`, `15_ap08_ng_attempt1.png`.

---

## 9. HOLD / RESUME demonstration

Safest/clearest station: **AP03** (checklist gate, then HOLD).

Sequence:
1. Open AP03 inspector (op AWAITING_COMPLETION).
2. Click **"⋯ Exception"** → **HOLD**.
3. Observe: State **HELD**, Routing **STAY_AT_STATION**, HELD metric +1.
4. Click **▶ STEP** → conveyor does **not** index past the held position (blocked).
5. Click **RESUME** → State returns to **AWAITING_COMPLETION** (exact pre-hold state).
6. Complete the normal action (checklist + CONFIRM & COMPLETE).

Facts:
- HOLD is available only at contract-authorized stations (**AP03**, **AP11**) — not all stations.
- **AUTO cannot bypass HELD** — a held operation stays HELD until explicit RESUME.

Screenshots: `11_hold.png`, `12_held.png`, `13_resume.png`.

---

## 10. AP11 — Final QC + RELEASE (two-stage)

Stage 1 (final QC):
- Inspector shows final-QC observations + proposal + a **single PASS** button (no FAIL).
- Click **PASS** → Result **CONFIRMED**, Quality **PASS**, State **AWAITING_COMPLETION**.
- Product is **not yet RELEASED** (Status still `completed_station`, RELEASED count unchanged).

Stage 2 (final disposition):
- **RELEASE** button appears only after QC PASS.
- Click **RELEASE** → Result **RELEASED**, Status **released**, RELEASED metric +1, WIP moves off-line at index.

Facts:
- **FAIL is intentionally not exposed at AP11** at this baseline (negative final-QC routing unconfirmed).
- HOLD/RESUME available via the Exception drawer (AP11 has exception capability).

Screenshots: `08_ap11_qc_pass.png`, `09_ap11_release_gate.png`, `10_ap11_released.png`.

---

## 11. AUTO demo — exact operator script

| Step | Operator action | Exact control | Automated behavior | Monitor | Presenter message |
|---|---|---|---|---|---|
| 1 | RESET | **↻ Reset Line** | rebuild 6 sub-lines | overview | |
| 2 | open detail | double-click **ASSY-SL01** | | Frame B | |
| 3 | keep Mode | Mode stays **AUTO** (default) | runtime auto-resolves decisions | | "AUTO is the same semantics, automated" |
| 4 | choose speed | Speed → **1x** (or 0.25x for slow) | pacing only | | |
| 5 | start | **▶▶ AUTO** | continuous STEP loop | dwell + WIP advance | button → **⏹ STOP** |
| 6 | observe | — | stations resolve automatically | AP04 JOIN, AP06 PASS, AP08 PASS | "the machine supplies the same DONE/PASS/RELEASE" |
| 7 | inspect | click a station/WIP | inspector read-only | proposal/evidence/quality | |
| 8 | stop at AP11 | **⏹ STOP** or **⏸ PAUSE** | stop loop | final QC → RELEASE | |
| 9 | speed back | Speed → **1x** | | | |
| 10 | reset | **↻ RESET** | fresh | | |

- **Mode=AUTO** (completion mode) and the **▶▶ AUTO** button are **distinct**: Mode decides whether the
  runtime auto-resolves each station's decision; the AUTO button just repeatedly presses STEP.
- AUTO runs **continuously** (repeated STEP at the chosen speed), not as a single mega-step.
- Speed is **presentation pacing only** (does not change simulation semantics).
- To freeze long enough to show AP06/AP08 evidence in AUTO: set a low speed (0.1x–0.5x) and/or
  press **⏸ PAUSE** then click the station.

---

## 12. AUTO exception scenarios

| Scenario | Target sub-line | Observable events | Presenter interaction | Recommended speed | Notes |
|---|---|---|---|---|---|
| AP06 FAIL → RETEST → PASS | ASSY-SL03 | AP06 FAIL#1 → RETEST_PENDING → PASS#2 | none (AUTO) | 0.25x–1x | fast; use STEP mode for live explanation |
| AP08 NG → REINSPECT → PASS | ASSY-SL02 | AP08 NG#1 → REINSPECT_PENDING → PASS#2 | none (AUTO) | 0.25x–1x | same |
| HELD under AUTO | any | held op stays HELD | create via MANUAL first | — | AUTO never bypasses HELD |

Caveat: the scenario selector internally **targets SL03/SL02**, but the UI's per-station
command buttons are bound to the selected context (**ASSY-SL01** by default). Therefore:
- In **AUTO**, exception scenarios are fully demonstrable (all sub-lines auto-resolve).
- In **MANUAL**, the exception scenario on SL03/SL02 is not reliably clickable via the visible UI
  (commands target SL01). **Recommend STEP mode for MANUAL exception explanation**, or demonstrate
  AP06 FAIL by clicking FAIL on ASSY-SL01 (operator override of the PASS proposal) — see §7.

---

## 13. Presenter-safe recommended flow (10–15 min)

Recommended order (based on actual UI behavior and time):

- **A. Orientation (1–2 min)** — overview, 6 sub-lines, legend, metrics.
- **B. STEP walkthrough of key stations only (4–5 min)** — PRE-ASSY DONE, AP03 checklist gate,
  AP04 JOIN identity handoff, AP06 evidence→PASS, AP11 QC→RELEASE (skip the pure-DONE stations).
- **C. One exception scenario (2–3 min)** — AP06 FAIL→RETEST→PASS in STEP (clearest to explain).
- **D. AUTO full-line run (2–3 min)** — RESET, Mode AUTO, speed 1x–2x, ▶▶ AUTO, watch full release,
  stop before line empties.
- **E. Recap (1–2 min)** — released count, genealogy `MTR-0001 ← SSO2-0001 + RSO2-0001`, Quality
  Events strip.

Time estimates assume 1x speed and a presenter who pre-rehearsed the STEP clicks.

---

## 14. Known UI limitations / presenter warnings

| Limitation (verified) | Workaround |
|---|---|
| **⚠ Clear Alarms** actually performs a full reset (same as Reset Line) | Do not present it as alarm-clear; use it as a second reset |
| **⬇ Export** is a placeholder (`console.log` only) | Do not demonstrate export |
| **⚙ Settings** and **? Help** are inert (no handler) | Do not click them during the demo |
| Scenario selector targets **SL03/SL02** internally; per-station command buttons target **ASSY-SL01** | Use AUTO for exception scenarios, or STEP on ASSY-SL01 (override FAIL on AP06) |
| "actions required" count includes **all WIPs** on the line (continuous feed), not just the target | Resolve all highlighted stations before indexing; explain this is synchronized-line behavior |
| Selected WIP **changes after AP04** (SSO2 → MTR identity) | Explicitly call out the identity handoff at AP04 |
| AUTO at 10x is too fast to observe | Use 0.25x–1x and **⏸ PAUSE** to inspect |
| Popup (top-right) can cover stations near the top-right | Drag-scroll/zoom or close popup with **×** |
| Inspector/popup controls may require scrolling on small windows | Recommend ≥1280px width; zoom out with **🔍−** |

---

## 15. Evidence paths

- `docs/ui/evidence/demo-guide-evidence-01/` — 15 screenshots (initial UI, control panel,
  inspector tabs, AP03 checklist, AP06/AP08 evidence, AP11 QC+release, HOLD/RESUME, AP06 FAIL, AP08 NG).
- `docs/ui/evidence/manual-e2e-01/` — full per-station journey screenshots (01–18) + TRACE.md.
