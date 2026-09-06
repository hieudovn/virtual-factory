# SA REVIEW INBOX

Task: VF-vNEXT-G8
Status: READY FOR SA REVIEW (Platform vNext Regression Baseline)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized gate after G7)
Prerequisite: Issue #52 accepted as completed; G1-G7 contracts authoritative

Gate type:
Regression baseline gate — Platform vNext Regression Baseline (G8), per Issue #53

Architecture baseline:
ARCH-01..06 accepted; G1-G7 contracts authoritative
Required base (branch point): 3f8c9409cac5698399ab4d386506b0419d68a5df (accepted G7-C03 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive; NO src/ change):
- .ai-harness/regression/run_vnext_baseline.py — canonical, repo-native G8
  regression entrypoint (uses existing `python -m pytest -q -p no:cacheprovider`
  per deterministic group; reports the failing group; exits non-zero if any
  required group fails; optional machine-readable JSON output). Verified: forced
  group failure -> exit 1 + `BASELINE FAILED groups: <group>`.
- .ai-harness/regression/vnext_baseline_manifest.json — machine-readable
  baseline manifest/contract (schema vf.vnext.g8.regression.manifest v1.0.0)
  referencing the existing authoritative tests/commands for every group (G1
  workspace; G2 provenance; G3 observation/event/alarm; G4
  composition/coordinator; G5 federation; G6 hierarchy UI; G7 run control;
  UI/API dashboard; complete ASSY oracle; continuous/compressor; G8 cross-gate
  invariants; full suite). No test-logic duplication.
- tests/test_vnext_g8_invariants.py — 9 cross-gate invariant tests proving the
  ALIGNMENT across G1 structural resolution, G6 hierarchy UI projection and G7
  run-control effective-scope/context identity for TIPA + continuous:
  workspace roots never executable; TIPA -> six ASSY executable descendants;
  continuous -> exactly continuous/PROCESS (no deeper topology); RunContextV2
  workspace/scope identity aligns with target resolution; disjoint path
  namespaces (no cross-workspace ambiguity).

Deliberate non-duplication:
- Independent TIPA/continuous active runs (G7-C02) and per-attempt fresh
  execution state / reset same-run-same-attempt (G7-C03) are already directly
  proven by the accepted g7_run_control group and are REFERENCED, not duplicated.

Canonical command:
python .ai-harness/regression/run_vnext_baseline.py
(machine JSON: .ai-harness/traces/g8_baseline.json; overall PASS)

Regression results (canonical entrypoint, evidence 01):
- g1_workspace PASS; g2_provenance PASS; g3_observation_event_alarm PASS;
  g4_composition_coordinator PASS; g5_federation PASS; g6_hierarchy_ui PASS;
  g7_run_control PASS; ui_api_dashboard PASS; assy_oracle PASS;
  continuous_compressor PASS; g8_cross_gate_invariants PASS (9);
  full_suite PASS -> 1965 passed (0 failures).
- Compile check PASS (`python -m compileall -q src tests .ai-harness/regression
  .ai-harness/scripts` -> exit 0; no configured ruff/mypy/black).
- Preflight PASSED; verify_changed_files PASSED (G8 allowlist only).

Deferred (NOT implemented): G9 semantic binding, G10 SH-WTP runtime, full replay
browser/editor/history subsystem, scenario editor, universal reset/
synchronization policy. (G8 baseline entrypoint is the accepted regression
program.)

STOP conditions: none triggered.

G9 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G8.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G8/ (01 regression baseline + cross-gate
invariants)






