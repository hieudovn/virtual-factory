# VF-vNEXT-G1 · Evidence 02 — Structural model / API + containment & identity invariants

## 1. Public API (`src/virtual_factory/workspace/`)

```python
# identity
StructuralPath(segments: tuple[str, ...])          # workspace/scope/.../scope
StructuralPath.from_string("TIPA/ASSY/ASSY-SL01")
SimulationObjectRef(owning_scope_path, object_id)  # canonical: scope/object

# model
ScopeMode.CONTAINER_ONLY | ScopeMode.EXECUTABLE_CAPABLE
Archetype.CONTINUOUS | BATCH | DISCRETE | COMPOSED   # informational metadata
SimulationObject(object_id, object_type=None, display_name=None)
SimulationScope(scope_id, path, mode, archetype=None, display_name=None,
                children=(), objects=())
Workspace(workspace_id, path, display_name=None, description=None,
          top_level_scopes=())

# builder
ScopeSpec(scope_id, mode, parent_scope_id=None, archetype=None,
          display_name=None, objects=())
ObjectSpec(object_id, object_type=None, display_name=None)
build_workspace(workspace_id, scope_specs, *, display_name=None,
                description=None) -> Workspace

# config + loader
WorkspaceConfig / ScopeConfig / ObjectConfig / WorkspaceManifestFile
load_workspace_config(path) -> WorkspaceConfig
load_workspace_manifest(path) -> Workspace
```

Key model methods:
- `SimulationScope.require_executable()` — fail-closed guard; raises if the
  scope is container-only (no fake runtime).
- `Workspace.find_scope(scope_id)`, `find_scope_by_path(path)`,
  `resolve_scope(path)` (fail-closed), `resolve_object(ref)` (fail-closed).

## 2. Frozen semantics honored (ARCH-01 / ARCH-06 C01)

- Workspace = top-level grouping of Scopes (a Workspace has no Objects directly).
- Scope = recursive structural subsystem; exactly one structural parent (tree).
- Object = leaf structural reference inside exactly one owning Scope.
- Executability is a capability (`ScopeMode`), never implied by archetype/type/
  name; a container-only scope owns no fake runtime.
- Archetype is informational classification metadata — NOT engine-selection
  authority and NOT a universal engine-cardinality rule (ARCH-06 C01).
- G1 does NOT implement the execution boundary behind an executable-capable
  scope (deferred to later gates).
- Connectivity/dependency (graph) is NOT implemented as containment.

## 3. Containment / identity invariants (implemented)

| # | Invariant | Enforcement |
|---|---|---|
| I1 | Workspace id non-empty and path-safe | `StructuralPath.__post_init__` / builder |
| I2 | Scope id path-safe, no `/` | `StructuralPath` segment validation |
| I3 | **Scope id unique WITHIN its structural parent namespace** (not global across the Workspace); the full `StructuralPath` is the authoritative unambiguous identity | builder `_compute_paths` (same parent path + same id → same path → rejected) |
| I4 | Parent reference is path-qualified (`StructuralPath`) and exists (missing/invalid parent fails); resolution never depends on a globally-unique bare id | builder `_validate_parents` |
| I5 | No containment self-nesting (a parent path already containing the child's id); with path-qualified parents the parent depth strictly decreases, so multi-node cycles are unrepresentable | builder `_detect_self_nesting` |
| I6 | Object id unique within its owning Scope | builder `_compute_paths` |
| I7 | Object belongs to a declared Scope; resolution fail-closed | `Workspace.resolve_object` |
| I8 | Container-only scope never treated as executable | `SimulationScope.require_executable` |
| I9 | Deterministic tree independent of input iteration order | builder sorts children/objects by id/path |
| I10 | Structural identity never equals/replaces PIM canonical id | identity module carries no canonical fields; B2 separation documented |
| I11 | No workspace-name hard-coding in platform behavior | builder/loader fully generic (workspace id is data) |
| I12 | Bare-id convenience lookup must NOT silently return the first match when duplicate local ids exist | `find_scope`/`find_object`/`scope_path_by_id` raise `StructuralValidationError` on ambiguity; path-based lookup is canonical |

## 4. Identity / path determinism

`StructuralPath` is the canonical identity of a scope:
`"TIPA/ASSY/ASSY-SL01"`. Parent/child is derivable: `path.parent`,
`path.child(scope_id)`. `SimulationObjectRef` canonical form:
`"TIPA/ASSY/ASSY-SL01/AP04"`. Both round-trip through `from_string/as_string`.
Object resolution requires an existing owning scope (fail-closed).

## 5. Design discipline (G: small + dependency-light)

- No God registry, no global mutable singleton (one Workspace per build; loader
  returns a single validated tree).
- No domain-name conditionals (no `if workspace == "TIPA"` anywhere).
- No bidirectional ownership (parent → child only; parent derived from path).
- Structural model does not import UI, PIM client, historian, MQTT/OPC UA, or
  any domain runtime internals. The only cross-module imports are within
  `workspace/` itself.
- Model is immutable/value-style (frozen dataclasses), carries no domain state.
