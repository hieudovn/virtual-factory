"""VF-DM-M3-S03 — TIPA integration tests.

2 SSO2 sources → shared buffer → AP01-AP06 → final quality → finished/rework.
"""

import pytest
from virtual_factory.assembly.tipa import build_tipa_topology, build_tipa_handler_registry
from virtual_factory.assembly.quality import QualityDisposition
from virtual_factory.assembly.wip import WipId, WipStatus
from virtual_factory.discrete.events import ScheduledEvent
from virtual_factory.discrete.run_context import RunContext
from virtual_factory.discrete.run_service import DiscreteRunService


def _evt(event_id, simulation_time_s=0.0, event_type="", target_id="", causation_id=None):
    return ScheduledEvent(
        event_id=event_id, simulation_time_s=simulation_time_s,
        event_type=event_type, target_id=target_id, causation_id=causation_id,
    )


def _rc(**kw):
    defaults = {"run_id": "tipa-demo", "model_id": "tipa-assembly"}
    defaults.update(kw)
    return RunContext(**defaults)


def _run_to_completion(svc, max_steps=200):
    for _ in range(max_steps):
        snap = svc.snapshot
        if snap.status in ("completed", "stopped", "failed"):
            break
        svc.step_once()
    return svc.snapshot


# ═══════════════════════════════════════════
# TIPA Topology
# ═══════════════════════════════════════════

class TestTIPATopology:
    """Topology structure verification."""

    def test_all_primitives_present(self):
        topo = build_tipa_topology()
        ids = set(topo.primitives.keys())
        assert "sso2-1" in ids
        assert "sso2-2" in ids
        assert "shared-buffer" in ids
        for ap in ["AP01", "AP02", "AP03", "AP04", "AP05", "AP06"]:
            assert ap in ids
        assert "final-quality" in ids
        assert "finished-sink" in ids

    def test_sso2_routes_to_shared_buffer(self):
        topo = build_tipa_topology()
        assert topo.next_primitive("sso2-1") == "shared-buffer"
        assert topo.next_primitive("sso2-2") == "shared-buffer"

    def test_ap_chain_sequential(self):
        topo = build_tipa_topology()
        assert topo.next_primitive("AP01") == "AP02"
        assert topo.next_primitive("AP05") == "AP06"

    def test_quality_routing(self):
        topo = build_tipa_topology()
        assert topo.next_primitive("final-quality", "pass") == "finished-sink"
        assert topo.next_primitive("final-quality", "rework") == "AP04"

    def test_ap06_to_final_quality(self):
        topo = build_tipa_topology()
        assert topo.next_primitive("AP06") == "final-quality"


# ═══════════════════════════════════════════
# Single WIP — PASS flow
# ═══════════════════════════════════════════

class TestTIPASingleWIPPass:
    """One WIP: sso2-1 → buffer → AP01-AP06 → final-quality(PASS) → finished-sink."""

    def test_single_wip_completes_to_sink(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        final = _run_to_completion(svc)
        assert final.status == "completed"

        ws = state.get_wip(WipId("wip-0001"))
        assert ws is not None
        assert ws.status == WipStatus.COMPLETED
        assert ws.location == "finished-sink"

    def test_wip_passes_through_all_aps(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        _run_to_completion(svc)
        # Trace should contain PROCESS_START for AP01-AP06
        trace = svc.snapshot.recent_events
        process_targets = [
            t.target_id for t in trace
            if t.event_type == "PROCESS_START" and t.target_id.startswith("AP")
        ]
        assert len(process_targets) == 6  # AP01-AP06

    def test_simulation_time_reflects_processing(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        final = _run_to_completion(svc)
        # 6 APs × 1.0s processing each = 6.0s minimum
        assert final.simulation_time_s >= 6.0

    def test_pending_events_zero(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        final = _run_to_completion(svc)
        assert final.pending_events == 0


# ═══════════════════════════════════════════
# Rework flow
# ═══════════════════════════════════════════

class TestTIPARework:
    """REWORK: AP06 → final-quality(REWORK) → AP04 → AP05 → AP06 → final-quality(PASS) → sink."""

    def test_rework_eventually_completes(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.REWORK, QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        final = _run_to_completion(svc)
        assert final.status == "completed"

        ws = state.get_wip(WipId("wip-0001"))
        assert ws.status == WipStatus.COMPLETED
        assert ws.location == "finished-sink"

    def test_rework_revisits_ap04(self):
        """AP04 should be visited twice: initial pass + after rework."""
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.REWORK, QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        _run_to_completion(svc)
        trace = svc.snapshot.recent_events
        ap04_starts = [t for t in trace
                       if t.event_type == "PROCESS_START" and t.target_id == "AP04"]
        assert len(ap04_starts) == 2  # initial + rework


# ═══════════════════════════════════════════
# Two-source flow
# ═══════════════════════════════════════════

class TestTIPATwoSource:
    """2 SSO2 sources feed into shared buffer → both WIPs complete."""

    def test_two_wips_both_complete(self):
        reg, state, wc = build_tipa_handler_registry({
            "wip-0001": [QualityDisposition.PASS],
            "wip-0002": [QualityDisposition.PASS],
        })
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
            _evt("wip-0002-create", 0.0, "WIP_CREATED", "sso2-2"),
        ])

        final = _run_to_completion(svc, max_steps=300)
        assert final.status == "completed"

        ws1 = state.get_wip(WipId("wip-0001"))
        ws2 = state.get_wip(WipId("wip-0002"))
        assert ws1.status == WipStatus.COMPLETED
        assert ws2.status == WipStatus.COMPLETED
        assert ws1.location == "finished-sink"
        assert ws2.location == "finished-sink"


# ═══════════════════════════════════════════
# Buffer occupancy
# ═══════════════════════════════════════════

class TestTIPABuffer:
    """Shared buffer correctly tracks occupancy."""

    def test_buffer_starts_and_ends_empty(self):
        reg, state, wc = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(_rc(), reg, initial_events=[
            _evt("wip-0001-create", 0.0, "WIP_CREATED", "sso2-1"),
        ])

        assert state.buffer_size("shared-buffer") == 0
        _run_to_completion(svc)
        assert state.buffer_size("shared-buffer") == 0
