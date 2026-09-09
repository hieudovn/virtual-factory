# SA REVIEW INBOX

Task: VF-vNEXT-G24
Status: READY FOR SA REVIEW (Multi-Workspace UI Switching + Monitoring Shell)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G23 complete)
Prerequisite: Issue #74 (G23) accepted; Issue #75 (G24) current

Gate type:
IMPLEMENTATION gate — Multi-Workspace UI Switching + Monitoring Shell, per
Issue #75. Brings the G23 registry/session selection onto the current
FastAPI + static HTML/CSS/JS UI as a small workspace shell (selector +
read-only monitor + workspace-scoped run controls). UI is observer/controller
only; domain runtimes remain the truth owners.

Base:
G23 head = 320fc4ec1cfcf3b3ebb9566dbc79b3219ab2a33d
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive, isolated):
- src/virtual_factory/ui/workspace_monitor.py (headless WorkspaceMonitor +
  build_platform_registry over the G23 registry + G22 sessions)
- src/virtual_factory/ui/api.py (G24 endpoints: /workspaces shell page,
  /vnext/workspaces, /vnext/workspaces/select,
  /vnext/workspaces/{id}/view, /vnext/workspaces/{id}/control)
- src/virtual_factory/ui/static/workspace_shell.{html,js,css} (shell page:
  selector from backend registry; TIPA reuses /assy-demo six-sub-line UI;
  shwtp shows G21 5-scope slice monitor; shared run bar targets the
  selected workspace only)
- src/virtual_factory/shwtp/expansion.py (read-only ShwtpPlantSlice.monitor_rows()
  observer projection; no physics/domain-semantics change)
- tests/test_vnext_g24_workspace_ui.py (30 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G24 gate context +
  g24_workspace_shell group)

Frozen boundaries preserved:
G23 registry semantics; G22 session semantics; G21/G20/G19/G18/G14/G15; TIPA
ASSY; runcontrol G7 boundary (no SH-WTP reference; runcontrol untouched).
No gateway routing, no MQTT/Kafka/production export, no MES/PIM change, no G4
redesign, no domain semantics change, no T110/Line2.

Authority unchanged:
vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Regression: G24 30 passed; full suite PASS (see report); complete canonical
vNext baseline PASS.

G24 started: YES (completed; READY FOR SA REVIEW)
G25 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G24.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G24/01-workspace-shell.md
