"""Durable Bottled Water D-Day MQTT runtime (DDAY-VF-UAT-01-C01).

Long-running process:
``BottledWaterFactory → FR1 scheduler → plantos_export → QoS-1 MQTT``.

Does not change timestamp semantics, add source-time reservation/checkpoint,
or synchronize the simulation clock to wall clock. A restart is a fresh
deterministic run and may replay the same source timestamps.
"""

from __future__ import annotations

import hashlib
import os
import signal
import threading
from pathlib import Path
from typing import Any

from virtual_factory.protocols.mqtt_gateway import MqttGateway, MqttPublishError
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    CONTRACT_VERSION,
    TOPIC_PREFIX,
    load_runtime_profile,
    utc_timestamp,
)

COMMAND = "dday-bw-runtime"
WORKSPACE_ID = "bottled-water-dday"
PROFILE_ID = "dday-bw-runtime-fr1"
PLANT_SOURCE_ID = "BW-DEMO-01"
DEFAULT_MQTT_HOST = "plantos-emqx"
DEFAULT_MQTT_PORT = 1883
DEFAULT_CLIENT_ID = "vf-dday-bw-demo-01"
DICTIONARY_SHA256 = "cbe389ec7d3c022a78b7853044f08ba148a7b8a41e374931973683c8886b07ca"
REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = REPO_ROOT / "configs" / "workspaces" / WORKSPACE_ID
DICTIONARY_PATH = WORKSPACE_DIR / "plantos_export.dictionary.yaml"


def packaged_workspace_dir() -> Path:
    return WORKSPACE_DIR


def verify_runtime_identity() -> dict:
    """Fail closed if the packaged workspace/profile/contract is not the D-Day set."""
    profile = load_runtime_profile()
    if profile.get("profile_id") != PROFILE_ID:
        raise RuntimeError(f"expected profile {PROFILE_ID}, got {profile.get('profile_id')}")
    if profile.get("contract_version") != CONTRACT_VERSION:
        raise RuntimeError(
            f"expected contract {CONTRACT_VERSION}, got {profile.get('contract_version')}"
        )
    if profile.get("workspace_id") != WORKSPACE_ID:
        raise RuntimeError(f"expected workspace {WORKSPACE_ID}")
    digest = hashlib.sha256(DICTIONARY_PATH.read_bytes()).hexdigest()
    if digest != DICTIONARY_SHA256:
        raise RuntimeError("plantos_export.dictionary.yaml SHA-256 mismatch")
    return {
        "command": COMMAND,
        "workspace_id": WORKSPACE_ID,
        "profile_id": PROFILE_ID,
        "contract_version": CONTRACT_VERSION,
        "plant_source_id": PLANT_SOURCE_ID,
        "dictionary_sha256": digest,
        "timestamp_epoch": utc_timestamp(0),
        "source_time_reservation": False,
        "wall_clock_sync": False,
    }


def _install_stop_signals(stop_flag: threading.Event) -> None:
    def _handle(signum, _frame) -> None:
        stop_flag.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)


def run_dday_bw_runtime(
    mqtt_host: str = DEFAULT_MQTT_HOST,
    mqtt_port: int = DEFAULT_MQTT_PORT,
    mqtt_client_id: str | None = DEFAULT_CLIENT_ID,
    mqtt_connect_retries: int = 20,
    mqtt_connect_delay: float = 1.0,
    gateway: Any | None = None,
    stop_flag: threading.Event | None = None,
    max_cycles: int | None = None,
    pace: bool = True,
    install_signals: bool = True,
) -> dict:
    """Run one fresh deterministic Bottled Water D-Day MQTT session.

    Returns a result dict with ``exit_code`` and ``shutdown_trace``.
    """
    identity = verify_runtime_identity()
    factory = BottledWaterFactory(
        WORKSPACE_DIR / "line.yaml",
        WORKSPACE_DIR / "factory.yaml",
    )
    owns_gateway = gateway is None
    if gateway is None:
        gateway = MqttGateway(
            host=mqtt_host,
            port=int(mqtt_port),
            topic_prefix=TOPIC_PREFIX,
            client_id=mqtt_client_id,
        )
        gateway.connect(retries=mqtt_connect_retries, delay_s=mqtt_connect_delay)
    flag = stop_flag or threading.Event()
    if install_signals:
        _install_stop_signals(flag)

    shutdown_trace: list[dict] = []
    exit_code = 0
    cycles = 0
    try:
        factory.start()
        while not flag.is_set():
            factory.publish_live_mqtt(gateway)
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                flag.set()
                break
            if pace and not flag.is_set():
                flag.wait(timeout=float(factory.tick_interval_s))
            if flag.is_set():
                break
            factory.step()
    except MqttPublishError as exc:
        exit_code = 1
        shutdown_trace.append({"phase": "publish_fail_closed", "error": str(exc)})
    try:
        factory.stop()
        published = factory.publish_live_mqtt(gateway)
        shutdown_trace.append({
            "phase": "stopped_event_publish",
            "published": published,
            "simulation_time_s": factory.snapshot()["factory"]["simulation_time_s"],
        })
        if owns_gateway or hasattr(gateway, "disconnect"):
            summary = gateway.disconnect()
            if isinstance(summary, dict):
                shutdown_trace.append({"phase": "drain", **summary})
            else:
                shutdown_trace.append({"phase": "drain", "ok": True})
    except MqttPublishError as exc:
        exit_code = 1
        shutdown_trace.append({"phase": "shutdown_fail_closed", "error": str(exc)})
    return {
        "exit_code": exit_code,
        "identity": identity,
        "cycles": cycles,
        "shutdown_trace": shutdown_trace,
    }


def run_dday_bw_runtime_cli(args: Any) -> int:
    host = args.mqtt_host or os.environ.get("MQTT_HOST") or DEFAULT_MQTT_HOST
    result = run_dday_bw_runtime(
        mqtt_host=host,
        mqtt_port=int(args.mqtt_port),
        mqtt_client_id=args.mqtt_client_id or os.environ.get("MQTT_CLIENT_ID") or DEFAULT_CLIENT_ID,
        mqtt_connect_retries=int(args.mqtt_connect_retries),
        mqtt_connect_delay=float(args.mqtt_connect_delay),
    )
    return int(result["exit_code"])
