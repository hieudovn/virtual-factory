"""VF-vNEXT-G6 — Shared Hierarchical UI Primitives tests.

Proves (Issue #51): recursive hierarchy serialization preserves canonical
StructuralPath; deterministic G1 order; container-only vs executable
capability; path-qualified selection (no ambiguous bare-id authority); exact
TIPA -> ASSY -> six sub-lines; ASSY-SLxx selection maps to the existing
sub-line context without resetting/reconstructing runtimes; structural
selection never changes ASSY domain semantics; continuous view stays truthful
(root-only context, no invented hierarchy) while retaining existing behavior;
Inspector (object) vs Monitoring (scope) context stay distinct; no G7
run-control API added; shared primitives are domain-agnostic (additive JS
contract checks).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REAL_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from virtual_factory.federation import (  # noqa: E402
    SUB_LINE_IDS,
    TipaAssyFederation,
    assy_scope_path,
    build_tipa_workspace,
    sub_line_path,
)
from virtual_factory.ui import hierarchy as ui_h  # noqa: E402
from virtual_factory.ui.api import create_app  # noqa: E402
from virtual_factory.workspace import (  # noqa: E402
    ObjectSpec,
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    build_workspace,
)

UI_STATIC = Path(__file__).resolve().parent.parent / "src" / "virtual_factory" / "ui" / "static"


def _tipa_workspace():
    return build_tipa_workspace()


def _client():
    app = create_app(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=1.0
    )
    return TestClient(app)


# ═══════════════════════════════════════════════════════════
# 1-3. Recursive serialization, deterministic order, capability
# ═══════════════════════════════════════════════════════════

class TestHierarchyProjection:
    def test_recursive_serialization_preserves_canonical_path(self):
        ws = _tipa_workspace()
        tree = ui_h.workspace_to_dict(ws)
        assert tree["workspace_id"] == "TIPA"
        assert tree["path"] == "TIPA"
        assy = tree["scopes"][0]
        assert assy["scope_id"] == "ASSY"
        assert assy["path"] == "TIPA/ASSY"  # canonical full StructuralPath
        for child in assy["children"]:
            assert child["path"].startswith("TIPA/ASSY/ASSY-SL")

    def test_deterministic_order_from_g1(self):
        ws1 = _tipa_workspace()
        ws2 = _tipa_workspace()
        def flatten(node):
            out = [node["path"]]
            for c in node["children"]:
                out.extend(flatten(c))
            return out
        t1 = [flatten(s) for s in ui_h.workspace_to_dict(ws1)["scopes"]]
        t2 = [flatten(s) for s in ui_h.workspace_to_dict(ws2)["scopes"]]
        assert t1 == t2
        assy = ui_h.workspace_to_dict(ws1)["scopes"][0]
        ids = [c["scope_id"] for c in assy["children"]]
        assert ids == list(SUB_LINE_IDS)  # canonical sorted order

    def test_container_vs_executable_capability_represented(self):
        ws = _tipa_workspace()
        assy = ui_h.workspace_to_dict(ws)["scopes"][0]
        assert assy["container_only"] is True
        assert assy["executable_capable"] is False
        assert assy["mode"] == "container_only"
        for child in assy["children"]:
            assert child["container_only"] is False
            assert child["executable_capable"] is True
            assert child["mode"] == "executable_capable"


# ═══════════════════════════════════════════════════════════
# 4. Path-qualified selection (no ambiguous bare-id authority)
# ═══════════════════════════════════════════════════════════

class TestSelectionPathQualified:
    def test_bare_id_is_not_lookup_authority(self):
        # Duplicate local scope ids under different parents must never be
        # resolved by a bare id; only the canonical path is authoritative.
        from virtual_factory.workspace.builder import StructuralValidationError

        ws = build_workspace("TEST", [
            ScopeSpec("CTRL", ScopeMode.CONTAINER_ONLY),
            ScopeSpec("UNIT", ScopeMode.EXECUTABLE_CAPABLE, parent_path=StructuralPath(("TEST", "CTRL"))),
            ScopeSpec("CTRL", ScopeMode.CONTAINER_ONLY, parent_path=StructuralPath(("TEST", "CTRL", "UNIT"))),
        ])
        with pytest.raises(StructuralValidationError):
            ws.find_scope("CTRL")  # ambiguous bare id -> fail closed
        tree = ui_h.workspace_to_dict(ws)

        def collect(node):
            yield node["path"]
            for child in node["children"]:
                yield from collect(child)

        paths = list(collect({"path": tree["path"], "children": tree["scopes"]}))
        assert "TEST" in paths  # workspace root path
        assert "TEST/CTRL" in paths
        assert "TEST/CTRL/UNIT/CTRL" in paths
        assert all(p == "TEST" or p.startswith("TEST/") for p in paths)

    def test_selection_resolves_by_canonical_path_only(self):
        ws = _tipa_workspace()
        scope = ws.resolve_scope(sub_line_path("ASSY-SL03"))
        assert scope.scope_id == "ASSY-SL03"
        ctx = ui_h.structural_context(ws, scope_path=sub_line_path("ASSY-SL03"))
        assert ctx["selection"]["path"] == "TIPA/ASSY/ASSY-SL03"
        with pytest.raises(ui_h.UiHierarchyError):
            ui_h.structural_context(ws, scope_path=StructuralPath(("TIPA", "DOES-NOT-EXIST")))

    def test_container_selection_allowed_but_no_execution_implied(self):
        ws = _tipa_workspace()
        ctx = ui_h.structural_context(ws, scope_path=assy_scope_path())
        sel = ctx["selection"]
        assert sel["kind"] == "scope"
        assert sel["scope_id"] == "ASSY"
        assert sel["container_only"] is True
        assert sel["executable_capable"] is False
        assert ctx["executable_controls_implied"] is False  # capability baseline


# ═══════════════════════════════════════════════════════════
# 5. Exact TIPA hierarchy through API + projection
# ═══════════════════════════════════════════════════════════

class TestTipaExactHierarchy:
    def test_api_hierarchy_exact(self):
        c = _client()
        payload = c.get("/api/ui/hierarchy").json()
        assert payload["workspace_id"] == "TIPA"
        assert [s["scope_id"] for s in payload["scopes"]] == ["ASSY"]
        assy = payload["scopes"][0]
        assert assy["container_only"] is True
        assert [ch["scope_id"] for ch in assy["children"]] == list(SUB_LINE_IDS)

    def test_api_context_default_workspace_selection(self):
        c = _client()
        ctx = c.get("/api/ui/context").json()
        assert ctx["workspace"]["workspace_id"] == "TIPA"
        assert ctx["selection"]["kind"] == "workspace"
        assert ctx["selection"]["path"] == "TIPA"

    def test_api_context_sub_line_selection(self):
        c = _client()
        ctx = c.get("/api/ui/context", params={"path": "TIPA/ASSY/ASSY-SL06"}).json()
        sel = ctx["selection"]
        assert sel["kind"] == "scope"
        assert sel["scope_id"] == "ASSY-SL06"
        assert sel["path"] == "TIPA/ASSY/ASSY-SL06"
        assert sel["executable_capable"] is True

    def test_api_context_bad_path_fails_closed(self):
        c = _client()
        r = c.get("/api/ui/context", params={"path": "TIPA/UNKNOWN"})
        assert r.status_code == 400

    def test_api_hierarchy_unknown_workspace(self):
        c = _client()
        assert c.get("/api/ui/hierarchy", params={"workspace": "NOPE"}).status_code == 404
        assert c.get("/api/ui/context", params={"workspace": "NOPE"}).status_code == 404


# ═══════════════════════════════════════════════════════════
# 6-7. ASSY selection mapping + domain semantics unchanged
# ═══════════════════════════════════════════════════════════

class TestAssySelectionNoRuntimeReconstruction:
    def test_sub_line_path_maps_to_same_existing_sub_line_context(self):
        # The structural path segment equals the canonical ASSY sub-line id the
        # existing overview/controller selects by.
        for sid in SUB_LINE_IDS:
            path = sub_line_path(sid)
            assert path.as_string() == f"TIPA/ASSY/{sid}"
            scope = _tipa_workspace().resolve_scope(path)
            assert scope.scope_id == sid

    def test_hierarchy_selection_does_not_reset_or_reconstruct_runtime(self):
        host = TipaAssyFederation(config_path=str(REAL_CONFIG)).initialize()
        # Structural context building is pure/read-only: runtimes stay identical
        # objects at their current time (no reset/reconstruction).
        before_ids = {sid: id(host.runtime(sid)) for sid in SUB_LINE_IDS}
        before_times = {sid: host.runtime(sid).simulation_time_s for sid in SUB_LINE_IDS}
        for _ in range(3):
            for sid in SUB_LINE_IDS:
                ui_h.structural_context(host.workspace, scope_path=sub_line_path(sid))
        for sid in SUB_LINE_IDS:
            assert id(host.runtime(sid)) == before_ids[sid]
            assert host.runtime(sid).simulation_time_s == before_times[sid]

    def test_assy_domain_scripts_untouched_and_context_is_read_only(self):
        # assy_demo.js (domain rendering) is NOT part of this change set; the
        # additive ASSY context adapter issues no reset/step/reconstruction API
        # call and only touches the existing single-click selection seam.
        js = (UI_STATIC / "assy_context.js").read_text(encoding="utf-8")
        assert "reset(" not in js
        assert "/assy-demo/reset" not in js
        assert "/assy-demo/step" not in js
        assert "_refreshCardStyles" in js
        assert "fetch('/api/ui/context')" in js


# ═══════════════════════════════════════════════════════════
# 8. Continuous root-only context + retained behavior
# ═══════════════════════════════════════════════════════════

class TestContinuousTruthfulContext:
    def test_continuous_context_is_root_only_no_invented_hierarchy(self):
        c = _client()
        ctx = c.get("/api/ui/context/continuous").json()
        assert ctx["workspace"]["workspace_id"] == "continuous_mvp_01"
        assert ctx["hierarchy"] == []  # no invented nested scopes
        assert ctx["selection"]["kind"] == "workspace"

    def test_continuous_existing_behavior_retained(self):
        c = _client()
        assert c.post("/step").status_code == 200
        latest = c.get("/telemetry/latest").json()
        names = {item["name"] for item in latest}
        assert "LT102_LEVEL" in names
        assert c.get("/status").json()["plant_id"] == "continuous_mvp_01"

    def test_continuous_context_script_is_additive(self):
        js = (UI_STATIC / "continuous_context.js").read_text(encoding="utf-8")
        assert "/api/ui/context/continuous" in js
        assert "app.js" not in js  # never touches the existing controller

    def test_index_page_serves_shared_primitives_additively(self):
        c = _client()
        html = c.get("/").text
        assert "hierarchy.js" in html
        assert "continuous_context.js" in html
        assert "vf-context-section" in html
        assert "app.js" in html  # existing controller still loaded


# ═══════════════════════════════════════════════════════════
# 9. Inspector (object) vs Monitoring (scope) context distinct
# ═══════════════════════════════════════════════════════════

def _workspace_with_objects():
    return build_workspace("TEST", [
        ScopeSpec("CTRL", ScopeMode.CONTAINER_ONLY),
        ScopeSpec(
            "UNIT", ScopeMode.EXECUTABLE_CAPABLE,
            parent_path=StructuralPath(("TEST", "CTRL")),
            objects=(
                ObjectSpec("PUMP-1", "pump", "Pump One"),
                ObjectSpec("VALVE-1", "valve", "Valve One"),
            ),
        ),
    ])


class TestInspectorMonitoringSeparation:
    UNIT = StructuralPath(("TEST", "CTRL", "UNIT"))
    CTRL = StructuralPath(("TEST", "CTRL"))

    def test_scope_context_has_no_fabricated_object(self):
        ctx = ui_h.structural_context(_workspace_with_objects(), scope_path=self.UNIT)
        assert ctx["selection"]["kind"] == "scope"
        assert "object" not in ctx["selection"]

    def test_object_context_only_when_object_selected(self):
        ctx = ui_h.structural_context(
            _workspace_with_objects(), scope_path=self.UNIT, object_id="PUMP-1"
        )
        sel = ctx["selection"]
        assert sel["kind"] == "object"
        assert sel["object"]["object_id"] == "PUMP-1"
        assert sel["path"] == "TEST/CTRL/UNIT"  # ownership unchanged

    def test_object_not_in_other_scope_fails_closed(self):
        # Selecting an object that does not belong to the selected scope must
        # fail (never silently change structural ownership).
        with pytest.raises(ui_h.UiHierarchyError):
            ui_h.structural_context(
                _workspace_with_objects(), scope_path=self.CTRL, object_id="PUMP-1"
            )

    def test_container_scope_context_implies_no_executable_controls(self):
        ctx = ui_h.structural_context(_workspace_with_objects(), scope_path=self.CTRL)
        sel = ctx["selection"]
        assert sel["kind"] == "scope"
        assert sel["container_only"] is True
        assert ctx["executable_controls_implied"] is False


# ═══════════════════════════════════════════════════════════
# 10-11. No G7/G8+ scope; shared primitives domain-agnostic
# ═══════════════════════════════════════════════════════════

class TestNoG7AndDomainAgnosticPrimitives:
    def test_new_ui_endpoints_are_read_only_get(self):
        c = _client()
        paths = {"/api/ui/hierarchy", "/api/ui/context", "/api/ui/context/continuous"}
        seen = set()
        for route in c.app.routes:
            for method in getattr(route, "methods", None) or []:
                if getattr(route, "path", None) in paths:
                    seen.add((route.path, method))
        for p in paths:
            assert (p, "GET") in seen, p
        # No run-control/replay/orchestration route was added.
        assert not any(
            "/api/ui" in (getattr(r, "path", "") or "") and m != "GET"
            for r in c.app.routes for m in (getattr(r, "methods", None) or [])
        )

    def test_shared_hierarchy_js_is_domain_agnostic(self):
        js = (UI_STATIC / "hierarchy.js").read_text(encoding="utf-8")
        for forbidden in ("hydraulic", "thermal", "ASSY-SL", "AP0", "TIPA"):
            assert forbidden not in js, forbidden
        # Path-qualified selection and container/executable capability present.
        assert "dataset.path" in js
        assert "container_only" in js
        assert "executable_capable" in js

    def test_assy_page_includes_shared_primitives_additively(self):
        c = _client()
        html = c.get("/assy-demo").text
        assert "assy_demo.js" in html  # domain rendering retained
        assert "hierarchy.js" in html
        assert "assy_context.js" in html
        assert "vf-hierarchy-section" in html

    def test_hierarchy_module_has_no_run_control_api(self):
        src = (Path(__file__).resolve().parent.parent
               / "src" / "virtual_factory" / "ui" / "hierarchy.py").read_text(encoding="utf-8")
        assert "def run" not in src
        assert "def step" not in src
        assert "def reset" not in src
