# SA REVIEW INBOX

Task: VF-vNEXT-G8-C02
Status: READY FOR SA REVIEW (Platform vNext Regression Baseline — C02 reset identity proof)
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
  regression entrypoint. C01: manifest groups are first-class and may be pytest
  groups (existing `python -m pytest -q -p no:cacheprovider`) OR explicit
  repo-native command groups (bounded `{python}` / `{changed_files_file}`
  substitutions; every command group runs from repo root, reports its group id +
  PASS/FAIL, contributes non-zero to overall failure, and appears in the
  optional JSON output).
- .ai-harness/regression/vnext_baseline_manifest.json — machine-readable
  baseline manifest/contract (v1.1.0) referencing the existing authoritative
  tests/commands for every group (G1 workspace; G2 provenance; G3
  observation/event/alarm; G4 composition/coordinator; G5 federation; G6
  hierarchy UI; G7 run control; UI/API dashboard; complete ASSY oracle;
  continuous/compressor; G8 cross-gate invariants; full suite). C01: adds
  first-class non-pytest command groups checks_compile, checks_static_lint_type,
  checks_changed_files, checks_preflight; truthful `static_checks` note (no
  ruff/mypy/black/pyright/flake8 configured; none invented); stale `expected`
  metadata removed (no hard-coded contradicting counts).
- .ai-harness/regression/check_repo_static_config.py — truthful static/lint/type
  check (passes when none configured; fails if a configured static tool appears
  without baseline execution).
- tests/test_vnext_g8_invariants.py — 9 cross-gate invariant tests proving the
  ALIGNMENT across G1 structural resolution, G6 hierarchy UI projection and G7
  run-control effective-scope/context identity for TIPA + continuous:
  workspace roots never executable; TIPA -> six ASSY executable descendants;
  continuous -> exactly continuous/PROCESS (no deeper topology); RunContextV2
  workspace/scope identity aligns with target resolution; disjoint path
  namespaces (no cross-workspace ambiguity).
- tests/test_vnext_g8_entrypoint.py — 3 bounded smoke tests of the
  command-group code path (failing command group -> non-zero exit + names the
  group; passing command group -> exit 0; {python} substitution).
- C02 (SA comment 5557757350): tests/test_demo_composition.py
  TestReset::test_reset_creates_fresh_runtimes and
  test_reset_creates_fresh_configs no longer use the unsafe id()-after-GC /
  address-reuse pattern. They keep STRONG references to the pre-reset
  runtime/config objects and assert DIRECT identity (`is not`) per sub-line
  after reset — deterministic by construction; assertion NOT weakened; no
  production/semantics change. Minimum allowlist addition for this one test
  file.

Deliberate non-duplication:
- Independent TIPA/continuous active runs (G7-C02) and per-attempt fresh
  execution state / reset same-run-same-attempt (G7-C03) are already directly
  proven by the accepted g7_run_control group and are REFERENCED, not duplicated.

Canonical command:
python .ai-harness/regression/run_vnext_baseline.py
(machine JSON: .ai-harness/traces/g8_baseline.json; overall PASS)

Regression results (canonical entrypoint, evidence 01/02/03):
- g1_workspace PASS; g2_provenance PASS; g3_observation_event_alarm PASS;
  g4_composition_coordinator PASS; g5_federation PASS; g6_hierarchy_ui PASS;
  g7_run_control PASS; ui_api_dashboard PASS; assy_oracle PASS (354,
  deterministic); continuous_compressor PASS; g8_cross_gate_invariants PASS
  (12); full_suite PASS -> 1968 passed (0 failures).
- checks_compile PASS; checks_static_lint_type PASS (truthful: no static tool
  configured); checks_changed_files PASS; checks_preflight PASS.
- C02 stress: corrected TestReset identity tests 30x fresh subprocess runs -> 0
  failures (no address-reuse dependence).
- Compile check PASS; no configured ruff/mypy/black (truthful note).
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
invariants; 02 C01 harness checks as first-class baseline groups; 03 C02
reset identity proof)






