"""VF-DM-M5-S02 — ObservationPoint + TriggerPolicy + FieldPolicy + ObservationPolicy tests."""

import pytest

from virtual_factory.observation.point import (
    FieldPolicy,
    ObservationPoint,
    TriggerKind,
    TriggerPolicy,
)
from virtual_factory.observation.policy import ObservationPolicy
from virtual_factory.observation.envelope import ObservationType


# ═══════════════════════════════════════════════════
# TriggerKind
# ═══════════════════════════════════════════════════

class TestTriggerKind:
    def test_exactly_four_values(self):
        kinds = set(TriggerKind)
        assert kinds == {
            TriggerKind.ON_EVENT,
            TriggerKind.PERIODIC,
            TriggerKind.ON_CHANGE,
            TriggerKind.MANUAL,
        }

    def test_stable_serialized_values(self):
        assert TriggerKind.ON_EVENT.value == "on_event"
        assert TriggerKind.PERIODIC.value == "periodic"
        assert TriggerKind.ON_CHANGE.value == "on_change"
        assert TriggerKind.MANUAL.value == "manual"


# ═══════════════════════════════════════════════════
# TriggerPolicy — ON_EVENT
# ═══════════════════════════════════════════════════

class TestTriggerPolicyOnEvent:
    def test_matching_event_qualifies(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_COMPLETE",),
            target_ids=("AP04",),
        )
        assert tp.matches_event("PROCESS_COMPLETE", "AP04") is True

    def test_wrong_event_type_rejected(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_COMPLETE",),
        )
        assert tp.matches_event("WIP_CREATED", "AP04") is False

    def test_wrong_target_rejected(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_COMPLETE",),
            target_ids=("AP04",),
        )
        assert tp.matches_event("PROCESS_COMPLETE", "AP06") is False

    def test_multiple_event_types_accepted(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_START", "PROCESS_COMPLETE"),
        )
        assert tp.matches_event("PROCESS_START", "AP01") is True
        assert tp.matches_event("PROCESS_COMPLETE", "AP01") is True
        assert tp.matches_event("QUALITY_CHECK", "AP01") is False

    def test_empty_event_types_matches_all(self):
        tp = TriggerPolicy(kind=TriggerKind.ON_EVENT)
        assert tp.matches_event("ANY_EVENT", "AP99") is True

    def test_empty_target_ids_matches_all(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_COMPLETE",),
        )
        assert tp.matches_event("PROCESS_COMPLETE", "AP99") is True


# ═══════════════════════════════════════════════════
# TriggerPolicy — PERIODIC
# ═══════════════════════════════════════════════════

class TestTriggerPolicyPeriodic:
    def test_positive_interval_valid(self):
        tp = TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=5.0)
        assert tp.interval_s == 5.0

    def test_zero_interval_invalid(self):
        with pytest.raises(ValueError, match="positive interval_s"):
            TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=0.0)

    def test_negative_interval_invalid(self):
        with pytest.raises(ValueError, match="positive interval_s"):
            TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=-1.0)

    def test_eligible_after_interval(self):
        tp = TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=5.0)
        assert tp.is_periodic_eligible(5.0) is True
        assert tp.is_periodic_eligible(10.0) is True

    def test_not_eligible_before_interval(self):
        tp = TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=5.0)
        assert tp.is_periodic_eligible(4.9) is False

    def test_periodic_ignores_event_matches(self):
        tp = TriggerPolicy(kind=TriggerKind.PERIODIC, interval_s=1.0)
        assert tp.matches_event("PROCESS_COMPLETE", "AP04") is False


# ═══════════════════════════════════════════════════
# TriggerPolicy — ON_CHANGE
# ═══════════════════════════════════════════════════

class TestTriggerPolicyOnChange:
    def test_threshold_crossing_qualifies(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_CHANGE,
            change_field="temperature",
            change_threshold=0.5,
        )
        assert tp.has_changed(
            {"temperature": 20.0}, {"temperature": 20.6}
        ) is True

    def test_below_threshold_does_not_qualify(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_CHANGE,
            change_field="temperature",
            change_threshold=0.5,
        )
        assert tp.has_changed(
            {"temperature": 20.0}, {"temperature": 20.3}
        ) is False

    def test_first_observation_qualifies(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_CHANGE,
            change_field="temperature",
            change_threshold=0.5,
        )
        assert tp.has_changed(None, {"temperature": 20.0}) is True

    def test_missing_change_field_invalid(self):
        with pytest.raises(ValueError, match="non-empty change_field"):
            TriggerPolicy(kind=TriggerKind.ON_CHANGE, change_threshold=0.5)

    def test_negative_threshold_invalid(self):
        with pytest.raises(ValueError, match="non-negative threshold"):
            TriggerPolicy(
                kind=TriggerKind.ON_CHANGE,
                change_field="x",
                change_threshold=-0.1,
            )

    def test_missing_field_in_data_returns_false(self):
        tp = TriggerPolicy(
            kind=TriggerKind.ON_CHANGE,
            change_field="missing",
            change_threshold=0.5,
        )
        assert tp.has_changed({"a": 1}, {"a": 2}) is False


