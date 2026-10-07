#!/usr/bin/env python3
"""Collect DDAY-VF-UAT-01-C01 durable-runtime machine evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

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
from virtual_factory.workspaces.plantos_export import CONTRACT_VERSION, utc_timestamp

RECON = "485af9ac24c66f69db29ef308a144cfebe1e054b"
CLI = (
    "virtual-factory dday-bw-runtime "
    "--mqtt-host plantos-emqx --mqtt-port 1883 "
    "--mqtt-client-id vf-dday-bw-demo-01"
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


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


def main() -> None:
    identity = verify_runtime_identity()
    recorder = _Recorder()
    result = run_dday_bw_runtime(
        gateway=MqttGateway(client=recorder),
        max_cycles=11,
        pace=False,
        install_signals=False,
    )
    counts = Counter()
    qos_values = set()
    for topic, payload, qos in recorder.recorded:
        qos_values.add(qos)
        if "/signal/" not in topic:
            continue
        data = json.loads(payload)
        counts[(data["source_id"], data["signal_id"])] += 1

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
    first_ts = sorted({item["timestamp"] for item in _payloads(first, "event")})
    second_ts = sorted({item["timestamp"] for item in _payloads(second, "event")})

    ok = _Recorder()
    ok_result = run_dday_bw_runtime(
        gateway=MqttGateway(client=ok),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    failed = _Recorder(acked=False)
    failed_result = run_dday_bw_runtime(
        gateway=MqttGateway(client=failed),
        max_cycles=1,
        pace=False,
        install_signals=False,
    )
    digest = hashlib.sha256(
        (WORKSPACE_DIR / "plantos_export.dictionary.yaml").read_bytes()
    ).hexdigest()
    last_event = _payloads(ok, "event")[-1]

    evidence = {
        "task_id": "DDAY-VF-UAT-01-C01",
        "baseline_recon_sha": RECON,
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "command": COMMAND,
        "cli": CLI,
        "compose_artifact": "deploy/dday-vf-uat.compose.yml",
        "workspace_id": WORKSPACE_ID,
        "profile_id": PROFILE_ID,
        "contract_version": CONTRACT_VERSION,
        "plant_source_id": identity["plant_source_id"],
        "dictionary_sha256": digest,
        "dictionary_sha256_expected": DICTIONARY_SHA256,
        "timestamp_epoch": utc_timestamp(0),
        "source_time_reservation": False,
        "wall_clock_sync": False,
        "warmup_implemented": False,
        "checkpoint_implemented": False,
        "qos": sorted(qos_values),
        "bounded_cycles": 11,
        "fast_motor_current_publishes": counts[("BW-FP-CAP01", "motor_current")],
        "slow_water_flow_publishes": counts[("BW-WT-FEED01", "water_flow")],
        "event_types_observed": sorted({item["event_type"] for item in _payloads(recorder, "event")}),
        "operating_state_signal_publishes": sum(
            1
            for topic, payload, _qos in recorder.recorded
            if "/signal/" in topic and json.loads(payload).get("signal_id") == "operating_state"
        ),
        "repeated_source_timestamps_allowed": first_ts == second_ts,
        "first_run_event_timestamps": first_ts,
        "second_run_event_timestamps": second_ts,
        "stopped_event": {
            "event_type": last_event.get("event_type"),
            "detail": last_event.get("detail"),
            "timestamp": last_event.get("timestamp"),
        },
        "shutdown_trace": ok_result["shutdown_trace"],
        "stopped_acked_before_disconnect": (
            ok.disconnected is True
            and ok_result["exit_code"] == 0
            and ok_result["shutdown_trace"][0]["phase"] == "stopped_event_publish"
            and ok_result["shutdown_trace"][1]["phase"] == "drain"
            and ok_result["shutdown_trace"][1].get("ok") is True
        ),
        "mqtt_fail_closed_exit_code": failed_result["exit_code"],
        "mqtt_fail_closed_trace": failed_result["shutdown_trace"],
        "bounded_run_exit_code": result["exit_code"],
        "deploy_authorized": False,
        "plantos_handoff": False,
        "merge_authorized": False,
        "uat_executed": False,
    }
    (HERE / "machine-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(HERE / "machine-evidence.json"), "head": evidence["head"]}))


if __name__ == "__main__":
    main()
