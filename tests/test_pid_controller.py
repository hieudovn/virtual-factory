"""Tests for PID controller: D-term, anti-windup, and derivative filter."""

from pathlib import Path

import pytest

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine


def test_d_term_contributes_on_changing_error() -> None:
    """When Kd > 0 and error changes, the D-term should affect the output."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    # Override PID gains — high Kd, zero Ki so only P+D act
    lic102 = engine.assembly.controllers["LIC102"]
    lic102.parameters["kp"] = 0.0
    lic102.parameters["ki"] = 0.0
    lic102.parameters["kd"] = 5.0

    # Step 1: PV = 1.0, no previous PV → D = 0
    engine.state.set_truth("T102.level_true", 1.0)
    engine.assembly.sensors["LT102"].sample(
        engine.state, timestamp_s=0.0, signal_config=config.signals["LT102_LEVEL"]
    )
    lic102.execute(engine.state, timestamp_s=0.0, signal_config=config.signals["LIC102_OUT"])
    output1 = engine.state.get_signal_numeric("LIC102_OUT")

    # Step 2: PV = 2.0, previous PV = 1.0 → D = Kd * (2-1)/1 = 5.0
    engine.state.set_truth("T102.level_true", 2.0)
    engine.assembly.sensors["LT102"].sample(
        engine.state, timestamp_s=1.0, signal_config=config.signals["LT102_LEVEL"]
    )
    lic102.execute(engine.state, timestamp_s=1.0, signal_config=config.signals["LIC102_OUT"])
    output2 = engine.state.get_signal_numeric("LIC102_OUT")

    # D-term acts in the opposite direction of PV increase (error decreases)
    # PV went up → error went down → D is negative (slows approach to setpoint)
    assert output2 != pytest.approx(output1, abs=1e-6), "D-term should change the output"


def test_anti_windup_stops_integral_at_max_output() -> None:
    """When output saturates at 100% and error is positive, integral should not grow."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    lic102 = engine.assembly.controllers["LIC102"]
    lic102.parameters["kp"] = 10.0
    lic102.parameters["ki"] = 100.0
    lic102.parameters["kd"] = 0.0
    lic102.integral = 0.0

    # Set PV far below setpoint so error is large positive → output saturates
    engine.state.set_signal_value("LT102_LEVEL", 0.0, timestamp_s=0.0, unit="m", quality="GOOD")
    lic102.execute(engine.state, timestamp_s=0.0, signal_config=config.signals["LIC102_OUT"])
    integral_after = lic102.integral

    # At 100% output with positive error, integral should NOT accumulate
    assert lic102.integral == pytest.approx(0.0, abs=1e-6), "Anti-windup should prevent integral growth at saturation"


def test_anti_windup_stops_integral_at_min_output() -> None:
    """When output saturates at 0% and error is negative, integral should not grow."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    lic102 = engine.assembly.controllers["LIC102"]
    lic102.parameters["kp"] = 5.0
    lic102.parameters["ki"] = 5.0
    lic102.parameters["kd"] = 0.0
    lic102.integral = 0.0

    # Set PV far above setpoint so error is negative → output tries to go < 0%
    # error = 2.5 - 10 = -7.5
    # p_out = 5 * (-7.5) = -37.5
    # tentative_i = 5 * (0 + (-7.5)) = -37.5
    # tentative_output = -37.5 + (-37.5) = -75 → below 0
    # error is negative → anti-windup should prevent integral from going more negative
    engine.state.set_signal_value("LT102_LEVEL", 10.0, timestamp_s=0.0, unit="m", quality="GOOD")
    lic102.execute(engine.state, timestamp_s=0.0, signal_config=config.signals["LIC102_OUT"])

    # Anti-windup should have kept integral at 0
    assert lic102.integral == pytest.approx(0.0, abs=1e-6), "Anti-windup should clamp integral when output < 0%"


def test_derivative_on_measurement_avoids_kick() -> None:
    """Setpoint change alone should not cause a derivative spike (derivative on PV, not error)."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    lic102 = engine.assembly.controllers["LIC102"]
    lic102.parameters["kp"] = 0.0
    lic102.parameters["ki"] = 0.0
    lic102.parameters["kd"] = 10.0
    lic102.last_pv = 1.0  # previous PV

    # Change setpoint only, PV stays same → derivative of PV is 0
    # (setpoint change should not create derivative kick)
    lic102.config.setpoint = 5.0  # big setpoint change
    engine.state.set_signal_value("LT102_LEVEL", 1.0, timestamp_s=1.0, unit="m", quality="GOOD")
    lic102.execute(engine.state, timestamp_s=1.0, signal_config=config.signals["LIC102_OUT"])
    output = engine.state.get_signal_numeric("LIC102_OUT")

    # D-term should be ~0 because PV didn't change
    assert output == pytest.approx(0.0, abs=1e-6), "Derivative on PV should avoid kick on setpoint change"
