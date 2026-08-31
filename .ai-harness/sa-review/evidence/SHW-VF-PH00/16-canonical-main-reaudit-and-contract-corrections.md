# 16 — Canonical Main Re-audit & SA Contract Corrections (C02)

**Audit baseline (canonical):** `main` @ `25a02a520f8371345242879954d7822553e9d004`
(verified: `git rev-parse origin/main` == this SHA, post VF-REPO-LINEAGE-01 merge).

## A. Re-audit result — PH00 findings now CONSISTENT

| PH00 finding (previously CHANGED in C01) | C02 re-audit on canonical main | Verdict |
|---|---|---|
| Runtime families | six-sub-line modules present (8: line_runtime, demo_controller, assy_mes_bridge, observation_bridge, demo_composition, quality_records, operation_execution, station_contracts) **and** `demo_assy_mes/` (9 files) **and** continuous engine **and** discrete kernel | CONSISTENT |
| Runtime entrypoints | `/assy-demo/*` and `/demo-assy-mes/*` both present in `ui/api.py`; `virtual-factory` CLI unchanged | CONSISTENT |
| ASSY architecture | six-sub-line stack + `tipa_assy_demo.yaml` + `docker-compose.assy.yml` all present | CONSISTENT |
| Output/provenance architecture | `mes.py` carries MES v1.1 mappings (`CHECKLIST_CONFIRMED`, `release`, `measurement_result`, `oee_summary`, etc.) | CONSISTENT |

Previously-UNCHANGED findings re-confirmed on canonical main:

| Finding | Re-audit | Verdict |
|---|---|---|
| continuous/compressor engine + `ModelRegistry` | `core/{model_registry,simulation_engine}.py` present | UNCHANGED |
| `simulators/wtp` (VF-1) | `simulators/wtp/main.py` present | UNCHANGED |
| `simulators/vf2` (VF-2) | `simulators/vf2/main.py` present | UNCHANGED |
| `core/` + `discrete/` architecture | `core/model_registry.py`, `core/simulation_engine.py`, `discrete/engine.py` present | UNCHANGED |
| SH WTP placement recommendation | `configs/workspaces/` is config-level, unaffected | UNCHANGED |

**Conclusion: no material new contradiction.** C01's STOP cause (lineage divergence)
is resolved — canonical `main` now contains the six-sub-line ASSY lineage PH00
audited. Re-audit PASSES; proceed to apply SA corrections.

## B. SA contract corrections applied (B1–B10)

### B1 — Canonical identity authority
PIM owns canonical object IDs and canonical signal IDs. VF consumes them
read-only. VF MUST NOT invent or rewrite `canonical_signal_id`. A VF-internal
key is a distinct concept: `runtime_signal_id` / `local_signal_id` /
`model_signal_key`.

### B2 — Three distinct identities
- `workspace_id` = stable logical VF workspace identity.
- `canonical_signal_id` = PIM-owned semantic identity (consumed read-only).
- `outputs.namespace` = protocol/path-safe output namespace.

`workspace_id == outputs.namespace` hard invariant is **removed**. Instead:
`outputs.namespace` MUST be uniquely and deterministically bound to
`workspace_id`, but string equality is NOT required (e.g.
`workspace_id: SHW-WTP` / `outputs.namespace: shw-wtp` is permitted).

### B3 — Runtime engine discriminator
For SH WTP: `runtime.engine: continuous_process`. `vf-core` is NOT an engine
discriminator (it is a platform/shared-layer concept). Conceptual engine kinds
remain the existing runtime families (`continuous_process`, `discrete_assembly`,
`discrete_generic`). No dispatch implementation in C02.

### B4 — Semantic binding fail-closed
Workspace-level concept `semantic_binding.mode` ∈ {`required`, `optional`,
`none`}. For SH WTP: `mode: required`. When required, missing artifact
reference / version / SHA, SHA mismatch, or non-`compatible` review status makes
the workspace invalid to load/run. Contract-only; no validation implemented.

### B5 — Compatibility ownership
PIM owns artifact identity/version/SHA. Compatibility is a relationship between
the exact upstream artifact and the exact VF consumer contract/runtime version,
decided by VF/PIM integration review (not solely by PIM). Conceptual shape:

```yaml
semantic_source:
  artifact: ...
  version: ...
  commit_sha: ...
compatibility:
  consumer: vf
  consumer_contract_version: ...
  status: compatible | review_required | incompatible
  reviewed_by_gate: ...
```

### B6 — Simulation provenance terminology
`origin_kind: simulation` for VF-generated output. Preferred data statuses:
`synthetic` and `simulated_ground_truth`. Plain `measured` / `ground_truth` are
NOT used for ordinary VF-generated data (they could be confused with real
plant/site truth).

### B7 — Legacy WTP/VF2 fate (CLOSED)
`simulators/wtp` and `simulators/vf2` are **LEGACY / REFERENCE** for the SH WTP
migration path: do not delete/move now; no new SH WTP feature development there;
do not import as SH WTP runtime dependencies; reusable patterns/formulas may be
inspected later; promotion into shared models requires a separate SA-reviewed
DOMAIN-MODEL/CORE gate. No longer an open question.

### B8 — Dedicated CORE gate for provenance threading (CLOSED)
Workspace identity/provenance threading through shared runtime-output
infrastructure requires a **dedicated CORE gate** — NOT folded silently into
PH01. Affected layers: runtime assembly, telemetry, observation, CSV/JSONL,
MQTT, OPC UA, Sparkplug, tests. No implementation in C02.

### B9 — Workspace root (CLOSED)
Current-phase canonical workspace root: `configs/workspaces/`. SH WTP target:
`configs/workspaces/shw-wtp/`. No top-level `workspaces/` restructure at this
stage.

### B10 — Fidelity (CLOSED)
SH WTP initial ceiling: `runtime.fidelity_ceiling: logical_only`. Future
increases require evidence and an explicit SA-reviewed gate.

## C. Preserved accepted PH00 direction (re-audit did not disprove)

- one VF platform / many isolated workspaces;
- no new SH WTP mini-engine;
- SH WTP reuses existing continuous `SimulationEngine` + `ModelRegistry`;
- WTP reusable behavior belongs in reusable domain models, not workspace engine code;
- immutable/version-pinned PIM consumption;
- workspace isolation requirements;
- ASSY regression protection.

## D. Changed-file proof (C02)

This C02 gate modifies ONLY `.ai-harness/` artifacts (evidence/report/CURRENT.md).
No production code (`src/`, `configs/`, `simulators/`, `tests/`, `docs/`,
`deploy/`, `pyproject.toml`, `Dockerfile`, compose files) is changed.
