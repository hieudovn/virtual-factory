"""Test the clarification engine with known inputs."""

import random

from ..clarification_engine import compute_stage3_clarification


def test_normal_operation():
    result = compute_stage3_clarification(
        raw_turbidity=45.0, raw_ph=7.15,
        coag_dose_rate=25.0, ph_pump_flow=5.0,
        mixer_speed=300, flocculator_speed=40,
        rng=random.Random(42),
    )
    # At optimal settings: ~85% turbidity removal
    # 45 * 0.15 ≈ 6.75 NTU (with noise ~0.3)
    assert 5.0 <= result["settled_turbidity"] <= 8.5, f"Got {result['settled_turbidity']}"
    assert 6.8 <= result["settled_ph"] <= 7.3, f"Got {result['settled_ph']}"
    assert 2.5 <= result["floc_size_index"] <= 4.5, f"Got {result['floc_size_index']}"


def test_low_coagulant_dose():
    result = compute_stage3_clarification(
        raw_turbidity=45.0, raw_ph=7.15,
        coag_dose_rate=8.0,  # LOW dose
        ph_pump_flow=5.0, mixer_speed=300, flocculator_speed=40,
        rng=random.Random(42),
    )
    # Low dose → poor removal
    assert result["settled_turbidity"] > 15.0, f"Expected high turbidity, got {result['settled_turbidity']}"


def test_high_raw_turbidity():
    result = compute_stage3_clarification(
        raw_turbidity=100.0,  # VERY turbid
        raw_ph=7.15,
        coag_dose_rate=25.0, ph_pump_flow=5.0,
        mixer_speed=300, flocculator_speed=40,
        rng=random.Random(42),
    )
    # Harder to treat → still high after treatment
    assert result["settled_turbidity"] > 10.0, f"Got {result['settled_turbidity']}"


def test_missing_coagulant():
    result = compute_stage3_clarification(
        raw_turbidity=45.0, raw_ph=7.15,
        coag_dose_rate=0.0, ph_pump_flow=0.0,
        mixer_speed=0, flocculator_speed=0,
        rng=random.Random(42),
    )
    # No coagulant → almost no removal
    assert result["settled_turbidity"] > 30.0


if __name__ == "__main__":
    test_normal_operation()
    test_low_coagulant_dose()
    test_high_raw_turbidity()
    test_missing_coagulant()
    print("All clarification engine tests passed!")
