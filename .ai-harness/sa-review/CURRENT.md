# SA REVIEW INBOX

Task: VF-vNEXT-G26
Status: READY FOR SA REVIEW (Comprehensive Validation & UAT Readiness)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G25 complete)
Prerequisite: G25 accepted; Issue #77 (G26) current

Gate type:
COMPREHENSIVE VALIDATION / UAT READINESS gate, per Issue #77. No new
architecture. Validates the accepted integrated multi-workspace MVP at the
browser/user level, produces a compact UAT checklist with results, a classified
UX issue list, a demo-scale stability smoke check, and a final readiness verdict.
Only small, evidence-driven UI fixes were allowed and applied.

Base:
G25 head = 3c83176ce2a8a504637dfe674ea30b2332bc7968
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (evidence + two small static UI fixes; NO production Python change):
- src/virtual_factory/ui/static/workspace_shell.js (small UI fixes:
  initial-load selection; expose NEW ATTEMPT / REPLAY buttons + enablement)
- src/virtual_factory/ui/static/workspace_shell.html (NEW ATTEMPT / REPLAY buttons)
- .ai-harness/sa-review/evidence/VF-vNEXT-G26/ (01 test plan/coverage matrix,
  02 browser functional results, 03 UAT checklist/results UAT-01..UAT-08,
  04 UX issue list, 05 stability/readiness, 06 regression summary,
  07 final readiness report, stability_smoke.py, stability-results.json)
- .ai-harness/sa-review/reports/VF-vNEXT-G26.md (final readiness report)
- .ai-harness/regression/vnext_baseline_manifest.json (G26 gate context; no new
  pytest group added - G26 adds no test module and must not duplicate G1-G25)

Browser functional validation (live server, /workspaces):
selector from backend registry (TIPA, shwtp); TIPA select -> 6 live ASSY
sub-lines; STEP/RESET/STOP/NEW ATTEMPT/REPLAY verified; shwtp select -> 5-scope
slice RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108 with live flow/tank values;
switching isolation both directions; error handling 404/400/400/400; reload;
no console errors/warnings/unhandled rejections.

UAT: UAT-01..UAT-08 all PASS.

UX: no BLOCKER; one MAJOR (backend new_attempt/replay not exposed in the shell,
so STOP left no in-UI recovery) fixed under this gate; one MINOR (initial load
did not select a Workspace: up to ~3s blank view + "no workspace" run-control
target) fixed; one MINOR narrow-viewport table overflow and four OBSERVATIONs
recorded (not fixed, documented).

Stability smoke: all_ok true, 17/17 checks, 270 steps (120 TIPA + 150 shwtp),
20 switches, bad requests handled, server responsive after; ~108s wall time
(demo-scale timing observation only, not a performance claim).

Verdict: UAT_DEMO_READY (see report).

Frozen boundaries preserved:
No gateway routing / production export / multi-gateway / store-and-forward; no
SH-WTP whole-plant/site-faithful; no T110/Line2; no /assy-demo unification; no
G4/G19/coupling redesign; no distributed execution; no broad UI redesign; no
PIM/MES change.

Authority unchanged:
vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Regression: complete canonical vNext baseline PASS at the pushed head (full suite
PASS; file/preflight checks PASS for the G26 changed-file set). See report.

G26 started: YES (completed; READY FOR SA REVIEW)
Next gate started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G26.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G26/
