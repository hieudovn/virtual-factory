"""Tests for VF-2 dynamic SignalRegistry (ST03)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from simulators.vf2.models import (
    VF2SignalBehavior,
    VF2SignalDirection,
    VF2SignalType,
    VF2SimulationSignal,
)
from simulators.vf2.package_loader import load_package
from simulators.vf2.signal_registry import SignalRegistry

GOLDEN = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "sample_pim_package.json"
)


@pytest.fixture(scope="module")
def pkg():
    return load_package(GOLDEN)


@pytest.fixture(scope="module")
def reg(pkg):
    return SignalRegistry(pkg)


class TestSignalRegistry:

    # AC-4
    def test_from_package(self, reg, pkg):
        assert reg.signal_count == len(pkg.signals)
        assert reg.signal_count == 4

    # AC-5
    def test_get_existing(self, reg):
        sid = "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER"
        sig = reg.get(sid)
        assert sig is not None
        assert sig.data_type == "float64"
        assert sig.engineering_unit == "m3/h"

    def test_get_nonexistent(self, reg):
        assert reg.get("NONEXISTENT.SIGNAL") is None

    def test_all_signal_ids(self, reg):
        ids = reg.all_signal_ids
        assert len(ids) == 4
        assert all(id_.startswith("VF2.") for id_ in ids)

    def test_filter_by_direction(self, reg):
        inputs = reg.filter_by_direction(VF2SignalDirection.VF2_INPUT)
        assert len(inputs) == 4  # All 4 are VF2_INPUT in golden fixture

    def test_filter_by_signal_type(self, reg):
        measurements = reg.filter_by_signal_type(VF2SignalType.MEASUREMENT)
        assert len(measurements) == 4

    # AC-6
    def test_filter_by_asset(self, reg):
        sigs = reg.filter_by_asset("ASSET-REF-PMP-101A")
        assert len(sigs) == 3  # FT-101, PT-101, VB-101

    def test_filter_by_asset_unit(self, reg):
        sigs = reg.filter_by_asset("UNIT-REF-PUMP-STATION-01")
        assert len(sigs) == 1  # LT-101

    def test_filter_by_instrument(self, reg):
        sigs = reg.filter_by_instrument("INST-REF-FT-101")
        assert len(sigs) == 1
        assert sigs[0].name == "Discharge Flow Transmitter"

    # AC-7
    def test_default_behavior_measurement(self, reg):
        sid = "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER"
        sig = reg.get(sid)
        assert sig is not None
        behavior = reg.get_default_behavior(sig)
        assert behavior["type"] == "random_walk"
        assert "baseline" in behavior
        assert "noise_std" in behavior

    # AC-8
    def test_default_behavior_status(self, reg):
        sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.STATUS_SIG",
            canonical_asset_id="ASSET-REF-PMP-101A",
            name="Test Status",
            direction=VF2SignalDirection.VF2_OUTPUT,
            behavior=VF2SignalBehavior(
                signal_type=VF2SignalType.STATUS,
                initial_value=True,
            ),
        )
        # Build a minimal registry containing just this signal
        mini_reg = SignalRegistry.__new__(SignalRegistry)
        mini_reg._by_id = {sig.simulation_signal_id: sig}
        behavior = mini_reg.get_default_behavior(sig)
        assert behavior["type"] == "constant"
        assert behavior["value"] is True

    def test_default_behavior_alarm(self, reg):
        sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.ALARM_SIG",
            canonical_asset_id="ASSET-REF-PMP-101A",
            name="Test Alarm",
            direction=VF2SignalDirection.VF2_OUTPUT,
            behavior=VF2SignalBehavior(signal_type=VF2SignalType.ALARM),
        )
        mini_reg = SignalRegistry.__new__(SignalRegistry)
        mini_reg._by_id = {sig.simulation_signal_id: sig}
        behavior = mini_reg.get_default_behavior(sig)
        assert behavior["type"] == "constant"
        assert behavior["value"] is False

    def test_default_behavior_setpoint(self, reg):
        sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.SP_SIG",
            canonical_asset_id="ASSET-REF-PMP-101A",
            name="Test Setpoint",
            direction=VF2SignalDirection.VF2_OUTPUT,
            behavior=VF2SignalBehavior(
                signal_type=VF2SignalType.SETPOINT,
                initial_value=42.0,
            ),
        )
        mini_reg = SignalRegistry.__new__(SignalRegistry)
        mini_reg._by_id = {sig.simulation_signal_id: sig}
        behavior = mini_reg.get_default_behavior(sig)
        assert behavior["type"] == "constant"
        assert behavior["value"] == 42.0

    def test_default_behavior_feedback(self, reg):
        sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.FB_SIG",
            canonical_asset_id="ASSET-REF-PMP-101A",
            name="Test Feedback",
            direction=VF2SignalDirection.VF2_INPUT,
            behavior=VF2SignalBehavior(signal_type=VF2SignalType.FEEDBACK),
        )
        mini_reg = SignalRegistry.__new__(SignalRegistry)
        mini_reg._by_id = {sig.simulation_signal_id: sig}
        behavior = mini_reg.get_default_behavior(sig)
        assert behavior["type"] == "dependent"

    # Convenience properties
    def test_input_signals(self, reg):
        assert len(reg.input_signals) == 4

    def test_output_signals(self, reg):
        assert len(reg.output_signals) == 0

    def test_measurement_signals(self, reg):
        assert len(reg.measurement_signals) == 4

    def test_status_signals(self, reg):
        assert len(reg.status_signals) == 0

    # AC-9
    def test_no_hardcoded_signals(self, reg):
        """VF-2 MUST NOT have hardcoded signal IDs."""
        assert reg.signal_count == len(
            load_package(GOLDEN).signals
        ), "Registry should only know what's in the package"
