# SA REVIEW INBOX

Task: VF-vNEXT-G24-C01
Status: READY FOR SA REVIEW (Workspace Shell reflects selected G22 TIPA RuntimeSession)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G24 complete)
Prerequisite: Issue #75 (G24) accepted; G24-C01 current

Gate type:
CORRECTION gate — G24-C01, on the G24 head
899e851167de768669769dfe650bb46e011024d7. Makes the Workspace Shell's TIPA view
reflect the SELECTED G22 TIPA RuntimeSession: live per-sub-line projection read
from the selected session's own bridge (no second runtime); /assy-demo labelled
a separate legacy demo runtime (identity/state not shared).

Base:
G24 head = 899e851167de768669769dfe650bb46e011024d7
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive, read-only):
- src/virtual_factory/runcontrol/assy_bridge.py (AssyExecutionBridge.sub_line_views())
- src/virtual_factory/ui/workspace_monitor.py (TIPA view live per-sub-line values
  from selected session bridge; runtime_kind=selected_g22_session; /assy-demo
  separate legacy demo runtime label)
- src/virtual_factory/ui/static/workspace_shell.js (live per-sub-line table;
  /assy-demo "(NOT this session)" link)
- tests/test_vnext_g24_workspace_ui.py (C01 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G24-C01 gate context)

Frozen boundaries preserved:
No ASSY runtime/UI rewrite; no legacy-controller unification; no G22/G23
semantics change; runcontrol SH-WTP-free; G21 slice untouched; no G25.

Authority unchanged:
vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Regression: G24 + C01 37 passed; full suite PASS; complete canonical vNext
baseline PASS (see report).

G24-C01 started: YES (completed; READY FOR SA REVIEW)
G25 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G24-C01.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G24-C01/01-tipa-live-projection.md
