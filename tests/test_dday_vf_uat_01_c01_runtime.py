"""DDAY-VF-UAT-01-C01 — durable Bottled Water MQTT runtime."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from virtual_factory.main import build_parser
from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.workspaces.dday_bw_runtime import (
    COMMAND,
    DICTIONARY_SHA256,
    PROFILE_ID,
    WORKSPACE_DIR,
    WORKSPACE_ID,
    run_dday_bw_runtime,
    verify_runtime_identity,
)
from virtual_factory.workspaces.plantos_export import CONTRACT_VERSION, SIX_EVENT_TYPES, utc_timestamp

REPO = Path(__file__).resolve().parent.parent
COMPOSE = REPO / "deploy" / "dday-vf-uat.compose.yml"
LAUNCHER = REPO / "src" / "virtual_factory" / "workspaces" / "dday_bw_runtime.py"
FAST_KEYS = {
    ("BW-FP-CAP01", "motor_current"),
    ("BW-FP-CAP01", "drive_load"),
    ("BW-FP-CAP01", "vibration_rms"),
    ("BW-FP-CAP01", "speed"),
    ("BW-FP-CAP01", "cycle_time"),
    ("BW-FP-CAP01", "cap_torque"),
}
MEDIUM_KEYS = {
    ("BW-FP-FIL01", "fill_rate"),
    ("BW-UT-CMP01", "air_pressure"),
    ("BW-UT-CMP01", "active_power"),
    ("BW-UT-PWR01", "plant_active_power"),
    ("BW-FP-CAP01", "bearing_temperature"),
}
SLOW_KEYS = {
    ("BW-WT-FEED01", "water_flow"),
    ("BW-WT-RO01", "production_flow"),
    ("BW-WT-TK01", "level"),
    ("BW-UT-CMP01", "energy_total"),
    ("BW-UT-PWR01", "plant_energy_total"),
}
COUNT_KEYS = {
    ("BW-FP", "total_count"),
    ("BW-FP", "good_count"),
    ("BW-FP", "reject_count"),
    ("BW-WH-FG01", "inventory_count"),
    ("BW-WH-FG01", "receipt_count"),
    ("BW-WH-FG01", "dispatch_count"),
}


class _AckHandle:
    def __init__(self, rc: int = 0, acked: bool = True) -> None:
        self.rc = rc
        self.acked = acked

    def is_published(self) -> bool:
        return self.acked

    def wait_for_publish(self, timeout: float = 1.0) -> None:
        if not self.acked:
            raise TimeoutError("publish acknowledgement timed out")


class _Recorder:
    def __init__(self, acked: bool = True, rc: int = 0) -> None:
        self.recorded: list[tuple[str, str, int]] = []
        self.acked = acked
        self.rc = rc
        self.disconnected = False

    def connect(self, host, port):
        return None

    def loop_start(self) -> None:
        return None

    def loop_stop(self) -> None:
        return None

    def publish(self, topic, payload, qos=0, retain=False):
        self.recorded.append((topic, payload, qos))
        return _AckHandle(self.rc, self.acked)

    def disconnect(self) -> None:
        self.disconnected = True


def _keys(recorder: _Recorder, kind: str) -> list[tuple[str, str]]:
    out = []
    for topic, payload, _qos in recorder.recorded:
        if f"/{kind}/" not in topic:
            continue
        data = json.loads(payload)
        if kind == "signal":
            out.append((data["source_id"], data["signal_id"]))
        else:
            out.append((data["source_id"], data["event_type"]))
    return out


def _payloads(recorder: _Recorder, kind: str) -> list[dict]:
    rows = []
    for topic, payload, _qos in recorder.recorded:
        if f"/{kind}/" not in topic:
            continue
        rows.append(json.loads(payload))
    return rows


def test_c01_entrypoint_starts_correct_workspace_and_profile():
    identity = verify_runtime_identity()
    assert identity["command"] == COMMAND
    assert identity["workspace_id"] == WORKSPACE_ID
    assert identity["profile_id"] == PROFILE_ID
    assert identity["contract_version"] == CONTRACT_VERSION
    assert identity["source_time_reservation"] is False
    assert identity["wall_clock_sync"] is False
    parser = build_parser()
    args = parser.parse_args([
        "dday-bw-runtime",
        "--mqtt-host",
        "plantos-emqx",
        "--mqtt-port",
        "1883",
        "--mqtt-client-id",
        "vf-dday-bw-demo-01",
    ])
    assert args.command == "dday-bw-runtime"
    assert args.mqtt_host == "plantos-emqx"
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = compose["services"]["virtual-factory-dday"]
    assert service["container_name"] == "virtual-factory-dday"
    assert service["restart"] == "unless-stopped"
    assert "ports" not in service
    assert "volumes" not in service
    assert service["command"] == [
        "virtual-factory",
        "dday-bw-runtime",
        "--mqtt-host",
        "plantos-emqx",
        "--mqtt-port",
        "1883",
        "--mqtt-client-id",
        "vf-dday-bw-demo-01",
    ]
    assert compose["networks"]["plantos-net"]["external"] is True


def test_c01_mixed_cadence_and_event_driven():
    recorder = _Recorder()
    result = run_dday_bw_runtime(
        gateway=MqttGateway(client=recorder),
        max_cycles=11,
        pace=False,
        install_signals=False,
    )
    assert result["exit_code"] == 0
    first_signals = []
    for topic, payload, qos in recorder.recorded:
        data = json.loads(payload)
        if "/signal/" in topic:
            first_signals.append((data["source_id"], data["signal_id"]))
        if len([row for row in recorder.recorded[: len(first_signals) + 3]]) and False:
            break
    # First cycle publishes all 22 measurements.
    opening = []
    for topic, payload, _qos in recorder.recorded:
        if "/signal/" not in topic:
            continue
        data = json.loads(payload)
        key = (data["source_id"], data["signal_id"])
        if key in opening:
            break
        opening.append(key)
    assert set(opening) == FAST_KEYS | MEDIUM_KEYS | SLOW_KEYS | COUNT_KEYS
    counts = Counter()
    for topic, payload, qos in recorder.recorded:
        assert qos == 1
        if "/signal/" not in topic:
            continue
        data = json.loads(payload)
        counts[(data["source_id"], data["signal_id"])] += 1
    assert counts[("BW-FP-CAP01", "motor_current")] == 11
    assert counts[("BW-WT-FEED01", "water_flow")] == 2
    events = _payloads(recorder, "event")
    types = {item["event_type"] for item in events}
    assert types <= set(SIX_EVENT_TYPES)
    assert any(item["event_type"] == "MACHINE_STATE_CHANGED" for item in events)
    assert all("/operating_state" not in topic for topic, _payload, _qos in recorder.recorded if "/signal/" in topic)


def test_c01_separate_runs_may_repeat_deterministic_source_timestamps():
    first = _Recorder()
    second = _Recorder()
    run_dday_bw_runtime(
        gateway=MqttGateway(client=first),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    run_dday_bw_runtime(
        gateway=MqttGateway(client=second),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    first_ts = {item["timestamp"] for item in _payloads(first, "event")}
    second_ts = {item["timestamp"] for item in _payloads(second, "event")}
    assert utc_timestamp(0) in first_ts
    assert first_ts == second_ts
    assert utc_timestamp(0) == "2026-10-03T00:00:00.000Z"


def test_c01_no_wall_clock_sync_or_reservation_logic():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "time.time()" not in source
    assert "VF_SOURCE_TIME_FLOOR" not in source
    assert "/var/lib/virtual-factory" not in source
    assert "source-time.json" not in source
    compose_text = COMPOSE.read_text(encoding="utf-8")
    assert "VF_SOURCE_TIME_FLOOR" not in compose_text
    assert "source-time.json" not in compose_text
    assert "volumes:" not in compose_text
    assert utc_timestamp(610) == "2026-10-03T00:10:10.000Z"


def test_c01_stopped_event_acked_before_shutdown_and_fail_closed():
    recorder = _Recorder()
    result = run_dday_bw_runtime(
        gateway=MqttGateway(client=recorder),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    assert result["exit_code"] == 0
    assert recorder.disconnected is True
    events = _payloads(recorder, "event")
    assert events
    last_event = events[-1]
    assert last_event["event_type"] == "MACHINE_STATE_CHANGED"
    assert "STOPPED" in last_event.get("detail", "")
    assert result["shutdown_trace"][0]["phase"] == "stopped_event_publish"
    assert result["shutdown_trace"][1]["phase"] == "drain"
    assert result["shutdown_trace"][1]["ok"] is True
    last_topic = recorder.recorded[-1][0]
    assert "/event/" in last_topic
    failed = _Recorder(acked=False)
    failed_result = run_dday_bw_runtime(
        gateway=MqttGateway(client=failed),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    assert failed_result["exit_code"] == 1
    assert any("fail_closed" in item["phase"] for item in failed_result["shutdown_trace"])


def test_c01_dictionary_sha_unchanged():
    digest = hashlib.sha256(
        (WORKSPACE_DIR / "plantos_export.dictionary.yaml").read_bytes()
    ).hexdigest()
    assert digest == DICTIONARY_SHA256
    assert digest == "cbe389ec7d3c022a78b7853044f08ba148a7b8a41e374931973683c8886b07ca"
