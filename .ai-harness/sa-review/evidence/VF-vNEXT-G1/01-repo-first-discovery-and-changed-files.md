# VF-vNEXT-G1 · Evidence 01 — Repo-first discovery + changed-file inventory

## 1. Baseline (exact SHAs)

| Item | SHA |
|---|---|
| Production base (`origin/main`, inspected before branching) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Branch | `feature/vf-vnext-g1` (from accepted ARCH-06 head `41300d34d952143e195bc446cfaeeea4c25465d1`) |
| G1 head | `feature/vf-vnext-g1` pushed head (recorded in PM final response / `git rev-parse HEAD`) |

Note: origin/main is the canonical production pin used by the harness for every
prior gate. The architecture branches (ARCH-01..06) were never merged into
production; their only production-code effect is zero (all gates were
documentation-only). G1 branches from the accepted ARCH-06 head so the existing
ASSY regression oracle and continuous/compressor baseline suites (which live on
that lineage) are present for mandatory regression.

## 2. Repo-first discovery summary

Inspected before implementation:

| Seam | Finding | Classify |
|---|---|---|
| `src/virtual_factory/core/schema.py` | Pydantic v2 `PlantConfig` (flat plant config, `extra="allow"`); **no Workspace/Scope layer** | reuse (config conventions) |
| `src/virtual_factory/core/config_loader.py` | `load_yaml` + `load_plant_config` pattern | reuse (loader pattern) |
| `src/virtual_factory/core/validators.py` | validation helpers | reference |
| `src/virtual_factory/assembly/sub_line_identity.py` | canonical TIPA→ASSY→ASSY-SL01..06 identity (frozen dataclasses, exactly-6 validation, hydraulic/thermal) | **adapt/reference** (lossless source for fixture proof) |
| `src/virtual_factory/assembly/demo_composition.py` | `AssyDemoComposition` six-context precedent | legacy/reference (composition precedent only) |
| `src/virtual_factory/integration/control_boundary.py` | `scope_refs: tuple[str, ...] = ()` field | reference only (existing scope-ref concept; not touched) |
| PH00 evidence | `configs/workspaces/` is the frozen workspace root (B9); SH WTP target `configs/workspaces/shw-wtp/` | **new generic foundation** |
| PH00 B1–B3 | three distinct identities (workspace_id / canonical_signal_id / outputs.namespace) | must preserve separation |
| tests | many ASSY + continuous tests (see evidence 05) | regression oracle |
| Any existing `Workspace`/`Scope` class | **confirmed absent** in `src/` | new generic foundation |

## 3. Changed-file inventory (why each is in scope)

### New production foundation — `src/virtual_factory/workspace/`

| File | Purpose |
|---|---|
| `identity.py` | Immutable `StructuralPath` (`workspace/scope/.../scope`) + `SimulationObjectRef`; deterministic, path-safe ids; never equals PIM canonical id |
| `model.py` | `ScopeMode` (container_only / executable_capable), `Archetype` (informational), `SimulationObject`, `SimulationScope`, `Workspace` (immutable validated tree); `require_executable()` guard |
| `builder.py` | `ScopeSpec`/`ObjectSpec` + `build_workspace()`: fail-closed validation (missing parent, duplicate ids, containment cycle, mode guard), deterministic ordering |
| `config.py` | Pydantic `WorkspaceConfig`/`ScopeConfig`/`ObjectConfig` generic manifest schema (recursive), `to_workspace()` |
| `loader.py` | `load_workspace_manifest()` YAML loading seam for `configs/workspaces/` |
| `__init__.py` | public API |

### New config fixtures — `configs/workspaces/`

| File | Purpose |
|---|---|
| `tipa_assy_demo.yaml` | representative structural fixture: TIPA Workspace → ASSY container-only Scope → ASSY-SL01..06 executable-capable Scopes → representative object refs |
| `generic_continuous_demo.yaml` | illustrative continuous fixture: nested container-only areas + executable-capable units + generic equipment/instrument refs; NO SH-WTP site truth |

### New tests — `tests/`

| File | Purpose |
|---|---|
| `test_workspace_foundation.py` | structural model / identity / path / determinism / resolution units |
| `test_workspace_validation.py` | fail-closed negative tests |
| `test_workspace_config.py` | config seam + representative fixtures + lossless proofs |

### Harness — `.ai-harness/` (task JSON, evidence, report, CURRENT.md)

Documentation/evidence only.

## 4. Classification of seams touched

| Bucket | Items |
|---|---|
| reuse | core config/schema conventions (Pydantic v2, extra=allow), loader pattern |
| adapt/wrap | none added into existing runtime (no adapter into `AssyLineRuntime`) |
| new generic foundation | `src/virtual_factory/workspace/`, `configs/workspaces/` |
| legacy/reference | `assembly/sub_line_identity.py` (source for lossless proof only), `demo_composition.py` (untouched), `simulators/wtp`, `simulators/vf2` (untouched) |
| explicitly deferred | G2+ (runtime context/provenance, coordinator/ports, semantic binding, ASSY federation, UI, SH WTP runtime) |

No production code outside `src/virtual_factory/workspace/` was modified. No
`AssyLineRuntime` change. No existing test was edited (only new test files
added).
