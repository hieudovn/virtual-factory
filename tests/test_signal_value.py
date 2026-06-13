from virtual_factory.telemetry.signal_value import SignalValue


def test_signal_value_can_be_created() -> None:
    """SignalValue should carry value, metadata, and timestamp."""
    signal = SignalValue(
        name="LT102_LEVEL",
        value=1.23,
        unit="m",
        category="industrial_signal",
        timestamp_s=12.0,
        source="LT102",
    )

    assert signal.name == "LT102_LEVEL"
    assert signal.value == 1.23
    assert signal.quality == "GOOD"


def test_signal_value_numeric_value_is_accessible() -> None:
    """Numeric telemetry should expose the raw numeric value."""
    signal = SignalValue(
        name="LIC102_OUT",
        value=42.0,
        unit="percent",
        category="controller_signal",
        timestamp_s=0.0,
    )

    assert float(signal.value) == 42.0
