"""VF-vNEXT-G3 — typed immutable Event fact + Alarm specialization tests.

Proves (Issue #48 "Required tests / proofs"): Event fact is immutable and
deterministic to serialize; Alarm fact is an Event specialization/category (not
a separate truth model); no arbitrary mutation of payload/facts; no fabricated
PIM canonical identity or evidence maturity; no G4+ surface.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from virtual_factory.provenance import DataStatus, ProvenanceV2
from virtual_factory.telemetry.event_fact import (
    AlarmEventFact,
    EventCategory,
    EventFact,
    EventFactError,
)
from virtual_factory.workspace import StructuralPath


def _fact(**overrides) -> EventFact:
    kwargs = dict(
        event_id="evt-1",
        event_type="process.started",
        category=EventCategory.PROCESS,
        simulation_time_s=1.5,
    )
    kwargs.update(overrides)
    return EventFact(**kwargs)


def _alarm_fact(**overrides) -> AlarmEventFact:
    kwargs = dict(
        event_id="alarm-assert-1",
        event_type="alarm.assert",
        category=EventCategory.ALARM,
        simulation_time_s=2.0,
        severity="warning",
        alarm_id="T102_LOW_LEVEL",
        alarm_kind="low",
        transition="assert",
        threshold=0.5,
        message="T102 level is low",
    )
    kwargs.update(overrides)
    return AlarmEventFact(**kwargs)


def test_event_fact_is_immutable() -> None:
    fact = _fact()
    with pytest.raises(FrozenInstanceError):
        fact.event_type = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        fact.payload = {"x": 1}  # type: ignore[misc]


def test_event_fact_payload_is_deep_frozen() -> None:
    fact = _fact(payload={"nested": {"value": 1}, "items": [1, 2]})
    with pytest.raises(TypeError):
        fact.payload["nested"]["value"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        fact.payload["items"][0] = 99  # type: ignore[index]
    assert fact.payload["nested"]["value"] == 1


def test_event_fact_serialization_is_deterministic_and_stable() -> None:
    fact = _fact(payload={"a": 1, "b": [True, None]})
    d1 = fact.to_dict()
    d2 = fact.to_dict()
    assert d1 == d2
    assert list(d1.keys()) == [
        "event_id",
        "event_type",
        "category",
        "simulation_time_s",
        "run_id",
        "workspace_id",
        "scope_path",
        "source",
        "severity",
        "status",
        "payload",
        "correlation_id",
        "causation_id",
        "provenance",
    ]
    assert d1["category"] == "process"


def test_missing_identity_fails_closed() -> None:
    with pytest.raises(EventFactError):
        EventFact(event_id="", event_type="x", category=EventCategory.PROCESS, simulation_time_s=0.0)
    with pytest.raises(EventFactError):
        EventFact(event_id="e", event_type="  ", category=EventCategory.PROCESS, simulation_time_s=0.0)


def test_category_must_be_event_category() -> None:
    with pytest.raises(EventFactError):
        _fact(category="process")  # type: ignore[arg-type]


def test_invalid_time_fails_closed() -> None:
    with pytest.raises(EventFactError):
        _fact(simulation_time_s=-1.0)
    with pytest.raises(EventFactError):
        _fact(simulation_time_s=True)  # type: ignore[arg-type]


def test_workspace_scope_identity_consistency_fail_closed() -> None:
    # scope rooted in a different workspace than workspace_id -> fail closed.
    with pytest.raises(EventFactError):
        _fact(
            workspace_id="W1",
            scope_path=StructuralPath(("W2", "AREA", "UNIT")),
        )
    with pytest.raises(EventFactError):
        _fact(scope_path="W/AREA")  # type: ignore[arg-type]


def test_provenance_carried_without_fabricating_canonical_or_evidence() -> None:
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        data_status=DataStatus.SYNTHETIC,
    )
    fact = _fact(
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        provenance=provenance,
    )
    d = fact.to_dict()
    assert d["scope_path"] == "W/AREA/UNIT"
    assert d["provenance"]["workspace_id"] == "W"
    assert d["provenance"]["run_id"] == "run-1"
    # No PIM canonical identity / evidence maturity is ever fabricated.
    assert "canonical_signal_id" not in d
    assert "canonical_signal_id" not in d["provenance"]
    assert "evidence" not in d["provenance"]
    assert "data_status" in d["provenance"]


def test_provenance_workspace_mismatch_fails_closed() -> None:
    provenance = ProvenanceV2(workspace_id="W2", run_id="run-1")
    with pytest.raises(EventFactError):
        _fact(workspace_id="W1", provenance=provenance)


def test_provenance_run_id_mismatch_fails_closed() -> None:
    provenance = ProvenanceV2(workspace_id="W", run_id="run-9")
    with pytest.raises(EventFactError):
        _fact(
            run_id="run-1",
            workspace_id="W",
            provenance=provenance,
        )


def test_provenance_scope_path_mismatch_fails_closed() -> None:
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
    )
    with pytest.raises(EventFactError):
        _fact(
            run_id="run-1",
            workspace_id="W",
            scope_path=StructuralPath(("W", "AREA", "OTHER")),
            provenance=provenance,
        )


def test_event_and_provenance_authorities_agree_when_both_present() -> None:
    provenance = ProvenanceV2(
        workspace_id="W",
        run_id="run-1",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
    )
    fact = _fact(
        run_id="run-1",
        workspace_id="W",
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        provenance=provenance,
    )
    d = fact.to_dict()
    assert d["run_id"] == "run-1"
    assert d["scope_path"] == "W/AREA/UNIT"
    assert d["provenance"]["run_id"] == "run-1"
    assert d["provenance"]["scope_path"] == "W/AREA/UNIT"


# ── Alarm ⊂ Event ──────────────────────────────────────────────

def test_alarm_fact_is_event_specialization() -> None:
    fact = _alarm_fact()
    assert isinstance(fact, EventFact)  # Alarm is an Event, not a separate model
    assert fact.category is EventCategory.ALARM
    assert fact.event_type == "alarm.assert"


def test_alarm_fact_requires_alarm_metadata() -> None:
    with pytest.raises(EventFactError):
        _alarm_fact(alarm_id="")
    with pytest.raises(EventFactError):
        _alarm_fact(alarm_kind="")
    with pytest.raises(EventFactError):
        _alarm_fact(transition="ack")


def test_alarm_fact_category_must_be_alarm() -> None:
    with pytest.raises(EventFactError):
        _alarm_fact(category=EventCategory.PROCESS)


def test_alarm_fact_serialization_is_deterministic() -> None:
    fact = _alarm_fact()
    d1 = fact.to_dict()
    d2 = fact.to_dict()
    assert d1 == d2
    assert d1["category"] == "alarm"
    assert d1["alarm"] == {
        "alarm_id": "T102_LOW_LEVEL",
        "alarm_kind": "low",
        "transition": "assert",
        "threshold": 0.5,
        "message": "T102 level is low",
    }
    # Alarm-specific metadata rides beside the shared event identity — there is
    # no second event-id authority.
    assert d1["alarm"]["alarm_id"] != d1["event_id"]
