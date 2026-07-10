"""Tests for VF-2 transform evaluator (ST05)."""

from __future__ import annotations

import random

import pytest

from simulators.vf2.transform_evaluator import evaluate_transform


class TestTransformEvaluator:

    # AC-6
    def test_simple_input(self):
        rng = random.Random(42)
        val = evaluate_transform("input * 2.0", {"input": 5.0}, rng)
        assert val == 10.0

    def test_clamp(self):
        rng = random.Random(42)
        assert evaluate_transform("clamp(5, 0, 10)", {}, rng) == 5.0
        assert evaluate_transform("clamp(15, 0, 10)", {}, rng) == 10.0
        assert evaluate_transform("clamp(-5, 0, 10)", {}, rng) == 0.0

    def test_noise_within_range(self):
        rng = random.Random(42)
        values = [evaluate_transform("noise(50, 5)", {}, rng) for _ in range(100)]
        assert all(30 <= v <= 70 for v in values)  # Within ~4σ

    def test_math_functions(self):
        rng = random.Random(42)
        assert evaluate_transform("abs(-5)", {}, rng) == 5.0
        assert evaluate_transform("max(3, 7)", {}, rng) == 7.0
        assert evaluate_transform("sqrt(16)", {}, rng) == 4.0
        assert evaluate_transform("min(3, 7)", {}, rng) == 3.0
        assert evaluate_transform("round(3.7)", {}, rng) == 4.0

    # AC-7
    def test_rejects_dangerous_code(self):
        rng = random.Random(42)
        with pytest.raises(Exception):
            evaluate_transform("__import__('os').system('ls')", {}, rng)

    def test_rejects_open(self):
        rng = random.Random(42)
        with pytest.raises(Exception):
            evaluate_transform("open('/etc/passwd')", {}, rng)

    def test_multi_variable(self):
        rng = random.Random(42)
        ns = {"A": 10.0, "B": 3.0}
        assert evaluate_transform("A + B * 2", ns, rng) == 16.0

    def test_pi_constant(self):
        rng = random.Random(42)
        import math
        assert evaluate_transform("pi", {}, rng) == math.pi
