"""TIPA-VF-G1A-CONTRACT-QA-01 — Draft 2020-12 schema and local reference checks.

Read-only contract QA. These tests do not implement factory runtime and do not
edit the published designs. They validate the five published schemas, resolve
their relative references through an in-memory registry (no HTTP), and validate
the published T01/T02 specification examples.

If a published schema and fixture disagree, the failing test is the evidence;
the report records the contradiction as a blocker rather than changing either
file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO / "docs" / "design" / "tipa-g1"
FIXTURE_DIR = SCHEMA_DIR / "fixtures"

SCHEMA_FILES = (
    "factory-run-v0.1.schema.json",
    "module-manifest-v0.1.schema.json",
    "factory-event-v0.1.schema.json",
    "material-transaction-v0.1.schema.json",
    "factory-scenario-fixture-v0.1.schema.json",
)
FIXTURE_FILES = (
    "T01_TWO_PRODUCERS_JOIN.json",
    "T02_UPSTREAM_STARVATION.json",
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _schemas() -> dict[str, dict]:
    return {name: _load_json(SCHEMA_DIR / name) for name in SCHEMA_FILES}


def _registry() -> Registry:
    resources = []
    for schema in _schemas().values():
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator(schema_name: str):
    schema = _load_json(SCHEMA_DIR / schema_name)
    return Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=FormatChecker(),
    )


def _validate_fixture(fixture_name: str):
    fixture = _load_json(FIXTURE_DIR / fixture_name)
    return sorted(
        _validator("factory-scenario-fixture-v0.1.schema.json").iter_errors(fixture),
        key=lambda error: list(error.absolute_path),
    )


def test_five_meta_schemas_are_valid_draft_2020_12():
    """All five published schemas are valid Draft 2020-12 schemas."""
    schemas = _schemas()
    assert len(schemas) == 5
    for name, schema in schemas.items():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", name
        Draft202012Validator.check_schema(schema)


def test_scenario_relative_refs_resolve_from_local_registry():
    """The scenario fixture's $refs resolve locally without an HTTP fetch."""
    scenario = _load_json(SCHEMA_DIR / "factory-scenario-fixture-v0.1.schema.json")
    registry = _registry()
    resolver = registry.resolver(base_uri=scenario["$id"])
    for ref in ("factory-run-v0.1.schema.json", "module-manifest-v0.1.schema.json"):
        resolved = resolver.lookup(ref)
        assert resolved.contents["$id"].endswith(ref)


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_published_t01_t02_fixtures_validate(fixture_name):
    """T01/T02 must satisfy the published scenario schema.

    This is intentionally strict: the design register says format validation is
    necessary (though not sufficient). A failure is a published-contract gap,
    not a test-side workaround.
    """
    errors = _validate_fixture(fixture_name)
    if errors:
        detail = "\n".join(
            f"  {list(error.absolute_path)}: {error.message}" for error in errors
        )
        pytest.fail(f"{fixture_name} does not validate:\n{detail}")


def test_t01_two_parent_join_is_design_oracle_not_runtime_result():
    """T01 describes the intended two-parent join; it is not engine output."""
    fixture = _load_json(FIXTURE_DIR / "T01_TWO_PRODUCERS_JOIN.json")
    actions = [event["action"] for event in fixture["events"]]
    assert actions.count("RECEIVE") == 2
    assert "REQUEST_JOIN" in actions
    assert "START_JOIN" in actions
    assert "COMPLETE_JOIN" in actions
    oracles = {oracle["id"]: oracle for oracle in fixture["oracles"]}
    assert oracles["O02"]["expected"] == 2
    assert oracles["O03"]["expected"] == 1
    assert any("not observed runtime output" in text for text in fixture["known_limitations"])
    assert "runtime_result" not in fixture
    assert "execution_status" not in fixture


def test_t02_rotor_starvation_is_design_oracle_not_runtime_result():
    """T02 describes AP04 starvation/no phantom feed; it is not engine output."""
    fixture = _load_json(FIXTURE_DIR / "T02_UPSTREAM_STARVATION.json")
    actions = [event["action"] for event in fixture["events"]]
    assert "OUTAGE_START" in actions
    assert "WAIT_FOR_MATERIAL" in actions
    assert "COMPLETE_JOIN" not in actions
    oracles = {oracle["id"]: oracle for oracle in fixture["oracles"]}
    assert oracles["O01"]["expected"] == 0
    assert oracles["O03"]["expected"] == 0
    assert fixture["known_limitations"]
    assert "runtime_result" not in fixture
    assert "execution_status" not in fixture
