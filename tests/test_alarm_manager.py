from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.telemetry.alarm_manager import AlarmManager


def _alarm_value(outputs, name: str) -> bool:
    return next(signal.value for signal in outputs if signal.name == name)


def test_low_level_alarm_becomes_true_from_measured_signal() -> None:
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    state = RuntimeState()
    state.set_signal_value("LT102_LEVEL", 0.25, timestamp_s=1.0, unit="m", source="LT102")

    outputs = AlarmManager(config.alarms).evaluate(state, config, timestamp_s=1.0)

    assert _alarm_value(outputs, "T102_LOW_LEVEL_ALARM") is True


def test_high_level_alarm_becomes_true_from_measured_signal() -> None:
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    state = RuntimeState()
    state.set_signal_value("LT102_LEVEL", 4.75, timestamp_s=1.0, unit="m", source="LT102")

    outputs = AlarmManager(config.alarms).evaluate(state, config, timestamp_s=1.0)

    assert _alarm_value(outputs, "T102_HIGH_LEVEL_ALARM") is True


def test_no_flow_alarm_becomes_true_from_measured_signal() -> None:
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    state = RuntimeState()
    state.set_signal_value("FT101_FLOW", 0.0, timestamp_s=1.0, unit="m3/s", source="FT101")

    outputs = AlarmManager(config.alarms).evaluate(state, config, timestamp_s=1.0)

    assert _alarm_value(outputs, "P101_NO_FLOW_ALARM") is True


def test_bad_quality_alarm_becomes_true() -> None:
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    state = RuntimeState()
    state.set_signal_value("LT102_LEVEL", 1.0, timestamp_s=1.0, unit="m", quality="BAD", source="LT102")

    outputs = AlarmManager(config.alarms).evaluate(state, config, timestamp_s=1.0)

    assert _alarm_value(outputs, "LT102_BAD_QUALITY_ALARM") is True


def test_alarm_outputs_are_industrial_event_signal_values() -> None:
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    state = RuntimeState()
    state.set_signal_value("LT102_LEVEL", 0.25, timestamp_s=1.0, unit="m", source="LT102")

    outputs = AlarmManager(config.alarms).evaluate(state, config, timestamp_s=1.0)

    low_alarm = next(signal for signal in outputs if signal.name == "T102_LOW_LEVEL_ALARM")
    assert low_alarm.category == "industrial_event"
    assert low_alarm.unit == "bool"


def test_alarm_manager_does_not_read_internal_truth() -> None:
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    state = RuntimeState()
    state.set_truth("T102.level_true", 0.1)
    state.set_signal_value("LT102_LEVEL", 1.0, timestamp_s=1.0, unit="m", source="LT102")

    outputs = AlarmManager(config.alarms).evaluate(state, config, timestamp_s=1.0)

    assert _alarm_value(outputs, "T102_LOW_LEVEL_ALARM") is False
