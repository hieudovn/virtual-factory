# VF-vNEXT-G14B — SH-WTP T106→T108 Explicit Lagged Federation — Evidence

Gate: `VF-vNEXT-G14B` · Bounded two-scope synthetic/reference federation evaluation.

## 1. Coupling policy (frozen)

`coupling_policy = "explicit_lagged"` — Jacobi-style one-window-lag.

- Exposed/enforced ONLY in the SH-WTP federation layer (`shwtp/federation.py`).
- NOT a property/semantic of `CompositionGraph`, `BoundaryPort`,
  `CompositionBinding`, T106, or T108 (verified: no `coupling_policy`/`policy`
  attribute on the graph; no such dataclass field on port/binding).
- Unsupported policy values fail closed at `ShwtpFederationConfig` construction.

## 2. Frozen architecture separation

`CompositionGraph != execution order` and `coupling policy = orchestration policy`.
The existing G4 `Coordinator` / `ExecutableParticipant` / `BoundaryTransfer`
semantics are reused unchanged. No G4 file was modified.

## 3. Participants

| Scope | Runtime | Adapter | Role |
| --- | --- | --- | --- |
| `shwtp/line1/l1_t106` | T106 (G13B, LogicalOnly) | `ShwtpT106Participant` | source (stages F01 transfer) |
| `shwtp/line1/l1_t108` | T108 (G13, FirstOrder) | `ShwtpT108Participant` | sink (commits F01 inflow, lagged) |

Exactly one F01 binding: `BIND-SHW-F01-T106-OUT-T108-IN`.

## 4. Lag semantics (proven)

- Before window 1: T108 committed inflow = explicit `initial_t108_inflow_m3_s`.
- Window 1: T108 advances with the initial inflow (NOT Q106[1]); T106 produces
  Q106[1]; after both advance, Q106[1] is committed to T108.
- Window 2: T108 advances with exactly Q106[1]; T106 produces Q106[2]; after
  boundary 2, Q106[2] becomes window-3 input.
- No same-window feed-through; no same-window retroactive T108 step
  (`step_index` advances exactly once per window; window-1 step record is
  immutable with the initial inflow).

## 5. Communication window

`communication_step_s > 0`; `T106Config.dt_s == T108Config.dt_s ==
communication_step_s` (G14B baseline constraint only — documented in
`federation.py`; not a universal VF rule). No multirate/interpolation/substepping.

## 6. Transfer contract

- Transfer id `XFER-SHW-F01-{window_id}`; source `shwtp/line1/l1_t106#out_flow`;
  target `shwtp/line1/l1_t108#in_flow`; binding id `BIND-SHW-F01-T106-OUT-T108-IN`;
  window/time/workspace/run identities exact; payload deep-frozen
  (`MappingProxyType`) with exactly one key `volumetric_flow_m3_s` (finite, >= 0).

## 7. Fail-closed behavior

Unsupported coupling policy; non-positive/non-finite `communication_step_s`;
missing/negative/non-finite initial T108 inflow or scenario flows; wrong
participant scope; mismatched run/workspace; wrong F01 source/target/binding;
wrong/stale/future/duplicate/invalid window id; wrong payload key/type; multiple
inbound transfers to T108; inbound transfer to T106; backward or non-exact
boundary; workspace/container target.

## 8. Provenance / authority (unchanged)

- T106: `simulation / synthetic / logical_only`.
- T108: `simulation / synthetic / first_order`.
- `vf_runtime_authorization = NOT_AUTHORIZED`;
  `site_authorized_execution = NOT_AUTHORIZED`.

## 9. Test evidence

- `tests/test_vnext_g14b_federation.py` — 55 tests PASS.
- G14A (20), G13B (19), G13 (28) remain green; full suite green.
- Complete canonical vNext baseline PASS (see report `VF-vNEXT-G14B.md`).

## 10. Unchanged

T106/T108 domain equations + canonical ids + provenance; G14A projection; G4;
G1/G2/G7/G9; G10–G14A; PIM; ASSY/continuous/UI. No G15.
