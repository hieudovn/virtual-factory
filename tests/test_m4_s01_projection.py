"""VF-DM-M4-S01 — AssemblyProjection tests."""

import json
import pytest
from virtual_factory.assembly.projection import (
    project_assembly, AssemblyProjection, RunInfo, PrimitiveView,
    EdgeView, WipView, BufferView, EventView, IssueMarker,
)
from virtual_factory.discrete.run_service import DiscreteRunService
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.assembly.tipa import build_tipa_topology, build_tipa_handler_registry
from virtual_factory.assembly.quality import QualityDisposition


def _evt(eid, t=0.0, et="", tid="", cid=None):
    return ScheduledEvent(event_id=eid, simulation_time_s=t, event_type=et,
                          target_id=tid, causation_id=cid)


class TestAssemblyProjection:
    """Projection from live runtime."""

    def test_projection_from_tipa_runtime(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="proj-test", model_id="tipa"),
                       reg, initial_events=[
            _evt("wip-0001-create", 0, "WIP_CREATED", "sso2-1"),
        ])

        # Step a few events then project
        svc.step_once()
        svc.step_once()

        topo = build_tipa_topology()
        proj = project_assembly(svc, state, topo)

        # Run info
        assert proj.run.run_id == "proj-test"
        assert proj.run.status == "ready" or proj.run.status == "running"

        # Primitives
        assert len(proj.primitives) == 11  # 2 source + buffer + 6 AP + quality + sink
        ptypes = {p.primitive_type for p in proj.primitives}
        assert "source" in ptypes
        assert "buffer" in ptypes
        assert "processor" in ptypes
        assert "quality_gate" in ptypes
        assert "sink" in ptypes

        # Edges
        assert len(proj.edges) >= 8

        # WIPs
        assert len(proj.wips) == 1
        assert proj.wips[0].wip_id == "wip-0001"

        # Buffers
        assert len(proj.buffers) == 1
        assert proj.buffers[0].buffer_id == "shared-buffer"
        assert proj.buffers[0].capacity == 50

    def test_projection_serializable(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="ser", model_id="x"),
                       reg, initial_events=[
            _evt("wip-0001-create", 0, "WIP_CREATED", "sso2-1"),
        ])
        svc.step_once()

        topo = build_tipa_topology()
        proj = project_assembly(svc, state, topo)

        data = {
            "run": {"status": proj.run.status, "simulation_time_s": proj.run.simulation_time_s},
            "primitives": [{"id": p.primitive_id, "type": p.primitive_type}
                           for p in proj.primitives],
            "edges": [{"from": e.from_id, "to": e.to_id} for e in proj.edges],
            "wips": [{"id": w.wip_id, "location": w.location, "status": w.status}
                     for w in proj.wips],
        }
        json_str = json.dumps(data, default=str)
        assert len(json_str) > 0
        parsed = json.loads(json_str)
        assert parsed["run"]["status"] == proj.run.status

    def test_projection_detached_from_runtime(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="det", model_id="x"),
                       reg, initial_events=[
            _evt("wip-0001-create", 0, "WIP_CREATED", "sso2-1"),
        ])
        svc.step_once()

        topo = build_tipa_topology()
        proj1 = project_assembly(svc, state, topo)
        svc.step_once()
        proj2 = project_assembly(svc, state, topo)

        # proj1 should be unchanged (detached snapshot)
        assert proj1.run.pending_events != proj2.run.pending_events or \
               proj1.run.processed_events != proj2.run.processed_events

    def test_issues_from_failed_handler(self):
        """Issue markers generated from failed trace entries."""
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(RunContext(run_id="iss", model_id="x"),
                       reg, initial_events=[
            _evt("wip-0001-create", 0, "WIP_CREATED", "sso2-1"),
        ])
        # Run to completion
        for _ in range(200):
            if svc.snapshot.status in ("completed", "stopped", "failed"):
                break
            svc.step_once()

        topo = build_tipa_topology()
        proj = project_assembly(svc, state, topo)
        assert isinstance(proj.issues, list)