# ═══════════════════════════════════════════════════
# TriggerPolicy — MANUAL
# ═══════════════════════════════════════════════════

class TestTriggerPolicyManual:
    def test_valid_declaration(self):
        tp = TriggerPolicy(kind=TriggerKind.MANUAL)
        assert tp.kind == TriggerKind.MANUAL

    def test_manual_does_not_match_events(self):
        tp = TriggerPolicy(kind=TriggerKind.MANUAL)
        assert tp.matches_event("PROCESS_COMPLETE", "AP04") is False


# ═══════════════════════════════════════════════════
# FieldPolicy — default deny + explicit allow-list
# ═══════════════════════════════════════════════════

class TestFieldPolicy:
    def test_extracts_only_selected_fields(self):
        fp = FieldPolicy(extract=("a", "c"))
        result = fp.select({"a": 1, "b": 2, "c": 3, "d": 4})
        assert result == {"a": 1, "c": 3}

    def test_undeclared_field_hidden(self):
        fp = FieldPolicy(extract=("a",))
        result = fp.select({"a": 1, "secret": "leaked"})
        assert "secret" not in result

    def test_new_internal_field_hidden_automatically(self):
        """If reality model adds a new field, it stays hidden by default."""
        fp = FieldPolicy(extract=("event_type", "result"))
        reality = {"event_type": "X", "result": "ok", "new_debug_field": 123}
        result = fp.select(reality)
        assert "new_debug_field" not in result

    def test_deny_wins_over_extract(self):
        fp = FieldPolicy(extract=("a", "b", "c"), deny=("b",))
        result = fp.select({"a": 1, "b": 2, "c": 3})
        assert result == {"a": 1, "c": 3}

    def test_empty_extract_exposes_nothing(self):
        fp = FieldPolicy(extract=())
        result = fp.select({"a": 1, "b": 2})
        assert result == {}

    def test_source_not_mutated(self):
        fp = FieldPolicy(extract=("a",))
        original = {"a": 1, "b": 2}
        fp.select(original)
        assert original == {"a": 1, "b": 2}

    def test_empty_field_name_in_extract_raises(self):
        with pytest.raises(ValueError, match="extract field names"):
            FieldPolicy(extract=("a", ""))

    def test_empty_field_name_in_deny_raises(self):
        with pytest.raises(ValueError, match="deny field names"):
            FieldPolicy(deny=("",))


# ═══════════════════════════════════════════════════
# ObservationPoint
# ═══════════════════════════════════════════════════

def _make_point(**overrides) -> ObservationPoint:
    defaults = {
        "point_id": "ap04-completion",
        "observation_type": ObservationType.EVENT,
        "label": "AP04 Process Complete",
        "source_type": "assembly.event",
        "source_filter": {"event_type": "PROCESS_COMPLETE", "target_id": "AP04"},
        "trigger": TriggerPolicy(
            kind=TriggerKind.ON_EVENT,
            event_types=("PROCESS_COMPLETE",),
            target_ids=("AP04",),
        ),
        "fields": FieldPolicy(extract=("event_type", "result")),
    }
    defaults.update(overrides)
    return ObservationPoint(**defaults)


class TestObservationPoint:
    def test_valid_construction(self):
        p = _make_point()
        assert p.point_id == "ap04-completion"
        assert p.observation_type == ObservationType.EVENT
        assert p.source_type == "assembly.event"
        assert p.enabled is True

    def test_point_id_required(self):
        with pytest.raises(ValueError, match="point_id"):
            _make_point(point_id="")

    def test_source_type_required(self):
        with pytest.raises(ValueError, match="source_type"):
            _make_point(source_type="")

    def test_uses_s01_observation_type(self):
        p = _make_point(observation_type=ObservationType.STATE)
        assert p.observation_type == ObservationType.STATE

    def test_disabled_point(self):
        p = _make_point(enabled=False)
        assert p.enabled is False

    def test_no_projection_field(self):
        """ObservationPoint must not have a projections/destination field."""
        p = _make_point()
        assert not hasattr(p, "projections")
        assert not hasattr(p, "projection")
        assert not hasattr(p, "destination")
        assert not hasattr(p, "consumer")

    def test_invalid_observation_type_raises(self):
        with pytest.raises(ValueError, match="observation_type"):
            _make_point(observation_type="bad")  # type: ignore[arg-type]

    def test_invalid_trigger_raises(self):
        with pytest.raises(ValueError, match="trigger"):
            _make_point(trigger="not_a_trigger")  # type: ignore[arg-type]

    def test_invalid_fields_raises(self):
        with pytest.raises(ValueError, match="fields"):
            _make_point(fields="not_fields")  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════
