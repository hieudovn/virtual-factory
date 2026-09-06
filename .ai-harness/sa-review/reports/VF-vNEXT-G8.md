# VF-vNEXT-G8 — Platform vNext Regression Baseline

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G8` (GitHub Issue #53) + C01 |
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
  entrypoint (repo-native Python; per-group PASS/FAIL; exits non-zero on any
  required group failure; optional machine-readable JSON output). C01: manifest
  groups are first-class and may be pytest groups (existing `python -m pytest -q
  -p no:cacheprovider`) OR explicit repo-native command groups (`{python}` and
  `{changed_files_file}` bounded substitutions).
- `.ai-harness/regression/vnext_baseline_manifest.json` — machine-readable
  baseline manifest/contract (v1.1.0) referencing existing authoritative test
  modules/commands (no test duplication). C01: adds first-class non-pytest
  groups `checks_compile`, `checks_static_lint_type`, `checks_changed_files`,
  `checks_preflight`; truthful `static_checks` note (no ruff/mypy/black/
  pyright/flake8 configured; none invented); stale `expected` metadata removed.
- `.ai-harness/regression/check_repo_static_config.py` — truthful static/
  lint/type check (fails if a configured static tool appears without baseline
  execution).
- `tests/test_vnext_g8_invariants.py` — 9 cross-gate invariant tests proving
  the alignment across G1 structural resolution, G6 hierarchy UI projection and
  G7 run-control effective-scope/context identity for TIPA + continuous
  (workspace roots non-executable; TIPA → six ASSY executables; continuous →
  only `continuous/PROCESS`; RunContext identity alignment; disjoint path
  namespaces; no deeper invented topology).
- `tests/test_vnext_g8_entrypoint.py` — 3 bounded smoke tests of the
  command-group code path (failing command group → non-zero exit + names the
  group; passing command group → exit 0; `{python}` substitution).

## 3. Deliberate non-duplication

Invariants already strongly proven by accepted gate suites (independent
TIPA/continuous active runs G7-C02; per-attempt fresh execution state G7-C03)
are referenced via the manifest's `g7_run_control` group rather than
duplicated.

## 4. Regression results (canonical entrypoint, evidence 01/02)

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
| g8_cross_gate_invariants | PASS (12 = 9 invariants + 3 entrypoint smokes) |
| full_suite | **1968 passed** (0 failures) |
| checks_compile | PASS |
| checks_static_lint_type | PASS (truthful: no static tool configured) |
| checks_changed_files | PASS |
| checks_preflight | PASS |

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

`.ai-harness/sa-review/evidence/VF-vNEXT-G8/` —
`01-regression-baseline-and-invariants.md`,
`02-c01-harness-checks.md` (harness checks as first-class baseline groups).

## 8. Final status

```text
VF-vNEXT-G8-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G9 is NOT started.
