"""VF-DM-M5-S01 — ObservationEnvelope + ObservationType tests."""

import json

import pytest

from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

def _make_envelope(**overrides) -> ObservationEnvelope:
    defaults = {
        "observation_id": "obs-00001",
        "idempotency_key": "run-1|evt-001|ap04|1.0",
        "observation_type": ObservationType.EVENT,
        "run_id": "run-1",
        "model_id": "tipa",
        "simulation_time_s": 12.5,
    }
    defaults.update(overrides)
    return ObservationEnvelope(**defaults)


# ═══════════════════════════════════════════════════
# ObservationType
# ═══════════════════════════════════════════════════

class TestObservationType:
    def test_all_four_values_exist(self):
        assert ObservationType.EVENT.value == "event"
        assert ObservationType.MEASUREMENT.value == "measurement"
        assert ObservationType.STATE.value == "state"
        assert ObservationType.HUMAN_ENTRY.value == "human_entry"

    def test_serialization_is_stable_string(self):
        for t in ObservationType:
            serialized = t.value
            assert isinstance(serialized, str)
            # Round-trip
            assert ObservationType(serialized) is t

    def test_no_extra_types(self):
        assert len(ObservationType) == 4


# ═══════════════════════════════════════════════════
# ObservationEnvelope — construction
# ═══════════════════════════════════════════════════

class TestEnvelopeConstruction:
    def test_required_fields(self):
        env = _make_envelope()
        assert env.observation_id == "obs-00001"
        assert env.idempotency_key == "run-1|evt-001|ap04|1.0"
        assert env.observation_type == ObservationType.EVENT
        assert env.run_id == "run-1"
        assert env.model_id == "tipa"
        assert env.simulation_time_s == 12.5

    def test_defaults_are_sensible(self):
        env = _make_envelope(
            observation_id="obs-x",
            idempotency_key="r|e|p|1.0",
            observation_type=ObservationType.MEASUREMENT,
            run_id="r",
            model_id="m",
            simulation_time_s=0.0,
        )
        assert env.source_domain == ""
        assert env.source_path == ""
        assert env.subject_type is None
        assert env.subject_id is None
        assert env.quality == "GOOD"
        assert env.schema_version == "1.0"
        assert env.occurred_at is None
        assert env.correlation_id is None
        assert env.causation_id is None
        assert env.context == {}
        assert env.payload == {}

    def test_optional_occurred_at_none(self):
        env = _make_envelope(occurred_at=None)
        assert env.occurred_at is None

    def test_emitted_at_is_utc_iso(self):
        env = _make_envelope()
        # emitted_at is set by default factory
        assert isinstance(env.emitted_at, str)
        assert "T" in env.emitted_at  # ISO 8601
        assert "+" in env.emitted_at or "Z" in env.emitted_at  # timezone

    def test_full_construction(self):
        env = _make_envelope(
            source_domain="assembly",
            source_path="processor.AP04",
            subject_type="wip",
            subject_id="wip-0001",
            occurred_at="2026-08-09T00:00:12.5Z",
            context={"station_id": "AP04", "flow_id": "base"},
            payload={"event_type": "PROCESS_COMPLETE", "result": "committed"},
            correlation_id="wip-0001",
            causation_id="evt-0041",
        )
        assert env.source_domain == "assembly"
        assert env.source_path == "processor.AP04"
        assert env.subject_type == "wip"
        assert env.subject_id == "wip-0001"
        assert env.occurred_at == "2026-08-09T00:00:12.5Z"
        assert env.context == {"station_id": "AP04", "flow_id": "base"}
        assert env.payload == {"event_type": "PROCESS_COMPLETE", "result": "committed"}

    def test_missing_observation_id_raises(self):
        with pytest.raises(ValueError, match="observation_id"):
            _make_envelope(observation_id="")

    def test_missing_idempotency_key_raises(self):
        with pytest.raises(ValueError, match="idempotency_key"):
            _make_envelope(idempotency_key="")

    def test_missing_run_id_raises(self):
        with pytest.raises(ValueError, match="run_id"):
            _make_envelope(run_id="")

    def test_invalid_simulation_time_raises(self):
        with pytest.raises(ValueError, match="simulation_time_s"):
            _make_envelope(simulation_time_s=-1.0)

    def test_bool_simulation_time_raises(self):
        with pytest.raises(ValueError, match="simulation_time_s"):
            _make_envelope(simulation_time_s=True)  # type: ignore[arg-type]

    def test_invalid_observation_type_raises(self):
        with pytest.raises(ValueError, match="observation_type"):
            _make_envelope(observation_type="bad")  # type: ignore[arg-type]


