# VF-vNEXT-G20 — Generic Gateway / Workstation Observation Binding

Gate: `VF-vNEXT-G20`
Base (required): `babd1f4c872751a47392f9bd26fa865da056ff80` (G19 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Additive generic gateway/workstation observation binding seam: one or more
simulation scopes publish observations through one logical gateway/workstation
without coupling domain runtime to MES/API transport. Architectural seam only —
no production transport.

## Implemented (additive, isolated)

- `src/virtual_factory/integration/binding.py` — `GatewayWorkstation`,
  `GatewayScopeBinding`, `GatewayBindingTable`, `collect_executable_scope_paths`,
  `build_assy_gateway_binding` (ASSY-SL01..06 → ASSY-GW-01 fixture).
- `tests/test_vnext_g20_gateway_binding.py` (22 tests).
- `.ai-harness/regression/vnext_baseline_manifest.json`: G20 gate context +
  `g20_gateway_binding` group.

## Required semantics

- runtime remains sole source of truth;
- gateway read-only observer/adapter/forwarding boundary;
- explicit deterministic scope→gateway binding;
- N scopes → 1 gateway; 1 scope → N gateways allowed;
- gateway identity distinct from Scope/PIM identity;
- message provenance preserved; independent/idempotent messages;
- batching transport-only;
- fail closed on unknown/duplicate/ambiguous binding + identity mismatch;
- deterministic serialization;
- gateway topology ≠ execution order/containment hierarchy.

## Frozen boundaries preserved

ASSY MES bridge + observation stack unchanged; G19/G18/G14/G15 unchanged; no
MQTT/Kafka/REST/retry/security; no MES/PIM modification; no G4 redesign; no
ASSY domain semantics change; no UI.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G20: 22 passed.
- Full suite: 2374 passed.
- Complete canonical vNext baseline
  (g1_workspace, g2_provenance, g3, g4, g5, g6, g7, ui_api_dashboard,
  assy_oracle, continuous_compressor, g8, g9, g10, g11, g12a, g12b, g12c, g13,
  g13b, g14a, g14b, g15, g16, g17a, g18, g19, g20, full_suite, checks_compile,
  checks_static_lint_type, checks_changed_files, checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G20/01-gateway-binding.md`
