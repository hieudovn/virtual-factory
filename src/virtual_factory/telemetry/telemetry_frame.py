"""Build publishable industrial telemetry frames from runtime state."""

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig, SignalConfig
from virtual_factory.telemetry.output_policy import OutputPolicy
from virtual_factory.telemetry.signal_value import SignalValue


def build_publishable_frame(
    config: PlantConfig,
    state: RuntimeState,
    policy: OutputPolicy,
    timestamp_s: float,
) -> list[SignalValue]:
    """Return policy-allowed signal values for external publication."""
    frame: list[SignalValue] = []
    for signal_name, signal_config in config.signals.items():
        if not policy.can_publish(signal_config):
            continue
        current_value = state.get_signal_value(signal_name)
        if current_value is None:
            continue
        frame.append(_coerce_signal_value(signal_name, current_value, signal_config, timestamp_s))
    return frame


def _coerce_signal_value(
    name: str,
    current_value: object,
    signal_config: SignalConfig,
    timestamp_s: float,
) -> SignalValue:
    if isinstance(current_value, SignalValue):
        return SignalValue(
            name=name,
            value=current_value.value,
            unit=current_value.unit or signal_config.unit,
            category=signal_config.category,
            quality=current_value.quality,
            timestamp_s=current_value.timestamp_s,
            source=current_value.source or signal_config.source,
        )
    return SignalValue(
        name=name,
        value=current_value,
        unit=signal_config.unit,
        category=signal_config.category,
        quality="GOOD",
        timestamp_s=timestamp_s,
        source=signal_config.source,
    )
