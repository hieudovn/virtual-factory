"""TIPA-VF-G1A-CONTRACT-QA-01 — cross-record semantic negative tests.

These tests implement only the semantic rules explicitly stated in the G1A
register/DD-01: decimal quantities, EA integrality, offset-aware UTC, exact
epoch+tick time, unique identities, port direction/compatibility and
transaction idempotency. They do not implement a factory runtime.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO / "docs" / "design" / "tipa-g1"
CASES_PATH = Path(__file__).resolve().parent / "fixtures" / "tipa_g1a_invalid_cases.json"

DIGEST = "sha256:" + ("0" * 64)
DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
UTC_RE = re.compile(r"(?:Z|\+00:00)$")


class SemanticError(ValueError):
    """A contract-valid document violates a documented cross-field rule."""


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _schema_errors(schema_name: str, document: dict) -> list:
    validator = Draft202012Validator(
        _schema(schema_name), registry=_registry(), format_checker=FormatChecker()
    )
    return sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))


def _run() -> dict:
    return {
        "contract_version": "vf-factory-run-v0.1",
        "factory_run_id": "TIPA-P0-QA",
        "generation": 1,
        "workspace_id": "tipa-manufacturing-p0",
        "definition_revision": "P0-DEMO-v0.1",
        "definition_digest": DIGEST,
        "seed": 42,
        "epoch_utc": "2026-10-31T00:00:00Z",
        "timezone": "Asia/Ho_Chi_Minh",
        "production_day_start": "06:00",
        "mode": "INTEGRATED",
        "shift_calendar_revision": "TIPA-3SHIFTS-v1",
        "scenario_revision": "QA-v0.1",
        "model_revisions": {"SSO2": "P0v0.1", "RSO2": "P0v0.1", "ASSY": "P0v0.1"},
    }


def _module(module_id: str = "SSO2") -> dict:
    return {
        "contract_version": "vf-module-manifest-v0.1",
        "module_id": module_id,
        "workspace_id": "tipa-manufacturing-p0",
        "model_type": "DISCRETE_MODULE",
        "model_revision": "P0v0.1",
        "fidelity": "F2",
        "supported_modes": ["STANDALONE", "INTEGRATED"],
        "capabilities": ["EXTERNAL_MATERIAL_INPUT", "ADVANCE_TO_EVENT_BOUNDARY"],
        "ports": [
            {
                "port_id": f"{module_id}-OUT",
                "direction": "OUT",
                "material_types": ["STATOR_ASSEMBLY"],
                "unit": "EA",
                "buffer_id": f"{module_id}-OUT",
                "eligibility_policy": "QUALIFIED_ONLY",
                "capacity": "20",
            },
            {
                "port_id": f"{module_id}-SCRAP",
                "direction": "OUT",
                "material_types": ["SCRAP"],
                "unit": "EA",
                "buffer_id": f"{module_id}-SCRAP",
                "eligibility_policy": "NO_QUALITY_GATE",
                "capacity": None,
            },
        ],
    }


def _event() -> dict:
    return {
        "contract_version": "vf-factory-event-v0.1",
        "factory_run_id": "TIPA-P0-QA",
        "generation": 1,
        "event_id": "EV-1",
        "source_event_id": "SRC-1",
        "module_id": "SSO2",
        "simulation_tick_us": 1_000_000,
        "occurred_at_utc": "2026-10-31T00:00:01Z",
        "event_type": "PRODUCE",
        "causation_id": None,
        "correlation_id": None,
        "operation_execution_id": None,
        "wip_id": "SSO2-WIP-001",
        "lot_id": None,
        "equipment_id": None,
        "source_kind": "SIMULATED",
        "definition_provenance": "SYNTHETIC_ASSUMPTION",
        "definition_digest": DIGEST,
        "payload": {},
    }


def _transaction() -> dict:
    return {
        "contract_version": "vf-material-transaction-v0.1",
        "factory_run_id": "TIPA-P0-QA",
        "generation": 1,
        "transaction_id": "TX-1",
        "idempotency_key": "IDEM-1",
        "simulation_tick_us": 1_000_000,
        "ledger_expected_version": 0,
        "transaction_type": "TRANSFORM",
        "operation_execution_id": None,
        "transfer_id": None,
        "recipe_revision": None,
        "legs": [
            {
                "material_id": "SSO2-WIP-001",
                "material_type": "STATOR_ASSEMBLY",
                "quantity": "1",
                "unit": "EA",
                "from_location": "SSO2-OUT",
                "to_location": "ASSY-IN",
            }
        ],
        "parent_refs": ["SSO2-WIP-001", "RSO2-WIP-001"],
        "child_refs": ["MTR-001"],
        "source_kind": "SIMULATED",
        "definition_provenance": "SYNTHETIC_ASSUMPTION",
    }


def _scenario() -> dict:
    assy = _module("ASSY")
    assy["ports"] = [
        {
            "port_id": "ASSY-SSO2-IN",
            "direction": "IN",
            "material_types": ["STATOR_ASSEMBLY"],
            "unit": "EA",
            "buffer_id": "ASSY-IN",
            "eligibility_policy": "QUALIFIED_ONLY",
            "capacity": "20",
        }
    ]
    return {
        "contract_version": "vf-scenario-fixture-v0.1",
        "fixture_id": "QA-FIXTURE",
        "run_header": _run(),
        "modules": [_module(), assy],
        "events": [
            {"tick_us": 1_000_000, "module_id": "SSO2", "action": "PRODUCE", "subject_id": "SSO2-WIP-001"},
            {"tick_us": 2_000_000, "module_id": "ASSY", "action": "RECEIVE", "subject_id": "SSO2-WIP-001"},
        ],
        "oracles": [{"id": "O01", "rule": "join_input_parent_count", "expected": 2}],
        "known_limitations": [],
    }


BASE_DOCUMENTS = {
    "run": _run,
    "module": _module,
    "event": _event,
    "transaction": _transaction,
    "scenario": _scenario,
}
BASE_SCHEMAS = {
    "run": "factory-run-v0.1.schema.json",
    "module": "module-manifest-v0.1.schema.json",
    "event": "factory-event-v0.1.schema.json",
    "transaction": "material-transaction-v0.1.schema.json",
    "scenario": "factory-scenario-fixture-v0.1.schema.json",
}


def _apply_patch(document: dict, patch: list[dict]) -> dict:
    document = copy.deepcopy(document)
    for operation in patch:
        parts = operation["path"].split(".")
        target = document
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        last = parts[-1]
        if operation.get("delete"):
            if isinstance(target, list):
                target.pop(int(last))
            else:
                target.pop(last)
        else:
            if isinstance(target, list):
                target[int(last)] = copy.deepcopy(operation["value"])
            else:
                target[last] = copy.deepcopy(operation["value"])
    return document


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not UTC_RE.search(value):
        raise SemanticError(f"not an explicit UTC instant: {value!r}")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise SemanticError(f"not offset-aware UTC: {value!r}")
    return parsed.astimezone(timezone.utc)


def _decimal(value: str, *, ea: bool, allow_zero: bool = False) -> Decimal:
    if not isinstance(value, str) or not DECIMAL_RE.match(value):
        raise SemanticError(f"not a canonical decimal string: {value!r}")
    try:
        quantity = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - regex already guards
        raise SemanticError(f"invalid decimal: {value!r}") from exc
    if quantity < 0 or (quantity == 0 and not allow_zero):
        raise SemanticError(f"nonpositive quantity: {value!r}")
    if ea and quantity != quantity.to_integral_value():
        raise SemanticError(f"fractional EA quantity: {value!r}")
    return quantity


def _require(document: dict, *keys: str) -> None:
    for key in keys:
        if key not in document or document[key] in (None, ""):
            raise SemanticError(f"missing required identity field: {key}")


def validate_run(document: dict) -> None:
    _require(document, "factory_run_id", "workspace_id", "definition_revision",
             "definition_digest", "epoch_utc", "timezone", "scenario_revision")
    if document.get("generation", 0) < 1:
        raise SemanticError("generation must be >= 1")
    if not re.match(r"^sha256:[a-f0-9]{64}$", document["definition_digest"]):
        raise SemanticError("definition_digest is not a pinned SHA-256")
    _parse_utc(document["epoch_utc"])
    if not document.get("model_revisions"):
        raise SemanticError("model_revisions must not be empty")


def validate_module(document: dict) -> None:
    _require(document, "module_id", "workspace_id", "model_type", "model_revision")
    if not document.get("supported_modes"):
        raise SemanticError("supported_modes must not be empty")
    ports = document.get("ports") or []
    seen = set()
    for port in ports:
        _require(port, "port_id", "buffer_id", "eligibility_policy")
        if port["port_id"] in seen:
            raise SemanticError(f"duplicate port_id: {port['port_id']}")
        seen.add(port["port_id"])
        if port.get("direction") not in ("IN", "OUT"):
            raise SemanticError(f"invalid port direction: {port.get('direction')!r}")
        if not port.get("material_types"):
            raise SemanticError("port material_types must not be empty")
        capacity = port.get("capacity")
        if capacity is not None:
            _decimal(str(capacity), ea=port.get("unit") == "EA")


def validate_event(document: dict, run_header: dict | None = None) -> None:
    _require(document, "factory_run_id", "event_id", "source_event_id", "module_id",
             "event_type", "occurred_at_utc", "definition_digest")
    tick = document.get("simulation_tick_us")
    if not isinstance(tick, int) or isinstance(tick, bool) or tick < 0:
        raise SemanticError("simulation_tick_us must be a non-negative integer")
    occurred = _parse_utc(document["occurred_at_utc"])
    if document.get("source_kind") not in ("SIMULATED", "REPLAYED_SOURCE"):
        raise SemanticError("invalid source_kind")
    if document.get("definition_provenance") not in (
        "PDF_EXPLICIT", "VF_ACCEPTED_BASELINE", "MES_AS_BUILT",
        "SA_INFERENCE", "SYNTHETIC_ASSUMPTION", "PENDING_TIPA",
    ):
        raise SemanticError("invalid definition_provenance")
    if not re.match(r"^sha256:[a-f0-9]{64}$", document["definition_digest"]):
        raise SemanticError("event definition_digest is not a pinned SHA-256")
    if run_header is not None:
        expected = _parse_utc(run_header["epoch_utc"]) + timedelta(microseconds=tick)
        if occurred != expected:
            raise SemanticError(
                f"event time {occurred.isoformat()} != epoch+tick {expected.isoformat()}"
            )


def validate_transaction(document: dict) -> None:
    _require(document, "transaction_id", "idempotency_key", "transaction_type")
    legs = document.get("legs") or []
    if not legs:
        raise SemanticError("transaction needs at least one leg")
    for leg in legs:
        _require(leg, "material_id", "material_type", "quantity", "unit")
        _decimal(leg["quantity"], ea=leg.get("unit") == "EA")
    parents = document.get("parent_refs") or []
    children = document.get("child_refs") or []
    if len(parents) != len(set(parents)):
        raise SemanticError("duplicate parent ref (parent consumed twice)")
    if len(children) != len(set(children)):
        raise SemanticError("duplicate child ref")
    if document["transaction_type"] == "TRANSFORM" and not (parents and children):
        raise SemanticError("TRANSFORM requires parent_refs and child_refs")


def _document_digest(document: dict) -> str:
    blob = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def check_transaction_replay(previous: dict, incoming: dict) -> str:
    """Return 'new', 'noop' or raise on identity/idempotency conflict."""
    if previous["transaction_id"] != incoming["transaction_id"]:
        if previous["idempotency_key"] == incoming["idempotency_key"]:
            raise SemanticError("same idempotency key with a different transaction identity")
        return "new"
    if previous["idempotency_key"] != incoming["idempotency_key"]:
        raise SemanticError("same transaction identity with a different idempotency key")
    if _document_digest(previous) != _document_digest(incoming):
        raise SemanticError("same idempotency key with a different payload digest")
    return "noop"


def validate_scenario(document: dict) -> None:
    validate_run(document["run_header"])
    modules = document.get("modules") or []
    module_ids = [module["module_id"] for module in modules]
    if len(module_ids) != len(set(module_ids)):
        raise SemanticError("duplicate module_id")
    for module in modules:
        validate_module(module)
    buffers: dict[str, list[dict]] = {}
    for module in modules:
        for port in module.get("ports") or []:
            buffers.setdefault(port["buffer_id"], []).append(port)
    for buffer_id, ports in buffers.items():
        out_types = {t for p in ports if p["direction"] == "OUT" for t in p["material_types"]}
        in_types = {t for p in ports if p["direction"] == "IN" for t in p["material_types"]}
        if out_types and in_types and not (out_types & in_types):
            raise SemanticError(f"incompatible material types on buffer {buffer_id}")
    signatures = set()
    for event in document.get("events") or []:
        if event["module_id"] not in module_ids:
            raise SemanticError(f"event references unknown module: {event['module_id']}")
        signature = (event["tick_us"], event["module_id"], event["action"], event["subject_id"])
        if signature in signatures:
            raise SemanticError(f"duplicate event identity: {signature}")
        signatures.add(signature)
    if not document.get("oracles"):
        raise SemanticError("scenario needs at least one oracle")


VALIDATORS = {
    "run": validate_run,
    "module": validate_module,
    "event": lambda document: validate_event(document, _run()),
    "transaction": validate_transaction,
    "scenario": validate_scenario,
}


def _cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_invalid_cases(case):
    document = _apply_patch(BASE_DOCUMENTS[case["base"]](), case["patch"])
    schema_name = BASE_SCHEMAS[case["base"]]
    errors = _schema_errors(schema_name, document)
    if case["layer"] == "schema":
        assert errors, f"{case['id']} unexpectedly passed JSON Schema"
        return
    assert not errors, f"{case['id']} is not a semantic-only case: {[e.message for e in errors]}"
    with pytest.raises(SemanticError):
        VALIDATORS[case["base"]](document)


def test_valid_base_documents_pass_schema_and_semantics():
    for name, factory in BASE_DOCUMENTS.items():
        document = factory()
        assert not _schema_errors(BASE_SCHEMAS[name], document), name
        VALIDATORS[name](document)


def test_event_duplicate_identity_rejected():
    event = _event()
    duplicate = copy.deepcopy(event)
    seen = set()
    with pytest.raises(SemanticError):
        for item in (event, duplicate):
            identity = (item["event_id"], item["source_event_id"])
            if identity in seen:
                raise SemanticError("duplicate event identity")
            seen.add(identity)


def test_transaction_idempotency_same_key_same_payload_is_noop():
    first = _transaction()
    second = copy.deepcopy(first)
    assert check_transaction_replay(first, second) == "noop"


def test_transaction_idempotency_same_key_different_payload_rejects():
    first = _transaction()
    second = copy.deepcopy(first)
    second["legs"][0]["material_id"] = "DIFFERENT"
    with pytest.raises(SemanticError):
        check_transaction_replay(first, second)


def test_transaction_idempotency_different_key_rejects():
    first = _transaction()
    second = copy.deepcopy(first)
    second["idempotency_key"] = "IDEM-2"
    with pytest.raises(SemanticError):
        check_transaction_replay(first, second)


def test_transform_requires_both_parents_and_child():
    transaction = _transaction()
    transaction["parent_refs"] = []
    with pytest.raises(SemanticError):
        validate_transaction(transaction)


def test_ea_quantity_is_integral_but_kg_decimal_is_allowed():
    transaction = _transaction()
    transaction["legs"][0]["unit"] = "KG"
    transaction["legs"][0]["quantity"] = "1.5"
    validate_transaction(transaction)
    transaction["legs"][0]["unit"] = "EA"
    with pytest.raises(SemanticError):
        validate_transaction(transaction)


def test_t02_has_no_phantom_rso2_produce_event():
    fixture = json.loads(
        (SCHEMA_DIR / "fixtures" / "T02_UPSTREAM_STARVATION.json").read_text(encoding="utf-8")
    )
    rso2_produce = [
        event for event in fixture["events"]
        if event["module_id"] == "RSO2" and event["action"] == "PRODUCE"
    ]
    assert rso2_produce == []
