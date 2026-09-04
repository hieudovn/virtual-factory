"""Adapters reconciling legacy/domain run-context precedents with the G2 generic context.

The generic :class:`~virtual_factory.provenance.context.RunContextV2` is the
single platform-level run-context authority. Existing domain-specific context
types convert into it WITHOUT creating a second authoritative definition:

- ``discrete.RunContext`` is the discrete-domain constructor input and stays
  backward compatible; this module provides a lossless conversion into
  ``RunContextV2`` (its ``engine_kind`` becomes the informational ``profile``,
  its ``source_kind`` maps to the frozen ``origin_kind=simulation``).
"""

from __future__ import annotations

from virtual_factory.provenance.context import RunContextV2, RunContextV2Error
from virtual_factory.provenance.enums import OriginKind
from virtual_factory.provenance.envelope import ProvenanceV2
from virtual_factory.workspace.identity import StructuralPath


def from_discrete_run_context(
    run_context,
    workspace_id: str,
    *,
    scope_path: StructuralPath | None = None,
) -> RunContextV2:
    """Losslessly adapt a legacy ``discrete.RunContext`` into the generic context.

    ``workspace_id`` is required (it is not present on the legacy discrete
    context). ``scope_path`` is optional. ``engine_kind`` is carried as the
    informational ``profile`` (NOT an engine-cardinality authority); the frozen
    ``source_kind='simulation'`` is validated but not re-encoded (provenance
    origin_kind is derived at envelope build time).
    """
    # Import lazily to keep the generic package free of a hard discrete import
    # at module load time (the adapter is the single coupling point).
    from virtual_factory.discrete.run_context import RunContext

    if not isinstance(run_context, RunContext):
        raise RunContextV2Error(
            f"run_context must be discrete.RunContext, got {type(run_context).__name__}"
        )
    return RunContextV2(
        workspace_id=workspace_id,
        run_id=run_context.run_id,
        scope_path=scope_path,
        scenario_id=run_context.scenario_id,
        scenario_version=run_context.scenario_version,
        model_id=run_context.model_id,
        model_version=run_context.model_version,
        profile=run_context.engine_kind,
        random_seed=run_context.random_seed,
        environment=run_context.environment,
        source_run_id=None,
    )


def to_provenance_v2(
    context: RunContextV2,
    *,
    origin_kind: OriginKind = OriginKind.SIMULATION,
    fidelity=None,
    data_status=None,
    semantic_contract_version: str | None = None,
    semantic_contract_sha: str | None = None,
    evidence_note: str | None = None,
    runtime_signal_id: str | None = None,
    simulation_time_s: float | None = None,
    step: int | None = None,
) -> ProvenanceV2:
    """Build an immutable ``ProvenanceV2`` from a generic run context.

    Purely additive; does not fabricate any PIM canonical id. Semantic pins are
    passed through as opaque immutable strings (G9 owns binding validation).
    """
    return ProvenanceV2(
        workspace_id=context.workspace_id,
        run_id=context.run_id,
        scope_path=context.scope_path,
        scenario_id=context.scenario_id,
        origin_kind=origin_kind,
        fidelity=fidelity,
        data_status=data_status,
        semantic_contract_version=semantic_contract_version,
        semantic_contract_sha=semantic_contract_sha,
        evidence_note=evidence_note,
        runtime_signal_id=runtime_signal_id,
        simulation_time_s=simulation_time_s,
        step=step,
    )
