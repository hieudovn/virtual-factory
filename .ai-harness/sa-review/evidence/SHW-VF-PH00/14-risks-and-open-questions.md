# 14 — Risks & Open Questions

## 14.1 Risks (with mitigations)

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **Duplicate mini-engine recurrence** — SH WTP re-implemented as a third standalone simulator like `simulators/wtp`/`vf2` | HIGH (exactly the failure this gate prevents) | Workspace contract (§06) forces `runtime.engine: continuous_process`; core-change governance (§08) forbids new engines; placement (§11) forbids a new top-level simulator |
| R2 | **Shared-core → domain coupling** (`core/simulation_engine.py` imports `equipment/balance`) | MEDIUM (blocks clean multi-engine) | Flagged (§03); do NOT fix in PH00; schedule a CORE gate only if a second continuous-like engine is actually needed |
| R3 | **No workspace id in output today** — isolation is by CLI args only | MEDIUM | Output provenance contract (§10) adds `workspace_id`; threading it requires a dedicated CORE gate (B8) — NOT folded into PH01 |
| R4 | **Scenario format divergence** (`compressor_benchmark_scenarios.yaml` `inject_fault` unloadable) | MEDIUM | Flagged (§02/§03); SHW scenarios must use the supported action set; `inject_fault` unification is a separate gate |
| R5 | **ASSY hard-coded topology** could be mistaken for the workspace pattern | LOW | §04 explicitly documents ASSY as project-specific and NOT the template for SH WTP |
| R6 | **PIM contract shape instability** (stub is empty) | MEDIUM | PIM boundary (§12) pins artifact+version+sha and requires compatibility review on change; empty stub means `review_required` until populated |
| R7 | **Test-suite sprawl** (90 test files, no per-family markers) | LOW | Isolation test plan (§07) adds per-workspace test files + a workspace-isolation gate |

## 14.2 SA decisions — CLOSED (C02; no longer open questions)

1. **Legacy WTP/VF2 fate (B7) — CLOSED.** `simulators/wtp` and `simulators/vf2`
   are **LEGACY / REFERENCE** for the SH WTP migration path: do not delete/move
   now; no new SH WTP feature development there; do not import them as SH WTP
   runtime dependencies; reusable patterns may be inspected later; promotion
   into shared models requires a separate SA-reviewed DOMAIN-MODEL/CORE gate.
2. **Workspace root (B9) — CLOSED.** `configs/workspaces/`; SH WTP target
   `configs/workspaces/shw-wtp/`; no top-level `workspaces/` restructure.
3. **Provenance threading (B8) — CLOSED.** Requires a dedicated CORE gate; NOT
   folded into PH01. Affected layers: runtime assembly, telemetry, observation,
   CSV/JSONL, MQTT, OPC UA, Sparkplug, tests.
4. **Fidelity (B10) — CLOSED.** `runtime.fidelity_ceiling: logical_only`;
   increases require evidence + explicit SA-reviewed gate.
5. **Canonical identity (B1) — CLOSED.** PIM owns `canonical_object_id` /
   `canonical_signal_id`; VF consumes read-only and uses a DISTINCT internal key
   (`runtime_signal_id`/`local_signal_id`/`model_signal_key`). The prior
   `canonical_signal_id = <workspace_id>.<asset>.<signal>` proposal is REJECTED.

## 14.3 Non-risks (explicitly out of scope)

- ASSY, continuous, compressor demos are **not** at risk — PH00 changes no code.
- No core API change is required to decide the workspace design (§12.3).
- No repo restructure is required before PH01 (§11: `configs/workspaces/` is
  additive).
