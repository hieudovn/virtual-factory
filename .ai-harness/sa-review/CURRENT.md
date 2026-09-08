# SA REVIEW INBOX

Task: VF-vNEXT-G15
Status: READY FOR SA REVIEW (SH-WTP Federated Evaluation Trace & Diagnostics)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G14B-C01 complete)
Prerequisite: Issue #65 (G14B-C01) accepted; Issue #66 (G15) current

Gate type:
IMPLEMENTATION gate — SH-WTP Federated Evaluation Trace & Diagnostics (G15), per Issue #66.
Deterministic evaluation/inspection layer ONLY over the accepted G14B federation. No new runtime/coupling/plant semantics.

Architecture baseline:
G1-G14B-C01 contracts authoritative; G14B-C01 final head = 75521720ae6330160c16075084a36a07ecaa6521 (branch point)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Target (frozen):
- evaluate T106 -> REL-SHW-F01 -> T108 under explicit_lagged (accepted ShwtpFederation + G14B-C01 identity locking)
- one immutable evaluation row per completed window + deterministic summary + lag_windows=1 evaluation metadata

Implemented (additive, isolated):
- src/virtual_factory/shwtp/evaluation.py (+ __init__ exports):
  * ShwtpEvaluationRow (window identity, times, run_id, policy, T106 input/output-staged, T108 inflow-used/committed-next/requested/applied, volume/level/overflow, mass-balance residual, provenance/fidelity/status refs);
  * t108_mass_balance_residual (exact accepted-model invariant; exactly 0.0; no invented tolerance; non-zero fails closed);
  * ShwtpEvaluator(config, window_count>=1) bounded sequential runner (fresh attempt per instance; only completed windows recorded; failed window fails closed);
  * ShwtpEvaluationSummary (derived only from trace: totals/min/max/levels/lag_windows/max residual).
- tests/test_vnext_g15_evaluation.py (30 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G15 gate context + g15_evaluation group)

Frozen boundaries preserved:
- T106 (G13B 19 green) / T108 (G13 28 green) equations + provenance unchanged; G4/Coordinator/participant/transfer unchanged; G14A (20 green) unchanged; G14B-C01 (63 green) unchanged; PIM/G7 unchanged.
- No T110/F02-F07; no scheduler/profile engine; no tolerance policy; no variable per-window scenarios; no UI/alarms/KPIs; no plant-wide execution.
- vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED.

Regression (post-commit, clean tree): G15 30 passed; full suite 2253 passed;
complete canonical vNext baseline PASS (g1..g13b + g14a + g14b + g15 + full_suite + compile/static/changed-files/preflight).

G15 started: YES (completed; READY FOR SA REVIEW)
G16 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G15.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G15/01-evaluation-trace.md
