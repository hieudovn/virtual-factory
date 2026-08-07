"""VF-DM-M4-S03 — Scene model tests."""

from virtual_factory.assembly.scene import (
    NodeView, EdgeView, WipTokenView, EventMarkerView,
    SimulationScene, LayoutDefinition, NodeLayout, build_scene,
    _AssemblyProjection, _RunInfo, _PrimitiveView, _WipView, _EventView,
)
from virtual_factory.assembly.tipa import build_tipa_topology


class TestSceneModel:
    def test_scene_from_tipa_runtime(self):
        topo = build_tipa_topology()

        # Manual projection (scene module inlined types)
        proj = _AssemblyProjection(
            run=_RunInfo(status="running", simulation_time_s=1.0,
                         pending_events=3, processed_events=2,
                         run_id="scene", model_id="tipa"),
            primitives=[
                _PrimitiveView(primitive_id=pid, primitive_type="processor",
                               label=pid, properties={"processing_time_s": 1.0})
                for pid in ["AP01","AP02","AP03","AP04","AP05","AP06"]
            ],
            wips=[_WipView(wip_id="w-1", location="AP01", status="processing",
                           flow_id="base", step_count=1, is_terminal=False)],
            recent_events=[
                _EventView(event_id="e1", event_type="PROCESS_START",
                           target_id="AP01", simulation_time_s=0.5,
                           wip_id="w-1", state_changes=(), result="committed",
                           error_code=None),
            ],
        )

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

        scene = build_scene(proj, topo, layout)
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