# ObservationPolicy
# ═══════════════════════════════════════════════════

class TestObservationPolicy:
    def test_industrial_mode_rejects_internal_truth(self):
        policy = ObservationPolicy.industrial()
        assert policy.is_allowed("industrial_signal") is True
        assert policy.is_allowed("internal_truth") is False

    def test_normal_categories_allowed(self):
        policy = ObservationPolicy.industrial()
        assert policy.is_allowed("controller_signal") is True
        assert policy.is_allowed("actuator_feedback") is True
        assert policy.is_allowed("industrial_event") is True

    def test_debug_mode_allows_internal_truth(self):
        policy = ObservationPolicy.debug()
        assert policy.is_allowed("internal_truth") is True

    def test_benchmark_mode_allows_internal_truth(self):
        policy = ObservationPolicy.benchmark()
        assert policy.is_allowed("internal_truth") is True

    def test_unknown_category_rejected(self):
        policy = ObservationPolicy.industrial()
        assert policy.is_allowed("nonexistent") is False

    def test_denied_wins_over_allowed(self):
        policy = ObservationPolicy(
            mode="industrial",
            allowed_categories=frozenset({"internal_truth", "industrial_signal"}),
            denied_categories=frozenset({"internal_truth"}),
        )
        assert policy.is_allowed("internal_truth") is False

    def test_no_consumer_selection(self):
        """ObservationPolicy must not have consumer/gateway fields."""
        policy = ObservationPolicy.industrial()
        assert not hasattr(policy, "consumer")
        assert not hasattr(policy, "projection")
        assert not hasattr(policy, "gateway")
        assert not hasattr(policy, "topic")


# ═══════════════════════════════════════════════════
# Architecture Boundaries
# ═══════════════════════════════════════════════════

class TestArchitectureBoundary:
    def test_no_mes_odoo_imports_in_point(self):
        import inspect
        import virtual_factory.observation.point as mod
        source = inspect.getsource(mod)
        forbidden = ["mes_adapter", "odoo", "MESAdapter", "MESInput", "MESOutput"]
        for f in forbidden:
            assert f not in source, f"point.py imports {f}"

    def test_no_mes_odoo_imports_in_policy(self):
        import inspect
        import virtual_factory.observation.policy as mod
        source = inspect.getsource(mod)
        forbidden = ["mes_adapter", "odoo", "MESAdapter", "MESInput", "MESOutput"]
        for f in forbidden:
            assert f not in source, f"policy.py imports {f}"

    def test_no_protocol_network_imports(self):
        """Check that point.py and policy.py have no protocol/network imports."""
        import inspect
        import virtual_factory.observation.point as mod_p
        import virtual_factory.observation.policy as mod_po

        forbidden = ["import mqtt", "import socket", "import asyncio",
                     "import fastapi", "import opcua", "import requests",
                     "from mqtt", "from fastapi", "from opcua"]
        for mod in (mod_p, mod_po):
            source = inspect.getsource(mod)
            for f in forbidden:
                assert f not in source, f"{mod.__name__} contains '{f}'"

    def test_no_service_router_projection_gateway(self):
        """S02 must not implement ObservationService/Router/Projection/Gateway."""
        import inspect
        import virtual_factory.observation.point as mod
        source = inspect.getsource(mod)
        forbidden = [
            "ObservationService", "ObservationRouter",
            "MESProjection", "IIoTProjection", "ProjectionProtocol",
            "ObservationGateway",
        ]
        for f in forbidden:
            assert f not in source, f"point.py contains {f}"

    def test_no_runtime_orchestration(self):
        import inspect
        import virtual_factory.observation.point as mod
        source = inspect.getsource(mod)
        forbidden = [
            "DiscreteRunService", "DiscreteSimulationEngine",
            "AssemblyRuntimeState", "HandlerRegistry", "asyncio",
        ]
        for f in forbidden:
            assert f not in source, f"point.py imports {f}"

    def test_s01_tests_still_pass(self):
        """Quick check that S01 imports still work."""
        from virtual_factory.observation.envelope import (
            ObservationEnvelope, ObservationType as OT, make_idempotency_key,
        )
        assert OT.EVENT.value == "event"
        assert callable(make_idempotency_key)
