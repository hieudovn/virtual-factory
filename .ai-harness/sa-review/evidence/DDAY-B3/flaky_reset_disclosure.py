#!/usr/bin/env python3
"""DDAY-B3 — disclosure evidence for the pre-existing flaky reset test.

`tests/test_demo_composition.py::TestReset::test_reset_creates_fresh_configs`
asserts that the `id()` values of the per-context config objects before and after
`reset()` are disjoint:

    old_config_ids = {id(ctx.config) for ctx in comp.contexts.values()}
    comp.reset()
    new_config_ids = {id(ctx.config) for ctx in comp.contexts.values()}
    assert old_config_ids.isdisjoint(new_config_ids)

`id()` is a memory address, and after `reset()` the previous config objects become
unreachable, so CPython is free to hand the same addresses to the replacements.
The assertion is therefore not guaranteed — it is a genuine pre-existing flake,
not a B3 regression.

This script demonstrates the mechanism deterministically (no reliance on luck),
and is also an assertion-level reproduction of the failure condition.

SA Issue #104 explicitly places this outside B3: "do not fix the unrelated flaky
reset test or PR-state normalization debt inside B3."

Usage:  python flaky_reset_disclosure.py
Exit 0 = mechanism demonstrated.
"""

from __future__ import annotations

import gc
import sys


def demonstrate_id_reuse(iterations: int = 2000) -> dict:
    """Show that id() values are reused once objects become unreachable."""

    def build() -> list[int]:
        return [id(object()) for _ in range(64)]

    first = build()
    gc.collect()
    second = build()
    overlap = set(first) & set(second)
    return {
        "first_sample_size": len(first),
        "second_sample_size": len(second),
        "overlapping_ids": len(overlap),
        "ids_reused": len(overlap) > 0,
    }


def demonstrates_non_disjoint_possible(attempts: int = 500) -> dict:
    """Repeat the exact set operation the test performs, many times."""
    disjoint = 0
    overlapping = 0
    example_overlap: list[int] = []

    for _ in range(attempts):
        old_ids = {id(object()) for _ in range(6)}
        gc.collect()
        new_ids = {id(object()) for _ in range(6)}
        if old_ids.isdisjoint(new_ids):
            disjoint += 1
        else:
            overlapping += 1
            if not example_overlap:
                example_overlap = sorted(old_ids & new_ids)
        gc.collect()

    return {
        "attempts": attempts,
        "disjoint": disjoint,
        "overlapping": overlapping,
        "flaked": overlapping > 0,
        "example_overlapping_ids": example_overlap,
    }


def main() -> int:
    print("=" * 72)
    print("DDAY-B3 — pre-existing flaky reset test: root-cause disclosure")
    print("=" * 72)

    reuse = demonstrate_id_reuse()
    print("\n[1] id() reuse after objects become unreachable")
    print(f"    overlapping ids between two equal-sized samples: {reuse['overlapping_ids']}")
    print(f"    ids reused: {reuse['ids_reused']}")

    flake = demonstrates_non_disjoint_possible()
    print("\n[2] the exact set operation the flaky test performs")
    print(f"    attempts: {flake['attempts']}")
    print(f"    disjoint (assertion would pass): {flake['disjoint']}")
    print(f"    overlapping (assertion would fail): {flake['overlapping']}")
    print(f"    example overlapping ids: {flake['example_overlapping_ids']}")

    expected = "assert old_config_ids.isdisjoint(new_config_ids)"
    print("\n[3] the assertion under test")
    print(f"    {expected}")
    print("    observed failure in this session (junit evidence):"
          " `assert False where False = <built-in method isdisjoint ...>`")

    print("\n[4] scope")
    print("    tests/test_demo_composition.py is outside the DDAY-B3 allowlist.")
    print("    SA Issue #104: do not fix the unrelated flaky reset test inside B3.")

    print("\n" + "=" * 72)
    if reuse["ids_reused"]:
        print("MECHANISM DEMONSTRATED — the assertion is not guaranteed")
        print("=" * 72)
        return 0
    print("MECHANISM NOT DEMONSTRATED")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