# ═══════════════════════════════════════════════════
# Idempotency
# ═══════════════════════════════════════════════════

class TestIdempotency:
    def test_same_inputs_same_key(self):
        k1 = make_idempotency_key("run-1", "evt-001", "ap04", "1.0")
        k2 = make_idempotency_key("run-1", "evt-001", "ap04", "1.0")
        assert k1 == k2
        assert k1 == "run-1|evt-001|ap04|1.0"

    def test_different_run_changes_key(self):
        k1 = make_idempotency_key("run-1", "evt-001", "ap04")
        k2 = make_idempotency_key("run-2", "evt-001", "ap04")
        assert k1 != k2

    def test_different_source_event_changes_key(self):
        k1 = make_idempotency_key("run-1", "evt-001", "ap04")
        k2 = make_idempotency_key("run-1", "evt-002", "ap04")
        assert k1 != k2

    def test_different_point_changes_key(self):
        k1 = make_idempotency_key("run-1", "evt-001", "ap04")
        k2 = make_idempotency_key("run-1", "evt-001", "ap06")
        assert k1 != k2

    def test_different_schema_version_changes_key(self):
        k1 = make_idempotency_key("run-1", "evt-001", "ap04", "1.0")
        k2 = make_idempotency_key("run-1", "evt-001", "ap04", "2.0")
        assert k1 != k2

    def test_different_observation_id_same_idempotency(self):
        """observation_id varies but idempotency_key is stable."""
        env1 = _make_envelope(
            observation_id="obs-aaa",
            idempotency_key=make_idempotency_key("run-1", "evt-001", "ap04"),
        )
        env2 = _make_envelope(
            observation_id="obs-bbb",
            idempotency_key=make_idempotency_key("run-1", "evt-001", "ap04"),
        )
        assert env1.observation_id != env2.observation_id
        assert env1.idempotency_key == env2.idempotency_key

    def test_empty_component_raises(self):
        with pytest.raises(ValueError):
            make_idempotency_key("", "evt", "ap04")
        with pytest.raises(ValueError):
            make_idempotency_key("run", "", "ap04")
        with pytest.raises(ValueError):
            make_idempotency_key("run", "evt", "")

    def test_pipe_in_component_raises(self):
        with pytest.raises(ValueError, match="\\|"):
            make_idempotency_key("run|1", "evt", "ap04")


# ═══════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════

class TestSerialization:
    def test_to_dict_preserves_all_fields(self):
        env = _make_envelope(
            source_domain="assembly",
            source_path="processor.AP04",
            subject_type="wip",
            subject_id="wip-0001",
            occurred_at="2026-08-09T00:00:12.5Z",
            context={"station_id": "AP04"},
            payload={"result": "committed"},
            correlation_id="wip-0001",
        )
        d = env.to_dict()
        assert d["observation_id"] == env.observation_id
        assert d["idempotency_key"] == env.idempotency_key
        assert d["observation_type"] == "event"
        assert d["simulation_time_s"] == 12.5
        assert d["occurred_at"] == "2026-08-09T00:00:12.5Z"
        assert d["emitted_at"] == env.emitted_at
        assert d["source_domain"] == "assembly"
        assert d["source_path"] == "processor.AP04"
        assert d["subject_type"] == "wip"
        assert d["subject_id"] == "wip-0001"
        assert d["context"] == {"station_id": "AP04"}
        assert d["correlation_id"] == "wip-0001"
        assert d["schema_version"] == "1.0"

    def test_to_dict_is_json_serializable(self):
        env = _make_envelope(
            subject_type="wip",
            subject_id="wip-0001",
            payload={"value": 1.23, "nested": {"ok": True}},
        )
        json_str = json.dumps(env.to_dict())
        parsed = json.loads(json_str)
        assert parsed["observation_id"] == env.observation_id
        assert parsed["payload"] == {"value": 1.23, "nested": {"ok": True}}

    def test_to_dict_roundtrip_context(self):
        env = _make_envelope(context={"a": 1, "b": [2, 3]})
        d = env.to_dict()
        assert d["context"] == {"a": 1, "b": [2, 3]}


