"""VF-DM-M5-S05 — Gateway Protocol + Integration tests."""

import json
import os
import tempfile

import pytest

from virtual_factory.integration.gateway import (
    DeliveryResult,
    DeliveryStatus,
    ObservationGatewayProtocol,
)
from virtual_factory.integration.gateways.memory import InMemoryObsGateway
from virtual_factory.integration.gateways.jsonl import JsonlObsGateway
from virtual_factory.integration.gateways.mqtt import MqttObsGateway
from virtual_factory.observation.projection import ProjectedMessage
from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
)
from virtual_factory.observation.point import (
    FieldPolicy,
    ObservationPoint,
    TriggerKind,
    TriggerPolicy,
)
from virtual_factory.observation.service import (
    ObservationService,
    RealityInput,
)
from virtual_factory.observation.router import (
    ObservationRouter,
    ProjectionSubscription,
)
from virtual_factory.observation.projections.mes import MESProjection
from virtual_factory.observation.projections.iiot import IIoTProjection


# ═══════════════════════════════════════════════════
# DeliveryResult
# ═══════════════════════════════════════════════════

class TestDeliveryResult:
    def test_delivered(self):
        r = DeliveryResult(gateway_id="gw", message_key="k1", status=DeliveryStatus.DELIVERED)
        assert r.status == DeliveryStatus.DELIVERED

    def test_failed(self):
        r = DeliveryResult(gateway_id="gw", message_key="k1", status=DeliveryStatus.FAILED,
                           error_code="E01")
        assert r.error_code == "E01"

    def test_immutable(self):
        r = DeliveryResult(gateway_id="gw", message_key="k1", status=DeliveryStatus.DELIVERED)
        with pytest.raises(Exception):
            r.status = DeliveryStatus.FAILED  # type: ignore[misc]


# ═══════════════════════════════════════════════════
# InMemoryObsGateway
# ═══════════════════════════════════════════════════

class TestInMemoryGateway:
    def test_send_stores_message(self):
        gw = InMemoryObsGateway()
        msg = ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k")
        r = gw.send(msg)
        assert r.status == DeliveryStatus.DELIVERED
        assert len(gw.messages) == 1

    def test_preserves_key(self):
        gw = InMemoryObsGateway()
        msg = ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="my-key")
        r = gw.send(msg)
        assert r.message_key == "my-key"

    def test_does_not_mutate_message(self):
        gw = InMemoryObsGateway()
        msg = ProjectedMessage(projection_id="p", message_type="t", schema_name="s",
                               key="k", payload={"a": 1})
        gw.send(msg)
        assert msg.payload["a"] == 1

    def test_failure_injection(self):
        gw = InMemoryObsGateway()
        gw.set_fail_next(2)
        msg = ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k1")
        assert gw.send(msg).status == DeliveryStatus.FAILED
        assert gw.send(msg).status == DeliveryStatus.FAILED
        assert gw.send(msg).status == DeliveryStatus.DELIVERED
        assert len(gw.messages) == 1


# ═══════════════════════════════════════════════════
# JsonlObsGateway
# ═══════════════════════════════════════════════════

