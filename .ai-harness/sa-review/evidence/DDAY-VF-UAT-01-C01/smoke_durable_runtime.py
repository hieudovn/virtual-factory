#!/usr/bin/env python3
"""DDAY-VF-UAT-01-C01 — durable Bottled Water MQTT runtime smoke."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import yaml


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

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

COMPOSE = REPO_ROOT / "deploy" / "dday-vf-uat.compose.yml"
LAUNCHER = REPO_ROOT / "src" / "virtual_factory" / "workspaces" / "dday_bw_runtime.py"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


class _Ack:
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
        return _Ack(self.rc, self.acked)

    def disconnect(self) -> None:
        self.disconnected = True


def _payloads(recorder: _Recorder, kind: str) -> list[dict]:
    rows = []
    for topic, payload, _qos in recorder.recorded:
        if f"/{kind}/" not in topic:
            continue
        rows.append(json.loads(payload))
    return rows


def main() -> int:
    print("=" * 72)
    print("DDAY-VF-UAT-01-C01 — durable Bottled Water MQTT runtime")
    print("=" * 72)

    identity = verify_runtime_identity()
    claim(identity["command"] == COMMAND, "command is dday-bw-runtime")
    claim(identity["workspace_id"] == WORKSPACE_ID, "workspace is bottled-water-dday")
    claim(identity["profile_id"] == PROFILE_ID, "profile is dday-bw-runtime-fr1")
    claim(identity["contract_version"] == CONTRACT_VERSION, "contract remains dday-bw-b1-v2")
    claim(identity["source_time_reservation"] is False, "no source-time reservation")
    claim(identity["wall_clock_sync"] is False, "no wall-clock source-time sync")

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
    claim(args.command == "dday-bw-runtime", "CLI parses dday-bw-runtime")
    claim(args.mqtt_host == "plantos-emqx", "CLI default host is plantos-emqx")

    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = compose["services"]["virtual-factory-dday"]
    claim(service["restart"] == "unless-stopped", "compose restart is unless-stopped")
    claim("ports" not in service, "compose publishes no public MQTT port")
    claim("volumes" not in service, "compose has no checkpoint volume")
    claim(
        service["command"]
        == [
            "virtual-factory",
            "dday-bw-runtime",
            "--mqtt-host",
            "plantos-emqx",
            "--mqtt-port",
            "1883",
            "--mqtt-client-id",
            "vf-dday-bw-demo-01",
        ],
        "compose starts the durable CLI",
    )

    recorder = _Recorder()
    result = run_dday_bw_runtime(
        gateway=MqttGateway(client=recorder),
        max_cycles=11,
        pace=False,
        install_signals=False,
    )
    claim(result["exit_code"] == 0, "bounded run exits 0")
    counts = Counter()
    qos_values = {qos for _topic, _payload, qos in recorder.recorded}
    claim(qos_values == {1}, "every publish is QoS 1")
    for topic, payload, _qos in recorder.recorded:
        if "/signal/" not in topic:
            continue
        data = json.loads(payload)
        counts[(data["source_id"], data["signal_id"])] += 1
    claim(counts[("BW-FP-CAP01", "motor_current")] == 11, "FAST motor_current publishes 11 times")
    claim(counts[("BW-WT-FEED01", "water_flow")] == 2, "SLOW water_flow publishes twice over 11 cycles")
    events = _payloads(recorder, "event")
    types = {item["event_type"] for item in events}
    claim(types <= set(SIX_EVENT_TYPES), "events stay inside the six accepted types")
    claim(any(item["event_type"] == "MACHINE_STATE_CHANGED" for item in events), "MACHINE_STATE_CHANGED is published")
    claim(
        all("/operating_state" not in topic for topic, _payload, _qos in recorder.recorded if "/signal/" in topic),
        "operating_state is not a live measurement signal",
    )

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
    claim(utc_timestamp(0) in first_ts, "first run publishes epoch t=0")
    claim(first_ts == second_ts, "separate runs may repeat deterministic source timestamps")
    claim(utc_timestamp(0) == "2026-10-03T00:00:00.000Z", "epoch is unchanged")

    source = LAUNCHER.read_text(encoding="utf-8")
    compose_text = COMPOSE.read_text(encoding="utf-8")
    claim("datetime.now" not in source, "launcher does not call datetime.now")
    claim("time.time()" not in source, "launcher does not call time.time")
    claim("VF_SOURCE_TIME_FLOOR" not in source, "launcher has no source-time floor")
    claim("source-time.json" not in source, "launcher has no checkpoint file")
    claim("VF_SOURCE_TIME_FLOOR" not in compose_text, "compose has no source-time floor")
    claim("volumes:" not in compose_text, "compose mounts no reservation volume")

    ok = _Recorder()
    ok_result = run_dday_bw_runtime(
        gateway=MqttGateway(client=ok),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    last_event = _payloads(ok, "event")[-1]
    claim(ok_result["exit_code"] == 0, "clean shutdown exits 0")
    claim(ok.disconnected is True, "gateway disconnects after STOPPED")
    claim(last_event["event_type"] == "MACHINE_STATE_CHANGED", "final event is MACHINE_STATE_CHANGED")
    claim("STOPPED" in last_event.get("detail", ""), "final event detail is STOPPED")
    claim(ok_result["shutdown_trace"][0]["phase"] == "stopped_event_publish", "STOPPED publish is traced")
    claim(ok_result["shutdown_trace"][1]["phase"] == "drain", "ACK drain happens after STOPPED")
    claim(ok_result["shutdown_trace"][1]["ok"] is True, "STOPPED drain is ACKed")

    failed = _Recorder(acked=False)
    failed_result = run_dday_bw_runtime(
        gateway=MqttGateway(client=failed),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    claim(failed_result["exit_code"] == 1, "MQTT ACK failure exits non-zero")
    claim(
        any("fail_closed" in item["phase"] for item in failed_result["shutdown_trace"]),
        "MQTT ACK failure remains fail-closed",
    )

    digest = hashlib.sha256((WORKSPACE_DIR / "plantos_export.dictionary.yaml").read_bytes()).hexdigest()
    claim(digest == DICTIONARY_SHA256, "dictionary SHA-256 is unchanged")

    print()
    if _failures:
        print(f"SMOKE FAILED ({len(_failures)} claim(s))")
        for item in _failures:
            print(f"  - {item}")
        return 1
    print("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
