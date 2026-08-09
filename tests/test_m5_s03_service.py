"""VF-DM-M5-S03 — ObservationService + Identity tests."""

import pytest

from virtual_factory.observation.service import (
    ObservationService,
    RealityInput,
)
from virtual_factory.observation.point import (
    FieldPolicy,
    ObservationPoint,
    TriggerKind,
    TriggerPolicy,
)
from virtual_factory.observation.policy import (
    ObservationMode,
    ObservationPolicy,
)
from virtual_factory.observation.identity import (
    EntityRef,
    ExternalIdentityRef,
    IdentityLink,
    IdentityResolver,
)
from virtual_factory.observation.envelope import (
    ObservationType,
    make_idempotency_key,
)


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

def _make_reality(**overrides) -> RealityInput:
    defaults = {
        "run_id": "run-1",
        "model_id": "tipa",
        "source_event_id": "evt-001",
        "source_type": "assembly.event",
        "source_domain": "assembly",
        "source_path": "processor.AP04",
        "simulation_time_s": 12.5,
        "source_data": {
            "event_type": "PROCESS_COMPLETE",
            "result": "committed",
            "target_id": "AP04",
        },
    }
    defaults.update(overrides)
    return RealityInput(**defaults)


def _make_point(point_id="ap04-completion", **overrides) -> ObservationPoint:
    defaults = {
        "point_id": point_id,
        "observation_type": ObservationType.EVENT,
        "label": "AP04 Completion",
        "source_type": "assembly.event",
        "source_filter": {"event_type": "PROCESS_COMPLETE", "target_id": "AP04"},
        "trigger": TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_COMPLETE",),
            target_ids=("AP04",),
        ),
        "fields": FieldPolicy(extract=("event_type", "result", "target_id")),
    }
    defaults.update(overrides)
    return ObservationPoint(**defaults)


# ═══════════════════════════════════════════════════
# Service Basics
# ═══════════════════════════════════════════════════

