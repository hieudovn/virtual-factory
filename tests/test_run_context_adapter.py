"""VF-vNEXT-G2 — discrete.RunContext reconciliation tests.

Proves the legacy discrete.RunContext stays backward compatible and converts
losslessly into the generic RunContextV2 — no duplicate run-identity authority.
"""

from __future__ import annotations

import pytest

from virtual_factory.discrete.run_context import RunContext, RunContextError
from virtual_factory.provenance import (
    DataStatus,
    OriginKind,
    RunContextV2,
    RunContextV2Error,
    from_discrete_run_context,
    to_provenance_v2,
)
from virtual_factory.workspace import StructuralPath


def test_legacy_discrete_run_context_still_works() -> None:
    """Backward compatibility: the legacy constructor/validation is unchanged."""
    rc = RunContext(run_id="run-1", model_id="model-1", scenario_id="scn-1")
    assert rc.run_id == "run-1"
    assert rc.engine_kind == "discrete_manufacturing"
    assert rc.source_kind == "simulation"
    with pytest.raises(RunContextError):
        RunContext(run_id="", model_id="model-1")


def test_conversion_is_lossless_for_existing_fields() -> None:
    rc = RunContext(
        run_id="run-1",
        model_id="model-1",
        model_version="v2",
        scenario_id="scn-1",
        scenario_version="v1",
        random_seed=7,
        environment="demo",
    )
    ctx = from_discrete_run_context(rc, workspace_id="W")
    assert isinstance(ctx, RunContextV2)
    assert ctx.workspace_id == "W"
    assert ctx.run_id == rc.run_id
    assert ctx.model_id == rc.model_id
    assert ctx.model_version == rc.model_version
    assert ctx.scenario_id == rc.scenario_id
    assert ctx.scenario_version == rc.scenario_version
    assert ctx.random_seed == rc.random_seed
    assert ctx.environment == rc.environment
    # engine_kind is carried as the informational profile (not engine authority).
    assert ctx.profile == "discrete_manufacturing"


def test_conversion_requires_workspace_and_valid_source() -> None:
    from virtual_factory.provenance import RunContextV2Error

    rc = RunContext(run_id="run-1", model_id="model-1")
    with pytest.raises(RunContextV2Error):
        from_discrete_run_context(rc, workspace_id="  ")
    with pytest.raises(RunContextV2Error):
        from_discrete_run_context("not-a-run-context", workspace_id="W")  # type: ignore[arg-type]


def test_discrete_context_maps_to_simulation_provenance() -> None:
    rc = RunContext(run_id="run-1", model_id="model-1", scenario_id="scn-1")
    ctx = from_discrete_run_context(
        rc,
        workspace_id="W",
        scope_path=StructuralPath(("W", "ASSY", "ASSY-SL01")),
    )
    prov = to_provenance_v2(ctx, data_status=DataStatus.SYNTHETIC)
    assert prov.workspace_id == "W"
    assert prov.run_id == "run-1"
    assert prov.scenario_id == "scn-1"
    assert prov.origin_kind is OriginKind.SIMULATION
    assert prov.scope_path == StructuralPath(("W", "ASSY", "ASSY-SL01"))


def test_no_duplicate_authority() -> None:
    """The generic context is the single platform authority; the discrete context
    is the domain constructor input that adapts into it."""
    from virtual_factory.provenance.context import RunContextV2 as Generic

    assert Generic is RunContextV2
    assert RunContext is not RunContextV2
    # The adapter produces the generic type (one authority), never a second.
    assert isinstance(
        from_discrete_run_context(RunContext(run_id="r", model_id="m"), workspace_id="W"),
        RunContextV2,
    )


def test_adapter_cannot_create_mismatched_scope_context() -> None:
    """The discrete adapter must not produce a generic context whose scope path
    roots in a different workspace than workspace_id (fail closed)."""
    rc = RunContext(run_id="run-1", model_id="model-1")
    with pytest.raises(RunContextV2Error):
        from_discrete_run_context(
            rc,
            workspace_id="W1",
            scope_path=StructuralPath(("W2", "ASSY", "ASSY-SL01")),
        )
