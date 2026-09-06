# VF-vNEXT-G8 · Evidence 01 — Platform vNext Regression Baseline

Gate: GitHub Issue #53 — one canonical, repo-native vNext regression baseline
for the accepted G1-G7 platform invariants. No semantics/feature change; no
G9/G10.

## Base / head lineage
- Required base (G7 accepted head): `3f8c9409cac5698399ab4d386506b0419d68a5df`
- Branch: `feature/vf-vnext-g8` (created from the required base)
- Production base (`origin/main`): `f5261c8ca18cd4e01779c0274b55270ba028b4e5`
  (unchanged; G7 not merged)
- Head at review: see report (pushed after this evidence)

## A — Canonical G8 regression entrypoint
`.ai-harness/regression/run_vnext_baseline.py`

Repo-native Python harness (no new framework): it reads the manifest and runs
each group with the existing `python -m pytest -q -p no:cacheprovider`
invocation from the repo root. It reports a per-group PASS/FAIL (identifying the
failing group), writes an optional machine-readable JSON summary, and exits
non-zero if any required group fails (smoke-verified: forced group failure →
exit 1 with `BASELINE FAILED groups: <group>`).

Canonical command (all groups + full suite):
```
python .ai-harness/regression/run_vnext_baseline.py
```
Partial / machine evidence forms:
```
python .ai-harness/regression/run_vnext_baseline.py --groups g1_workspace,g7_run_control
python .ai-harness/regression/run_vnext_baseline.py --json-output <path>.json
```

## B — Baseline manifest / contract
`.ai-harness/regression/vnext_baseline_manifest.json` (schema
`vf.vnext.g8.regression.manifest`, version 1.0.0). It references existing
authoritative pytest modules/commands only; no test implementation is
duplicated. Groups: G1 workspace foundation; G2 provenance; G3
observation/event/alarm; G4 composition/coordinator; G5 federation; G6
hierarchy UI; G7 run control; UI/API dashboard; complete ASSY oracle;
continuous/compressor; G8 cross-gate invariants; full repository suite.

## C — Cross-gate invariant tests (only the genuinely missing slice)
`tests/test_vnext_g8_invariants.py` (9 tests). Proves alignment ACROSS G1
structural resolution, G6 shared hierarchy UI projection and G7 run-control
effective-scope/context identity for both canonical workspaces, plus:
- Workspace roots (TIPA + continuous) are never executable (structural target
  kind "workspace"; UI selection kind "workspace"; root never a participant).
- TIPA: structural == UI == run-control effective scopes == the six ASSY
  executable descendants (`TIPA/ASSY/ASSY-SL01..06`); executable targets
  resolve only themselves.
- continuous: structural == UI == run-control effective scopes == exactly
  `continuous/PROCESS`; no deeper invented topology (PROCESS has no children).
- RunContextV2 workspace/scope identity aligns with target resolution
  (workspace target → no scope_path; executable target → scope_path == target).
- TIPA and continuous structural authorities coexist with disjoint path
  namespaces (no cross-workspace ambiguity).

Already-directly-proven invariants are REFERENCED (manifest `g7_run_control`
group), not duplicated: independent TIPA/continuous active runs (G7-C02) and
per-attempt fresh execution state / reset same-run-same-attempt (G7-C03).

## D — Regression results (run via the canonical entrypoint)
Command: `python .ai-harness/regression/run_vnext_baseline.py --json-output .ai-harness/traces/g8_baseline.json`

| Group | Result |
|---|---|
| g1_workspace | PASS (exit 0) |
| g2_provenance | PASS (exit 0) |
| g3_observation_event_alarm | PASS (exit 0) |
| g4_composition_coordinator | PASS (exit 0) |
| g5_federation | PASS (exit 0) |
| g6_hierarchy_ui | PASS (exit 0) |
| g7_run_control | PASS (exit 0) |
| ui_api_dashboard | PASS (exit 0) |
| assy_oracle | PASS (exit 0) |
| continuous_compressor | PASS (exit 0) |
| g8_cross_gate_invariants | PASS (exit 0, 9 passed) |
| full_suite | PASS (exit 0, **1965 passed**) |
| overall | **PASS** (failed_groups: []) |

Individual group counts (accepted, unchanged): G1 32; G2 36; G3 328; G4 56;
G5 26; G6 31; G7 run-control 50; UI/API dashboard 134; ASSY oracle 354;
continuous/compressor 61. Full suite = 1956 (pre-G8) + 9 new G8 invariants =
**1965 passed** (0 failures).

## Harness checks
- Compile: `python -m compileall -q src tests .ai-harness/regression
  .ai-harness/scripts` → exit 0 (no configured ruff/mypy/black in repo).
- Preflight: PASSED (after commit; branch `feature/vf-vnext-g8`, origin/main
  matches `f5261c8`).
- verify_changed_files: PASSED (only the G8 allowlist paths changed; no src/
  config/docs change).

## Intentionally excluded surfaces
No legacy/demo-only production or UI behavior was modified or run differently.
The ASSY oracle + continuous/compressor + UI/API groups are included exactly as
the accepted gate baselines (unchanged test modules). Continuous legacy
`/start /step /stop /reset` endpoints remain untouched (G7 compatibility).

## Confirmation
- G9/G10 NOT started.
- No change to G1-G7 architecture/semantics; no new hierarchy; no run-control/
  lifecycle change; no PIM binding; no cross-workspace data exchange.
