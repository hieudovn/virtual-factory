"""VF-vNEXT-G8 — Platform vNext Regression Baseline cross-gate invariants.

Issue #53 section C: add only the smallest tests genuinely needed to prove
cross-gate integration invariants that are NOT already directly covered by the
individual accepted gate suites. Each gate suite (G1-G7) proves its own slice;
this module proves the ALIGNMENT across the G1 structural authority, the G6
shared hierarchy UI projection, and the G7 run-control effective-scope/context
identity for both canonical workspaces (TIPA and continuous), plus that
workspace roots are never executable and that the two structural authorities
coexist without cross-workspace ambiguity.

Invariants already strongly/directly proven by accepted gate suites are
REFERENCED (via the manifest's g7_run_control group), not duplicated here —
notably: independent active TIPA/continuous runs (G7-C02) and per-attempt fresh
execution state (G7-C03).
"""

from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.federation import (  # noqa: E402
    SUB_LINE_IDS,
    build_tipa_workspace,
    sub_line_path,
)
from virtual_factory.runcontrol import (  # noqa: E402
    RunLifecycleService,
    build_continuous_workspace,
    process_scope_path,
    resolve_target,
)
from virtual_factory.ui import hierarchy as ui_h  # noqa: E402
from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.workspace import StructuralPath  # noqa: E402

# A RunLifecycleService whose bridge is never invoked for create/status reads;
# create_run only resolves targets and freezes context (no execution).
def _read_only_service(ws) -> RunLifecycleService:
    return RunLifecycleService(ws, lambda: None)


def _client():
    return TestClient(
        create_app(
            config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=1.0
        )
    )


def _executable_paths(node) -> set[str]:
    """Flatten a workspace_to_dict JSON tree to its executable scope paths."""
    out: set[str] = set()
    stack = list(node.get("scopes", []))
    while stack:
        scope = stack.pop()
        if scope.get("executable_capable") is True:
            out.add(scope["path"])
        stack.extend(scope.get("children", []))
    return out


TIPA_SUBLINE_PATHS = tuple(f"TIPA/ASSY/{sid}" for sid in SUB_LINE_IDS)


# ═══════════════════════════════════════════════════════════
# Workspace roots are never executable (TIPA + continuous)
# ═══════════════════════════════════════════════════════════

class TestWorkspaceRootsAreNotExecutable:
    def test_both_workspace_roots_resolve_as_workspace_never_executable(self):
        cases = [
            (build_tipa_workspace(), "TIPA"),
            (build_continuous_workspace(), "continuous"),
        ]
        for ws, root in cases:
            res = resolve_target(ws, StructuralPath((root,)))
            assert res.target_kind == "workspace"  # never 'executable'
            assert root not in res.effective_scope_strings  # root not participant

    def test_ui_context_workspace_root_selection_is_workspace(self):
        c = _client()
        for workspace in ("TIPA", "continuous"):
            ctx = c.get("/api/ui/context", params={"workspace": workspace}).json()
            assert ctx["selection"]["kind"] == "workspace"
            assert ctx["selection"]["path"] == workspace


# ═══════════════════════════════════════════════════════════
# G1 structural  ==  G6 UI hierarchy  ==  G7 run-control effective scopes
# ═══════════════════════════════════════════════════════════