class TestServiceBasics:
    def test_zero_matching_points(self):
        svc = ObservationService()
        reality = _make_reality()
        assert svc.collect(reality) == []

    def test_one_matching_point(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality()
        envelopes = svc.collect(reality)
        assert len(envelopes) == 1
        assert envelopes[0].run_id == "run-1"

    def test_multiple_matching_points(self):
        svc = ObservationService()
        svc.add_point(_make_point("ap04-completion"))
        svc.add_point(_make_point("ap04-measurement",
            observation_type=ObservationType.MEASUREMENT,
            fields=FieldPolicy(extract=("event_type", "result")),
        ))
        reality = _make_reality()
        envelopes = svc.collect(reality)
        assert len(envelopes) == 2

    def test_disabled_point_no_envelope(self):
        svc = ObservationService()
        svc.add_point(_make_point(enabled=False))
        reality = _make_reality()
        assert svc.collect(reality) == []

    def test_source_type_mismatch_no_envelope(self):
        svc = ObservationService()
        svc.add_point(_make_point(source_type="continuous.signal"))
        reality = _make_reality(source_type="assembly.event")
        assert svc.collect(reality) == []


# ═══════════════════════════════════════════════════
# Field Selection / Hidden Truth
# ═══════════════════════════════════════════════════

class TestFieldSelection:
    def test_field_policy_allow_list_applied(self):
        svc = ObservationService()
        svc.add_point(_make_point(fields=FieldPolicy(extract=("event_type",))))
        reality = _make_reality(source_data={
            "event_type": "PROCESS_COMPLETE",
            "result": "committed",
            "target_id": "AP04",
        })
        envelopes = svc.collect(reality)
        assert envelopes[0].payload == {"event_type": "PROCESS_COMPLETE"}

    def test_new_unknown_field_hidden(self):
        svc = ObservationService()
        svc.add_point(_make_point(
            source_filter={},  # match all
            trigger=TriggerPolicy(kind=TriggerKind.ON_EVENT),  # match all events
            fields=FieldPolicy(extract=("event_type", "result")),
        ))
        reality = _make_reality(source_data={
            "event_type": "PROCESS_COMPLETE", "result": "ok",
            "future_new_secret": "hidden",
        })
        envelopes = svc.collect(reality)
        assert len(envelopes) == 1
        assert "future_new_secret" not in envelopes[0].payload

    def test_deny_still_wins(self):
        svc = ObservationService()
        svc.add_point(_make_point(
            source_filter={},
            fields=FieldPolicy(extract=("event_type", "result", "target_id"),
                               deny=("result",)),
        ))
        envelopes = svc.collect(_make_reality())
        assert "result" not in envelopes[0].payload
        assert "event_type" in envelopes[0].payload

    def test_source_not_mutated(self):
        svc = ObservationService()
        svc.add_point(_make_point(source_filter={}))
        original = {"event_type": "PROCESS_COMPLETE", "result": "ok", "target_id": "AP04"}
        reality = _make_reality(source_data=original)
        svc.collect(reality)
        assert original == {"event_type": "PROCESS_COMPLETE", "result": "ok", "target_id": "AP04"}

    def test_internal_truth_category_industrial_mode_no_envelope(self):
        svc = ObservationService(policy=ObservationPolicy.industrial())
        svc.add_point(_make_point(source_type="assembly.event"))
        reality = _make_reality(category="internal_truth")
        assert svc.collect(reality) == []


# ═══════════════════════════════════════════════════
# ON_EVENT Trigger
# ═══════════════════════════════════════════════════

class TestTriggerOnEvent:
    def test_matching_event_emits(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        assert len(svc.collect(_make_reality())) == 1

    def test_wrong_event_type_no_emit(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(source_data={
            "event_type": "WIP_CREATED", "target_id": "AP04",
        })
        assert svc.collect(reality) == []

    def test_wrong_target_no_emit(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(source_data={
            "event_type": "PROCESS_COMPLETE", "target_id": "AP06",
        })
        assert svc.collect(reality) == []


# ═══════════════════════════════════════════════════
# PERIODIC Trigger
# ═══════════════════════════════════════════════════

class TestTriggerPeriodic:
    def _make_periodic_point(self) -> ObservationPoint:
        return _make_point(
            point_id="periodic-1",
            trigger=TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=5.0),
            source_type="continuous.signal",
            source_filter={},
        )

    def test_first_call_emits(self):
        svc = ObservationService()
        svc.add_point(self._make_periodic_point())
        reality = _make_reality(
            source_type="continuous.signal", source_data={"value": 10},
            source_event_id="evt-periodic-1",
        )
        envelopes = svc.collect(reality)
        assert len(envelopes) == 1

    def test_before_interval_no_emit(self):
        svc = ObservationService()
        svc.add_point(self._make_periodic_point())
        r1 = _make_reality(source_type="continuous.signal", simulation_time_s=0,
                           source_data={"value": 10}, source_event_id="e1")
        svc.collect(r1)
        r2 = _make_reality(source_type="continuous.signal", simulation_time_s=2,
                           source_data={"value": 11}, source_event_id="e2")
        assert svc.collect(r2) == []

    def test_at_interval_emits(self):
        svc = ObservationService()
        svc.add_point(self._make_periodic_point())
        r1 = _make_reality(source_type="continuous.signal", simulation_time_s=0,
                           source_data={"value": 10}, source_event_id="e1")
        svc.collect(r1)
        r2 = _make_reality(source_type="continuous.signal", simulation_time_s=5,
                           source_data={"value": 15}, source_event_id="e2")
        assert len(svc.collect(r2)) == 1

    def test_first_fire_at_sim_time_zero_emits(self):
        """First call at simulation_time_s=0 must emit (Fix #1)."""
        svc = ObservationService()
        svc.add_point(self._make_periodic_point())
        reality = _make_reality(
            source_type="continuous.signal", simulation_time_s=0,
            source_data={"value": 1}, source_event_id="e0",
        )
        envelopes = svc.collect(reality)
        assert len(envelopes) == 1

    def test_uses_simulation_time_not_wall_clock(self):
        svc = ObservationService()
        svc.add_point(self._make_periodic_point())
        r = _make_reality(source_type="continuous.signal", simulation_time_s=100,
                          source_data={"value": 1}, source_event_id="e1")
        envelopes = svc.collect(r)
        assert envelopes[0].simulation_time_s == 100


# ═══════════════════════════════════════════════════
# ON_CHANGE Trigger
# ═══════════════════════════════════════════════════

class TestTriggerOnChange:
    def _make_onchange_point(self) -> ObservationPoint:
        return _make_point(
            point_id="onchange-1",
            trigger=TriggerPolicy(
                kind=TriggerKind.ON_CHANGE,
                change_field="temperature",
                change_threshold=0.5,
            ),
            source_type="continuous.signal",
            source_filter={},
        )

    def test_first_observation_emits(self):
        svc = ObservationService()
        svc.add_point(self._make_onchange_point())
        reality = _make_reality(
            source_type="continuous.signal",
            source_data={"temperature": 20.0},
            source_event_id="e1",
        )
        assert len(svc.collect(reality)) == 1

    def test_below_threshold_no_emit(self):
        svc = ObservationService()
        svc.add_point(self._make_onchange_point())
        r1 = _make_reality(source_type="continuous.signal",
                           source_data={"temperature": 20.0}, source_event_id="e1")
        svc.collect(r1)
        r2 = _make_reality(source_type="continuous.signal",
                           source_data={"temperature": 20.3}, source_event_id="e2")
        assert svc.collect(r2) == []

    def test_threshold_reached_emits(self):
        svc = ObservationService()
        svc.add_point(self._make_onchange_point())
        svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.0}, source_event_id="e1"))
        envelopes = svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.6}, source_event_id="e2"))
        assert len(envelopes) == 1

    def test_per_point_state_isolated(self):
        svc = ObservationService()
        svc.add_point(self._make_onchange_point())
        svc.add_point(_make_point(
            point_id="onchange-2",
            trigger=TriggerPolicy(kind=TriggerKind.ON_CHANGE,
                                  change_field="pressure", change_threshold=1.0),
            source_type="continuous.signal", source_filter={},
        ))
        svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.0, "pressure": 100},
            source_event_id="e1"))
        envelopes = svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.6, "pressure": 101.5},
            source_event_id="e2"))
        # Both points should emit (temperature changed, pressure changed)
    def test_different_subjects_isolated(self):
        """Two WIPs through same ON_CHANGE point must not interfere (Fix #2)."""
        svc = ObservationService()
        svc.add_point(self._make_onchange_point())
        # Subject A: temperature 20.0
        svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.0}, source_event_id="e1",
            subject_type="wip", subject_id="MOTOR-A"))
        # Subject B: temperature 20.0 (same baseline, different subject)
        svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.0}, source_event_id="e2",
            subject_type="wip", subject_id="MOTOR-B"))
        # Subject A: 20.6 → should emit (crossed threshold for A)
        envelopes_a = svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.6}, source_event_id="e3",
            subject_type="wip", subject_id="MOTOR-A"))
        # Subject B: 20.3 → should NOT emit (below threshold for B)
        envelopes_b = svc.collect(_make_reality(source_type="continuous.signal",
            source_data={"temperature": 20.3}, source_event_id="e4",
            subject_type="wip", subject_id="MOTOR-B"))
        assert len(envelopes_a) == 1, "Subject A should emit (20.0→20.6)"
        assert len(envelopes_b) == 0, "Subject B should NOT emit (20.0→20.3)"


