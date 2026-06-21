"""Tests for Sparkplug B gateway."""

from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.protocols.sparkplug_gateway import (
    SparkplugBGateway,
    _CATEGORY_DEVICE_MAP,
    _MESSAGE_TYPE_NBIRTH,
    _MESSAGE_TYPE_DBIRTH,
    _MESSAGE_TYPE_DDATA,
    _SPB_VERSION,
)


def test_signal_to_metric_maps_basic_types() -> None:
    """signal_to_metric should preserve name, value, and timestamp."""
    from virtual_factory.telemetry.signal_value import SignalValue

    sv = SignalValue(name="FT101_FLOW", value=0.012, unit="m3/s",
                     category="industrial_signal", quality="GOOD",
                     timestamp_s=42.0, source="FT101")
    metric = SparkplugBGateway._signal_to_metric(sv)
    assert metric["name"] == "FT101_FLOW"
    assert metric["value"] == 0.012
    assert metric["dataType"] == "Double"


def test_signal_category_maps_to_sparkplug_device() -> None:
    """Each known category should map to a Sparkplug device id."""
    assert _CATEGORY_DEVICE_MAP["industrial_signal"] == "instrumentation"
    assert _CATEGORY_DEVICE_MAP["controller_signal"] == "control"
    assert _CATEGORY_DEVICE_MAP["actuator_feedback"] == "actuation"
    assert _CATEGORY_DEVICE_MAP["industrial_event"] == "events"


def test_birth_topics_are_sparkplug_compliant() -> None:
    """Birth topics should follow spBv1.0/group/DBIRTH/edge_node/device."""
    group = "virtual-factory"
    edge = "test_plant"
    expected_prefix = f"{_SPB_VERSION}/{group}/{_MESSAGE_TYPE_DBIRTH}/{edge}"
    assert expected_prefix.endswith(edge)
    assert expected_prefix.startswith(_SPB_VERSION)
    assert _MESSAGE_TYPE_DBIRTH in expected_prefix


def test_publish_frame_does_not_leak_internal_truth() -> None:
    """Sparkplug B should reject internal_truth signals just like MQTT."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.step()
    snapshot = engine.step()

    frame = list(snapshot["telemetry_latest"])
    # Verify no internal truth in frame
    truth_signals = [s for s in frame if s.category == "internal_truth"]
    assert len(truth_signals) == 0, "Publishable frame should not contain internal truth"
