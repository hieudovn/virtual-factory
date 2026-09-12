# VF-vNEXT-G18 — Scenario-Assumed Topology Overlay — Evidence

Gate: `VF-vNEXT-G18` · Implementation gate (additive mechanism + tests).
Base: `ae1dbd3575df11f5aad68762cd5c7f47620f55d8` (G17A accepted head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/connectivity/scenario_overlay.py` — generic
  `VF_SCENARIO_ASSUMED_TOPOLOGY` overlay:
  - `AssumedTopologyEdge` — immutable edge with explicit `assumption_id` +
    `version`; frozen `source_kind = vf_scenario_assumption` and
    `status = assumed/synthetic`; `rationale`; `replaces_assumption_id`;
    enforced `reversible = True`.
  - `ScenarioTopologyOverlay` — immutable, deterministic, inert set of edges;
    fail-closed on duplicate id and duplicate exact logical assumption; no
    order/coupling-policy fields; `remove`/`replace` return new overlays.
  - `authorization()` frozen to `NOT_AUTHORIZED`.
- `src/virtual_factory/shwtp/overlay.py` — first bounded fixture:
  T108 (`shwtp/line1/l1_t108`) --ASSUMED_FLOWS_TO--> DIST-P108
  (`shwtp/dist_p108`), VF-local identity only, never PIM canonical ids.
- `tests/test_vnext_g18_scenario_overlay.py` — 29 tests.

## 2. Required semantics coverage

| Requirement | Proof |
|---|---|
| id/version explicit | edge + overlay carry `assumption_id`/`overlay_id` + `version` |
| source = VF scenario assumption | `source_kind == vf_scenario_assumption` (frozen, fail-closed otherwise) |
| provenance/status synthetic | `status == assumed/synthetic` (frozen, fail-closed otherwise) |
| reversible/replaceable | `remove`/`replace` immutable; original never mutated |
| no back-propagation into PIM | authoritative graph `serialize()` identical before/after overlay build |
| authoritative vs assumed distinguishable | distinct schema (`vf.vnext.g18...` vs `vf.vnext.g12a...`), distinct fields |
| fail closed on malformed/ambiguous | empty identity, duplicate id, duplicate logical assumption, wrong schema/source_kind/status all raise |
| deterministic serialization | input-order-independent `serialize()`; round-trip verified |
| no execution order implied | no `order`/`execution_order` field anywhere |
| coupling policy stays orchestration | no `coupling_policy` field; `SHWTP_FEDERATION_COUPLING_POLICY == explicit_lagged` unchanged |
| no runtime/site authorization broadening | `authorization() == {runtime: NOT_AUTHORIZED, site_execution: NOT_AUTHORIZED}` |

## 3. T108->DIST-P108 fixture is assumed-only

- `relation_type = ASSUMED_FLOWS_TO` (never `REL-SHW-F05` or a PIM relation id).
- Endpoints are VF-local (`shwtp/line1/l1_t108`, `shwtp/dist_p108`), never
  `PROC-*` / `UNIT-*` PIM canonical ids.
- `status = assumed/synthetic` — never DocumentConfirmed/SourceMapped/
  site-verified.

## 4. Preserved / unchanged

G4 composition, G14A projection (2 ports / 1 binding), G14B explicit_lagged,
G15 evaluator, G17A review artifact, reference connectivity graph (G12A/B),
T106/T108 runtimes, PIM pins. No new coupling policy. No
T110/Line2/chemical/electrical/automation runtime.

## 5. Test evidence

- `tests/test_vnext_g18_scenario_overlay.py` — 29 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G18.md`).
