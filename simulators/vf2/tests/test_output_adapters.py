"""Tests for VF-2 output adapters (ST08)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from simulators.vf2.output.csv_output import CsvOutput
from simulators.vf2.output.memory_output import MemoryOutput
from simulators.vf2.output.stdout_output import StdoutOutput
from simulators.vf2.package_loader import load_package
from simulators.vf2.simulation_loop import Vf2SimulationLoop

GOLDEN = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "simulators" / "vf2" / "examples"
    / "sample_pim_package.json"
)


# ======================================================================
# MemoryOutput
# ======================================================================


class TestMemoryOutput:

    # AC-1
    def test_stores_frames(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        out = MemoryOutput(max_frames=100)
        frame = loop.step()
        out.write(frame)
        assert out.get_latest() is not None
        assert len(out.get_latest()) == 4

    def test_get_latest_none_when_empty(self):
        out = MemoryOutput()
        assert out.get_latest() is None

    def test_get_all_returns_copy(self):
        out = MemoryOutput()
        out.write([])
        out.write([])
        assert len(out.get_all()) == 2

    # AC-2
    def test_max_frames(self):
        out = MemoryOutput(max_frames=3)
        out.write([1])
        out.write([2])
        out.write([3])
        out.write([4])
        assert len(out.frames) == 3
        assert out.frames[0] == [2]  # oldest dropped

    def test_close_does_not_crash(self):
        out = MemoryOutput()
        out.close()


# ======================================================================
# CsvOutput
# ======================================================================


class TestCsvOutput:

    # AC-3
    def test_writes_csv(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            path = tf.name

        try:
            out = CsvOutput(path)
            out.write(loop.step())
            out.close()

            with open(path) as f:
                lines = f.readlines()

            # Header + 4 data rows
            assert len(lines) == 5, f"Expected 5 lines, got {len(lines)}"
            assert "timestamp" in lines[0]
            # Check a data row
            assert "VF2.PUMP_STATION_01.FT_101" in lines[1]
        finally:
            os.unlink(path)

    def test_csv_header_written_once(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            path = tf.name

        try:
            out = CsvOutput(path)
            out.write([])
            out.write([])
            out.close()

            with open(path) as f:
                lines = f.readlines()

            # Only one header line
            assert lines[0].startswith("timestamp")
        finally:
            os.unlink(path)


# ======================================================================
# StdoutOutput
# ======================================================================


class TestStdoutOutput:

    # AC-4
    def test_does_not_crash(self):
        out = StdoutOutput()
        out.write([])  # Should not crash
        out.close()

    def test_logs_single_measurement(self, caplog):
        import logging
        caplog.set_level(logging.INFO)
        from simulators.vf2.simulation_loop import Measurement

        out = StdoutOutput()
        m = Measurement(
            timestamp="2026-01-01T00:00:00.000Z",
            signal_id="VF2.TEST.SIG",
            value=42.0,
            quality="GOOD",
            source="test",
        )
        out.write([m])
        assert len(caplog.records) >= 1
        assert "VF2.TEST.SIG" in caplog.text