# ═══════════════════════════════════════════════════
# ═══════════════════════════════════════════════════
# Idempotency key validation (in-envelope format check)
# ═══════════════════════════════════════════════════

class TestIdempotencyKeyValidation:
    """idempotency_key must match run_id|source_event_id|point_id|schema_version.
    All 4 parts must be non-empty."""

    def test_valid_key_accepted(self):
        env = _make_envelope(
            run_id="run-1",
            schema_version="1.0",
            idempotency_key="run-1|evt-001|ap04|1.0",
        )
        assert env.idempotency_key == "run-1|evt-001|ap04|1.0"

    def test_too_few_parts_raises(self):
        with pytest.raises(ValueError, match="4 pipe-separated"):
            _make_envelope(idempotency_key="run-1|evt-001|ap04")

    def test_too_many_parts_raises(self):
        with pytest.raises(ValueError, match="4 pipe-separated"):
            _make_envelope(idempotency_key="run-1|evt-001|ap04|1.0|extra")

    def test_empty_source_event_id_raises(self):
        with pytest.raises(ValueError, match="part 1 must be non-empty"):
            _make_envelope(idempotency_key="run-1||ap04|1.0")

    def test_empty_point_id_raises(self):
        with pytest.raises(ValueError, match="part 2 must be non-empty"):
            _make_envelope(idempotency_key="run-1|evt-001||1.0")

    def test_empty_schema_version_raises(self):
        with pytest.raises(ValueError, match="part 3 must be non-empty"):
            _make_envelope(idempotency_key="run-1|evt-001|ap04|")

    def test_empty_run_id_raises(self):
        with pytest.raises(ValueError, match="part 0 must be non-empty"):
            _make_envelope(idempotency_key="|evt-001|ap04|1.0")

    def test_wrong_run_id_raises(self):
        with pytest.raises(ValueError, match="first part must match run_id"):
            _make_envelope(
                run_id="run-2",
                idempotency_key="run-1|evt-001|ap04|1.0",
            )

    def test_wrong_schema_version_raises(self):
        with pytest.raises(ValueError, match="last part must match schema_version"):
            _make_envelope(
                schema_version="2.0",
                idempotency_key="run-1|evt-001|ap04|1.0",
            )


# ═══════════════════════════════════════════════════
# Time validation
# ═══════════════════════════════════════════════════

class TestTimeValidation:
    """occurred_at and emitted_at must be valid ISO 8601 via real datetime parsing."""

    # ── occurred_at ──

    def test_valid_occurred_at_z_accepted(self):
        env = _make_envelope(occurred_at="2026-08-09T00:00:12.5Z")
        assert env.occurred_at == "2026-08-09T00:00:12.5Z"

    def test_valid_occurred_at_offset_accepted(self):
        env = _make_envelope(occurred_at="2026-08-09T00:00:12.5+07:00")
        assert env.occurred_at == "2026-08-09T00:00:12.5+07:00"

    def test_occurred_at_none_accepted(self):
        env = _make_envelope(occurred_at=None)
        assert env.occurred_at is None

    def test_occurred_at_invalid_date_fails(self):
        with pytest.raises(ValueError, match="occurred_at"):
            _make_envelope(occurred_at="2026-02-30T12:00:00Z")

    def test_occurred_at_invalid_month_fails(self):
        with pytest.raises(ValueError, match="occurred_at"):
            _make_envelope(occurred_at="2026-99-99T12:00:00Z")

    def test_occurred_at_invalid_hour_fails(self):
        with pytest.raises(ValueError, match="occurred_at"):
            _make_envelope(occurred_at="2026-08-09T25:00:00Z")

    def test_occurred_at_no_timezone_fails(self):
        with pytest.raises(ValueError, match="occurred_at"):
            _make_envelope(occurred_at="2026-08-09T00:00:12.5")

    # ── emitted_at ──

    def test_default_emitted_at_is_valid_utc(self):
        env = _make_envelope()
        assert env.emitted_at.endswith("Z") or env.emitted_at.endswith("+00:00")

    def test_custom_utc_emitted_at_z_accepted(self):
        env = _make_envelope(emitted_at="2026-08-09T00:00:00Z")
        assert env.emitted_at == "2026-08-09T00:00:00Z"

    def test_custom_utc_emitted_at_plus_zero_accepted(self):
        env = _make_envelope(emitted_at="2026-08-09T00:00:00+00:00")
        assert env.emitted_at == "2026-08-09T00:00:00+00:00"

    def test_emitted_at_non_utc_offset_fails(self):
        with pytest.raises(ValueError, match="emitted_at must be UTC"):
            _make_envelope(emitted_at="2026-08-09T00:00:00+07:00")

    def test_emitted_at_no_timezone_fails(self):
        with pytest.raises(ValueError, match="emitted_at"):
            _make_envelope(emitted_at="2026-08-09T00:00:00")

    def test_emitted_at_invalid_calendar_fails(self):
        with pytest.raises(ValueError, match="emitted_at"):
            _make_envelope(emitted_at="2026-02-30T12:00:00Z")


