"""VF-vNEXT-G2 — generic runtime/run context tests.

Proves: immutability, deterministic serialization, identity separation,
fail-closed validation, mechanism neutrality (no engine-cardinality authority),
lineage metadata, and that continuous + discrete can use the same contract.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from virtual_factory.provenance import (
    RunContextV2,
    RunContextV2Error,
)
from virtual_factory.workspace import StructuralPath


def _basic(scope_path=None, **overrides) -> RunContextV2:
    kwargs = dict(
        workspace_id="W",
        run_id="run-1",
        scope_path=scope_path,
        scenario_id="scn-1",
        model_id="model-1",
    )
    kwargs.update(overrides)
    return RunContextV2(**kwargs)


def test_context_is_immutable() -> None:
    ctx = _basic()
    with pytest.raises(FrozenInstanceError):
        ctx.run_id = "other"  # type: ignore[misc]


def test_serialization_is_deterministic_and_stable() -> None:
    scope = StructuralPath(("W", "AREA", "UNIT"))
    ctx = _basic(scope_path=scope)
    d1 = ctx.to_dict()
    d2 = ctx.to_dict()
    assert d1 == d2
    assert list(d1.keys()) == [
        "workspace_id",
        "run_id",
        "scope_path",
        "scenario_id",
        "scenario_version",
        "model_id",
        "model_version",
        "profile",
        "random_seed",
        "environment",
        "source_run_id",
    ]
    assert d1["scope_path"] == "W/AREA/UNIT"


def test_identity_concepts_are_not_collapsed() -> None:
    ctx = _basic(
        scope_path=StructuralPath(("W", "AREA", "UNIT")),
        scenario_id="scn-1",
        model_id="model-1",
        profile="continuous_process",
    )
    # Distinct values, distinct fields — never aliased into one string.
    assert ctx.workspace_id != ctx.run_id
    assert ctx.scope_path.as_string() == "W/AREA/UNIT"
    assert ctx.scenario_id == "scn-1"
    assert ctx.model_id == "model-1"
    assert ctx.profile == "continuous_process"
    # There is NO canonical_signal_id / canonical_object_id field on the generic
    # context (PIM identity is read-only and absent here).
    assert not hasattr(ctx, "canonical_signal_id")
    assert not hasattr(ctx, "canonical_object_id")


def test_missing_required_identity_fails_closed() -> None:
    with pytest.raises(RunContextV2Error):
        RunContextV2(workspace_id="", run_id="run-1")
    with pytest.raises(RunContextV2Error):
        RunContextV2(workspace_id="W", run_id="  ")
    with pytest.raises(RunContextV2Error):
        RunContextV2(workspace_id="W", run_id="run-1", scenario_id="   ")


def test_invalid_scope_path_type_fails_closed() -> None:
    with pytest.raises(RunContextV2Error):
        RunContextV2(workspace_id="W", run_id="run-1", scope_path="W/AREA")  # type: ignore[arg-type]


def test_mismatched_scope_workspace_identity_fails_closed() -> None:
    with pytest.raises(RunContextV2Error):
        RunContextV2(
            workspace_id="W1",
            run_id="run-1",
            scope_path=StructuralPath(("W2", "AREA", "UNIT")),
        )


def test_invalid_random_seed_fails_closed() -> None:
    with pytest.raises(RunContextV2Error):
        RunContextV2(workspace_id="W", run_id="run-1", random_seed=True)  # type: ignore[arg-type]
    with pytest.raises(RunContextV2Error):
        RunContextV2(workspace_id="W", run_id="run-1", random_seed=-1)


def test_profile_is_informational_not_engine_authority() -> None:
    """Mechanism neutrality: any profile string is accepted; none is a universal
    engine-cardinality rule. Continuous and discrete share the same contract."""
    continuous = _basic(profile="continuous_process")
    discrete = _basic(profile="discrete_manufacturing")
    batch = _basic(profile="batch")
    hybrid = _basic(profile="composed")
    for ctx in (continuous, discrete, batch, hybrid):
        assert isinstance(ctx, RunContextV2)
        assert ctx.workspace_id == "W"
    # No 1-scope = 1-engine invariant anywhere in the type.
    assert continuous.profile != discrete.profile


def test_lineage_source_run_id_is_metadata_only() -> None:
    ctx = _basic(source_run_id="run-0")
    assert ctx.source_run_id == "run-0"
    # Lineage is carried but no orchestration is implemented.
    assert "source_run_id" in ctx.to_dict()


def test_scope_path_optional_for_legacy() -> None:
    ctx = RunContextV2(workspace_id="W", run_id="run-1")
    assert ctx.scope_path is None
    assert ctx.to_dict()["scope_path"] is None
