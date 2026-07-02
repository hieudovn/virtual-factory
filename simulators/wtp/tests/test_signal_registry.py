"""Test the signal registry."""

from ..signal_registry import SignalRegistry
from ..models import SignalType


def test_registry_counts():
    registry = SignalRegistry()
    assert len(registry.DV_CONFIGS) == 7, f"Expected 7 DVs, got {len(registry.DV_CONFIGS)}"
    assert len(registry.MV_CONFIGS) == 12, f"Expected 12 MVs, got {len(registry.MV_CONFIGS)}"
    assert len(registry.PV_SIGNALS) == 43, f"Expected 43 PVs, got {len(registry.PV_SIGNALS)}"
    assert len(registry.KPI_SIGNALS) == 30, f"Expected 30 KPIs, got {len(registry.KPI_SIGNALS)}"
    assert len(registry.all_signal_ids) == 92, f"Expected 92 total, got {len(registry.all_signal_ids)}"


def test_signal_types():
    registry = SignalRegistry()
    assert registry.get_signal_type("RAW-WATER-QUALITY-STATION-101.raw_turbidity") == SignalType.DV
    assert registry.get_signal_type("COAG-PUMP-101.flow_rate") == SignalType.MV
    assert registry.get_signal_type("CLARIFIER-101.settled_turbidity") == SignalType.PV
    assert registry.get_signal_type("PLANT-KPI-101.cost_per_m3") == SignalType.KPI
    assert registry.get_signal_type("nonexistent") is None


def test_mv_config():
    registry = SignalRegistry()
    cfg = registry.get_mv_config("COAG-PUMP-101.flow_rate")
    assert cfg is not None
    assert cfg.default_sp == 12.0
    assert cfg.min_sp == 5.0
    assert cfg.max_sp == 25.0
    assert cfg.slew_rate == 2.0


def test_dv_config():
    registry = SignalRegistry()
    cfg = registry.get_dv_config("RAW-WATER-QUALITY-STATION-101.raw_turbidity")
    assert cfg is not None
    assert cfg.baseline == 45.0
    assert cfg.bounds_min == 10.0
    assert cfg.bounds_max == 120.0


if __name__ == "__main__":
    test_registry_counts()
    test_signal_types()
    test_mv_config()
    test_dv_config()
    print("All signal registry tests passed!")
