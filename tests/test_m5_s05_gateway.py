"""VF-DM-M5-S05-C01 — Gateway Contract / MQTT Reuse / Serialization tests."""

import json
import os
import tempfile
from typing import Sequence

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
from virtual_factory.protocols.mqtt_gateway import MqttGateway


# ═══════════════════════════════════════════════════
# MockMqttGateway — composition test double
# ═══════════════════════════════════════════════════

class MockMqttGateway:
    """Mock for existing MqttGateway transport — has publish_raw()."""
    def __init__(self, fail_rc: int = 0, raise_on_publish: bool = False):
        self.published: list[tuple] = []
        self._fail_rc = fail_rc
        self._raise = raise_on_publish

    def publish_raw(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> int:
        if self._raise:
            raise ConnectionError("mock connection error")
        self.published.append((topic, payload, qos, retain))
        return self._fail_rc


# ═══════════════════════════════════════════════════
# Protocol type safety
# ═══════════════════════════════════════════════════

class TestProtocolTypeSafety:
    def test_protocol_uses_projected_message_not_any(self):
        """ObservationGatewayProtocol.send takes ProjectedMessage, not Any."""
        import inspect
        import virtual_factory.integration.gateway as mod
        source = inspect.getsource(mod)
        assert "ProjectedMessage" in source
        assert "send(self, message: ProjectedMessage)" in source or \
               "send(self, message: ProjectedMessage) -> DeliveryResult" in source

    def test_in_memory_implements_protocol(self):
        gw = InMemoryObsGateway()
        assert isinstance(gw, ObservationGatewayProtocol)


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
        finally:
            os.unlink(path)

    def test_unsupported_object_fails_and_no_line(self):
        """Non-JSON-serializable payload must FAILED, no line appended."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as f:
            path = f.name
        try:
            gw = JsonlObsGateway(path)
            msg = ProjectedMessage(projection_id="p", message_type="t",
                                   schema_name="s", key="k",
                                   payload={"bad": object()})
            r = gw.send(msg)
            assert r.status == DeliveryStatus.FAILED
            assert r.error_code == "serialization_error"
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 0  # nothing written
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════
# MqttObsGateway — real composition via MockMqttGateway
# ═══════════════════════════════════════════════════

class TestMqttGateway:
    def test_send_publishes_via_mqtt_gateway(self):
        gw = MqttObsGateway(topic_map={"mes.event": "vf/mes/events"})
        mock = MockMqttGateway()
        gw.set_mqtt(mock)
        msg = ProjectedMessage(projection_id="mes", message_type="mes.event",
                               schema_name="vf.mes.event", key="k1",
                               payload={"result": "PASS"})
        r = gw.send(msg)
        assert r.status == DeliveryStatus.DELIVERED
        assert len(mock.published) == 1
        topic, payload_str, qos, retain = mock.published[0]
        assert topic == "vf/mes/events"
        data = json.loads(payload_str)
        assert data["message_key"] == "k1"

    def test_qos_and_retain(self):
        gw = MqttObsGateway(topic_map={"x": "t"}, qos=2, retain=True)
        mock = MockMqttGateway()
        gw.set_mqtt(mock)
        gw.send(ProjectedMessage(projection_id="p", message_type="x", schema_name="s", key="k"))
        _, _, qos, retain = mock.published[0]
        assert qos == 2
        assert retain is True

    def test_unmapped_type_skipped(self):
        gw = MqttObsGateway(topic_map={})
        mock = MockMqttGateway()
        gw.set_mqtt(mock)
        r = gw.send(ProjectedMessage(projection_id="p", message_type="unknown", schema_name="s", key="k"))
        assert r.status == DeliveryStatus.SKIPPED

    def test_no_transport_fails(self):
        gw = MqttObsGateway()
        r = gw.send(ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k"))
        assert r.status == DeliveryStatus.FAILED
        assert r.error_code == "no_transport"

    def test_wildcard_topic_match(self):
        gw = MqttObsGateway(topic_map={"mes.*": "vf/mes"})
        mock = MockMqttGateway()
        gw.set_mqtt(mock)
        gw.send(ProjectedMessage(projection_id="p", message_type="mes.quality_result", schema_name="s", key="k"))
        assert mock.published[0][0] == "vf/mes"

    def test_unsupported_object_fails_no_publish(self):
        """Non-serializable payload → FAILED, publish not called."""
        gw = MqttObsGateway(topic_map={"mes.event": "vf/mes"})
        mock = MockMqttGateway()
        gw.set_mqtt(mock)
        msg = ProjectedMessage(projection_id="p", message_type="mes.event",
                               schema_name="s", key="k", payload={"bad": object()})
        r = gw.send(msg)
        assert r.status == DeliveryStatus.FAILED
        assert r.error_code == "serialization_error"
        assert len(mock.published) == 0

    def test_publish_non_zero_rc_fails(self):
        """MQTT rc != 0 → FAILED."""
        gw = MqttObsGateway(topic_map={"t": "topic"})
        mock = MockMqttGateway(fail_rc=1)
        gw.set_mqtt(mock)
        r = gw.send(ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k"))
        assert r.status == DeliveryStatus.FAILED
        assert r.error_code == "publish_rc"

    def test_publish_exception_fails(self):
        """MQTT exception → FAILED."""
        gw = MqttObsGateway(topic_map={"t": "topic"})
        mock = MockMqttGateway(raise_on_publish=True)
        gw.set_mqtt(mock)
        r = gw.send(ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k"))
        assert r.status == DeliveryStatus.FAILED
        assert r.error_code == "publish_error"

    def test_reuses_existing_mqtt_gateway_composition(self):
        """MqttObsGateway composes MqttGateway, not a raw paho client."""
        gw = MqttObsGateway(topic_map={"t": "topic"})
        real = MqttGateway(enabled=False)  # no real connection
        gw.set_mqtt(real)
        assert gw._mqtt is real


# ═══════════════════════════════════════════════════
# End-to-End M5 proof
# ═══════════════════════════════════════════════════

class TestEndToEndM5:
    def test_full_chain_reality_to_delivery(self):
        svc = ObservationService()
        svc.add_point(ObservationPoint(
            point_id="ap06-test", observation_type=ObservationType.EVENT,
            label="AP06 Test", source_type="assembly.event",
            source_filter={"event_type": "QUALITY_CHECK", "target_id": "AP06"},
            trigger=TriggerPolicy(kind=TriggerKind.ON_EVENT, event_types=("QUALITY_CHECK",)),
            fields=FieldPolicy(extract=("event_type", "result", "target_id")),
            context_map={"semantic_type": "semantic_type"},
        ))
        router = ObservationRouter()
        router.subscribe(ProjectionSubscription(projection=MESProjection()))
        router.subscribe(ProjectionSubscription(projection=IIoTProjection()))
        mem_gw = InMemoryObsGateway(gateway_id="mes-mem")
        iiot_gw = InMemoryObsGateway(gateway_id="iiot-mem")

        reality = RealityInput(
            run_id="e2e-1", model_id="tipa", source_event_id="evt-001",
            source_type="assembly.event", source_domain="assembly",
            source_path="processor.AP06", simulation_time_s=99.0,
            source_data={"event_type": "QUALITY_CHECK", "result": "PASS",
                         "target_id": "AP06", "semantic_type": "quality_result"},
            subject_type="wip", subject_id="MOTOR-000123",
        )
        envelopes = svc.collect(reality)
        assert len(envelopes) == 1
        projected = router.route(envelopes[0])
        assert len(projected) == 2
        for msg in projected:
            gw = mem_gw if msg.projection_id == "mes" else iiot_gw
            assert gw.send(msg).status == DeliveryStatus.DELIVERED
        assert len(mem_gw.messages) == 1
        assert mem_gw.messages[0].message_type == "mes.quality_result"
        assert len(iiot_gw.messages) == 1

    def test_gateway_failure_leaves_artifacts_unchanged(self):
        svc = ObservationService()
        svc.add_point(ObservationPoint(
            point_id="p1", observation_type=ObservationType.EVENT,
            label="L", source_type="assembly.event", source_filter={},
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
        reality_before = reality.source_data.copy()
        envelopes = svc.collect(reality)
        env_before = envelopes[0].to_dict()
        projected = router.route(envelopes[0])
        msg_key_before = projected[0].key

        gw = InMemoryObsGateway()
        gw.set_fail_next(1)
        assert gw.send(projected[0]).status == DeliveryStatus.FAILED

        # RealityInput unchanged
        assert reality.source_data == reality_before
        # Envelope unchanged
        assert envelopes[0].to_dict() == env_before
        # Message key unchanged
        assert projected[0].key == msg_key_before


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

    def test_no_topic_in_projected_message(self):
        msg = ProjectedMessage(projection_id="p", message_type="t", schema_name="s", key="k")
        assert not hasattr(msg, "topic")

    def test_observation_point_no_topic(self):
        p = ObservationPoint(point_id="p", observation_type=ObservationType.EVENT,
                             label="L", source_type="s")
        assert not hasattr(p, "topic")

    def test_observation_envelope_no_topic(self):
        env = ObservationEnvelope(observation_id="o", idempotency_key="r|e|p|1.0",
                                  observation_type=ObservationType.EVENT,
                                  run_id="r", model_id="m", simulation_time_s=0)
        assert not hasattr(env, "topic")

    def test_existing_mqtt_gateway_unchanged(self):
        """Existing MqttGateway API preserved (publish_frame still works)."""
        assert hasattr(MqttGateway, "publish_frame")
        assert hasattr(MqttGateway, "publish_raw")  # new, backward-compatible
