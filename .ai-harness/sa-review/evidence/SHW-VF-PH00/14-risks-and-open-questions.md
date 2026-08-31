# 14 — Risks & Open Questions

## 14.1 Risks (with mitigations)

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **Duplicate mini-engine recurrence** — SH WTP re-implemented as a third standalone simulator like `simulators/wtp`/`vf2` | HIGH (exactly the failure this gate prevents) | Workspace contract (§06) forces `runtime.engine: vf-core`; core-change governance (§08) forbids new engines; placement (§11) forbids a new top-level simulator |
| R2 | **Shared-core → domain coupling** (`core/simulation_engine.py` imports `equipment/balance`) | MEDIUM (blocks clean multi-engine) | Flagged (§03); do NOT fix in PH00; schedule a CORE gate only if a second continuous-like engine is actually needed |
| R3 | **No workspace id in output today** — isolation is by CLI args only | MEDIUM | Output provenance contract (§10) adds `workspace_id`; threading it is a small additive CORE gate, not PH00 |
| R4 | **Scenario format divergence** (`compressor_benchmark_scenarios.yaml` `inject_fault` unloadable) | MEDIUM | Flagged (§02/§03); SHW scenarios must use the supported action set; `inject_fault` unification is a separate gate |
| R5 | **ASSY hard-coded topology** could be mistaken for the workspace pattern | LOW | §04 explicitly documents ASSY as project-specific and NOT the template for SH WTP |
| R6 | **PIM contract shape instability** (stub is empty) | MEDIUM | PIM boundary (§12) pins artifact+version+sha and requires compatibility review on change; empty stub means `review_required` until populated |
| R7 | **Test-suite sprawl** (90 test files, no per-family markers) | LOW | Isolation test plan (§07) adds per-workspace test files + a workspace-isolation gate |

## 14.2 Open questions for SA (no silent resolution)

1. **Fate of `simulators/wtp` (VF-1) and `simulators/vf2` (VF-2).** Should SH WTP
   be implemented inside `src/virtual_factory` (recommended) and the standalone
   simulators retired/deprecated, or must they remain supported in parallel?
2. **Workspace root.** PH00 recommends `configs/workspaces/` (§11). Confirm this
   is acceptable before PH01, or direct the first-class `workspaces/` top-level.
3. **`outputs.namespace` threading.** Adding `workspace_id` to the telemetry
   frame/envelope is a small shared-core change — authorize a dedicated CORE
   gate for it, or allow it as part of PH01?
4. **Fidelity ceiling.** Confirm `fidelity_ceiling: logical_only` as the SH WTP
   starting ceiling (§09), with `FirstOrder` allowed only for documented
   parameters.
5. **Canonical signal id policy.** Confirm `canonical_signal_id =
   <workspace_id>.<asset>.<signal>` and that `SourceMapped` tags remain a
   separate read-only mapping (§10/§12).

## 14.3 Non-risks (explicitly out of scope)

- ASSY, continuous, compressor demos are **not** at risk — PH00 changes no code.
- No core API change is required to decide the workspace design (§12.3).
- No repo restructure is required before PH01 (§11: `configs/workspaces/` is
  additive).
