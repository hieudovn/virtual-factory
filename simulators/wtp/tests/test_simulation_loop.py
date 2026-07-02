"""Test the simulation loop with 100 steps."""

import random

from ..signal_registry import SignalRegistry
from ..disturbance_engine import DisturbanceEngine
from ..actuator_engine import ActuatorEngine
from ..simulation_loop import WtpSimulationLoop


def test_simulation_100_steps():
    registry = SignalRegistry()
    dist_engine = DisturbanceEngine(registry.DV_CONFIGS)
    act_engine = ActuatorEngine(registry.MV_CONFIGS)
    loop = WtpSimulationLoop(registry, dist_engine, act_engine)

    for i in range(100):
        measurements = loop.step(1.0)
        assert len(measurements) == 92, f"Step {i}: expected 92 measurements, got {len(measurements)}"

    assert loop.state.step_count == 100
    assert loop.state.time_s == 100.0
    assert loop.state.total_frames > 0

    # Verify some key signals exist
    all_values = loop.get_all_values()
    expected_signals = [
        "RAW-WATER-QUALITY-STATION-101.raw_turbidity",
        "COAG-PUMP-101.flow_rate",
        "CLARIFIER-101.settled_turbidity",
        "FILTER-101.filter_dp",
        "DISINFECTION-QUALITY-STATION-101.free_chlorine",
        "TRANSFER-OUTLET-QUALITY-STATION-101.outlet_compliance_status",
        "PLANT-KPI-101.cost_per_m3",
    ]
    for sid in expected_signals:
        assert sid in all_values, f"Missing signal: {sid}"

    print(f"All signals: {len(all_values)}")
    print(f"Time: {loop.state.time_s}s, Frames: {loop.state.step_count}")
    print("Simulation loop test passed!")


def test_simulation_filter_backwash():
    """Run long enough to trigger a filter backwash."""
    registry = SignalRegistry()
    dist_engine = DisturbanceEngine(registry.DV_CONFIGS)
    act_engine = ActuatorEngine(registry.MV_CONFIGS)
    loop = WtpSimulationLoop(registry, dist_engine, act_engine)

    # Run 5000 steps (filter DP should accumulate)
    for i in range(5000):
        loop.step(0.1)

    # DP should have changed from initial values
    assert loop.state.filter_dp_101_accum > 20.0 or loop.state.backwash_101_remaining > 0, \
        f"Filter DP didn't accumulate: {loop.state.filter_dp_101_accum}"
    print(f"Filter DP-101: {loop.state.filter_dp_101_accum:.1f} kPa")
    print(f"Backwash remaining: {loop.state.backwash_101_remaining:.0f}s")


if __name__ == "__main__":
    test_simulation_100_steps()
    test_simulation_filter_backwash()
    print("All simulation loop tests passed!")