class TestJsonlGateway:
    def test_writes_one_line(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            path = f.name
        try:
            gw = JsonlObsGateway(path, gateway_id="jsonl-test")
            msg = ProjectedMessage(projection_id="mes", message_type="mes.event",
                                   schema_name="vf.mes.event", key="k1",
                                   payload={"result": "PASS"})
            r = gw.send(msg)
            assert r.status == DeliveryStatus.DELIVERED
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["message_key"] == "k1"
            assert data["payload"]["result"] == "PASS"
        finally:
            os.unlink(path)

    def test_appends_multiple(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            path = f.name
        try:
            gw = JsonlObsGateway(path)
            gw.send(ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k1"))
            gw.send(ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k2"))
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════
# MqttObsGateway (mocked)
# ═══════════════════════════════════════════════════

class MockMqttClient:
    """Minimal mock for paho.mqtt.client."""
    def __init__(self):
        self.published: list[tuple] = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


class TestMqttGateway:
    def test_send_publishes(self):
        gw = MqttObsGateway(
            topic_map={"mes.event": "vf/mes/events"},
        )
        mock = MockMqttClient()
        gw.set_client(mock)
        msg = ProjectedMessage(projection_id="mes", message_type="mes.event",
                               schema_name="vf.mes.event", key="k1",
                               payload={"result": "PASS"})
        r = gw.send(msg)
        assert r.status == DeliveryStatus.DELIVERED
        assert len(mock.published) == 1
        topic, payload_str, qos, retain = mock.published[0]
        assert topic == "vf/mes/events"
        payload = json.loads(payload_str)
        assert payload["message_key"] == "k1"

    def test_qos_and_retain(self):
        gw = MqttObsGateway(topic_map={"x": "t"}, qos=2, retain=True)
        mock = MockMqttClient()
        gw.set_client(mock)
        gw.send(ProjectedMessage(projection_id="p", message_type="x", schema_name="s", key="k"))
        _, _, qos, retain = mock.published[0]
        assert qos == 2
        assert retain is True

    def test_unmapped_type_skipped(self):
        gw = MqttObsGateway(topic_map={})
        mock = MockMqttClient()
        gw.set_client(mock)
        r = gw.send(ProjectedMessage(projection_id="p", message_type="unknown", schema_name="s", key="k"))
        assert r.status == DeliveryStatus.SKIPPED

    def test_no_client_fails(self):
        gw = MqttObsGateway()
        r = gw.send(ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k"))
        assert r.status == DeliveryStatus.FAILED

    def test_wildcard_topic_match(self):
        gw = MqttObsGateway(topic_map={"mes.*": "vf/mes"})
        mock = MockMqttClient()
        gw.set_client(mock)
        gw.send(ProjectedMessage(projection_id="p", message_type="mes.quality_result", schema_name="s", key="k"))
        assert mock.published[0][0] == "vf/mes"


# ═══════════════════════════════════════════════════
# End-to-End M5 proof
# ═══════════════════════════════════════════════════

class TestEndToEndM5:
    def test_full_chain_reality_to_delivery(self):
        """RealityInput → Service → Router → Projections → Gateway."""
        # Setup service
        svc = ObservationService()
        svc.add_point(ObservationPoint(
            point_id="ap06-test",
            observation_type=ObservationType.EVENT,
            label="AP06 Test",
            source_type="assembly.event",
            source_filter={"event_type": "QUALITY_CHECK", "target_id": "AP06"},
            trigger=TriggerPolicy(kind=TriggerKind.ON_EVENT, event_types=("QUALITY_CHECK",)),
            fields=FieldPolicy(extract=("event_type", "result", "target_id")),
            context_map={"semantic_type": "semantic_type"},
        ))

        # Setup router
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(projection=MESProjection()))
        router.subscribe(ProjectionSubscription(projection=IIoTProjection()))

        # Setup gateways
        mem_gw = InMemoryObsGateway(gateway_id="mes-mem")
        iiot_gw = InMemoryObsGateway(gateway_id="iiot-mem")

        # Reality input
        reality = RealityInput(
            run_id="e2e-1", model_id="tipa",
            source_event_id="evt-ap06-001",
            source_type="assembly.event",
            source_domain="assembly", source_path="processor.AP06",
            simulation_time_s=99.0,
            source_data={
                "event_type": "QUALITY_CHECK",
                "result": "PASS",
                "target_id": "AP06",
                "semantic_type": "quality_result",
            },
            subject_type="wip", subject_id="MOTOR-000123",
        )

        # Collect
        envelopes = svc.collect(reality)
        assert len(envelopes) == 1

        # Route
        projected = router.route(envelopes[0])
        assert len(projected) == 2  # MES + IIoT

        # Deliver
        for msg in projected:
            if msg.projection_id == "mes":
                r = mem_gw.send(msg)
            else:
                r = iiot_gw.send(msg)
            assert r.status == DeliveryStatus.DELIVERED

        # Verify MES delivery
        assert len(mem_gw.messages) == 1
        assert mem_gw.messages[0].message_type == "mes.quality_result"

        # Verify IIoT delivery
        assert len(iiot_gw.messages) == 1

    def test_gateway_failure_leaves_artifacts_unchanged(self):
        """Failed delivery must not mutate observation artifacts."""
        svc = ObservationService()
        svc.add_point(ObservationPoint(
            point_id="p1", observation_type=ObservationType.EVENT,
            label="L", source_type="assembly.event",
            source_filter={},
            trigger=TriggerPolicy(kind=TriggerKind.ON_EVENT),
            fields=FieldPolicy(extract=("event_type",)),
        ))
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(projection=MESProjection()))

        reality = RealityInput(
            run_id="r1", model_id="m1", source_event_id="e1",
            source_type="assembly.event", source_domain="a", source_path="p",
            simulation_time_s=0, source_data={"event_type": "PROCESS_COMPLETE"},
        )

        envelopes = svc.collect(reality)
        envelope_before = envelopes[0].to_dict()
        projected = router.route(envelopes[0])
        msg_before_key = projected[0].key

        # Fail the gateway
        gw = InMemoryObsGateway()
        gw.set_fail_next(1)
        r = gw.send(projected[0])
        assert r.status == DeliveryStatus.FAILED

        # Envelope unchanged
        assert envelopes[0].to_dict() == envelope_before
        # Message unchanged
        assert projected[0].key == msg_before_key


# ═══════════════════════════════════════════════════
# Architecture Boundaries
# ═══════════════════════════════════════════════════

class TestArchitectureBoundary:
    def test_gateway_no_engine_imports(self):
        import inspect
        import virtual_factory.integration.gateway as mod
        source = inspect.getsource(mod)
        forbidden = ["from virtual_factory.discrete", "from virtual_factory.assembly",
                     "HandlerRegistry", "DiscreteRunService", "AssemblyRuntimeState"]
        for f in forbidden:
            assert f not in source

    def test_gateways_no_engine_imports(self):
        import inspect
        import virtual_factory.integration.gateways.mqtt as mod
        source = inspect.getsource(mod)
        forbidden = ["from virtual_factory.discrete", "from virtual_factory.assembly",
                     "HandlerRegistry", "import odoo"]
        for f in forbidden:
            assert f not in source

    def test_no_topic_in_projected_message(self):
        """ProjectedMessage must not have topic field."""
        msg = ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k")
        assert not hasattr(msg, "topic")
        assert not hasattr(msg, "mqtt_topic")

    def test_observation_point_no_topic(self):
        """ObservationPoint must not have topic field."""
        p = ObservationPoint(
            point_id="p", observation_type=ObservationType.EVENT,
            label="L", source_type="s",
        )
        assert not hasattr(p, "topic")

    def test_observation_envelope_no_topic(self):
        env = ObservationEnvelope(
            observation_id="o", idempotency_key="r|e|p|1.0",
            observation_type=ObservationType.EVENT,
            run_id="r", model_id="m", simulation_time_s=0,
        )
        assert not hasattr(env, "topic")
