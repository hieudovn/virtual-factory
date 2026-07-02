"""Test the disinfection engine."""

import random

from ..disinfection_engine import compute_stage5_disinfection


def test_normal_operation():
    result = compute_stage5_disinfection(
        chlorine_dose_rate=4.5,
        raw_ammonia=0.5,
        raw_algae_index=3.0,
        contact_time=30.0,
        rng=random.Random(42),
    )
    assert 0.5 <= result["free_chlorine"] <= 2.5, f"Got {result['free_chlorine']}"
    assert result["total_chlorine"] > 0, f"Got {result['total_chlorine']}"
    assert result["orp"] > 400, f"Got {result['orp']}"


def test_high_ammonia():
    result = compute_stage5_disinfection(
        chlorine_dose_rate=4.5,
        raw_ammonia=2.0,  # HIGH ammonia
        raw_algae_index=3.0,
        contact_time=30.0,
        rng=random.Random(42),
    )
    # High ammonia consumes chlorine → lower free chlorine
    assert result["free_chlorine"] < 1.0, f"Expected low free chlorine, got {result['free_chlorine']}"


def test_low_dose():
    result = compute_stage5_disinfection(
        chlorine_dose_rate=0.5,  # Very low dose
        raw_ammonia=0.5,
        raw_algae_index=3.0,
        contact_time=30.0,
        rng=random.Random(42),
    )
    assert result["free_chlorine"] < 0.5, f"Expected very low free chlorine, got {result['free_chlorine']}"
    assert result["disinfection_ok"] == False


if __name__ == "__main__":
    test_normal_operation()
    test_high_ammonia()
    test_low_dose()
    print("All disinfection engine tests passed!")
