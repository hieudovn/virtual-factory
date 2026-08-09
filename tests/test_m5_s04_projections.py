"""VF-DM-M5-S04 — Projections + ObservationRouter + ControlBoundary tests."""

import pytest

from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)
from virtual_factory.observation.projection import ProjectedMessage
from virtual_factory.observation.router import (
    ObservationRouter,
    ProjectionSubscription,
)
from virtual_factory.observation.projections.mes import MESProjection
from virtual_factory.observation.projections.iiot import IIoTProjection
from virtual_factory.integration.control_boundary import (
    ControlBoundary,
    ControlCommand,
    ControlCommandKind,
    MaterialContext,
    ProductionContext,
    QualitySpecContext,
    SimulationControlBatch,
)


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

def _make_envelope(**overrides) -> ObservationEnvelope:
    defaults = {
        "observation_id": "obs-001",
        "idempotency_key": "run-1|evt-001|ap06|1.0",
        "observation_type": ObservationType.EVENT,
        "run_id": "run-1",
        "model_id": "tipa",
        "simulation_time_s": 42.0,
        "source_domain": "assembly",
        "source_path": "processor.AP06",
        "subject_type": "wip",
        "subject_id": "MOTOR-000123",
        "context": {"station_id": "AP06"},
        "payload": {"event_type": "PROCESS_COMPLETE", "result": "PASS"},
        "correlation_id": "wip-0001",
        "causation_id": "evt-000",
    }
    defaults.update(overrides)
    return ObservationEnvelope(**defaults)


# ═══════════════════════════════════════════════════
# ProjectedMessage
# ═══════════════════════════════════════════════════

class TestProjectedMessage:
    def test_construction(self):
        msg = ProjectedMessage(
            projection_id="mes", message_type="mes.event",
            schema_name="vf.mes.event", key="k1",
            payload={"a": 1},
        )
        assert msg.projection_id == "mes"
        assert msg.schema_name == "vf.mes.event"

    def test_payload_is_read_only(self):
        msg = ProjectedMessage(
            projection_id="mes", message_type="mes.event",
            schema_name="vf.mes.event", payload={"a": 1},
        )
        with pytest.raises(TypeError):
            msg.payload["a"] = 2  # type: ignore[index]

    def test_required_fields(self):
        with pytest.raises(ValueError):
            ProjectedMessage(projection_id="", message_type="x", schema_name="x")


# ═══════════════════════════════════════════════════
# ObservationRouter
# ═══════════════════════════════════════════════════

class TestRouter:
    def test_zero_matching_projections(self):
        router = ObservationRouter()
        assert router.route(_make_envelope()) == []

    def test_one_matching_projection(self):
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(
            projection=MESProjection(),
            observation_types=(ObservationType.EVENT,),
        ))
        results = router.route(_make_envelope())
        assert len(results) == 1
        assert results[0].projection_id == "mes"

    def test_multiple_matching_projections(self):
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(
            projection=MESProjection(),
            observation_types=(ObservationType.EVENT,),
        ))
        router.subscribe(ProjectionSubscription(
            projection=IIoTProjection(),
            observation_types=(ObservationType.EVENT,),
        ))
        results = router.route(_make_envelope())
        assert len(results) == 2
        ids = {r.projection_id for r in results}
        assert ids == {"mes", "iiot"}

    def test_router_does_not_mutate_envelope(self):
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(
            projection=MESProjection(),
            observation_types=(ObservationType.EVENT,),
        ))
        env = _make_envelope()
        before = env.to_dict()
        router.route(env)
        after = env.to_dict()
        assert before == after

    def test_subscription_type_filter(self):
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(
            projection=MESProjection(),
            observation_types=(ObservationType.MEASUREMENT,),
        ))
        assert router.route(_make_envelope(observation_type=ObservationType.EVENT)) == []

    def test_subscription_domain_filter(self):
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(
            projection=IIoTProjection(),
            source_domains=("continuous",),
        ))
        assert router.route(_make_envelope(source_domain="assembly")) == []

    def test_predicate_filter(self):
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(
            projection=MESProjection(),
            predicate=lambda e: e.payload.get("result") == "FAIL",
        ))
        assert router.route(_make_envelope(payload={"result": "PASS"})) == []


# ═══════════════════════════════════════════════════
# MESProjection
# ═══════════════════════════════════════════════════

