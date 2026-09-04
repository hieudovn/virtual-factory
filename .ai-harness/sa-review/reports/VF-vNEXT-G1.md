# VF-vNEXT-G1 — Implement Workspace / Simulation Scope Foundation

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G1` (GitHub Issue #46) |
| Program | Implementation phase following completed architecture umbrella #39 (`VF-vNEXT-ARCH`) |
| Gate mode | Accelerated implementation gate (only authorized implementation gate) |
| Architecture baseline | ARCH-01 `41903e18…` + ARCH-02 `40454487…` + ARCH-03 `392401bd…` + ARCH-04 `d5c155b6…` + ARCH-05 `8fafa119…` + ARCH-06 `41300d34…` |
| Production base SHA (`origin/main`, inspected before branching) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Branch | `feature/vf-vnext-g1` (from accepted ARCH-06 head `41300d34…`) |
| G1 head | `feature/vf-vnext-g1` pushed head (recorded in PM final response; `git rev-parse HEAD`) |
| G2+ started | **NO** |

## 1. Objective

Implement the minimal reusable structural foundation for
`Platform → Workspace → hierarchical Simulation Scope → Simulation Object`:
deterministic structural identity/path, container-only vs executable-capable
scope mode, fail-closed hierarchy/reference validation, a generic workspace
config/loading seam (`configs/workspaces/`, PH00 B9), and representative
fixtures proving lossless `TIPA → ASSY → ASSY-SL01..06` and a generic
continuous hierarchy without inventing SH-WTP site truth.

## 2. Implementation (production)

New dependency-light package `src/virtual_factory/workspace/`:

- `identity.py` — immutable `StructuralPath` (`workspace/scope/.../scope`) and
  `SimulationObjectRef`; deterministic, path-safe; distinct from PIM canonical id.
- `model.py` — `ScopeMode` (container_only / executable_capable), `Archetype`
  (informational), `SimulationObject`, `SimulationScope`, `Workspace`; immutable
  validated tree; `require_executable()` guard.
- `builder.py` — `ScopeSpec`/`ObjectSpec` + `build_workspace()`; fail-closed
  validation (missing parent, duplicate ids, containment cycle, mode guard);
  deterministic ordering.
- `config.py` + `loader.py` — generic Pydantic manifest schema + YAML loading
  seam (`load_workspace_manifest`).
- `__init__.py` — public API.

New config fixtures: `configs/workspaces/tipa_assy_demo.yaml`,
`configs/workspaces/generic_continuous_demo.yaml`.

No existing production module was modified; `AssyLineRuntime` untouched.

## 3. Design invariants (evidence 02)

Nested containment tree; deterministic structural paths; global-unique scope ids
within a Workspace (stronger invariant over per-parent, matching canonical ASSY
evidence); container-only never treated as executable; archetype is metadata not
engine authority (ARCH-06 C01); structural identity never equals PIM canonical
identity; no workspace-name hard-coding; no God registry/singleton.

## 4. Validation (evidence 04)

Fail-closed: missing/invalid parent, duplicate child identity, containment
cycle, object on nonexistent Scope, object not found, executable assumption on
container-only, invalid path/reference, duplicate object ids, determinism vs
input order.

## 5. Lossless proofs (evidence 03)

- TIPA/ASSY: `TIPA(Workspace) → ASSY(container_only) → ASSY-SL01..06
  (executable_capable)` matches the canonical `AssyProductionLineIdentity`
  exactly (ids + hydraulic/thermal variants); no runtime/domain rewrite.
- Generic continuous: nested container-only areas + executable-capable units +
  generic object refs; no SH-WTP site truth, no evidence-maturity fields.

## 6. Test / regression results (evidence 05)

| Suite | Result |
|---|---|
| New G1 unit/negative/config tests | **28 passed** |
| ASSY regression oracle (incl. ARCH-05 C01 automated obligations) | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1675 passed** (0 failures; no baseline exceptions) |
| Compile check | PASS (no configured ruff/mypy/black in repo) |

## 7. Non-decisions / deferred (evidence 06)

G2 Runtime Context + Provenance v2, G3 Observation/Event/Alarm alignment, G4
Coordinator/Ports, G5 ASSY federation, G6 UI primitives, G7 Scenario/Run
Control, G8 Regression baseline gate, G9 Semantic Binding, G10 SH WTP runtime —
all NOT implemented. No semantic binding, no coordinator, no provenance-v2, no
UI change, no `AssyLineRuntime` rewrite, no legacy WTP mini-engine change.

## 8. STOP-condition assessment (evidence 06 §2)

None triggered: no ARCH-01..06 decision changed; generic model represents both
fixtures without hard-coding; no runtime needed to function; PIM identity
separate; ASSY untouched (354 passed); config seam additive; no SH-WTP site
truth; scope did not expand into G2+.

## 9. Acceptance

| Criterion | Result |
|---|---|
| Generic Workspace/Scope/Object foundation in production code | PASS (`src/virtual_factory/workspace/`) |
| Nested containment + deterministic structural paths | PASS |
| Container-only vs executable-capable without fake runtime | PASS |
| Fail-closed validation | PASS |
| Generic config/loading seam | PASS |
| TIPA/ASSY lossless without runtime/domain rewrite | PASS |
| Generic continuous without site invention | PASS |
| No workspace-name hard-coding | PASS |
| PIM semantic identity separate | PASS |
| No G2+ implementation | PASS |
| Mandatory tests/regressions pass | PASS (28 + 354 + 61 + full 1675) |
| Working tree clean and head pushed | PASS (after push) |

## 10. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G1/` — 6 files (01…06).

## 11. Final status

```text
VF-vNEXT-G1 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G2 is NOT started.
