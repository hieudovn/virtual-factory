"""DDAY-B6 / B6-C01 — workspace-local PlantOS export view (not a simulator).

Maps the existing Bottled Water factory snapshot onto the frozen B1 MQTT
topic shape and the C01 versioned envelope. This module does not own
factory state, does not copy topology into a second runtime, does not
calculate PlantOS KPIs, and does not edit generic protocol or telemetry
code.

Primary topic shape (B1, preserved):
    virtual-factory/bottled-water-dday/{kind}/{asset_id}/{signal_or_event}

The in-memory sink is a VF adapter / unit-test aid. It is not a PlantOS
historian.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

WORKSPACE_ID = "bottled-water-dday"
CONTRACT_VERSION = "dday-bw-b1-v2"
PLANT_SOURCE_ID = "BW-DEMO-01"
TOPIC_PREFIX = f"virtual-factory/{WORKSPACE_ID}"
TOPIC_PATTERN = f"{TOPIC_PREFIX}/{{kind}}/{{asset_id}}/{{signal_or_event}}"
PROVENANCE_RAW = "SIMULATED_RAW"
QUALITY_GOOD = "GOOD"
UTC_EPOCH = datetime(2026, 10, 3, 0, 0, 0, tzinfo=timezone.utc)
TIMESTAMP_KIND = "simulated_source_utc"
TRANSPORT_KIND_EVENT_ONLY = "event_only_non_measurement"
OPERATING_STATE_EVENT_TYPE = "MACHINE_STATE_CHANGED"
SIX_EVENT_TYPES = (
    "MACHINE_STATE_CHANGED",
    "ALARM_RAISED",
    "ALARM_CLEARED",
    "DOWNTIME_START",
    "DOWNTIME_END",
    "SCENARIO_PHASE_CHANGED",
)
MQTT_QOS = 1
ADAPTER_ROLE = "vf_unit_test_aid_not_plantos_historian"
INGESTION_PATH = "local_in_memory_plantos_compatible"
TIMESTAMP_SEMANTICS = {
    "timestamp": TIMESTAMP_KIND,
    "timestamp_meaning": (
        "Deterministic simulated-source UTC instant for ordering and replay "
        "(frozen epoch 2026-10-03T00:00:00.000Z + simulation_time_s). "
        "Not wall-clock receipt time."
    ),
    "simulation_time_s": "simulation_elapsed_seconds",
    "receipt_time": "plantos_or_runtime_owned_not_generated_by_vf",
}
TRANSPORT_SEMANTICS = {
    "operating_state": TRANSPORT_KIND_EVENT_ONLY,
    "operating_state_event_type": OPERATING_STATE_EVENT_TYPE,
    "operating_state_not_a_measurement": True,
    "mqtt_qos": MQTT_QOS,
    "mqtt_acknowledged_delivery": True,
    "mqtt_drain_before_disconnect": True,
}

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
_PACKAGED_DICTIONARY = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "workspaces"
    / WORKSPACE_ID
    / "plantos_export.dictionary.yaml"
)

REQUIRED_SIGNAL_FAMILIES = ("wt", "production", "capper", "compressor", "fg", "energy")
COMPLETE_EXPORT_METADATA_FIELDS = (
    "semantic_role",
    "datatype",
    "unit",
    "cadence",
    "quality",
    "provenance",
    "plantos_mapping_key",
)
REQUIRED_ENVELOPE_FIELDS = (
    "contract_version",
    "workspace_id",
    "plant_source_id",
    "source_id",
    "timestamp",
    "simulation_time_s",
    "quality",
    "provenance",
)


class UnmappedExportError(ValueError):
    """Fail-closed: an unlisted signal or event must not become PlantOS semantics."""


def build_topic(kind: str, asset_id: str, signal_or_event: str) -> str:
    """B1 topic for one signal or event. No generic gateway topic rewrite."""
    return f"{TOPIC_PREFIX}/{kind}/{asset_id}/{signal_or_event}"


def utc_timestamp(simulation_time_s: float | None) -> str:
    """Deterministic simulated-source UTC instant, not wall-clock receipt time.

    ``timestamp = 2026-10-03T00:00:00Z + simulation_time_s``. PlantOS/runtime
    may attach a transport receipt time; VF does not generate that as source
    truth.
    """
    instant = UTC_EPOCH + timedelta(seconds=float(simulation_time_s or 0.0))
    return instant.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _is_exported_entry(entry: dict) -> bool:
    if entry.get("not_exported"):
        return False
    status = str(entry.get("export_status") or "EXPORTED").upper()
    return status == "EXPORTED"


def load_export_dictionary(path: str | Path | None = None) -> dict:
    """Read the selected D-Day export dictionary. Mapping contract, not state."""
    dictionary_path = Path(path) if path else _PACKAGED_DICTIONARY
    data = yaml.safe_load(dictionary_path.read_text(encoding="utf-8")) or {}
    if not data.get("signals") or not data.get("events"):
        raise ValueError(f"export dictionary missing signals/events: {dictionary_path}")
    return data


def selected_signal_entries(dictionary: Optional[dict] = None) -> list[dict]:
    data = dictionary or load_export_dictionary()
    return [dict(entry) for entry in data.get("signals") or ()]


def declared_unavailable_entries(dictionary: Optional[dict] = None) -> list[dict]:
    data = dictionary or load_export_dictionary()
    return [dict(entry) for entry in data.get("unavailable") or ()]


def review_set_entries(dictionary: Optional[dict] = None) -> list[dict]:
    data = dictionary or load_export_dictionary()
    return [dict(entry) for entry in data.get("review_set") or ()]


def selected_event_entries(dictionary: Optional[dict] = None) -> list[dict]:
    data = dictionary or load_export_dictionary()
    return [dict(entry) for entry in data.get("events") or ()]


def event_only_state_entries(dictionary: Optional[dict] = None) -> list[dict]:
    data = dictionary or load_export_dictionary()
    return [dict(entry) for entry in data.get("event_only_states") or ()]


def event_only_state_keys(dictionary: Optional[dict] = None) -> list[tuple[str, str]]:
    return [
        (str(entry["source_id"]), str(entry["signal_id"]))
        for entry in event_only_state_entries(dictionary)
    ]


def exported_signal_entries(dictionary: Optional[dict] = None) -> list[dict]:
    return [
        entry for entry in selected_signal_entries(dictionary)
        if _is_exported_entry(entry)
    ]


def unavailable_signal_entries(dictionary: Optional[dict] = None) -> list[dict]:
    declared = declared_unavailable_entries(dictionary)
    if declared:
        return declared
    return [
        entry for entry in selected_signal_entries(dictionary)
        if not _is_exported_entry(entry)
    ]


def selected_signal_keys(dictionary: Optional[dict] = None) -> list[tuple[str, str]]:
    return [
        (str(entry["source_id"]), str(entry["signal_id"]))
        for entry in exported_signal_entries(dictionary)
    ]


def lookup_event_only_entry(
    source_id: str,
    signal_id: str,
    dictionary: Optional[dict] = None,
) -> dict:
    for entry in event_only_state_entries(dictionary):
        if entry.get("source_id") == source_id and entry.get("signal_id") == signal_id:
            return entry
    raise UnmappedExportError(
        f"unmapped event-only state {source_id}.{signal_id}; fail closed"
    )


def lookup_signal_entry(
    source_id: str,
    signal_id: str,
    dictionary: Optional[dict] = None,
) -> dict:
    for entry in event_only_state_entries(dictionary):
        if entry.get("source_id") == source_id and entry.get("signal_id") == signal_id:
            raise UnmappedExportError(
                f"event-only non-measurement {source_id}.{signal_id}; not a measurement"
            )
    for entry in selected_signal_entries(dictionary):
        if entry.get("source_id") == source_id and entry.get("signal_id") == signal_id:
            if not _is_exported_entry(entry):
                raise UnmappedExportError(
                    f"unavailable export signal {source_id}.{signal_id}; not exported"
                )
            return entry
    for entry in unavailable_signal_entries(dictionary):
        if entry.get("source_id") == source_id and entry.get("signal_id") == signal_id:
            raise UnmappedExportError(
                f"unavailable export signal {source_id}.{signal_id}; not exported"
            )
    raise UnmappedExportError(
        f"unmapped export signal {source_id}.{signal_id}; fail closed"
    )


def lookup_event_entry(event_type: str, dictionary: Optional[dict] = None) -> dict:
    for entry in selected_event_entries(dictionary):
        if entry.get("event_type") == event_type:
            return entry
    raise UnmappedExportError(
        f"unmapped export event {event_type}; fail closed"
    )


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


def _simulation_time(snapshot: dict, *candidates) -> float:
    for value in candidates:
        if value is not None:
            return float(value)
    factory = snapshot.get("factory") or {}
    return float(factory.get("simulation_time_s") or 0.0)


def _envelope_base(
    snapshot: dict,
    source_id: str,
    simulation_time_s: float,
    *,
    quality: str = QUALITY_GOOD,
    provenance: str = PROVENANCE_RAW,
) -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "workspace_id": snapshot.get("workspace_id", WORKSPACE_ID),
        "plant_source_id": snapshot.get("plant_id", PLANT_SOURCE_ID),
        "source_id": source_id,
        "asset_id": source_id,
        "timestamp": utc_timestamp(simulation_time_s),
        "timestamp_kind": TIMESTAMP_KIND,
        "simulation_time_s": simulation_time_s,
        "quality": quality,
        "provenance": provenance,
    }


def _signal_payload(
    snapshot: dict,
    asset_id: str,
    signal_id: str,
    signal: dict,
    entry: dict,
) -> dict:
    simulation_time_s = _simulation_time(
        snapshot,
        signal.get("simulation_time_s"),
    )
    payload = _envelope_base(
        snapshot,
        asset_id,
        simulation_time_s,
        quality=signal.get("quality", entry.get("quality", QUALITY_GOOD)),
        provenance=signal.get("provenance", entry.get("provenance", PROVENANCE_RAW)),
    )
    payload.update({
        "signal_id": signal_id,
        "value": signal.get("value"),
        "unit": signal.get("unit", entry.get("unit")),
        "semantic_role": entry.get("semantic_role"),
        "datatype": entry.get("datatype"),
        "cadence": entry.get("cadence"),
        "plantos_mapping_key": entry.get("plantos_mapping_key"),
    })
    scenario_id = _scenario_id_for(asset_id, snapshot)
    if scenario_id:
        payload["scenario_id"] = scenario_id
    return payload


def _event_payload(snapshot: dict, event: dict, entry: dict) -> dict:
    asset_id = (
        event.get("source_id")
        or event.get("station_id")
        or event.get("asset_id")
        or snapshot.get("plant_id")
    )
    simulation_time_s = _simulation_time(snapshot, event.get("simulation_time_s"))
    payload = _envelope_base(
        snapshot,
        str(asset_id),
        simulation_time_s,
        quality=event.get("quality", entry.get("quality", QUALITY_GOOD)),
        provenance=event.get("provenance", entry.get("provenance", PROVENANCE_RAW)),
    )
    payload["event_type"] = event.get("event_type")
    payload["semantic_role"] = entry.get("semantic_role")
    payload["datatype"] = entry.get("datatype")
    payload["cadence"] = entry.get("cadence")
    payload["plantos_mapping_key"] = entry.get("plantos_mapping_key")
    if event.get("event_type") == OPERATING_STATE_EVENT_TYPE:
        payload["not_a_measurement"] = True
        payload["transport_kind"] = TRANSPORT_KIND_EVENT_ONLY
        if event.get("detail"):
            payload["operating_state"] = str(event["detail"]).split("=")[-1]
    if event.get("detail"):
        payload["detail"] = event["detail"]
    if event.get("downtime_code"):
        payload["reason_code"] = event["downtime_code"]
        payload["downtime_code"] = event["downtime_code"]
        payload["planned"] = bool(event.get("planned", False))
    if event.get("failure_code"):
        payload["failure_code"] = event["failure_code"]
    scenario_id = event.get("scenario_id") or _scenario_id_for(str(asset_id), snapshot)
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


def map_selected_signal(
    snapshot: dict,
    source_id: str,
    signal_id: str,
    dictionary: Optional[dict] = None,
) -> PublishedMessage:
    """Map one selected signal. Unlisted IDs fail closed."""
    entry = lookup_signal_entry(source_id, signal_id, dictionary)
    if _blocked_name(source_id) or _blocked_name(signal_id):
        raise UnmappedExportError(
            f"blocked export signal {source_id}.{signal_id}; fail closed"
        )
    node = (snapshot.get("nodes") or {}).get(source_id) or {}
    signal = (node.get("signals") or {}).get(signal_id)
    if not isinstance(signal, dict):
        raise UnmappedExportError(
            f"selected signal {source_id}.{signal_id} missing from factory snapshot"
        )
    payload = _signal_payload(snapshot, source_id, signal_id, signal, entry)
    return PublishedMessage(
        topic=build_topic("signal", source_id, signal_id),
        kind="signal",
        asset_id=source_id,
        signal_or_event=signal_id,
        payload=payload,
    )


def map_selected_event(
    snapshot: dict,
    event: dict,
    dictionary: Optional[dict] = None,
) -> PublishedMessage:
    """Map one selected event. Unlisted types fail closed."""
    event_type = str(event.get("event_type") or "")
    entry = lookup_event_entry(event_type, dictionary)
    if _blocked_name(event_type):
        raise UnmappedExportError(f"blocked export event {event_type}; fail closed")
    payload = _event_payload(snapshot, event, entry)
    asset_id = str(payload["source_id"])
    return PublishedMessage(
        topic=build_topic("event", asset_id, event_type),
        kind="event",
        asset_id=asset_id,
        signal_or_event=event_type,
        payload=payload,
    )


def map_snapshot(
    snapshot: dict,
    dictionary: Optional[dict] = None,
) -> list[PublishedMessage]:
    """Project only the selected D-Day dictionary onto MQTT JSON messages."""
    selected = dictionary or load_export_dictionary()
    messages: list[PublishedMessage] = []
    nodes = snapshot.get("nodes") or {}
    for entry in exported_signal_entries(selected):
        source_id = str(entry["source_id"])
        signal_id = str(entry["signal_id"])
        if source_id not in nodes or signal_id not in (nodes[source_id].get("signals") or {}):
            continue
        messages.append(map_selected_signal(snapshot, source_id, signal_id, selected))
    for event in snapshot.get("recent_events") or ():
        event_type = str(event.get("event_type") or "")
        if not event_type:
            continue
        try:
            lookup_event_entry(event_type, selected)
        except UnmappedExportError:
            continue
        messages.append(map_selected_event(snapshot, event, selected))
    return messages


def runtime_event_identity(event: dict) -> tuple:
    """Stable identity of one retained runtime event.

    Classification stamps are not part of identity, so later enrichment of the
    same record does not look like a new event to the transport cursor.
    """
    return (
        str(event.get("event_type") or ""),
        str(
            event.get("source_id")
            or event.get("station_id")
            or event.get("asset_id")
            or ""
        ),
        event.get("simulation_time_s"),
        event.get("detail"),
        event.get("scenario_id"),
    )


class ExportSessionCursor:
    """Tiny per-run/session watermark: each runtime event publishes once."""

    def __init__(self) -> None:
        self._seen: set[tuple] = set()

    def reset(self) -> None:
        self._seen.clear()

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    def unseen(self, events: Iterable[dict]) -> list[dict]:
        pending: list[dict] = []
        for event in events:
            key = runtime_event_identity(event)
            if not key[0] or key in self._seen:
                continue
            pending.append(event)
        return pending

    def mark(self, events: Iterable[dict]) -> None:
        for event in events:
            key = runtime_event_identity(event)
            if key[0]:
                self._seen.add(key)

    def is_seen(self, event: dict) -> bool:
        key = runtime_event_identity(event)
        return bool(key[0]) and key in self._seen


def map_unseen_transport_events(
    snapshot: dict,
    cursor: ExportSessionCursor,
    dictionary: Optional[dict] = None,
) -> list[tuple[dict, PublishedMessage]]:
    """Live transport projection: accepted events not yet published this session.

    Does not mark the cursor and does not mutate snapshot.recent_events.
    """
    selected = dictionary or load_export_dictionary()
    paired: list[tuple[dict, PublishedMessage]] = []
    for event in cursor.unseen(snapshot.get("recent_events") or ()):
        event_type = str(event.get("event_type") or "")
        if not event_type:
            continue
        try:
            lookup_event_entry(event_type, selected)
        except UnmappedExportError:
            continue
        paired.append((event, map_selected_event(snapshot, event, selected)))
    return paired


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


def dictionary_summary(dictionary: Optional[dict] = None) -> dict:
    selected = dictionary or load_export_dictionary()
    families = sorted({
        str(entry.get("family"))
        for entry in selected_signal_entries(selected)
        if entry.get("family")
    })
    return {
        "contract_version": selected.get("contract_version", CONTRACT_VERSION),
        "workspace_id": selected.get("workspace_id", WORKSPACE_ID),
        "plant_source_id": selected.get("plant_source_id", PLANT_SOURCE_ID),
        "fail_closed": bool(selected.get("fail_closed", True)),
        "timestamp_semantics": dict(selected.get("timestamp_semantics") or TIMESTAMP_SEMANTICS),
        "transport_semantics": dict(selected.get("transport_semantics") or TRANSPORT_SEMANTICS),
        "review_set": review_set_entries(selected),
        "families": families,
        "required_families": list(REQUIRED_SIGNAL_FAMILIES),
        "signal_count": len(exported_signal_entries(selected)),
        "event_types": [
            str(entry["event_type"]) for entry in selected_event_entries(selected)
        ],
        "signals": [
            {
                "source_id": entry["source_id"],
                "signal_id": entry["signal_id"],
                "family": entry.get("family"),
                "semantic_role": entry.get("semantic_role"),
                "datatype": entry.get("datatype"),
                "unit": entry.get("unit"),
                "cadence": entry.get("cadence"),
                "quality": entry.get("quality"),
                "provenance": entry.get("provenance"),
                "plantos_mapping_key": entry.get("plantos_mapping_key"),
                "export_status": entry.get("export_status", "EXPORTED"),
            }
            for entry in exported_signal_entries(selected)
        ],
        "unavailable": [
            {
                "source_id": entry.get("source_id"),
                "signal_id": entry.get("signal_id"),
                "family": entry.get("family"),
                "export_status": entry.get("export_status", "UNAVAILABLE"),
                "not_exported": True,
                "reason": entry.get("reason"),
            }
            for entry in unavailable_signal_entries(selected)
        ],
        "event_only_states": [
            {
                "source_id": entry["source_id"],
                "signal_id": entry["signal_id"],
                "event_type": entry.get("plantos_event_type", OPERATING_STATE_EVENT_TYPE),
                "transport_kind": entry.get("transport_kind", TRANSPORT_KIND_EVENT_ONLY),
                "not_a_measurement": True,
                "export_status": entry.get("export_status", "EVENT_ONLY"),
                "plantos_mapping_key": entry.get("plantos_mapping_key"),
            }
            for entry in event_only_state_entries(selected)
        ],
    }


class PlantosLocalIngestion:
    """VF adapter / unit-test aid. Not a PlantOS historian."""

    def __init__(self, signal_capacity: int = 8000, event_capacity: int = 400) -> None:
        self._signals: deque[PublishedMessage] = deque(maxlen=signal_capacity)
        self._events: deque[PublishedMessage] = deque(maxlen=event_capacity)
        self._current: dict[tuple[str, str], PublishedMessage] = {}
        self._current_states: dict[tuple[str, str], PublishedMessage] = {}
        self._seen_events: set[tuple] = set()

    def clear(self) -> None:
        self._signals.clear()
        self._events.clear()
        self._current.clear()
        self._current_states.clear()
        self._seen_events.clear()

    def ingest(self, messages: Iterable[PublishedMessage]) -> None:
        for message in messages:
            if message.kind == "signal":
                self._current[(message.asset_id, message.signal_or_event)] = message
                self._signals.append(message)
                continue
            if message.payload.get("not_a_measurement") or message.payload.get(
                "transport_kind"
            ) == TRANSPORT_KIND_EVENT_ONLY:
                state_key = (message.asset_id, "operating_state")
                previous = self._current_states.get(state_key)
                self._current_states[state_key] = message
                if (
                    previous is not None
                    and previous.payload.get("operating_state")
                    == message.payload.get("operating_state")
                ):
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

    def event_only_states(self) -> list[dict]:
        return [message.as_dict() for message in self._current_states.values()]


@dataclass
class ExportBundle:
    snapshot: dict
    messages: list[PublishedMessage]
    sink: PlantosLocalIngestion
    id_resolution: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        factory = self.snapshot.get("factory") or {}
        from virtual_factory.workspaces.plantos_compat import compatibility_status

        return {
            "contract_version": CONTRACT_VERSION,
            "workspace_id": self.snapshot.get("workspace_id", WORKSPACE_ID),
            "plant_source_id": self.snapshot.get("plant_id", PLANT_SOURCE_ID),
            "plant_id": self.snapshot.get("plant_id"),
            "simulation_time_s": factory.get("simulation_time_s"),
            "timestamp_semantics": dict(TIMESTAMP_SEMANTICS),
            "transport_semantics": dict(TRANSPORT_SEMANTICS),
            "topic_pattern": TOPIC_PATTERN,
            "ingestion_path": INGESTION_PATH,
            "adapter_role": ADAPTER_ROLE,
            "plantos_ingestion_proven": False,
            "plantos_historian_proven": False,
            "plantos_compatibility": compatibility_status(),
            "export_dictionary": dictionary_summary(),
            "id_resolution": self.id_resolution,
            "current_values": self.sink.current_values(),
            "historian": self.sink.historian(limit=240),
            "events": self.sink.events(),
            "event_only_states": dictionary_summary()["event_only_states"],
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
    """Deliver mapped payloads at QoS 1. Count only confirmed deliveries."""
    published = 0
    import json

    for message in messages:
        gateway.publish_raw(
            message.topic,
            json.dumps(message.payload),
            qos=MQTT_QOS,
        )
        published += 1
    return published


def publish_snapshot_via_existing_mqtt(
    gateway: Any,
    snapshot: dict,
    cursor: ExportSessionCursor,
    dictionary: Optional[dict] = None,
) -> int:
    """Periodic live export: current signals plus unseen session events.

    Signals remain current-value. Events of all six accepted types publish
    once per cursor lifetime. The cursor is marked only after a confirmed
    QoS-1 ACK. snapshot.recent_events is not mutated.
    """
    import json

    selected = dictionary or load_export_dictionary()
    published = 0
    for message in map_snapshot(snapshot, selected):
        if message.kind != "signal":
            continue
        gateway.publish_raw(
            message.topic,
            json.dumps(message.payload),
            qos=MQTT_QOS,
        )
        published += 1
    for event, message in map_unseen_transport_events(snapshot, cursor, selected):
        gateway.publish_raw(
            message.topic,
            json.dumps(message.payload),
            qos=MQTT_QOS,
        )
        cursor.mark((event,))
        published += 1
    return published
