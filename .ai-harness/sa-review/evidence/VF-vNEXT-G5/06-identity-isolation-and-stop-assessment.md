# VF-vNEXT-G5 · Evidence 06 — Identity / isolation + STOP assessment (Issue #50 E + self-audit)

## Identity rules (proven)
- `TIPA/ASSY/ASSY-SL01..06` resolve through G1 `Workspace.resolve_scope`
  (`TestTipaWorkspace`).
- Sub-line runtime/adapter identity matches its registered structural scope:
  adapter `scope_path.as_string() == path.as_string() == "TIPA/ASSY/ASSY-SLxx"`
  and coordinator `participants` order equals the canonical sorted scope order
  (`TestFederationHost`).
- Structural identity stays distinct from PIM canonical semantic identity: the
  G1 path is never a PIM canonical id; the demo `ASSY-SLxx` metadata is only a
  path segment label (`test_structural_identity_is_distinct_from_pim_identity`);
  no PIM canonical ID is fabricated.

## Isolation rules (proven)
- Six runtimes and six (nested) configs are distinct objects; per-sub-line
  ordinal RNG seeds are distinct (`TestIsolation`).
- WIP/feed state is per-runtime: producing an RSO2 WIP in SL01 changes only
  SL01's buffer.
- No context can mutate another context directly: advancing SL01 through a
  coordinator window leaves SL02..06 canonical state byte-identical and their
  simulation time at 0.0 (`test_no_cross_scope_mutation_when_single_subline_advanced`).

## Identity drift/mismatch fails closed through EXISTING G4 rules (proven)
- Registration of an adapter bound to the container-only ASSY scope is rejected
  by the G4 `Coordinator` (`TestAssyContainerOnly`).
- A participant that is coherent before advance and drifts its `scope_path`
  DURING `advance_to()` (to another scope or to a non-StructuralPath) fails the
  window via the existing G4 C03 post-advance identity re-validation; no commit
  occurs (`TestIdentityFailClosed`).

## Natural ASSY time boundary vs G4 coordination boundary (self-audit)
The G4 coordinator requires exact boundary landing. The adapter only ever
advances via natural ASSY dwell/index steps and only reports success on an exact
landing; it refuses (fail closed, via `ParticipantError`) any target a natural
step would overshoot. No fractional dwell/index, no hidden time rewrite, no
global timestep was introduced. Tested by
`test_unreachable_fractional_boundary_fails_closed` and by every completed
parity window being a natural multiple-of-dwell boundary.

## No demo-policy-to-plant-truth leakage (self-audit)
- The host reuses the demo construction/isolation pattern ONLY to obtain six
  isolated runtimes; the G5 adapter advancement contains no continuous-feed /
  scenario-target logic (no feed replenish, no scenario selection inside the
  adapter). Scenario quality configs remain per-context demo configuration and
  are never asserted as plant truth.
- The federation seam exposes G1 structural identity as authority and does not
  promote `sub_line_identity` demo metadata to a generic platform model.

## STOP-condition assessment (Issue #50 STOP FOR SA)
| STOP condition | Status |
|---|---|
| Adapter requires modifying/retyping AssyLineRuntime domain behavior | NOT triggered (assembly/ untouched; runtime used as-is) |
| Arbitrary coordinator target requires fractional dwell/index or hidden time rewrite | NOT triggered (unsupported targets fail closed) |
| Six sub-lines cannot participate safely without a new synchronization policy | NOT triggered (shared natural 120s boundary reached by all six, no policy invented) |
| Safe solution requires treating ASSY container as executable | NOT triggered (container stays container-only) |
| Existing G1–G4 contracts must be broken | NOT triggered |
| Demo-specific identity/policy must become generic platform truth | NOT triggered |
| Scope expands into G6/G7/G8+/G9/G10 | NOT triggered (no such code added) |

No G6+ implementation appears; no `AssyLineRuntime` rewrite.
