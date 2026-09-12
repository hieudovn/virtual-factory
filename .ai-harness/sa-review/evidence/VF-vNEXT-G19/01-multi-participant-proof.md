# VF-vNEXT-G19 — Generic Multi-Participant Federation Proof (>2) — Evidence

Gate: `VF-vNEXT-G19` · Implementation gate (additive harness + tests).
Base: `44d026f4d081296c31d418806ac5e96575a2d8e4` (G18-C01 head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/federation/generic.py` — reusable synthetic harness:
  - `SyntheticParticipant` — mechanism-neutral G4 `ExecutableParticipant`; emits
    one detached transfer per window from its COMMITTED state (one window behind
    by construction); consumes inbound commits to update the NEXT window.
  - `SyntheticFederation` — workspace + graph + coordinator + participants; runs
    a window by preparing every participant then calling the G4 `Coordinator`.
  - `build_synthetic_federation(...)` — builds a linear chain of 3+ executable
    scopes with `N-1` bindings; optional `source_values` (per-window source
    sequence) and `registration_order` (permutation for ordering proof).
- `tests/test_vnext_g19_multi_participant.py` — 19 tests.

## 2. Required invariants coverage

| Invariant | Proof |
|---|---|
| reuse G4 semantics | imports `Coordinator`/`BoundaryTransfer`/`CompositionGraph`/`PortRef` etc.; no G4 file changed |
| CompositionGraph != execution order | graph has no `execution_order`/`coupling_policy`; coordinator sorts by scope path |
| coupling policy stays orchestration | `GENERIC_FEDERATION_COUPLING_POLICY = explicit_lagged` lives only in the harness, never on graph/ports/bindings/transfers |
| deterministic ordering | registration-order permutation produces identical outcomes/committed values |
| detached immutable transfers | original payload dict mutated after construction does not affect transfer; payload is frozen |
| fail closed on identity/workspace mismatch | cross-workspace binding, transfer workspace mismatch, dangling scope registration, container-only scope registration all raise |
| failed window not completed | advance failure / undeclared transfer / commit failure all yield `status="failed"` |
| 3+ participants, >=2 bindings | 3 and 4 participant chains; 2 and 3 committed transfers per window |
| identical inputs => identical results | two identical federations produce identical outcomes and per-participant committed values |
| no same-window feed-through | time-varying source: p2 receives p1's window-W output == p0's window-(W-1) output, never window-W |

## 3. Preserved / unchanged

G4 composition/coordinator; G14A projection; G14B explicit_lagged; G15
evaluator; G18 overlay; reference connectivity graph; T106/T108 runtimes; PIM
pins. No new coupling policy. No SH-WTP authority broadening (module imports no
shwtp). No UI.

## 4. Test evidence

- `tests/test_vnext_g19_multi_participant.py` — 19 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G19.md`).
