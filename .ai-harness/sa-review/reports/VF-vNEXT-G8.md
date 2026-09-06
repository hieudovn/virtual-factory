# VF-vNEXT-G8 — Platform vNext Regression Baseline

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G8` (GitHub Issue #53) |
| Program | Implementation phase (G8; only authorized gate after G7) |
| Required base (branch) | `3f8c9409cac5698399ab4d386506b0419d68a5df` (accepted G7-C03 head) |
| Branch | `feature/vf-vnext-g8` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Model | Flash |
| G9+ started | **NO** |

## 1. Objective

Create one canonical, repo-native vNext regression entrypoint and a
machine-readable baseline manifest/contract for the accepted G1-G7 regression
groups, add only the smallest genuinely-missing cross-gate invariant tests
(structural/run-control/UI-hierarchy alignment), and prove the accepted G1-G7
platform invariants remain green from the exact G7 accepted base lineage — with
no semantics change and no G9/G10.

## 2. Implementation (additive, no src change)

- `.ai-harness/regression/run_vnext_baseline.py` — canonical G8 regression
  entrypoint (repo-native Python; uses the existing `python -m pytest -q -p
  no:cacheprovider`; per-group PASS/FAIL; exits non-zero on any required group
  failure; optional machine-readable JSON output).
- `.ai-harness/regression/vnext_baseline_manifest.json` — machine-readable
  baseline manifest/contract referencing the existing authoritative test
  modules/commands for every group (no test duplication).
- `tests/test_vnext_g8_invariants.py` — 9 cross-gate invariant tests proving
  the alignment across G1 structural resolution, G6 hierarchy UI projection and
  G7 run-control effective-scope/context identity for TIPA + continuous
  (workspace roots non-executable; TIPA → six ASSY executables; continuous →
  only `continuous/PROCESS`; RunContext identity alignment; disjoint path
  namespaces; no deeper invented topology).

## 3. Deliberate non-duplication

Invariants already strongly proven by accepted gate suites (independent
TIPA/continuous active runs G7-C02; per-attempt fresh execution state G7-C03)
are referenced via the manifest's `g7_run_control` group rather than
duplicated.

## 4. Regression results (canonical entrypoint, evidence 01)

| Group | Result |
|---|---|
| g1_workspace | PASS |
| g2_provenance | PASS |
| g3_observation_event_alarm | PASS |
| g4_composition_coordinator | PASS |
| g5_federation | PASS |
| g6_hierarchy_ui | PASS |
| g7_run_control | PASS |
| ui_api_dashboard | PASS |
| assy_oracle (complete) | PASS |
| continuous_compressor | PASS |
| g8_cross_gate_invariants | PASS (9) |
| full_suite | **1965 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

Canonical command: `python .ai-harness/regression/run_vnext_baseline.py`
(overall PASS; machine JSON: `.ai-harness/traces/g8_baseline.json`).

## 5. STOP-condition assessment

None triggered. No G1-G7 architecture/semantics change; no new
workspace/runtime ownership model; no lifecycle/run-identity change; no
coordinator synchronization change; no ASSY/continuous domain change; no new
canonical hierarchy; no G9/G10.

## 6. Acceptance (Issue #53 criteria)

| Criterion | Result |
|---|---|
| One canonical repo-native regression entrypoint | PASS |
| Machine-readable manifest referencing existing tests (no duplication) | PASS |
| Cross-gate invariant tests added only where missing | PASS |
| Canonical entrypoint groups all green | PASS |
| Full repository suite green | PASS |
| Compile/static/preflight/changed-file validation passes | PASS |
| No G9/G10 and no semantics change | PASS |
| Working tree clean and branch/head pushed | PASS (after push) |

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G8/` — `01-regression-baseline-and-invariants.md`.

## 8. Final status

```text
VF-vNEXT-G8 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G9 is NOT started.