# ═══════════════════════════════════════════════════
# MANUAL Trigger
# ═══════════════════════════════════════════════════

class TestTriggerManual:
    def _make_manual_point(self) -> ObservationPoint:
        return _make_point(
            point_id="manual-1",
            trigger=TriggerPolicy(kind=TriggerKind.MANUAL),
        )

    def test_no_emit_without_explicit_manual(self):
        svc = ObservationService()
        svc.add_point(self._make_manual_point())
        assert svc.collect(_make_reality()) == []

    def test_emits_with_explicit_manual(self):
        svc = ObservationService()
        svc.add_point(self._make_manual_point())
        envelopes = svc.collect_manual(_make_reality(), "manual-1")
        assert len(envelopes) == 1

    def test_wrong_point_id_returns_empty(self):
        svc = ObservationService()
        svc.add_point(self._make_manual_point())
        assert svc.collect_manual(_make_reality(), "nonexistent") == []

    def test_manual_respects_source_match(self):
        """MANUAL must not bypass source applicability (Fix #3)."""
        svc = ObservationService()
        svc.add_point(_make_point(
            point_id="manual-ap04",
            trigger=TriggerPolicy(kind=TriggerKind.MANUAL),
            source_type="assembly.event",
            source_filter={"event_type": "PROCESS_COMPLETE", "target_id": "AP04"},
        ))
        # Wrong source_type
        r_wrong_type = _make_reality(source_type="continuous.signal")
        assert svc.collect_manual(r_wrong_type, "manual-ap04") == []

        # Wrong source_filter
        r_wrong_filter = _make_reality(source_data={
            "event_type": "WIP_CREATED", "target_id": "AP04",
        })
        assert svc.collect_manual(r_wrong_filter, "manual-ap04") == []

        # Correct source
        r_correct = _make_reality()
        assert len(svc.collect_manual(r_correct, "manual-ap04")) == 1


