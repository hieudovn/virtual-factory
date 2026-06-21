"""Tests for mass balance evaluation."""

from pathlib import Path

from virtual_factory.balance.basic_balance import MassBalance
from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine


def test_mass_balance_returns_expected_keys() -> None:
    """Mass balance result should contain all required fields after a step."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.step()

    result = engine.state.diagnostics.get("mass_balance", {})

    assert isinstance(result, dict)
    assert "mass_in_kg" in result
    assert "mass_out_kg" in result
    assert "mass_stored_before_kg" in result
    assert "mass_stored_after_kg" in result
    assert "mass_stored_delta_kg" in result
    assert "residual_kg" in result
    assert "residual_pct" in result
    assert "balanced" in result
    assert "message" in result


def test_mass_balance_is_balanced_after_second_step() -> None:
    """Balance report is a snapshot on first step; real balance starts from step 2."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)

    # First step: snapshot, no real balance
    engine.step()
    result1 = engine.state.diagnostics.get("mass_balance", {})
    assert result1.get("mass_stored_before_kg") is None  # snapshot indicator
    assert result1.get("balanced") is True

    # Second step onward: real balance
    for i in range(10):
        engine.step()
        result = engine.state.diagnostics.get("mass_balance", {})
        assert result.get("balanced") is True, (
            f"Step {i+2}: imbalance {result.get('residual_pct')}% — "
            f"residual_kg={result.get('residual_kg')}"
        )


def test_mass_balance_with_pump_off() -> None:
    """With pump off, mass_in is zero; outlet demand still draws mass."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.initialize()
    engine.state.set_truth("P101.running", False)

    # Step 1: snapshot
    engine.step()
    # Step 2: real balance
    engine.step()
    result = engine.state.diagnostics.get("mass_balance", {})

    assert result.get("mass_in_kg") == 0.0
    # Even with pump off, T102 outlet demand still drains the tank.


def test_mass_balance_can_be_evaluated_directly() -> None:
    """MassBalance can be instantiated and called without the engine."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.initialize()
    engine.state.set_truth("T101.volume_true", 8.0)
    engine.state.set_truth("T101.level_true", 4.0)
    engine.state.set_truth("T102.volume_true", 1.6)
    engine.state.set_truth("T102.level_true", 1.0)
    engine.state.set_truth("V101.outlet.flow_true", 0.012)
    engine.state.set_truth("T102.inflow_true", 0.012)
    engine.state.set_truth("T102.outflow_true", 0.006)

    bal = MassBalance(config)
    result = bal.evaluate(engine.state, dt_s=1.0)

    assert "balanced" in result
    assert isinstance(result["balanced"], bool)
