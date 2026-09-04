"""VF-vNEXT-G1 — Workspace manifest config seam + representative fixtures.

Proves:

- the generic config/loading seam (configs/workspaces/ per PH00 B9);
- lossless TIPA -> ASSY -> ASSY-SL01..06 structural expression WITHOUT any
  AssyLineRuntime rewrite or change;
- a generic continuous hierarchy WITHOUT any SH-WTP site truth invention;
- config is generic (no TIPA/SH-WTP name hard-coding in platform behavior).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from virtual_factory.workspace import (
    ScopeMode,
    WorkspaceConfig,
    load_workspace_config,
    load_workspace_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACES_DIR = REPO_ROOT / "configs" / "workspaces"
TIPA_ASSY_MANIFEST = WORKSPACES_DIR / "tipa_assy_demo.yaml"
GENERIC_CONTINUOUS_MANIFEST = WORKSPACES_DIR / "generic_continuous_demo.yaml"

CANONICAL_SIX = [
    "ASSY-SL01",
    "ASSY-SL02",
    "ASSY-SL03",
    "ASSY-SL04",
    "ASSY-SL05",
    "ASSY-SL06",
]


def test_workspaces_dir_exists_and_has_fixtures() -> None:
    assert WORKSPACES_DIR.is_dir()
    assert TIPA_ASSY_MANIFEST.exists()
    assert GENERIC_CONTINUOUS_MANIFEST.exists()


def test_tipa_assy_manifest_lossless_hierarchy() -> None:
    ws = load_workspace_manifest(TIPA_ASSY_MANIFEST)
    assert ws.workspace_id == "TIPA"
    assert ws.path.as_string() == "TIPA"

    assy = ws.find_scope("ASSY")
    assert assy is not None
    assert assy.mode is ScopeMode.CONTAINER_ONLY
    assert assy.is_container_only
    assert assy.path.as_string() == "TIPA/ASSY"

    # Exactly six child scopes, lossless ids.
    child_ids = [c.scope_id for c in assy.children]
    assert child_ids == CANONICAL_SIX

    # Every sub-line is executable-capable (no fake runtime, but MAY own one).
    for sl_id in CANONICAL_SIX:
        sl = ws.find_scope(sl_id)
        assert sl is not None
        assert sl.mode is ScopeMode.EXECUTABLE_CAPABLE
        assert sl.path.as_string() == f"TIPA/ASSY/{sl_id}"

    # Representative object refs are present under sub-line scopes.
    sl1 = ws.find_scope("ASSY-SL01")
    assert sl1 is not None
    obj_ids = {o.object_id for o in sl1.objects}
    assert {"SSO2", "AP04", "AP06", "AP11"} <= obj_ids


def test_tipa_assy_lossless_against_canonical_identity() -> None:
    """Prove the structural tree matches the canonical ASSY identity exactly."""
    from virtual_factory.assembly.sub_line_identity import (
        load_assy_demo_identity_from_yaml,
    )

    plant_config = REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml"
    canonical = load_assy_demo_identity_from_yaml(str(plant_config))
    canonical_ids = [sl.sub_line_id for sl in canonical.sub_lines]

    ws = load_workspace_manifest(TIPA_ASSY_MANIFEST)
    assert ws.workspace_id == canonical.plant_id == "TIPA"

    assy = ws.find_scope("ASSY")
    assert assy is not None
    assert assy.scope_id == canonical.production_line_id == "ASSY"

    structural_ids = [c.scope_id for c in assy.children]
    assert structural_ids == canonical_ids
    assert structural_ids == CANONICAL_SIX

    # Variant mapping preserved: hydraulic == SL01..03, thermal == SL04..06.
    hydraulic = {sl.sub_line_id for sl in canonical.hydraulic_sub_lines}
    thermal = {sl.sub_line_id for sl in canonical.thermal_sub_lines}
    assert hydraulic == {"ASSY-SL01", "ASSY-SL02", "ASSY-SL03"}
    assert thermal == {"ASSY-SL04", "ASSY-SL05", "ASSY-SL06"}


def test_generic_continuous_manifest_no_site_invention() -> None:
    ws = load_workspace_manifest(GENERIC_CONTINUOUS_MANIFEST)
    assert ws.workspace_id == "generic-continuous"

    # Container-only process areas with nested executable-capable units.
    area1 = ws.find_scope("AREA-1")
    assert area1 is not None
    assert area1.mode is ScopeMode.CONTAINER_ONLY
    unit101 = ws.find_scope("UNIT-101")
    assert unit101 is not None
    assert unit101.mode is ScopeMode.EXECUTABLE_CAPABLE
    assert unit101.path.as_string() == "generic-continuous/AREA-1/UNIT-101"

    # Container-only scope with no children (UTIL-1) is valid.
    util = ws.find_scope("UTIL-1")
    assert util is not None
    assert util.is_container_only
    assert util.children == ()

    # Objects present as representative refs.
    assert {o.object_id for o in unit101.objects} >= {
        "TK-101",
        "P-101",
        "V-101",
        "FT-101",
        "LT-101",
    }

    # MUST NOT claim SH-WTP site truth: manifest ids are generic; no
    # water-treatment site vocabulary is used as ids, and the parsed config
    # carries no evidence-maturity fields.
    manifest_text = GENERIC_CONTINUOUS_MANIFEST.read_text(encoding="utf-8")
    assert "shw" not in manifest_text.lower()
    assert "song-hong" not in manifest_text.lower()
    ws_config = load_workspace_config(GENERIC_CONTINUOUS_MANIFEST)
    dumped = ws_config.model_dump(exclude_none=True)
    flat = str(dumped).lower()
    assert "siteverified" not in flat
    assert "sourcemapped" not in flat
    assert "coagul" not in flat and "chlorin" not in flat and "filtrat" not in flat


def test_workspace_config_parse_and_build() -> None:
    config = load_workspace_config(GENERIC_CONTINUOUS_MANIFEST)
    assert isinstance(config, WorkspaceConfig)
    assert config.id == "generic-continuous"

    ws = config.to_workspace()
    assert ws.workspace_id == "generic-continuous"
    assert [s.scope_id for s in ws.top_level_scopes] == ["AREA-1", "AREA-2", "UTIL-1"]


def test_config_is_generic_not_name_hard_coded() -> None:
    """The seam builds ANY workspace id without platform name conditionals."""
    from virtual_factory.workspace import ScopeSpec, build_workspace

    ws = build_workspace(
        "some-custom-workspace",
        [ScopeSpec("ROOT-A", mode=ScopeMode.CONTAINER_ONLY)],
    )
    assert ws.workspace_id == "some-custom-workspace"
    assert ws.find_scope("ROOT-A") is not None

    # The loader seam likewise accepts an arbitrary manifest.
    import yaml

    import tempfile

    manifest = {
        "workspace": {
            "id": "another-ws",
            "scopes": [
                {
                    "id": "TOP",
                    "mode": "container_only",
                    "children": [
                        {
                            "id": "CHILD-1",
                            "mode": "executable_capable",
                            "objects": [{"id": "OBJ-1", "object_type": "thing"}],
                        }
                    ],
                }
            ],
        }
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ws.yaml"
        path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
        loaded = load_workspace_manifest(path)
        assert loaded.workspace_id == "another-ws"
        child = loaded.find_scope("CHILD-1")
        assert child is not None
        assert child.is_executable_capable
        assert child.find_object("OBJ-1") is not None
