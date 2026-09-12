# VF-vNEXT-G1 · Evidence 03 — Config seam + representative fixtures (lossless proofs)

## 1. Config seam (PH00 B9)

- Location: `configs/workspaces/` (frozen workspace root; introduced by G1 as it
  did not exist).
- Schema: `WorkspaceConfig` (id/name/description + recursive `ScopeConfig`
  children + `ObjectConfig` objects). Generic — no SH-WTP/TIPA name-specific
  platform behavior.
- `load_workspace_config(path)` parses + validates structure only.
- `load_workspace_manifest(path)` builds the validated immutable `Workspace`.
- NO semantic binding, NO runtime engine creation, NO coordinator/ports, NO
  provenance-v2 in the seam.

## 2. TIPA/ASSY structural fixture (lossless proof)

`configs/workspaces/tipa_assy_demo.yaml`:

```
TIPA (Workspace)
 └─ ASSY (Scope, container_only, archetype discrete)
     ├─ ASSY-SL01 .. ASSY-SL03 (Scope, executable_capable, hydraulic)
     ├─ ASSY-SL04 .. ASSY-SL06 (Scope, executable_capable, thermal)
     └─ each sub-line carries representative object refs: SSO2 (producer),
        AP04 / AP06 / AP11 (station)
```

Proven lossless (tests `test_workspace_config.py`):

- `ws.workspace_id == "TIPA"`, `ASSY.mode == container_only`, exactly six child
  scope ids equal the canonical `ASSY-SL01..06`, each `executable_capable`.
- Cross-checked against the canonical `AssyProductionLineIdentity` loaded from
  `configs/plants/tipa_assy_demo.yaml` (`load_assy_demo_identity_from_yaml`):
  plant_id == workspace_id == TIPA; production_line_id == ASSY scope id; the six
  structural scope ids == canonical six; hydraulic == SL01..03 and thermal ==
  SL04..06.
- **No `AssyLineRuntime` change and no runtime/domain rewrite**: the fixture and
  tests only reference the canonical identity module read-only. Existing ASSY
  runtime is untouched (regression evidence 05).

## 3. Generic continuous fixture (no site invention)

`configs/workspaces/generic_continuous_demo.yaml`:

```
generic-continuous (Workspace)
 ├─ AREA-1 (container_only) ── UNIT-101 (executable_capable, continuous)
 │                              objects: TK-101 tank, P-101 pump, V-101 valve,
 │                                       FT-101 flow_transmitter, LT-101
 │                        UNIT-102 (executable_capable, continuous)
 ├─ AREA-2 (container_only) ── UNIT-201 (executable_capable, continuous)
 └─ UTIL-1 (container_only, no children)
```

Proven (tests `test_workspace_config.py`):

- Nested process-area hierarchy with at least one container-only and one
  executable-capable Scope per level.
- Container-only scope with no children (UTIL-1) is valid (no fake runtime).
- Objects are generic equipment/instrument refs.
- **No SH-WTP site truth**: ids are generic; parsed config carries no
  SiteVerified/SourceMapped/evidence fields and no water-treatment vocabulary
  (coagul/chlorin/filtrat/shw/song-hong). Fidelity is not claimed.

## 4. Genericity proof (no workspace-name hard-coding)

- `build_workspace("some-custom-workspace", ...)` and an arbitrary temporary
  manifest (`another-ws` with `TOP/CHILD-1` + `OBJ-1`) build successfully
  (`test_config_is_generic_not_name_hard_coded`). The seam and builder are fully
  generic; workspace/scope ids are data.

## 5. PIM semantic identity stays separate

The structural identity module defines ONLY VF structural ids/paths. It never
declares `canonical_signal_id`, never renames a local key to a canonical id, and
never imports the PIM client. (PH00 B1/B2 preserved.)
