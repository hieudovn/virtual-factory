# VF-vNEXT-G2 · Evidence 01 — Repo-first discovery + changed-file inventory

## 1. Baseline

| Item | Value |
|---|---|
| G1 base (required) | `ac329fbd7f96614be9f09e8037a3e10cfabaf1dd` |
| Branch | `feature/vf-vnext-g2` (from G1 base) |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` (inspected; not merged) |

## 2. Repo-first discovery / classification

| Seam (verified) | Finding | Classification |
|---|---|---|
| `discrete/run_context.py` `RunContext` | frozen, owns `run_id`/`model_id`/`scenario_id`/`scenario_version`/`random_seed`/`environment`; hard-codes `engine_kind='discrete_manufacturing'`, `source_kind='simulation'` | **adapt** (domain precedent → adapter) |
| `discrete/state.py`, `engine.py`, `run_service.py` | consume `RunContext`; engine checks `isinstance(run_context, RunContext)` | reuse (unchanged) |
| `discrete/engine.py`, `run_service.py` use `run_id` as execution identity | existing run identity | reuse |
| `assembly/*` ASSY run ids/idempotency | must remain unchanged | deferred (G5) |
| `observation/envelope.py` | immutable envelope w/ `run_id`, `model_id`, time, idempotency | reuse (G3 owns alignment) |
| `telemetry/telemetry_frame.py` `build_publishable_frame` | plain `list[SignalValue]`, no envelope | **adapt** (additive G2 seam) |
| `telemetry/output_policy.py` | industrial publication categories; must not be repurposed as provenance truth | reuse (unchanged) |
| `telemetry/signal_value.py` `SignalValue` | frozen truth sample | reuse (unchanged) |
| `telemetry/export.py` | `frame_to_records`/CSV/JSONL over `SignalValue` | reuse (unchanged) |
| `integration/mqtt_gateway.py`, `opcua_gateway.py` | consume `list[SignalValue]` via `publish_frame` | reuse (not modified — protocol seam stays SignalValue) |
| PH00 `10-output-provenance-contract.md` | frozen additive envelope fields + rules (B1/B2/B6) | **generic new** (this gate) |
| G1 `workspace.identity.StructuralPath` | structural scope identity | reuse |

## 3. Changed-file inventory (why in scope)

| File | Purpose |
|---|---|
| `src/virtual_factory/provenance/enums.py` | `OriginKind`/`DataStatus`/`Fidelity` frozen truth labels |
| `src/virtual_factory/provenance/context.py` | generic immutable `RunContextV2` |
| `src/virtual_factory/provenance/envelope.py` | immutable `ProvenanceV2` |
| `src/virtual_factory/provenance/namespace.py` | deterministic output namespace |
| `src/virtual_factory/provenance/adapter.py` | `from_discrete_run_context` + `to_provenance_v2` |
| `src/virtual_factory/provenance/__init__.py` | public API |
| `src/virtual_factory/telemetry/telemetry_frame.py` | **additive** `ProvenancedFrame` + `build_provenanced_frame` (legacy `build_publishable_frame` unchanged) |
| 5 new test files | focused G2 proofs (see evidence 06) |
| `.ai-harness/` | task JSON + evidence + report + CURRENT.md |

No `discrete/`, `assembly/`, `observation/`, `ui/`, `integration/`, `core/`, or
`equipment/` production file was modified. `AssyLineRuntime` untouched.

## 4. Protocol/export propagation decision

`mqtt_gateway.py`/`opcua_gateway.py` consume `list[SignalValue]` directly
(`publish_frame`). G2 does **not** change those protocol contracts (their
SignalValue seam is unchanged and already works). Provenance is threaded at the
common `telemetry_frame` boundary as a wrapper (`ProvenancedFrame`), so a future
gate can attach it to protocol publishers without a breaking external schema.
Explicit deferral: no protocol schema change in G2 (no breaking schema was
required).
