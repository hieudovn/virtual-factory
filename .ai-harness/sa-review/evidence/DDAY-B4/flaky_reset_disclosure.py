#!/usr/bin/env python3
"""DDAY-B4 — disclosure evidence for the pre-existing flaky reset test.

The B4 regression subset run failed once and passed on rerun. The failing test is
the already-disclosed pre-existing flake in `tests/test_demo_composition.py`:

    TestReset::test_reset_creates_fresh_configs   (disclosed in DDAY-B3)
    TestReset::test_reset_creates_fresh_runtimes  (observed in DDAY-B4)

Both assert that the `id()` values collected before and after `reset()` are
disjoint:

    old_ids = {id(ctx.config) for ctx in comp.contexts.values()}
    comp.reset()
    new_ids = {id(ctx.config) for ctx in comp.contexts.values()}
    assert old_ids.isdisjoint(new_ids)

`id()` is a memory address. After `reset()` the previous objects become
unreachable, so CPython may hand the same addresses to their replacements. The
assertion is therefore not guaranteed — a genuine pre-existing flake, not a B4
regression. This is why `generate_evidence.py` records a rerun.

This script demonstrates the mechanism deterministically (no reliance on luck).

SA Issue #105 places this outside B4 §13: "unrelated harness/flaky-test cleanup".

Usage:  python flaky_reset_disclosure.py
Exit 0 = mechanism demonstrated.
"""

from __future__ import annotations

import gc
import sys


def demonstrate_id_reuse() -> dict:
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
    """Repeat the exact set operation the flaky tests perform, many times."""
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
    print("DDAY-B4 — pre-existing flaky reset test: root-cause disclosure")
    print("=" * 72)

    reuse = demonstrate_id_reuse()
    print("\n[1] id() reuse after objects become unreachable")
    print(f"    overlapping ids between two equal-sized samples: "
          f"{reuse['overlapping_ids']}")
    print(f"    ids reused: {reuse['ids_reused']}")

    flake = demonstrates_non_disjoint_possible()
    print("\n[2] the exact set operation the flaky tests perform")
    print(f"    attempts: {flake['attempts']}")
    print(f"    disjoint (assertion would pass): {flake['disjoint']}")
    print(f"    overlapping (assertion would fail): {flake['overlapping']}")
    print(f"    example overlapping ids: {flake['example_overlapping_ids']}")

    print("\n[3] the assertions under test")
    print("    assert old_config_ids.isdisjoint(new_config_ids)")
    print("    assert old_runtime_ids.isdisjoint(new_runtime_ids)")
    print("    observed in this session: 1 failure on the first regression")
    print("    subset run, 164/164 pass on rerun, and 1716/1716 on the full")
    print("    suite (see junit-b4-regression*.xml and junit-b4-full.xml).")

    print("\n[4] scope")
    print("    tests/test_demo_composition.py is unrelated to DDAY-B4.")
    print("    SA Issue #105 §13: do not do unrelated flaky-test cleanup in B4.")

    print("\n" + "=" * 72)
    if reuse["ids_reused"]:
        print("MECHANISM DEMONSTRATED — the assertion is not guaranteed")
        print("=" * 72)
        return 0
    print("MECHANISM NOT DEMONSTRATED")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
