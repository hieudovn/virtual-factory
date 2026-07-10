"""Tests for VF-2 simulation loop (ST07)."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulators.vf2.package_loader import load_package
from simulators.vf2.simulation_loop import Vf2SimulationLoop

GOLDEN = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "sample_pim_package.json"
)


@pytest.fixture(scope="module")
def pkg():
    return load_package(GOLDEN)


class TestSimulationLoop:

    # AC-1
    def test_step_produces_frame(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        frame = loop.step(1.0)
        assert len(frame) == 4  # 4 signals in golden fixture
        for m in frame:
            assert m.signal_id       # not empty
            assert m.timestamp       # ISO 8601
            assert m.source == "vf2-sim-01"

    # AC-6
    def test_measurement_fields(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        frame = loop.step(1.0)
        for m in frame:
            assert m.timestamp
            assert m.signal_id
            assert isinstance(m.value, (int, float))
            assert m.quality in ("GOOD", "UNCERTAIN", "BAD")
            assert m.source == "vf2-sim-01"

    # AC-2
    def test_run_60_steps(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        frames = loop.run(60, 1.0)
        assert len(frames) == 60
        for frame in frames:
            assert len(frame) == 4

    # AC-3
    def test_signal_values_change_over_time(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        f1 = loop.step(1.0)
        f2 = loop.step(1.0)
        changes = 0
        for m1, m2 in zip(f1, f2):
            if m1.value != m2.value:
                changes += 1
        assert changes > 0, "At least one signal should change (random_walk)"

    # AC-4
    def test_scenario_applies_overrides(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        # Normal steps first
        loop.run(10, 1.0)
        # Baseline values before scenario
        baseline = loop.step(1.0)

        # Activate pump trip
        result = loop.activate_scenario("SCN-PUMP-TRIP-002")
        assert result["status"] == "transitioning"

        # Run through full transition (30s)
        loop.run(35, 1.0)

        # Check affected signals are 0
        frame = loop.step(1.0)
        ft101 = [m for m in frame if "FT_101" in m.signal_id]
        pt101 = [m for m in frame if "PT_101" in m.signal_id]
        vb101 = [m for m in frame if "VB_101" in m.signal_id]

        if ft101:
            assert ft101[0].value == 0.0, f"FT_101 should be 0, got {ft101[0].value}"
        if pt101:
            assert pt101[0].value == 0.0, f"PT_101 should be 0, got {pt101[0].value}"
        if vb101:
            assert vb101[0].value == 0.0, f"VB_101 should be 0, got {vb101[0].value}"

    # AC-5
    def test_state_accumulates(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        loop.run(10, 1.0)
        assert loop.state.step_count == 10
        assert loop.state.time_s == 10.0

    def test_state_accumulates_with_custom_dt(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        loop.run(20, 0.5)
        assert loop.state.step_count == 20
        assert loop.state.time_s == 10.0  # 20 * 0.5

    def test_get_all_signal_ids(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        frame = loop.step(1.0)
        signal_ids = {m.signal_id for m in frame}
        expected = {
            "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER",
            "VF2.PUMP_STATION_01.PT_101.DISCHARGE_PRESSURE_TRANSMITTER",
            "VF2.PUMP_STATION_01.LT_101.SUCTION_LEVEL_TRANSMITTER",
            "VF2.PUMP_STATION_01.VB_101.PUMP_A_VIBRATION_SENSOR",
        }
        assert signal_ids == expected

    def test_activate_scenario_returns_status(self, pkg):
        loop = Vf2SimulationLoop(pkg)
        result = loop.activate_scenario("NONEXISTENT")
        assert result["status"] == "error"

    def test_1000_steps_stable(self, pkg):
        """Long run: verify no errors and values stay reasonable."""
        loop = Vf2SimulationLoop(pkg)
        frames = loop.run(1000, 1.0)
        assert len(frames) == 1000
        # All values should be reasonable floats
        for frame in frames:
            for m in frame:
                assert isinstance(m.value, (int, float))
                # random_walk should keep things bounded
                assert -1e6 < m.value < 1e6
