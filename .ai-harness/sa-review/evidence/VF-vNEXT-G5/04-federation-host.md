# VF-vNEXT-G5 · Evidence 04 — Federated ASSY host / composition (Issue #50 C)

`src/virtual_factory/federation/assy_host.py` — `TipaAssyFederation`

The smallest production federation host that:
- creates/owns the TIPA `Workspace` structure (G5-A) via `build_tipa_workspace()`;
- creates six isolated `AssyLineRuntime` contexts reusing the EXISTING
  `AssyDemoComposition` construction/config-isolation pattern (deep-copied
  config per sub-line + ordinal random seed + scenario quality normalize) — no
  second simulation engine;
- binds each context to its matching executable G1 scope: it resolves
  `TIPA/ASSY/ASSY-SLxx` through `Workspace.resolve_scope` and requires
  `is_executable_capable` (fails closed otherwise);
- exposes one `AssySubLineAdapter` per context so supported ASSY participants
  can be registered with a G4 `Coordinator` (`make_coordinator()` returns a
  Coordinator over the TIPA Workspace with an EMPTY composition graph — no
  cross-scope boundary exchange in G5);
- never makes the ASSY container itself executable (no adapter is created for
  the container; registration of a container-bound adapter is rejected by the
  existing G4 rule — evidence 03);
- never replaces domain truth with coordinator state: the wrapped runtime stays
  the single source of ASSY truth.

Coordination boundaries are NOT a new synchronization policy: `run_window`
registers the selected sub-lines and runs one coordinator window; it succeeds
only when every selected sub-line reaches the target through its natural ASSY
advancement (exact landing), otherwise the window fails closed. Advancing one
sub-line leaves all other contexts untouched (no forced alignment).

Proven by tests:
- `TestFederationHost` — six isolated runtimes wrapped without rewrite; six
  distinct configs/runtimes; deterministic registration order; adapter identity
  == registered structural scope;
- `TestAdapterTimeAndBoundary.test_all_six_reach_supported_shared_boundary` —
  all six land on the natural 120s dwell boundary (completed window);
- `TestIsolation.test_no_cross_scope_mutation_when_single_subline_advanced`.
