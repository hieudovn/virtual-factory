"""Tests for VF-2 behavior engine (ST05)."""

from __future__ import annotations

import random

from simulators.vf2.behavior_engine import BehaviorEngine, BehaviorState


class TestBehaviorEngine:

    # AC-1
    def test_constant(self):
        engine = BehaviorEngine(None, random.Random(42))
        val = engine.step_one("test", 1.0, {"type": "constant", "value": 42.0}, {})
        assert val == 42.0

    def test_constant_default(self):
        engine = BehaviorEngine(None, random.Random(42))
        val = engine.step_one("test", 1.0, {"type": "constant"}, {})
        assert val == 0.0

    # AC-2
    def test_random_walk_stays_in_bounds(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "random_walk", "baseline": 50.0, "noise_std": 1.0,
            "bounds_min": 40.0, "bounds_max": 60.0,
        }
        values = [engine.step_one("rw", 1.0, behavior, {}) for _ in range(1000)]
        assert all(40.0 <= v <= 60.0 for v in values)

    def test_random_walk_mean_reversion(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "random_walk", "baseline": 50.0, "noise_std": 5.0,
            "bounds_min": 0.0, "bounds_max": 100.0,
        }
        # After many steps, mean should be near baseline
        values = [engine.step_one("rw2", 1.0, behavior, {}) for _ in range(5000)]
        mean = sum(values) / len(values)
        assert 40.0 <= mean <= 60.0, f"Mean {mean:.1f} drifted too far from 50"

    # AC-3
    def test_sine_oscillates(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "sine", "baseline": 50.0, "amplitude": 10.0,
            "frequency_hz": 1.0, "noise_std": 0.0,
        }
        values = [engine.step_one("s", 0.01, behavior, {}) for _ in range(100)]
        # Should oscillate above and below baseline
        assert min(values) < 50.0, f"Min {min(values):.1f} not below baseline"
        assert max(values) > 50.0, f"Max {max(values):.1f} not above baseline"

    def test_sine_zero_noise(self):
        """Without noise, sine should be perfectly periodic."""
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "sine", "baseline": 0.0, "amplitude": 1.0,
            "frequency_hz": 0.5, "noise_std": 0.0,
        }
        v0 = engine.step_one("s2", 0.0, behavior, {})
        v1 = engine.step_one("s2", 0.25, behavior, {})
        v2 = engine.step_one("s2", 0.25, behavior, {})
        assert v0 >= 0.0  # sin(0) = 0
        assert v1 != v2  # different phases

    # AC-4
    def test_degradation_drifts(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "degradation", "baseline": 100.0,
            "drift_rate_per_s": 1.0, "noise_std": 0.0,
        }
        v1 = engine.step_one("d", 10.0, behavior, {})
        v2 = engine.step_one("d", 10.0, behavior, {})
        assert v2 > v1, "Degradation should drift upward"
        # After 20s at 1.0/s → drift = 20, value = 120
        assert abs(v2 - 120.0) < 0.01

    def test_degradation_with_noise(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "degradation", "baseline": 100.0,
            "drift_rate_per_s": 0.5, "noise_std": 0.1,
        }
        values = [engine.step_one("d2", 1.0, behavior, {}) for _ in range(100)]
        assert values[-1] > values[0], "Should trend upward"
        assert values[0] >= 99.0  # near baseline

    # AC-5
    def test_dependent_simple(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "dependent", "depends_on": ["STATUS"],
            "transform": "input * 120.0",
        }
        val = engine.step_one("dep", 1.0, behavior, {"STATUS": 1.0})
        assert val == 120.0

    def test_dependent_with_noise(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {
            "type": "dependent", "depends_on": ["FLOW"],
            "transform": "input * 200 + noise(0, 5)",
        }
        val = engine.step_one("dep2", 1.0, behavior, {"FLOW": 1.5})
        assert 290 <= val <= 310  # 1.5*200 = 300 ± noise

    # AC-8
    def test_step_generates_all_signals(self):
        """Integration: step() should produce values for all signals."""
        from pathlib import Path

        from simulators.vf2.package_loader import load_package
        from simulators.vf2.signal_registry import SignalRegistry

        golden = (
            Path(__file__).resolve().parent.parent
            / "examples"
            / "sample_pim_package.json"
        )
        pkg = load_package(golden)
        sig_reg = SignalRegistry(pkg)
        engine = BehaviorEngine(sig_reg, random.Random(42))

        values = engine.step(1.0, {})
        assert len(values) == sig_reg.signal_count
        assert all(isinstance(v, (int, float)) for v in values.values())

    def test_step_repeatability(self):
        """Same seed → same sequence."""
        from pathlib import Path

        from simulators.vf2.package_loader import load_package
        from simulators.vf2.signal_registry import SignalRegistry

        golden = (
            Path(__file__).resolve().parent.parent
            / "examples"
            / "sample_pim_package.json"
        )
        pkg = load_package(golden)
        sig_reg = SignalRegistry(pkg)

        e1 = BehaviorEngine(sig_reg, random.Random(99))
        e2 = BehaviorEngine(sig_reg, random.Random(99))
        v1 = e1.step(1.0, {})
        v2 = e2.step(1.0, {})
        assert v1 == v2

    def test_behavior_state(self):
        state = BehaviorState("test_signal")
        assert state.signal_id == "test_signal"
        assert state.current_value == 0.0
        assert state.phase == 0.0