class TestCrossGateEffectiveScopeAlignment:
    def test_tipa_structural_ui_runcontrol_all_align(self):
        ws = build_tipa_workspace()
        structural = resolve_target(ws, StructuralPath(("TIPA",)))
        # G1 structural authority: exactly the six ASSY executable descendants.
        assert structural.effective_scope_strings == TIPA_SUBLINE_PATHS
        # G6 shared hierarchy UI projection agrees.
        ui_paths = _executable_paths(ui_h.workspace_to_dict(ws))
        assert ui_paths == set(TIPA_SUBLINE_PATHS)
        # G7 run-control workspace-target effective scopes agree.
        rec = _read_only_service(ws).create_run("TIPA")
        assert rec.effective_scopes == TIPA_SUBLINE_PATHS
        # Executable target resolves only itself, in every layer.
        for sid in SUB_LINE_IDS:
            path = sub_line_path(sid)
            assert resolve_target(ws, path).effective_scope_strings == (
                path.as_string(),
            )
            assert _read_only_service(ws).create_run(path.as_string()).effective_scopes == (
                path.as_string(),
            )

    def test_continuous_structural_ui_runcontrol_all_align(self):
        ws = build_continuous_workspace()
        root = StructuralPath(("continuous",))
        # G1 structural authority: workspace target -> exactly PROCESS.
        assert resolve_target(ws, root).effective_scope_strings == (
            "continuous/PROCESS",
        )
        # executable PROCESS target -> only itself.
        assert resolve_target(ws, process_scope_path()).effective_scope_strings == (
            "continuous/PROCESS",
        )
        # G6 shared hierarchy UI projection: only PROCESS is executable.
        ui_paths = _executable_paths(ui_h.workspace_to_dict(ws))
        assert ui_paths == {"continuous/PROCESS"}
        # G7 run-control effective scopes agree for both target forms.
        for target in ("continuous", "continuous/PROCESS"):
            rec = _read_only_service(ws).create_run(target)
            assert rec.effective_scopes == ("continuous/PROCESS",)

    def test_runcontrol_effective_matches_structural_for_every_target(self):
        ws = build_tipa_workspace()
        targets = ("TIPA", "TIPA/ASSY", "TIPA/ASSY/ASSY-SL01")
        for target in targets:
            path = StructuralPath.from_string(target)
            expected = resolve_target(ws, path).effective_scope_strings
            rec = _read_only_service(ws).create_run(target)
            assert rec.effective_scopes == expected


# ═══════════════════════════════════════════════════════════
# RunContextV2 identity aligns with target resolution
# ═══════════════════════════════════════════════════════════

class TestRunContextIdentityAlignment:
    def test_workspace_target_context_has_no_scope_path(self):
        for ws, target in [
            (build_tipa_workspace(), "TIPA"),
            (build_continuous_workspace(), "continuous"),
        ]:
            rec = _read_only_service(ws).create_run(target)
            ctx = rec.context
            assert ctx.workspace_id == ws.workspace_id
            assert ctx.scope_path is None  # workspace target has no owning scope

    def test_executable_target_context_scope_path_aligns(self):
        cases = [
            (build_tipa_workspace(), "TIPA/ASSY/ASSY-SL03"),
            (build_continuous_workspace(), "continuous/PROCESS"),
        ]
        for ws, target in cases:
            rec = _read_only_service(ws).create_run(target)
            ctx = rec.context
            assert ctx.workspace_id == ws.workspace_id
            assert ctx.scope_path is not None
            assert ctx.scope_path.as_string() == target
            assert ctx.scope_path.workspace_id == ws.workspace_id


# ═══════════════════════════════════════════════════════════
# TIPA + continuous structural authorities coexist (no ambiguity)
# ═══════════════════════════════════════════════════════════

class TestStructuralAuthorityCoexistence:
    def test_no_cross_workspace_ambiguity_in_structural_ui(self):
        c = _client()
        tipa = c.get("/api/ui/hierarchy", params={"workspace": "TIPA"}).json()
        continuous = c.get(
            "/api/ui/hierarchy", params={"workspace": "continuous"}
        ).json()
        tipa_paths = _executable_paths(tipa) | {tipa["path"]}
        cont_paths = _executable_paths(continuous) | {continuous["path"]}
        # Disjoint path namespaces: no structural path is shared/ambiguous.
        assert tipa_paths.isdisjoint(cont_paths)

    def test_continuous_hierarchy_has_no_deeper_invented_topology(self):
        ws = build_continuous_workspace()
        tree = ui_h.workspace_to_dict(ws)
        assert [s["scope_id"] for s in tree["scopes"]] == ["PROCESS"]
        process = tree["scopes"][0]
        assert process["children"] == []  # no deeper unit/area/equipment scope