# ═══════════════════════════════════════════════════
# Immutability (MappingProxyType)
# ═══════════════════════════════════════════════════

class TestImmutability:
    def test_envelope_is_frozen(self):
        env = _make_envelope()
        with pytest.raises(Exception):
            env.observation_id = "mutated"  # type: ignore[misc]

    def test_context_is_read_only(self):
        env = _make_envelope(context={"key": "value"})
        with pytest.raises(TypeError, match="does not support item assignment"):
            env.context["key"] = "mutated"  # type: ignore[index]

    def test_payload_is_read_only(self):
        env = _make_envelope(payload={"val": 1})
        with pytest.raises(TypeError, match="does not support item assignment"):
            env.payload["val"] = 999  # type: ignore[index]

    def test_constructor_arg_mutation_does_not_affect_envelope(self):
        mutable_context = {"key": "original"}
        env = _make_envelope(context=mutable_context)
        mutable_context["key"] = "mutated"
        assert env.context["key"] == "original"

    def test_to_dict_returns_mutable_copy(self):
        env = _make_envelope(context={"k": "v"})
        d = env.to_dict()
        d["context"]["k"] = "mutated"
        # Original envelope unchanged
        assert env.context["k"] == "v"


# ═══════════════════════════════════════════════════
# Architecture boundary
# ═══════════════════════════════════════════════════

class TestArchitectureBoundary:
    def test_no_mes_odoo_imports(self):
        """ObservationEnvelope must not import MES/Odoo modules."""
        import inspect
        import virtual_factory.observation.envelope as mod

        source = inspect.getsource(mod)
        forbidden = [
            "mes_adapter",
            "odoo",
            "MESAdapter",
            "ProductionOrder",
            "MaterialRelease",
            "MESInput",
            "MESOutput",
            "MESEvent",
        ]
        for f in forbidden:
            assert f not in source, f"Found forbidden import: {f}"

    def test_no_protocol_network_imports(self):
        """ObservationEnvelope must not import MQTT/Sparkplug/OPC/HTTP."""
        import inspect
        import virtual_factory.observation.envelope as mod

        source = inspect.getsource(mod)
        forbidden = [
            "mqtt",
            "MQTT",
            "sparkplug",
            "Sparkplug",
            "opcua",
            "OpcUa",
            "fastapi",
            "FastAPI",
            "httpx",
            "requests",
            "socket",
        ]
        for f in forbidden:
            assert f not in source, f"Found forbidden import: {f}"

    def test_no_runtime_imports(self):
        """ObservationEnvelope must not import runtime engine/service."""
        import inspect
        import virtual_factory.observation.envelope as mod

        source = inspect.getsource(mod)
        forbidden = [
            "DiscreteSimulationEngine",
            "DiscreteRunService",
            "AssemblyRuntimeState",
            "DiscreteRunController",
            "HandlerRegistry",
        ]
        for f in forbidden:
            assert f not in source, f"Found forbidden import: {f}"

    def test_no_observation_point_router_projection(self):
        """S01 must not implement ObservationPoint/Router/Projection."""
        import inspect
        import virtual_factory.observation.envelope as mod

        source = inspect.getsource(mod)
        forbidden = [
            "ObservationPoint",
            "ObservationRouter",
            "FieldPolicy",
            "TriggerPolicy",
            "MESProjection",
            "IIoTProjection",
            "ProjectionProtocol",
            "ObservationService",
            "ObservationGateway",
        ]
        for f in forbidden:
            assert f not in source, f"Found forbidden S02+ name: {f}"
