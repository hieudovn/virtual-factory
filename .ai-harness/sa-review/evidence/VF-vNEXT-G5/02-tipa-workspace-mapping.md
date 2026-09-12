# VF-vNEXT-G5 · Evidence 02 — TIPA structural workspace mapping (Issue #50 A)

`src/virtual_factory/federation/tipa_workspace.py`

Builds exactly (deterministic, G1-validated):

    Workspace "TIPA"
    └── Scope "ASSY"  (container-only)          path TIPA/ASSY
        ├── ASSY-SL01 … ASSY-SL03  executable   path TIPA/ASSY/ASSY-SLxx
        └── ASSY-SL04 … ASSY-SL06  executable   path TIPA/ASSY/ASSY-SLxx

- `PLANT_ID="TIPA"`, `PRODUCTION_LINE_ID="ASSY"`,
  `SUB_LINE_IDS = sorted(CANONICAL_TIPA_SUB_LINE_IDS)` (ASSY-SL01..06).
- `assy_scope_path()` → `StructuralPath(("TIPA","ASSY"))`;
  `sub_line_path(id)` → `StructuralPath(("TIPA","ASSY",id))` — fails closed for
  any non-canonical id (`FederationStructuralError`).
- `build_tipa_workspace()` uses `build_workspace("TIPA", [...])` with the ASSY
  scope `CONTAINER_ONLY` and the six children `EXECUTABLE_CAPABLE` under parent
  `TIPA/ASSY`. The G1 builder validates parentage/duplicates/completeness.
- ASSY is never flattened to top-level; no fake runtime is created for ASSY.

Proven by tests:
- `TestTipaWorkspace` — hierarchy resolves through `Workspace.resolve_scope`;
  ASSY container-only; six children executable; canonical path strings; unknown
  id fails closed; deterministic build; structural path ≠ flattened demo id.

No new generic identity model: G1 `StructuralPath` is the runtime structural
identity authority; the TIPA demo sub-line metadata remains deployment
metadata (see evidence 06 isolation/identity).
