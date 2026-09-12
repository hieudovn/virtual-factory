# VF-vNEXT-G5-C01 · Evidence 08 — Decouple production host from AssyDemoComposition

SA review of exact head `0d04b417cbeb18942fc0bb3d80361b8525d4e3fb`
(comment `5543747531`) found one architecture-boundary defect: the production
federation host constructed/owned `AssyDemoComposition` and thereby leaked
demo-only policy into the production migration seam. Fixed.

## C01 — Decouple production federation host from demo orchestration/policy

`TipaAssyFederation` previously:
- constructed `AssyDemoComposition(..., scenario=...)` and called
  `composition.initialize()` in `initialize()`;
- stored it (`self._composition`) and exposed it (`composition` property);
- accepted a `DemoScenario` constructor argument;
- reused the demo object's contexts/runtimes (inheriting demo-only scenario
  targeting, hard-coded seeded upstream inventory, continuous-feed state, and
  demo step semantics).

Correction applied in `src/virtual_factory/federation/assy_host.py`:
- `TipaAssyFederation` no longer instantiates, stores or exposes
  `AssyDemoComposition` (no `_composition` field, no `composition` property).
- Its constructor takes ONLY `config_path` (no `DemoScenario`).
- `initialize()` builds the six isolated runtimes DIRECTLY from the accepted
  ASSY config/identity sources (`load_assy_config_from_yaml`,
  `load_assy_demo_identity_from_yaml`) reproducing the proven isolation
  mechanics only: per-sub-line deep-copied config + stable ordinal
  random-seed isolation (`base_seed + ordinal`), then one `AssyLineRuntime`
  per sub-line bound to its executable G1 scope.
- No `DemoScenario` / `ContinuousFeedPolicy` / selected-sub-line / demo-step /
  scenario-target / hard-coded replenishment is imported or promoted as
  federation truth (verified: the module namespace contains none of those
  names).
- Upstream seeding is NOT implicit production policy: runtimes are created at
  time 0 with no WIP. Tests that need seeded upstream state apply EXPLICIT
  equivalent preparation via the clearly-named test/demo preparation helper
  `seed_like_demo` (test file) before any window.
- `AssyDemoComposition` in `assembly/demo_composition.py` is UNCHANGED (its
  regressions remain green); `AssyLineRuntime` is UNCHANGED.

## Required tests added/adjusted

1. `test_production_host_initializes_without_demo_composition` — host module
   imports none of `AssyDemoComposition`/`DemoScenario`/`ContinuousFeedPolicy`;
   host has no `_composition`/`composition`/`scenario`/feed/demo-step state; six
   runtimes are exact `AssyLineRuntime`.
2. `test_federation_api_exposes_no_demo_policy_authority` — constructor takes
   only `config_path`; no pre-seeded WIP / no demo policy on the production host.
3. per-sub-line config/RNG isolation still asserted (`TestIsolation`).
4. standalone-vs-federated parity proven under EXPLICIT equivalent initial
   conditions (host runtimes and replicas both prepared via `seed_like_demo`)
   — `test_real_config_six_subline_replica_parity` (six sub-lines) plus the
   fast-config RELEASE/AP04-JOIN parity tests (which seed their own runtimes).
5. all six participate at a supported shared natural boundary after explicit
   equivalent preparation — `test_all_six_reach_supported_shared_boundary_after_explicit_prep`.
6. `AssyDemoComposition` behavior unchanged — its tests remain green in the
   complete ASSY regression oracle (354) and full suite.
7. All prior regressions green (below).

## Regression (re-run)

New G5 tests 26 passed; G4 56; G1 32; G2 36; G3 328; ASSY oracle 354;
continuous 61; full suite **1875 passed** (0 failures). Compile PASS.

## Preserved (unchanged)

Exact TIPA → ASSY → ASSY-SL01..06 hierarchy; ASSY container-only; same
`AssyLineRuntime` truth; natural-boundary-only adapter semantics (no fractional
dwell/time rewrite); no new synchronization policy; no G6+; no PIM identity
fabrication.
