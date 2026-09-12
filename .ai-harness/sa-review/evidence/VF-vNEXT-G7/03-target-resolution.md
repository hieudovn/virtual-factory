# VF-vNEXT-G7 · Evidence 03 — Hierarchical target resolution (Issue #52 B, 3-4, 14)

`src/virtual_factory/runcontrol/targets.py`

`resolve_target(workspace, target_path) -> TargetResolution` (read-only, G1
authority):
- canonical `StructuralPath` is the only lookup authority;
- workspace target → deterministic set of ALL executable scopes in the tree;
- container target → deterministic set of executable DESCENDANTS (the container
  itself is never returned as a participant);
- executable target → that scope only;
- unknown path / foreign workspace → `TargetResolutionError` (fail closed).

Result carries `target_kind` (`workspace|container|executable`) and
`effective_scope_paths` sorted by canonical path (deterministic). The lifecycle
service stores both full path strings and leaf ids, so the execution bridge
receives real executable sub-line ids only — a container-only scope never gains
executable/participant authority.

Proven by tests: `TestTargetResolution` (workspace→6, container→6 without the
container, executable→itself, unknown/foreign fail closed, deterministic order)
and `TestApiSurface.test_container_target_never_gets_executable_authority`.
