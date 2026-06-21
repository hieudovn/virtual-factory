"""Tests for output-policy guardrails in the simulation engine."""

import pytest
from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import OutputPolicyViolation, SimulationEngine

_CONFIG_PATH = "configs/plants/continuous_mvp_01.yaml"


def _engine_with_signal_override(override: dict) -> SimulationEngine:
    """Create an engine with a modified signal that might violate policy."""
    config = load_plant_config(_CONFIG_PATH)
    # Apply override to the first matching signal dict
    sig_name = override.get("name")
    if sig_name in config.signals:
        sig = config.signals[sig_name]
        if "category" in override:
            sig.category = override["category"]
        if "source" in override:
            sig.source = override["source"]
    return SimulationEngine(config)


def test_guardrail_passes_clean_config() -> None:
    """A standard MVP config should pass guardrail checks."""
    config = load_plant_config(_CONFIG_PATH)
    engine = SimulationEngine(config)
    engine.initialize()
    # Should not raise
    engine._check_output_policy()


def test_guardrail_blocks_internal_truth_publish() -> None:
    """Publishing internal_truth signal should raise OutputPolicyViolation."""
    engine = _engine_with_signal_override({
        "name": "LT102_LEVEL",
        "category": "internal_truth",
    })
    engine.initialize()
    with pytest.raises(OutputPolicyViolation, match="internal_truth"):
        engine._check_output_policy()


def test_guardrail_blocks_truth_in_source() -> None:
    """A signal with 'truth' in source should raise OutputPolicyViolation."""
    engine = _engine_with_signal_override({
        "name": "LT102_LEVEL",
        "source": "T102.level_true",
    })
    engine.initialize()
    with pytest.raises(OutputPolicyViolation, match="truth"):
        engine._check_output_policy()


def test_guardrail_fails_fast_before_step() -> None:
    """Step() should raise if config violates policy, before any execution."""
    engine = _engine_with_signal_override({
        "name": "LT102_LEVEL",
        "category": "internal_truth",
    })
    with pytest.raises(OutputPolicyViolation):
        engine.step()
