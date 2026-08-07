"""VF-DM-M4-S03 — Scene model tests.

M4-S03-C01: Scene consumes AssemblyProjection only (no AssemblyTopology).
M4-S03-C01 rework proof: TIPA → Quality REWORK → AP04 re-entry → projection → scene.
"""

from virtual_factory.assembly.scene import (
    NodeView, EdgeView, WipTokenView, EventMarkerView,
    SimulationScene, LayoutDefinition, NodeLayout, build_scene,
)
from virtual_factory.assembly.projection import (
    AssemblyProjection, RunInfo, PrimitiveView, WipView, EventView,
)
from virtual_factory.discrete.run_service import DiscreteRunService
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.assembly.tipa import build_tipa_topology, build_tipa_handler_registry
from virtual_factory.assembly.quality import QualityDisposition


class TestSceneModel:
    def test_scene_from_tipa_runtime(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="scene", model_id="tipa"),
                       reg, initial_events=[
            ScheduledEvent(event_id="wip-0001-create", simulation_time_s=0,
                          event_type="WIP_CREATED", target_id="sso2-1"),
        ])
        svc.step_once()
        svc.step_once()

        topo = build_tipa_topology()
        from virtual_factory.assembly.projection import project_assembly
        proj = project_assembly(svc, state, topo)

        # Simple linear layout for TIPA
        layout = LayoutDefinition(
            canvas_width=1400, canvas_height=400,
            nodes=[
                NodeLayout("sso2-1", 50, 200),
                NodeLayout("sso2-2", 50, 300),
                NodeLayout("shared-buffer", 200, 200),
                NodeLayout("AP01", 350, 200), NodeLayout("AP02", 500, 200),
                NodeLayout("AP03", 650, 200), NodeLayout("AP04", 800, 200),
                NodeLayout("AP05", 950, 200), NodeLayout("AP06", 1100, 200),
                NodeLayout("final-quality", 1250, 200),
                NodeLayout("finished-sink", 1400, 200),
            ],
        )

        scene = build_scene(proj, layout)
        assert scene.canvas_width == 1400
        assert len(scene.nodes) >= 6
        assert len(scene.wips) == 1

    def test_node_view_has_required_fields(self):
        n = NodeView(node_id="n1", primitive_id="p1", node_type="processor",
                     label="Test", x=0, y=0, width=100, height=50, status="idle")
        assert n.status in ("idle", "active", "waiting", "blocked", "error", "completed")

    def test_wip_token_view(self):
        w = WipTokenView(wip_id="w-1", current_node="AP01", status="processing",
                         flow_id="base", display_type="semi-finished")
        assert w.display_type in ("material", "semi-finished", "finished", "generic")

    def test_event_marker_view(self):
        m = EventMarkerView(event_type="QUALITY_CHECK", target_node="qg-1",
                            simulation_time_s=1.5, severity="warning", label="REWORK")
        assert m.severity in ("info", "warning", "error")

    def test_layout_get_node(self):
        layout = LayoutDefinition(nodes=[
            NodeLayout("n1", 10, 20),
            NodeLayout("n2", 50, 80),
        ])
        assert layout.get_node("n1") is not None
        assert layout.get_node("n99") is None


class TestReworkVisualizationProof:
    """M4-S03-C01 — TIPA → Quality REWORK → AP04 re-entry → Projection → Scene.

    Reference regression test, not official TIPA workflow logic.
    """

    def test_rework_flow_projection_and_scene(self):
        from virtual_factory.assembly.projection import project_assembly

        # Rework plan: first disposition = REWORK, second = PASS
        reg, state, _ = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.REWORK, QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="rework-scene", model_id="tipa"),
                       reg, initial_events=[
            ScheduledEvent(event_id="wip-0001-create", simulation_time_s=0,
                          event_type="WIP_CREATED", target_id="sso2-1"),
        ])
        # Run through: create → queue → process-start → process-complete at AP01
        # → ... → AP06 → quality check → REWORK → AP04 process-start
        for _ in range(16):
            svc.step_once()

        topo = build_tipa_topology()
        proj = project_assembly(svc, state, topo)

        # --- Assertions: same WIP ID ---
        assert len(proj.wips) == 1
        w = proj.wips[0]
        assert w.wip_id == "wip-0001"

        # --- flow_id = rework-1 ---
        assert w.flow_id == "rework-1", f"Expected rework-1, got {w.flow_id}"

        # --- Current node reflects actual rework station ---
        assert w.location is not None
        # After rework the WIP should be at AP04 (the rework target in TIPA)
        assert w.location == "AP04", f"Expected AP04, got {w.location}"

        # --- Rework marker is present ---
        rework_markers = [m for m in proj.issues if m.marker_type == "rework"]
        assert len(rework_markers) >= 1, "Expected rework marker in projection"

        # --- Scene: WipTokenView flow_id = rework-1 ---
        layout = LayoutDefinition(
            canvas_width=1400, canvas_height=400,
            nodes=[
                NodeLayout("sso2-1", 50, 200),
                NodeLayout("sso2-2", 50, 300),
                NodeLayout("shared-buffer", 200, 200),
                NodeLayout("AP01", 350, 200), NodeLayout("AP02", 500, 200),
                NodeLayout("AP03", 650, 200), NodeLayout("AP04", 800, 200),
                NodeLayout("AP05", 950, 200), NodeLayout("AP06", 1100, 200),
                NodeLayout("final-quality", 1250, 200),
                NodeLayout("finished-sink", 1400, 200),
            ],
        )
        scene = build_scene(proj, layout)

        # --- No duplicate WIP token ---
        wip_ids = [wt.wip_id for wt in scene.wips]
        assert len(wip_ids) == len(set(wip_ids)), f"Duplicate WIP tokens: {wip_ids}"

        # --- WipTokenView flow_id = rework-1 ---
        assert len(scene.wips) == 1
        assert scene.wips[0].flow_id == "rework-1"

        # --- Current node in scene matches projection location ---
        assert scene.wips[0].current_node == w.location
