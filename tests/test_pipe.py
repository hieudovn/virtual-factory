"""Tests for pipe equipment model."""

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.equipment.pipe import Pipe
from virtual_factory.core.schema import EquipmentConfig


def test_pipe_initializes_truth() -> None:
    """Pipe should initialize pressure drop, flow, and velocity truths."""
    config = EquipmentConfig(
        id="PIPE01",
        model_type="pipe_v1",
        parameters={"length_m": 20.0, "diameter_m": 0.1},
    )
    pipe = Pipe(config)
    state = RuntimeState()
    pipe.initialize_state(state)

    assert state.get_truth("PIPE01.pressure_drop_kpa") == 0.0
    assert state.get_truth("PIPE01.flow_true") == 0.0
    assert state.get_truth("PIPE01.velocity_m_s") == 0.0


def test_pipe_resistance_is_positive() -> None:
    """A pipe should have positive flow resistance."""
    config = EquipmentConfig(
        id="PIPE01",
        model_type="pipe_v1",
        parameters={"length_m": 50.0, "diameter_m": 0.05},
    )
    pipe = Pipe(config)
    K = pipe.resistance_k(density_kg_m3=997.0, viscosity_pa_s=0.00089)

    assert K > 0


def test_longer_pipe_has_higher_resistance() -> None:
    """A longer pipe of the same diameter should have higher resistance."""
    short = Pipe(EquipmentConfig(
        id="SHORT", model_type="pipe_v1",
        parameters={"length_m": 10.0, "diameter_m": 0.05},
    ))
    long = Pipe(EquipmentConfig(
        id="LONG", model_type="pipe_v1",
        parameters={"length_m": 100.0, "diameter_m": 0.05},
    ))

    assert long.resistance_k(997.0, 0.00089) > short.resistance_k(997.0, 0.00089)


def test_wider_pipe_has_lower_resistance() -> None:
    """A wider pipe of the same length should have lower resistance."""
    narrow = Pipe(EquipmentConfig(
        id="NARROW", model_type="pipe_v1",
        parameters={"length_m": 50.0, "diameter_m": 0.025},
    ))
    wide = Pipe(EquipmentConfig(
        id="WIDE", model_type="pipe_v1",
        parameters={"length_m": 50.0, "diameter_m": 0.1},
    ))

    assert wide.resistance_k(997.0, 0.00089) < narrow.resistance_k(997.0, 0.00089)