class TestMESProjection:
    def test_event_envelope_produces_execution_event(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(observation_type=ObservationType.EVENT))
        assert msg is not None
        assert msg.message_type == "mes.execution_event"
        assert "observation_id" in msg.payload
        assert msg.key == _make_envelope().idempotency_key

    def test_measurement_envelope_produces_measurement(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.MEASUREMENT,
            payload={"value": 72.4, "unit": "degC"},
        ))
        assert msg is not None
        assert msg.message_type == "mes.measurement"
        assert msg.payload.get("value") == 72.4

    def test_subject_preserved(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope())
        assert msg.payload["subject_type"] == "wip"
        assert msg.payload["subject_id"] == "MOTOR-000123"

    def test_station_from_context(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(context={"station_id": "AP06"}))
        assert msg.payload["station_id"] == "AP06"

    def test_correlation_preserved(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope())
        assert msg.headers["correlation_id"] == "wip-0001"

    def test_schema_name_matches_type(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.STATE,
            payload={},  # no event_type → falls through to STATE generic
        ))
        assert msg.schema_name == "vf.mes.state_snapshot"

    def test_no_odoo_ids(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope())
        for v in msg.payload.values():
            if isinstance(v, str):
                assert "odoo" not in v.lower()

    def test_quality_check_produces_quality_result(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.EVENT,
            payload={"event_type": "QUALITY_CHECK", "result": "PASS", "disposition": "pass"},
        ))
        assert msg is not None
        assert msg.message_type == "mes.quality_result"
        assert msg.schema_name == "vf.mes.quality_result"

    def test_checklist_complete_produces_checklist_result(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.EVENT,
            payload={"event_type": "CHECKLIST_COMPLETE", "result": "OK"},
        ))
        assert msg is not None
        assert msg.message_type == "mes.checklist_result"

    def test_explicit_semantic_type_overrides(self):
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.EVENT,
            context={"semantic_type": "genealogy_relationship"},
            payload={"event_type": "PROCESS_COMPLETE"},
        ))
        assert msg is not None
        assert msg.message_type == "mes.genealogy_relationship"

    def test_irrelevant_envelope_returns_none(self):
        """HUMAN_ENTRY without semantic_type → None (irrelevant)."""
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.HUMAN_ENTRY,
            payload={"event_type": "OPERATOR_NOTE"},
        ))
        assert msg is None

    def test_unknown_event_type_returns_none(self):
        """EVENT with unknown event_type → None (insufficient semantics)."""
        proj = MESProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.EVENT,
            payload={"event_type": "MYSTERY_EVENT"},
        ))
        assert msg is None


# ═══════════════════════════════════════════════════
# IIoTProjection
# ═══════════════════════════════════════════════════

class TestIIoTProjection:
    def test_measurement_produces_iiot_signal(self):
        proj = IIoTProjection()
        msg = proj.project(_make_envelope(
            observation_type=ObservationType.MEASUREMENT,
            payload={"temperature": 72.4},
        ))
        assert msg is not None
        assert msg.message_type == "iiot.signal"
        assert msg.payload.get("temperature") == 72.4

    def test_event_produces_iiot_event(self):
        proj = IIoTProjection()
        msg = proj.project(_make_envelope(observation_type=ObservationType.EVENT))
        assert msg.message_type == "iiot.event"

    def test_source_path_preserved(self):
        proj = IIoTProjection()
        msg = proj.project(_make_envelope())
        assert msg.payload["source_path"] == "processor.AP06"

    def test_no_mqtt_topic(self):
        proj = IIoTProjection()
        msg = proj.project(_make_envelope())
        assert "mqtt" not in str(msg.payload).lower()
        assert "topic" not in str(msg.payload).lower()

    def test_hidden_fields_not_reappear(self):
        """Secret fields blocked upstream should not reappear in IIoT."""
        proj = IIoTProjection()
        msg = proj.project(_make_envelope(payload={"visible": 1}))
        assert "internal_truth" not in msg.payload


# ═══════════════════════════════════════════════════
# Multi-projection proof
# ═══════════════════════════════════════════════════

class TestMultiProjection:
    def test_same_envelope_mes_and_iiot(self):
        env = _make_envelope(observation_type=ObservationType.MEASUREMENT,
                             payload={"resistance_u_v": 0.5})
        mes = MESProjection().project(env)
        iiot = IIoTProjection().project(env)
        assert mes is not None
        assert iiot is not None
        assert mes.projection_id != iiot.projection_id

    def test_observation_id_traceable_in_both(self):
        env = _make_envelope()
        mes = MESProjection().project(env)
        iiot = IIoTProjection().project(env)
        assert mes.payload["observation_id"] == env.observation_id
        assert iiot.payload["observation_id"] == env.observation_id

    def test_idempotency_key_traceable_in_both(self):
        env = _make_envelope()
        mes = MESProjection().project(env)
        iiot = IIoTProjection().project(env)
        assert mes.key == env.idempotency_key
        assert iiot.key == env.idempotency_key


# ═══════════════════════════════════════════════════
# ControlBoundary
# ═══════════════════════════════════════════════════

