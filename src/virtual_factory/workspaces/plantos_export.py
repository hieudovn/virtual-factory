"""DDAY-B6 — workspace-local PlantOS-compatible export (view, not a simulator).

Maps the existing Bottled Water factory snapshot onto the frozen B1 MQTT JSON
contract. This module does not own factory state, does not copy topology into a
second runtime, does not calculate PlantOS KPIs, and does not edit generic
protocol or telemetry code.

Primary topic shape (B1):
    virtual-factory/bottled-water-dday/{kind}/{asset_id}/{signal_or_event}

REST/debug consumers read the in-memory sink. Optional live MQTT delivery may
compose the existing ``MqttGateway.publish_raw`` without changing that class.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

WORKSPACE_ID = "bottled-water-dday"
TOPIC_PREFIX = f"virtual-factory/{WORKSPACE_ID}"
TOPIC_PATTERN = f"{TOPIC_PREFIX}/{{kind}}/{{asset_id}}/{{signal_or_event}}"
PROVENANCE_RAW = "SIMULATED_RAW"
QUALITY_GOOD = "GOOD"

ACCEPTED_AREAS = ("BW-WT", "BW-BP", "BW-FP", "BW-UT", "BW-WH")
DRILL_DOWN = {"BW-FP": "/bottled-water-demo"}

# Accepted process/utility relationships of the frozen B1 areas.
# Presentation of the existing factory, not a second topology model.
RELATIONSHIPS = (
    {
        "from_area": "BW-WT",
        "to_area": "BW-FP",
        "kind": "process",
        "label": "treated water → filler",
    },
    {
        "from_area": "BW-BP",
        "to_area": "BW-FP",
        "kind": "process",
        "label": "prepared bottles → blower/infeed",
    },
    {
        "from_area": "BW-UT",
        "to_area": "BW-FP",
        "kind": "utility",
        "label": "compressed air → line",
    },
    {
        "from_area": "BW-FP",
        "to_area": "BW-WH",
        "kind": "process",
        "label": "good bottles → finished goods",
    },
)

# Must stay aligned with bottled_water.HIDDEN_TRUTH_KEYS / FORBIDDEN_KPI_KEYS.
HIDDEN_TRUTH_KEYS = (
    "degradation_factor",
    "injected_fault_strength",
    "scenario_internal_phase_timer",
    "phase_timer",
    "fault_strength",
    "_factor",
    "_phase_elapsed_s",
    "_bearing_temp_c",
    "sag_factor",
    "injected_sag_strength",
)

FORBIDDEN_KPI_KEYS = (
    "oee",
    "availability",
    "performance",
    "quality_percentage",
    "quality_pct",
    "energy_per_unit",
    "energy_per",
    "health_score",
    "asset_health",
    "anomaly_score",
    "anomaly",
    "rul",
    "remaining_useful",
    "predictive",
)

_FORBIDDEN_NAME_FRAGMENTS = tuple(
    key.lower() for key in HIDDEN_TRUTH_KEYS + FORBIDDEN_KPI_KEYS
)

_PACKAGED_TOPOLOGY = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "workspaces"
    / WORKSPACE_ID
    / "topology.yaml"
)


def build_topic(kind: str, asset_id: str, signal_or_event: str) -> str:
    """B1 topic for one signal or event. No generic gateway topic rewrite."""
    return f"{TOPIC_PREFIX}/{kind}/{asset_id}/{signal_or_event}"


def _blocked_name(name: str) -> bool:
    lowered = str(name or "").lower()
    return any(fragment in lowered for fragment in _FORBIDDEN_NAME_FRAGMENTS)


def load_plantos_mapping(topology_path: str | Path | None = None) -> dict:
    """Read the frozen B1 plantos_mapping. Contract metadata, not live state."""
    path = Path(topology_path) if topology_path else _PACKAGED_TOPOLOGY
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapping = dict(data.get("plantos_mapping") or {})
    if not mapping:
        raise ValueError(f"topology has no plantos_mapping: {path}")
    return mapping


def _scenario_id_for(asset_id: str, snapshot: dict) -> Optional[str]:
    capper = snapshot.get("scenario") or {}
    compressor = snapshot.get("compressor_scenario") or {}
    if asset_id and asset_id == capper.get("target_asset"):
        return capper.get("id")
    if asset_id and asset_id == compressor.get("target_asset"):
        return compressor.get("id")
    return None


def _signal_payload(
    snapshot: dict,
    asset_id: str,
    signal_id: str,
    signal: dict,
) -> dict:
    payload = {
        "workspace_id": snapshot.get("workspace_id", WORKSPACE_ID),
        "asset_id": asset_id,
        "signal_id": signal_id,
        "value": signal.get("value"),
        "unit": signal.get("unit"),
        "timestamp_s": signal.get("simulation_time_s",
                                  snapshot.get("factory", {}).get("simulation_time_s")),
        "quality": signal.get("quality", QUALITY_GOOD),
        "provenance": signal.get("provenance", PROVENANCE_RAW),
    }
    scenario_id = _scenario_id_for(asset_id, snapshot)
    if scenario_id:
        payload["scenario_id"] = scenario_id
    return payload


def _event_payload(snapshot: dict, event: dict) -> dict:
    asset_id = (
        event.get("source_id")
        or event.get("station_id")
        or event.get("asset_id")
        or snapshot.get("plant_id")
    )
    payload = {
        "workspace_id": snapshot.get("workspace_id", WORKSPACE_ID),
        "event_type": event.get("event_type"),
        "asset_id": asset_id,
        "simulation_time_s": event.get("simulation_time_s"),
        "provenance": event.get("provenance", PROVENANCE_RAW),
    }
    if event.get("detail"):
        payload["detail"] = event["detail"]
    if event.get("downtime_code"):
        payload["reason_code"] = event["downtime_code"]
        payload["downtime_code"] = event["downtime_code"]
        payload["planned"] = bool(event.get("planned", False))
    if event.get("failure_code"):
        payload["failure_code"] = event["failure_code"]
    if event.get("quality"):
        payload["quality"] = event["quality"]
    scenario_id = event.get("scenario_id") or _scenario_id_for(asset_id, snapshot)
    if scenario_id:
        payload["scenario_id"] = scenario_id
    return payload


@dataclass(frozen=True)
class PublishedMessage:
    """One PlantOS-compatible MQTT JSON message derived from factory state."""

    topic: str
    kind: str
    asset_id: str
    signal_or_event: str
    payload: dict

    def as_dict(self) -> dict:
        return {
            "topic": self.topic,
            "kind": self.kind,
            "asset_id": self.asset_id,
            "signal_or_event": self.signal_or_event,
            "payload": dict(self.payload),
        }


def map_snapshot(snapshot: dict) -> list[PublishedMessage]:
    """Project the existing factory snapshot into B1 MQTT JSON messages."""
    messages: list[PublishedMessage] = []
    for asset_id, node in (snapshot.get("nodes") or {}).items():
        for signal_id, signal in (node.get("signals") or {}).items():
            if _blocked_name(signal_id) or _blocked_name(asset_id):
                continue
            payload = _signal_payload(snapshot, asset_id, signal_id, signal)
            messages.append(
                PublishedMessage(
                    topic=build_topic("signal", asset_id, signal_id),
                    kind="signal",
                    asset_id=asset_id,
                    signal_or_event=signal_id,
                    payload=payload,
                )
            )
    for event in snapshot.get("recent_events") or ():
        event_type = str(event.get("event_type") or "")
        if not event_type or _blocked_name(event_type):
            continue
        payload = _event_payload(snapshot, event)
        asset_id = str(payload["asset_id"])
        messages.append(
            PublishedMessage(
                topic=build_topic("event", asset_id, event_type),
                kind="event",
                asset_id=asset_id,
                signal_or_event=event_type,
                payload=payload,
            )
        )
    return messages


def resolve_ids(
    messages: Iterable[PublishedMessage],
    snapshot: dict,
    plantos_mapping: Optional[dict] = None,
) -> dict:
    """Prove every published id exists in the frozen Plant/Area/Asset map."""
    mapping = plantos_mapping or load_plantos_mapping()
    known = {node["source_id"] for node in snapshot.get("hierarchy") or ()}
    known.add(mapping.get("plant"))
    known.update(mapping.get("areas") or ())
    published = []
    unresolved = []
    for message in messages:
        published.append(message.asset_id)
        if message.asset_id not in known:
            unresolved.append(message.asset_id)
    areas = list(mapping.get("areas") or [])
    return {
        "plant": mapping.get("plant"),
        "areas": areas,
        "accepted_areas": list(ACCEPTED_AREAS),
        "line_mapping": mapping.get("line_mapping"),
        "machine_mapping": mapping.get("machine_mapping"),
        "published_ids": sorted(set(published)),
        "unresolved_ids": sorted(set(unresolved)),
        "resolved": not unresolved,
        "areas_match_contract": areas == list(ACCEPTED_AREAS),
    }


def _node_signal(snapshot: dict, node_id: str, signal_id: str):
    node = (snapshot.get("nodes") or {}).get(node_id) or {}
    signal = (node.get("signals") or {}).get(signal_id) or {}
    return signal.get("value")


def _area_abnormal(area_id: str, snapshot: dict) -> dict:
    """Public phase / operating_state only. Not a PlantOS health score."""
    if area_id == "BW-FP":
        phase = (snapshot.get("scenario") or {}).get("phase") or "NORMAL"
        return {
            "source": "capper_phase",
            "phase": phase,
            "abnormal": phase != "NORMAL",
        }
    if area_id == "BW-UT":
        phase = (snapshot.get("compressor_scenario") or {}).get("phase") or "NORMAL"
        return {
            "source": "compressor_phase",
            "phase": phase,
            "abnormal": phase != "NORMAL",
        }
    operating = _node_signal(snapshot, area_id, "operating_state") or "STOPPED"
    return {
        "source": "operating_state",
        "phase": operating,
        "abnormal": False,
    }


def _area_raw_values(area_id: str, snapshot: dict) -> dict:
    balances = snapshot.get("balances") or {}
    if area_id == "BW-WT":
        water = balances.get("water") or {}
        return {
            "tank_level_pct": water.get("tank_level_pct",
                                        _node_signal(snapshot, "BW-WT-TK01", "level")),
            "treated_water_flow_m3h": _node_signal(snapshot, "BW-WT-RO01", "production_flow"),
            "tank_volume_m3": water.get("tank_volume_m3",
                                        _node_signal(snapshot, "BW-WT-TK01", "volume_m3")),
        }
    if area_id == "BW-BP":
        return {
            "operating_state": _node_signal(snapshot, "BW-BP", "operating_state"),
            "preform_count": _node_signal(snapshot, "BW-BP", "preform_count"),
        }
    if area_id == "BW-FP":
        return {
            "operating_state": _node_signal(snapshot, "BW-FP", "operating_state"),
            "total_count": _node_signal(snapshot, "BW-FP", "total_count"),
            "good_count": _node_signal(snapshot, "BW-FP", "good_count"),
            "reject_count": _node_signal(snapshot, "BW-FP", "reject_count"),
        }
    if area_id == "BW-UT":
        energy = balances.get("energy") or {}
        return {
            "air_pressure_bar": _node_signal(snapshot, "BW-UT-CMP01", "air_pressure"),
            "plant_active_power_kw": energy.get(
                "plant_active_power_kw",
                _node_signal(snapshot, "BW-UT-PWR01", "plant_active_power"),
            ),
        }
    if area_id == "BW-WH":
        finished = balances.get("finished_goods") or {}
        return {
            "inventory_count": finished.get(
                "inventory_count",
                _node_signal(snapshot, "BW-WH-FG01", "inventory_count"),
            ),
            "receipt_count": finished.get(
                "receipt_count",
                _node_signal(snapshot, "BW-WH-FG01", "receipt_count"),
            ),
            "dispatch_count": finished.get(
                "dispatch_count",
                _node_signal(snapshot, "BW-WH-FG01", "dispatch_count"),
            ),
        }
    return {}


def overview_from_snapshot(snapshot: dict) -> dict:
    """Bounded overview view over the single factory snapshot."""
    nodes_by_id = {node["source_id"]: node for node in snapshot.get("hierarchy") or ()}
    areas = []
    for area_id in ACCEPTED_AREAS:
        node = nodes_by_id.get(area_id) or {}
        areas.append({
            "id": area_id,
            "name": node.get("name", area_id),
            "role": node.get("role", ""),
            "entity_type": node.get("entity_type", "area"),
            "raw_values": _area_raw_values(area_id, snapshot),
            "abnormal": _area_abnormal(area_id, snapshot),
            "drill_down": DRILL_DOWN.get(area_id),
        })
    factory = snapshot.get("factory") or {}
    return {
        "workspace_id": snapshot.get("workspace_id", WORKSPACE_ID),
        "plant_id": snapshot.get("plant_id"),
        "plant_name": snapshot.get("plant_name"),
        "run_state": factory.get("run_state"),
        "operating_state": factory.get("operating_state"),
        "simulation_time_s": factory.get("simulation_time_s"),
        "areas": areas,
        "relationships": [dict(item) for item in RELATIONSHIPS],
        "drill_down": dict(DRILL_DOWN),
    }


class PlantosLocalIngestion:
    """In-memory PlantOS-compatible ingestion path (local proof only)."""

    def __init__(self, signal_capacity: int = 4000, event_capacity: int = 240) -> None:
        self._signals: deque[PublishedMessage] = deque(maxlen=signal_capacity)
        self._events: deque[PublishedMessage] = deque(maxlen=event_capacity)
        self._current: dict[tuple[str, str], PublishedMessage] = {}
        self._seen_events: set[tuple] = set()

    def clear(self) -> None:
        self._signals.clear()
        self._events.clear()
        self._current.clear()
        self._seen_events.clear()

    def ingest(self, messages: Iterable[PublishedMessage]) -> None:
        for message in messages:
            if message.kind == "signal":
                self._current[(message.asset_id, message.signal_or_event)] = message
                self._signals.append(message)
                continue
            key = (
                message.asset_id,
                message.signal_or_event,
                message.payload.get("simulation_time_s"),
                message.payload.get("detail"),
                message.payload.get("reason_code"),
            )
            if key in self._seen_events:
                continue
            self._seen_events.add(key)
            self._events.append(message)

    @property
    def message_count(self) -> int:
        return len(self._signals) + len(self._events)

    def current_values(self) -> list[dict]:
        return [message.as_dict() for message in self._current.values()]

    def historian(self, limit: int = 80) -> list[dict]:
        items = list(self._signals)
        if limit >= 0:
            items = items[-limit:]
        return [message.as_dict() for message in items]

    def events(self, limit: int = 80) -> list[dict]:
        items = list(self._events)
        if limit >= 0:
            items = items[-limit:]
        return [message.as_dict() for message in items]


@dataclass
class ExportBundle:
    snapshot: dict
    messages: list[PublishedMessage]
    sink: PlantosLocalIngestion
    id_resolution: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        factory = self.snapshot.get("factory") or {}
        return {
            "workspace_id": self.snapshot.get("workspace_id", WORKSPACE_ID),
            "plant_id": self.snapshot.get("plant_id"),
            "simulation_time_s": factory.get("simulation_time_s"),
            "topic_pattern": TOPIC_PATTERN,
            "ingestion_path": "local_in_memory_plantos_compatible",
            "id_resolution": self.id_resolution,
            "current_values": self.sink.current_values(),
            "historian": self.sink.historian(),
            "events": self.sink.events(),
            "overview": overview_from_snapshot(self.snapshot),
            "message_count": self.sink.message_count,
        }


def export_bundle(
    snapshot: dict,
    sink: PlantosLocalIngestion,
    plantos_mapping: Optional[dict] = None,
) -> dict:
    """Debug/verification bundle: current values, historian, events, overview."""
    messages = map_snapshot(snapshot)
    resolution = resolve_ids(messages, snapshot, plantos_mapping)
    return ExportBundle(
        snapshot=snapshot,
        messages=messages,
        sink=sink,
        id_resolution=resolution,
    ).as_dict()


def publish_via_existing_mqtt(gateway: Any, messages: Iterable[PublishedMessage]) -> int:
    """Deliver mapped payloads through unchanged MqttGateway.publish_raw."""
    published = 0
    import json

    for message in messages:
        gateway.publish_raw(message.topic, json.dumps(message.payload))
        published += 1
    return published
