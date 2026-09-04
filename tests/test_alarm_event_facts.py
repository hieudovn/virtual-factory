"""VF-vNEXT-G3 — AlarmManager alarm Event-fact production + compatibility tests.

Proves (Issue #48): existing AlarmManager thresholds/output ``SignalValue``
behavior stays compatible; AlarmManager produces immutable alarm Event facts for
activation/clear transitions under the smallest correct contract; AlarmState is
a mutable DERIVED projection that never mutates historical facts; runtime state
remains the sole mutable execution truth; emitted alarm facts fabricate no
G1/G2/PIM identity.
"""

from __future__ import annotations

from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.telemetry.alarm_manager import AlarmManager
from virtual_factory.telemetry.event_fact import EventCategory, EventFact

_CONFIG = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))


def _state_with_level(level: float, timestamp_s: float) -> RuntimeState:
    state = RuntimeState()
    state.set_signal_value(
        "LT102_LEVEL", level, timestamp_s=timestamp_s, unit="m", source="LT102"
    )
    return state


def _alarm_facts_for(manager: AlarmManager, alarm_id: str):
    return [
        fact
        for fact in manager.event_store
        if fact.to_dict().get("alarm", {}).get("alarm_id") == alarm_id
    ]


def test_existing_single_evaluation_behavior_compatible() -> None:
    """Legacy behavior: a single evaluate() still returns industrial_event bools."""
    state = _state_with_level(0.25, timestamp_s=1.0)  # low-level alarm active
    outputs = AlarmManager(_CONFIG.alarms).evaluate(state, _CONFIG, timestamp_s=1.0)
    low = next(s for s in outputs if s.name == "T102_LOW_LEVEL_ALARM")
    assert low.value is True
    assert low.category == "industrial_event"
    assert low.unit == "bool"


def test_baseline_evaluation_emits_no_fact() -> None:
    """A first observation establishes the baseline condition (no transition)."""
    manager = AlarmManager(_CONFIG.alarms)
    manager.evaluate(_state_with_level(0.25, 1.0), _CONFIG, timestamp_s=1.0)
    assert len(manager.event_store) == 0


def test_activation_and_clear_transitions_produce_alarm_facts() -> None:
    manager = AlarmManager(_CONFIG.alarms)
    # t=1: level 1.0 -> low-level alarm inactive (baseline established).
    manager.evaluate(_state_with_level(1.0, 1.0), _CONFIG, timestamp_s=1.0)
    assert len(_alarm_facts_for(manager, "T102_LOW_LEVEL")) == 0
    # t=2: level 0.25 -> activation transition.
    manager.evaluate(_state_with_level(0.25, 2.0), _CONFIG, timestamp_s=2.0)
    # t=3: level 0.2 -> still active (no new fact).
    manager.evaluate(_state_with_level(0.2, 3.0), _CONFIG, timestamp_s=3.0)
    # t=4: level 1.0 -> clear transition.
    manager.evaluate(_state_with_level(1.0, 4.0), _CONFIG, timestamp_s=4.0)

    facts = _alarm_facts_for(manager, "T102_LOW_LEVEL")
    assert len(facts) == 2
    assert [f.to_dict()["alarm"]["transition"] for f in facts] == ["assert", "clear"]
    for fact in facts:
        assert isinstance(fact, EventFact)  # alarm fact is also an Event fact
        assert fact.category is EventCategory.ALARM
        assert fact.event_id != ""  # stable per-fact identity


def test_stable_condition_emits_no_duplicate_facts() -> None:
    manager = AlarmManager(_CONFIG.alarms)
    manager.evaluate(_state_with_level(1.0, 1.0), _CONFIG, timestamp_s=1.0)
    manager.evaluate(_state_with_level(0.25, 2.0), _CONFIG, timestamp_s=2.0)
    manager.evaluate(_state_with_level(0.25, 3.0), _CONFIG, timestamp_s=3.0)
    manager.evaluate(_state_with_level(0.25, 4.0), _CONFIG, timestamp_s=4.0)
    assert len(_alarm_facts_for(manager, "T102_LOW_LEVEL")) == 1


def test_alarm_state_is_derived_projection_and_never_mutates_facts() -> None:
    manager = AlarmManager(_CONFIG.alarms)
    manager.evaluate(_state_with_level(1.0, 1.0), _CONFIG, timestamp_s=1.0)
    manager.evaluate(_state_with_level(0.25, 2.0), _CONFIG, timestamp_s=2.0)
    facts_before = manager.event_store.to_records()
    state = manager.states["T102_LOW_LEVEL"]
    assert state.active is True  # derived from runtime level 0.25 < 0.5
    # Mutable derived projection update does not touch the historical facts.
    state.active = False  # type: ignore[misc]
    state.message = "mutated projection"  # type: ignore[misc]
    assert manager.states["T102_LOW_LEVEL"].active is False
    assert manager.event_store.to_records() == facts_before


def test_runtime_state_remains_authoritative_mutable_truth() -> None:
    manager = AlarmManager(_CONFIG.alarms)
    state = _state_with_level(1.0, 1.0)  # low-level alarm inactive (baseline)
    manager.evaluate(state, _CONFIG, timestamp_s=1.0)
    # Raise the source on the SAME runtime state -> activation transition.
    state.set_signal_value("LT102_LEVEL", 0.25, timestamp_s=2.0, unit="m", source="LT102")
    manager.evaluate(state, _CONFIG, timestamp_s=2.0)
    # The alarm output signal in runtime state is the live derived truth.
    live = state.get_signal_value("T102_LOW_LEVEL_ALARM")
    assert live is not None and live.value is True
    facts_before = len(manager.event_store)
    # Historical event facts do not feed back into runtime truth.
    state.set_signal_value("LT102_LEVEL", 1.0, timestamp_s=5.0, unit="m", source="LT102")
    manager.evaluate(state, _CONFIG, timestamp_s=5.0)
    assert state.get_signal_value("T102_LOW_LEVEL_ALARM").value is False
    assert len(manager.event_store) == facts_before + 1  # clear fact appended


def test_emitted_alarm_facts_do_not_fabricate_identity() -> None:
    manager = AlarmManager(_CONFIG.alarms)
    manager.evaluate(_state_with_level(1.0, 1.0), _CONFIG, timestamp_s=1.0)
    manager.evaluate(_state_with_level(0.25, 2.0), _CONFIG, timestamp_s=2.0)
    facts = _alarm_facts_for(manager, "T102_LOW_LEVEL")
    assert len(facts) == 1
    d = facts[0].to_dict()
    # No workspace/scope/provenance/canonical identity is fabricated by the
    # legacy continuous alarm manager (no G1/G2 context supplied).
    assert d["workspace_id"] is None
    assert d["scope_path"] is None
    assert d["provenance"] is None
    assert "canonical_signal_id" not in d
