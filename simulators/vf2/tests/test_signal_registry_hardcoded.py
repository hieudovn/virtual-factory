"""Negative tests: VF-2 SignalRegistry must NOT have hardcoded signal lists.

VF-1's ``signal_registry.py`` has class-level ``DV_CONFIGS``, ``MV_CONFIGS``,
``PV_SIGNALS``, and ``KPI_SIGNALS``.  VF-2 is fully dynamic — everything
comes from the PIM package.
"""

from __future__ import annotations


def test_no_hardcoded_dv_configs():
    """VF-2 SignalRegistry must NOT have class-level DV_CONFIGS."""
    from simulators.vf2.signal_registry import SignalRegistry

    assert not hasattr(SignalRegistry, "DV_CONFIGS"), (
        "VF-2 must not have hardcoded DV_CONFIGS — use package data"
    )


def test_no_hardcoded_mv_configs():
    """VF-2 SignalRegistry must NOT have class-level MV_CONFIGS."""
    from simulators.vf2.signal_registry import SignalRegistry

    assert not hasattr(SignalRegistry, "MV_CONFIGS"), (
        "VF-2 must not have hardcoded MV_CONFIGS — use package data"
    )


def test_no_hardcoded_pv_signals():
    """VF-2 SignalRegistry must NOT have class-level PV_SIGNALS."""
    from simulators.vf2.signal_registry import SignalRegistry

    assert not hasattr(SignalRegistry, "PV_SIGNALS"), (
        "VF-2 must not have hardcoded PV_SIGNALS — use package data"
    )


def test_no_hardcoded_kpi_signals():
    """VF-2 SignalRegistry must NOT have class-level KPI_SIGNALS."""
    from simulators.vf2.signal_registry import SignalRegistry

    assert not hasattr(SignalRegistry, "KPI_SIGNALS"), (
        "VF-2 must not have hardcoded KPI_SIGNALS — use package data"
    )


def test_no_hardcoded_all_signal_ids():
    """VF-2 SignalRegistry must NOT have class-level all_signal_ids list."""
    from simulators.vf2.signal_registry import SignalRegistry

    # Instance properties are fine; class-level constant lists are not
    s = SignalRegistry.__new__(SignalRegistry)
    s._by_id = {}
    ids = s.all_signal_ids
    assert ids == [], "all_signal_ids should come from package data, not a class constant"