class TestControlBoundary:
    def test_production_context_translated(self):
        boundary = ControlBoundary()
        batch = boundary.translate(
            run_id="r1", model_id="m1",
            production=ProductionContext(
                production_order_ref="MO-001", product_ref="SSO2",
            ),
        )
        assert batch.production_context is not None
        assert batch.production_context.production_order_ref == "MO-001"

    def test_control_command_translated(self):
        boundary = ControlBoundary()
        cmd = ControlCommand(
            command_id="cmd-1", command_type=ControlCommandKind.START,
            target_ref="source-1",
        )
        batch = boundary.translate("r1", "m1", commands=(cmd,))
        assert len(batch.commands) == 1
        assert batch.commands[0].command_type == ControlCommandKind.START

    def test_material_context_translated(self):
        boundary = ControlBoundary()
        mat = MaterialContext(
            release_id="R1", material_ref="SSO2", source_ref="source-1",
        )
        batch = boundary.translate("r1", "m1", materials=(mat,))
        assert len(batch.material_contexts) == 1
        assert batch.material_contexts[0].source_ref == "source-1"

    def test_quality_spec_translated(self):
        boundary = ControlBoundary()
        qs = QualitySpecContext(
            requirement_id="QR-1", test_type="resistance",
            min_value=0.1, max_value=1.0, unit="ohm",
        )
        batch = boundary.translate("r1", "m1", quality=(qs,))
        assert batch.quality_specs[0].min_value == 0.1
        assert batch.quality_specs[0].unit == "ohm"

    def test_no_engine_call(self):
        """ControlBoundary must not import Engine/HandlerRegistry."""
        import inspect
        import virtual_factory.integration.control_boundary as mod
        source = inspect.getsource(mod)
        forbidden = ["from virtual_factory.discrete",
                     "from virtual_factory.assembly",
                     "DiscreteRunService"]
        for f in forbidden:
            assert f not in source, f"control_boundary imports {f}"

    def test_simulation_control_batch_immutable(self):
        batch = SimulationControlBatch(run_id="r1", model_id="m1")
        with pytest.raises(Exception):
            batch.run_id = "mutated"  # type: ignore[misc]

    def test_no_odoo_dependency(self):
        import inspect
        import virtual_factory.integration.control_boundary as mod
        source = inspect.getsource(mod)
        assert "import odoo" not in source
        assert "from odoo" not in source

    def test_production_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="quantity"):
            ProductionContext(
                production_order_ref="MO-001", product_ref="SSO2", quantity=0,
            )

    def test_material_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="quantity"):
            MaterialContext(
                release_id="R1", material_ref="SSO2", quantity=-1,
            )

    def test_command_type_must_be_enum(self):
        with pytest.raises(ValueError, match="command_type"):
            ControlCommand(
                command_id="c1", command_type="start", target_ref="t1",  # type: ignore[arg-type]
            )

    def test_simulation_control_batch_model_id_required(self):
        with pytest.raises(ValueError, match="model_id"):
            SimulationControlBatch(run_id="r1", model_id="")


# ═══════════════════════════════════════════════════
# M4 Compatibility
# ═══════════════════════════════════════════════════

class TestM4Compatibility:
    def test_m4_mes_adapter_intact(self):
        """M4 MESAdapter must still be importable and functional."""
        from virtual_factory.assembly.mes_adapter import (
            MESAdapter, MESInput, MESOutput, MESEvent, MESEventType,
            ProductionOrder, MaterialRelease,
        )
        adapter = MESAdapter()
        inp = MESInput(
            run_id="r1",
            production_orders=[ProductionOrder(order_id="MO-001", product_id="SSO2", quantity=1)],
            material_releases=[MaterialRelease(release_id="R1", order_id="MO-001", wip_id="w-1", source_id="sso2-1")],
        )
        result = adapter.mes_to_simulation(inp)
        assert result["run_id"] == "r1"

        sim_events = [{"event_id": "e1", "event_type": "PROCESS_COMPLETE",
                        "simulation_time_s": 1.0, "wip_id": "w-1", "target_id": "AP01"}]
        output = adapter.simulation_to_mes("r1", "completed", sim_events)
        assert output.run_id == "r1"
        assert len(output.events) == 1


# ═══════════════════════════════════════════════════
# Architecture Boundaries
# ═══════════════════════════════════════════════════

class TestArchitectureBoundary:
    def test_no_gateway_in_router(self):
        import inspect
        import virtual_factory.observation.router as mod
        source = inspect.getsource(mod)
        forbidden = ["Gateway", "mqtt", "MQTT", "rest", "REST", "opc", "socket"]
        for f in forbidden:
            assert f not in source, f"router.py contains {f}"

    def test_no_network_in_projections(self):
        import inspect
        import virtual_factory.observation.projections.mes as mod
        source = inspect.getsource(mod)
        forbidden = ["import mqtt", "import http", "import socket",
                     "import odoo", "import requests"]
        for f in forbidden:
            assert f not in source, f"mes.py contains {f}"
