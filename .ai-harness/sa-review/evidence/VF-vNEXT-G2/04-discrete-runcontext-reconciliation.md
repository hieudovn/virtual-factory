# VF-vNEXT-G2 · Evidence 04 — discrete.RunContext reconciliation (no duplicate authority)

## 1. Chosen strategy

**Thin adapter** (`src/virtual_factory/provenance/adapter.py`): the legacy
`discrete.RunContext` stays exactly as-is (backward compatible — its constructor,
validation and consumers are unchanged). The generic `RunContextV2` is the single
platform run-context/provenance authority. `from_discrete_run_context(...)`
converts the legacy domain context losslessly into the generic one.

After G2 there is exactly ONE platform run-identity/provenance authority
(`RunContextV2` / `ProvenanceV2`). `discrete.RunContext` is the discrete-domain
constructor input that adapts INTO it — not a second platform authority.

## 2. Lossless field mapping

| `discrete.RunContext` | `RunContextV2` |
|---|---|
| `run_id` | `run_id` |
| `model_id` | `model_id` |
| `model_version` | `model_version` |
| `scenario_id` | `scenario_id` |
| `scenario_version` | `scenario_version` |
| `random_seed` | `random_seed` |
| `environment` | `environment` |
| `engine_kind` (fixed `discrete_manufacturing`) | `profile` (informational, not engine authority) |
| `source_kind` (fixed `simulation`) | validated → provenance `origin_kind=simulation` |
| — (absent) | `workspace_id` (required, supplied by caller) |
| — (absent) | `scope_path` (optional) |

## 3. Backward-compatibility proof

`discrete.RunContext(run_id=..., model_id=...)` still constructs and validates
identically; `DiscreteSimulationEngine`/`DiscreteRunService` `isinstance(...,
RunContext)` checks are untouched (no `discrete/` file changed). Existing
discrete tests pass unchanged.

## 4. Provenance construction

`to_provenance_v2(context, data_status=..., fidelity=..., ...)` builds an
immutable `ProvenanceV2` from a generic context. It never fabricates a canonical
id and never relabels simulation as plant measurement.