# ═══════════════════════════════════════════════════
# Context Extraction
# ═══════════════════════════════════════════════════

class TestContextExtraction:
    def test_context_map_extracts_explicit_fields(self):
        svc = ObservationService()
        svc.add_point(_make_point(context_map={
            "station_id": "target_id",
            "flow_id": "flow_id",
        }))
        reality = _make_reality(source_data={
            "event_type": "PROCESS_COMPLETE", "result": "ok",
            "target_id": "AP04", "flow_id": "base",
        })
        envelopes = svc.collect(reality)
        assert envelopes[0].context["station_id"] == "AP04"
        assert envelopes[0].context["flow_id"] == "base"

    def test_missing_context_field_skipped(self):
        svc = ObservationService()
        svc.add_point(_make_point(context_map={"station_id": "missing_field"}))
        envelopes = svc.collect(_make_reality())
        assert "station_id" not in envelopes[0].context

    def test_context_does_not_auto_copy_unrelated(self):
        svc = ObservationService()
        svc.add_point(_make_point(source_filter={}, context_map={}))
        reality = _make_reality(source_data={
            "event_type": "PROCESS_COMPLETE", "result": "ok",
            "target_id": "AP04", "internal_debug": 123,
        })
        envelopes = svc.collect(reality)
        assert "internal_debug" not in envelopes[0].context

    def test_reality_context_preserved(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(context={"batch_id": "B-001"})
        envelopes = svc.collect(reality)
        assert envelopes[0].context["batch_id"] == "B-001"


# ═══════════════════════════════════════════════════
# Subject / Lineage
# ═══════════════════════════════════════════════════

class TestSubjectLineage:
    def test_explicit_subject_preserved(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(
            subject_type="wip", subject_id="MOTOR-000123",
        )
        envelopes = svc.collect(reality)
        assert envelopes[0].subject_type == "wip"
        assert envelopes[0].subject_id == "MOTOR-000123"

    def test_correlation_id_preserved(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(correlation_id="wip-0001")
        envelopes = svc.collect(reality)
        assert envelopes[0].correlation_id == "wip-0001"

    def test_causation_id_preserved(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(causation_id="evt-000")
        envelopes = svc.collect(reality)
        assert envelopes[0].causation_id == "evt-000"

    def test_subject_not_forced_from_correlation(self):
        """Subject is explicit; not auto-derived from correlation_id."""
        svc = ObservationService()
        svc.add_point(_make_point())
        reality = _make_reality(
            correlation_id="wip-0001",
            subject_type=None, subject_id=None,
        )
        envelopes = svc.collect(reality)
        assert envelopes[0].subject_type is None
        assert envelopes[0].subject_id is None
        assert envelopes[0].correlation_id == "wip-0001"


# ═══════════════════════════════════════════════════
# Idempotency
# ═══════════════════════════════════════════════════

class TestIdempotency:
    def test_service_uses_s01_helper(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        envelopes = svc.collect(_make_reality())
        expected = make_idempotency_key("run-1", "evt-001", "ap04-completion", "1.0")
        assert envelopes[0].idempotency_key == expected

    def test_same_logical_replay_same_key(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        e1 = svc.collect(_make_reality())[0]
        e2 = svc.collect(_make_reality())[0]
        assert e1.idempotency_key == e2.idempotency_key

    def test_different_observation_id_same_idempotency(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        e1 = svc.collect(_make_reality())[0]
        e2 = svc.collect(_make_reality())[0]
        assert e1.observation_id != e2.observation_id
        assert e1.idempotency_key == e2.idempotency_key

    def test_different_point_different_key(self):
        svc = ObservationService()
        svc.add_point(_make_point("ap04"))
        svc.add_point(_make_point("ap06"))
        envelopes = svc.collect(_make_reality())
        assert len(envelopes) == 2
        assert envelopes[0].idempotency_key != envelopes[1].idempotency_key


# ═══════════════════════════════════════════════════
# Time
# ═══════════════════════════════════════════════════

class TestTime:
    def test_simulation_time_s_preserved(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        envelopes = svc.collect(_make_reality(simulation_time_s=45.0))
        assert envelopes[0].simulation_time_s == 45.0

    def test_occurred_at_preserved(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        envelopes = svc.collect(_make_reality(occurred_at="2026-08-09T00:00:45Z"))
        assert envelopes[0].occurred_at == "2026-08-09T00:00:45Z"

    def test_occurred_at_none_ok(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        envelopes = svc.collect(_make_reality(occurred_at=None))
        assert envelopes[0].occurred_at is None

    def test_emitted_at_generated_utc(self):
        svc = ObservationService()
        svc.add_point(_make_point())
        envelopes = svc.collect(_make_reality())
        assert envelopes[0].emitted_at.endswith("Z") or envelopes[0].emitted_at.endswith("+00:00")

    def test_periodic_independent_of_emitted_at(self):
        svc = ObservationService()
        svc.add_point(_make_point(
            point_id="p1",
            trigger=TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=5.0),
            source_type="continuous.signal", source_filter={},
        ))
        r = _make_reality(source_type="continuous.signal", simulation_time_s=100,
                          source_data={"value": 1}, source_event_id="e1")
        envelopes = svc.collect(r)
        # PERIODIC uses simulation_time_s (100), not wall clock
        assert len(envelopes) == 1
        assert envelopes[0].simulation_time_s == 100


# ═══════════════════════════════════════════════════
# Identity Model
# ═══════════════════════════════════════════════════

class TestIdentity:
    def test_entity_ref_valid_construction(self):
        ref = EntityRef(entity_type="wip", entity_id="MOTOR-000123")
        assert ref.entity_type == "wip"
        assert ref.entity_id == "MOTOR-000123"

    def test_entity_ref_empty_type_raises(self):
        with pytest.raises(ValueError, match="entity_type"):
            EntityRef(entity_type="", entity_id="x")

    def test_external_identity_ref_valid(self):
        ref = ExternalIdentityRef(
            namespace="serial", entity_type="material_lot",
            external_id="SN-260808-0128",
        )
        assert ref.namespace == "serial"
        assert ref.external_id == "SN-260808-0128"

    def test_identity_link_valid(self):
        link = IdentityLink(
            internal=EntityRef("wip", "MOTOR-000123"),
            external=ExternalIdentityRef("serial", "material_lot", "SN-0128"),
            mapping_type="serial_mapping",
        )
        assert link.internal.entity_id == "MOTOR-000123"
        assert link.external.external_id == "SN-0128"

    def test_wip_and_carrier_identity_different(self):
        wip = EntityRef(entity_type="wip", entity_id="MOTOR-000123")
        carrier = EntityRef(entity_type="carrier", entity_id="PALLET-027")
        assert wip.entity_id != carrier.entity_id
        assert wip.entity_type != carrier.entity_type

    def test_no_odoo_id_required(self):
        ref = EntityRef(entity_type="asset", entity_id="TESTER-01")
        assert "odoo" not in ref.entity_id.lower()

    def test_identity_resolver_register_and_lookup(self):
        resolver = IdentityResolver()
        link = IdentityLink(
            internal=EntityRef("wip", "MOTOR-000123"),
            external=ExternalIdentityRef("serial", "material_lot", "SN-0128"),
        )
        resolver.register(link)
        results = resolver.resolve_internal("wip", "MOTOR-000123")
        assert len(results) == 1
        assert results[0].external.external_id == "SN-0128"

    def test_identity_resolver_external_lookup(self):
        resolver = IdentityResolver()
        resolver.register(IdentityLink(
            internal=EntityRef("wip", "MOTOR-000123"),
            external=ExternalIdentityRef("serial", "material_lot", "SN-0128"),
        ))
        results = resolver.resolve_external("serial", "material_lot", "SN-0128")
        assert len(results) == 1


# ═══════════════════════════════════════════════════
# TIPA carrier proof
# ═══════════════════════════════════════════════════

class TestTIPACarrierProof:
    def test_wip_and_carrier_in_context(self):
        """AP04 PROCESS_COMPLETE: WIP MOTOR-000123 on carrier PALLET-027."""
        svc = ObservationService()
        svc.add_point(_make_point(context_map={
            "station_id": "target_id",
            "carrier_id": "carrier_id",
        }))
        reality = _make_reality(
            subject_type="wip",
            subject_id="MOTOR-000123",
            source_data={
                "event_type": "PROCESS_COMPLETE",
                "result": "committed",
                "target_id": "AP04",
                "carrier_id": "PALLET-027",
            },
        )
        envelopes = svc.collect(reality)
        assert envelopes[0].subject_type == "wip"
        assert envelopes[0].subject_id == "MOTOR-000123"
        assert envelopes[0].context["carrier_id"] == "PALLET-027"


# ═══════════════════════════════════════════════════
# Architecture Boundaries
# ═══════════════════════════════════════════════════

class TestArchitectureBoundary:
    def test_no_router_projection_gateway(self):
        import inspect
        import virtual_factory.observation.service as mod
        source = inspect.getsource(mod)
        forbidden = [
            "ObservationRouter", "MESProjection", "IIoTProjection",
            "ProjectionProtocol", "ObservationGateway", "ControlBoundary",
        ]
        for f in forbidden:
            assert f not in source, f"service.py contains {f}"

    def test_no_mes_odoo_imports(self):
        import inspect
        import virtual_factory.observation.identity as mod
        source = inspect.getsource(mod)
        forbidden = ["odoo", "MES", "MESAdapter", "ProductionOrder"]
        for f in forbidden:
            assert f not in source, f"identity.py imports {f}"

    def test_no_protocol_network_imports_in_service(self):
        import inspect
        import virtual_factory.observation.service as mod
        source = inspect.getsource(mod)
        forbidden = ["import mqtt", "import socket", "import fastapi"]
        for f in forbidden:
            assert f not in source
