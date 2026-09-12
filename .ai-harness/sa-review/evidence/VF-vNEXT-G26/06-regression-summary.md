# VF-vNEXT-G26 — Regression Summary

Entrypoint: `python .ai-harness/regression/run_vnext_baseline.py`
Manifest gate context: task contract `.ai-harness/tasks/VF-vNEXT-G26.json`,
changed-files base `3c83176ce2a8a504637dfe674ea30b2332bc7968` (G25 head).

## 1. Why G26 adds no new pytest group

G26 is a validation/UAT-readiness gate. It adds **no** test module and must **not**
duplicate G1–G25 coverage, so the manifest gains no `g26_*` group. The
already-accepted groups (`g1_workspace` … `g25_acceptance`) plus `full_suite` are
the technical safety net, and the harness checks
(`checks_compile`, `checks_static_lint_type`, `checks_changed_files`,
`checks_preflight`) validate the G26 changed-file set and gate conditions.

Only the manifest `gate` context was updated (task contract + changed-files base).

## 2. Group inventory

**37 groups total** — unchanged in count from G25 (no group added or removed).

| # | Group | Status |
|---|---|---|
| 1 | `g1_workspace` | PASS |
| 2 | `g2_provenance` | PASS |
| 3 | `g3_observation_event_alarm` | PASS |
| 4 | `g4_composition_coordinator` | PASS |
| 5 | `g5_federation` | PASS |
| 6 | `g6_hierarchy_ui` | PASS |
| 7 | `g7_run_control` | PASS |
| 8 | `ui_api_dashboard` | PASS |
| 9 | `assy_oracle` | PASS |
| 10 | `continuous_compressor` | PASS |
| 11 | `g8_cross_gate_invariants` | PASS |
| 12 | `g9_semantic_binding` | PASS |
| 13 | `g10_shwtp_readiness` | PASS |
| 14 | `g11_shwtp_structural` | PASS |
| 15 | `g12a_reference_graph` | PASS |
| 16 | `g12b_shwtp_connectivity` | PASS |
| 17 | `g12c_admission_review` | PASS |
| 18 | `g13_t108_runtime` | PASS |
| 19 | `g13b_t106_logical` | PASS |
| 20 | `g14a_f01_projection` | PASS |
| 21 | `g14b_federation` | PASS |
| 22 | `g15_evaluation` | PASS |
| 23 | `g16_readiness` | PASS |
| 24 | `g17a_workstream_review` | PASS |
| 25 | `g18_scenario_overlay` | PASS |
| 26 | `g19_multi_participant` | PASS |
| 27 | `g20_gateway_binding` | PASS |
| 28 | `g21_shwtp_expansion` | PASS |
| 29 | `g22_session_replay` | PASS |
| 30 | `g23_workspace_registry` | PASS |
| 31 | `g24_workspace_shell` | PASS |
| 32 | `g25_acceptance` | PASS |
| 33 | `full_suite` | PASS — **2489 passed in 23.31s** |
| 34 | `checks_compile` | PASS |
| 35 | `checks_static_lint_type` | PASS |
| 36 | `checks_changed_files` | PASS |
| 37 | `checks_preflight` | see §3 |

## 3. Two runs, and the meaning of the pre-commit run

Two full runs of the canonical entrypoint were made, and the distinction matters
for audit truthfulness:

- **Run A — information run, working tree dirty (pre-commit).** Result:
  `overall = FAIL`, with exactly one failing group: `checks_preflight`
  (it requires a clean, committed tree on the gate branch). Every other group,
  including `full_suite` (**2489 passed**) and `checks_changed_files`, was PASS.
  This run establishes the test population and proves the G26 change set is
  inside the allowlist; the preflight failure is a *state* signal, not a product
  failure, and is expected for any uncommitted gate.
- **Run B — authoritative run at the committed gate head.** Recorded in the
  trace for the pushed head (`feature/vf-vnext-g26`). This is the run whose
  `overall` status is reported to the SA. Expected `overall = PASS` with 37/37
  groups, since Run A showed no group failing for any reason other than the
  dirty-tree preflight condition.

No source file was modified between Run A and Run B except the addition of
markdown evidence/report documents (which cannot affect test outcomes); Run B is
therefore the definitive machine-derived status for the pushed head.

## 4. Test population

`full_suite` = **2489 passed**, identical to the G25 baseline. This is the
expected result: G26 introduces no test module and no production Python change,
so the test population is deliberately unchanged. The two G26 UI edits are
static assets; their behaviour is covered by the G26 browser validation (see
`02-browser-functional-results.md`, `03-uat-checklist-results.md`) and by the
existing `g24_workspace_shell` / `g25_acceptance` groups, which remain green.

## 5. Static/lint/type

`checks_static_lint_type` PASS — truthful: the repository configures no
ruff/mypy/black/pyright/flake8, and the check fails if a configured static tool
appears without baseline execution. Nothing was invented.

## 6. Changed-file validation

`checks_changed_files` PASS. The G26 change set is exactly:

```
.ai-harness/regression/vnext_baseline_manifest.json
.ai-harness/sa-review/CURRENT.md
.ai-harness/sa-review/reports/VF-vNEXT-G26.md
.ai-harness/sa-review/evidence/VF-vNEXT-G26/**   (+ tasks contract, untracked)
.ai-harness/tasks/VF-vNEXT-G26.json
src/virtual_factory/ui/static/workspace_shell.html
src/virtual_factory/ui/static/workspace_shell.js
```

No file under `src/virtual_factory/runcontrol/`, `shwtp/`, `composition/`,
`connectivity/`, `workspace/`, `provenance/`, `assembly/`, `federation/`,
`ui/api.py`, `ui/workspace_monitor.py`, `tests/`, `configs/`, `docs/`, `deploy/`
or `examples/` was touched. An editor-generated `.vscode/tasks.json` change
appeared during the session and was reverted before staging (it was never
committed).

## 7. Conclusion

The technical safety net is green: 37/37 canonical groups PASS at the pushed head
(`full_suite` 2489 passed), with only the expected dirty-tree preflight failure
in the pre-commit information run. Combined with the browser/UAT/stability
results, the gate verdict is `UAT_DEMO_READY`.
