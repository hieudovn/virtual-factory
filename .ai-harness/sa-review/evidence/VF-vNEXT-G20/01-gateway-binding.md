# VF-vNEXT-G20 — Generic Gateway / Workstation Observation Binding — Evidence

Gate: `VF-vNEXT-G20` · Implementation gate (additive model/binding/fixture + tests).
Base: `babd1f4c872751a47392f9bd26fa865da056ff80` (G19 head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/integration/binding.py` — generic, read-only scope→gateway
  observation binding seam:
  - `GatewayWorkstation` — logical gateway identity, distinct from G1
    `StructuralPath` (rejects `/`) and PIM canonical ids (rejects `PROC-`/`UNIT-`/
    `REL-`/`SIG-` prefixes).
  - `GatewayScopeBinding` — explicit deterministic scope→gateway binding with
    `binding_id`, `gateway_id`, `scope_path`, `domain`.
  - `GatewayBindingTable` — immutable deterministic set of bindings; fail-closed
    on unknown scope/gateway, duplicate binding id, duplicate logical binding,
    identity mismatch; deterministic `serialize()`/`from_dict()`; fan-in and
    fan-out resolution helpers.
  - `collect_executable_scope_paths(workspace)` — derive the known scope universe
    from a G1 Workspace.
  - `build_assy_gateway_binding()` — bounded TIPA ASSY fixture binding
    ASSY-SL01..06 → ASSY-GW-01 (declaration only; no ASSY runtime/MES rewrite).
- `tests/test_vnext_g20_gateway_binding.py` — 22 tests.

## 2. Required semantics coverage

| Requirement | Proof |
|---|---|
| runtime remains source of truth | binding module has no runtime imports/mutation; fixture is declaration-only |
| gateway read-only observer/adapter | `GatewayBindingTable` is a frozen dataclass; no mutation path |
| explicit deterministic scope→gateway binding | `GatewayScopeBinding` with deterministic identity/sort |
| N scopes → 1 gateway | fixture: 6 scopes → ASSY-GW-01 |
| 1 scope → N gateways allowed | test binds one scope to two gateways without error |
| gateway identity distinct from Scope/PIM | `GatewayWorkstation` rejects `/` and PIM prefixes |
| message provenance preserved | envelope source_domain/source_path/run_id/time survive resolution |
| messages independently identifiable/idempotent | `make_idempotency_key` distinct per source event |
| batching transport-only | no batching semantics added; existing message key preserved |
| unknown/duplicate/ambiguous binding fail closed | tests for unknown scope/gateway, duplicate id/logical, identity mismatch |
| deterministic serialization | input-order-independent serialize + round-trip |
| topology ≠ execution order/containment | no `execution_order`/`containment`/`order`/`parent` fields |

## 3. Preserved / unchanged

ASSY MES bridge + observation stack (`ObservationService`/`Router`/`Projection`/
`ObservationGatewayProtocol`) untouched; G19/G18/G14/G15 unchanged; no MQTT/
Kafka/REST/retry/security; no MES/PIM modification; no G4 redesign; no ASSY
domain semantics change; no UI.

## 4. Test evidence

- `tests/test_vnext_g20_gateway_binding.py` — 22 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G20.md`).
