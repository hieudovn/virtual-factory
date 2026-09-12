"""SH-WTP runtime-session factory (VF-vNEXT-G22 / VF-SHW-X2).

Builds a generic :class:`~virtual_factory.runcontrol.RuntimeSession` backed by an
accepted SH-WTP model. Lives in the SH-WTP package to preserve the frozen G7
boundary (runcontrol never references SH-WTP).

Two models are constructible through the SAME canonical seam:

- ``whole_plant_x2`` (**canonical default**, VF-SHW-X2-C01): the X2 whole-plant
  shallow runnable model (16 admitted scopes + the 9 frozen C1 controls);
- ``g21_slice`` (compatibility selector only): the accepted G21 5-scope runnable
  slice, reachable explicitly via ``model="g21_slice"`` or
  :func:`build_shwtp_g21_slice_session`.

Either way there is exactly ONE ``RunLifecycleService`` and ONE
``RuntimeSession`` per session instance: X2 adds no second session, run id,
clock or lifecycle authority.

The model's runtime identity (``run_id`` on every participant, transfer and
runtime-truth projection) comes from the ACTIVE attempt's immutable run context
through the ``bridge_factory_ctx`` seam, so a reset keeps the attempt identity
and a new attempt / replay receives the lifecycle-issued identity (VF-SHW-X2-C02,
C02-1). No model may mint or default its own run identity inside a session.
"""

from __future__ import annotations

from virtual_factory.runcontrol import (
    RunLifecycleService,
    RuntimeSession,
    SessionError,
)
from virtual_factory.shwtp.bridge import ShwtpExecutionBridge
from virtual_factory.shwtp.expansion import (
    build_shwtp_plant_slice,
    build_shwtp_plant_slice_workspace,
)
from virtual_factory.shwtp.whole_plant import (
    build_shwtp_whole_plant,
    build_shwtp_whole_plant_workspace,
)

SHWTP_MODEL_G21_SLICE = "g21_slice"
SHWTP_MODEL_WHOLE_PLANT_X2 = "whole_plant_x2"
SHWTP_MODELS = (SHWTP_MODEL_G21_SLICE, SHWTP_MODEL_WHOLE_PLANT_X2)

#: The canonical default model of the ``shwtp`` workspace (X2, VF-SHW-X2-C01).
SHWTP_DEFAULT_MODEL = SHWTP_MODEL_WHOLE_PLANT_X2

X2_SESSION_SCENARIO_ID = "shwtp-x2-whole-plant"
G21_SESSION_SCENARIO_ID = "shwtp-g21-slice"


def _resolve_model(model: str, model_kwargs: dict):
    """Return ``(workspace, build_for_run)`` for the selected model.

    ``build_for_run(run_id)`` builds the model bound to ONE attempt's runtime
    identity, so the session never falls back to a fixed model run id (C02-1).
    """
    if "run_id" in model_kwargs:
        raise SessionError(
            "the SH-WTP runtime identity is bound to the run-lifecycle attempt "
            "context; run_id must not be passed to the session factory"
        )
    if model == SHWTP_MODEL_G21_SLICE:
        return (
            build_shwtp_plant_slice_workspace(),
            lambda run_id: build_shwtp_plant_slice(run_id=run_id, **model_kwargs),
        )
    if model == SHWTP_MODEL_WHOLE_PLANT_X2:
        return (
            build_shwtp_whole_plant_workspace(),
            lambda run_id: build_shwtp_whole_plant(run_id=run_id, **model_kwargs),
        )
    raise SessionError(f"unknown SH-WTP model {model!r}; expected one of {SHWTP_MODELS}")


def _require_attempt_bound_bridge() -> object:
    """Fail closed: SH-WTP execution bridges are attempt-bound (C02-1).

    A zero-arg bridge factory would have to invent a run identity for the model
    (the previous ``run-shwtp-whole-plant-x2`` default), which is exactly the
    defect VF-SHW-X2-C02 fixes. The identity always comes from the attempt's own
    immutable run context.
    """
    raise SessionError(
        "SH-WTP execution bridges are attempt-bound: build them from the active "
        "attempt's run context (bridge_factory_ctx), never from an ambient/fixed run id"
    )


def build_shwtp_session(
    scenario_id: str = X2_SESSION_SCENARIO_ID,
    workspace_id: str = "shwtp",
    model: str = SHWTP_DEFAULT_MODEL,
    **model_kwargs,
) -> RuntimeSession:
    """Build the canonical SH-WTP runtime session over the selected model.

    The canonical default is the X2 whole-plant model (``whole_plant_x2``); the
    accepted G21 slice stays reachable through the explicit compatibility
    selector (``model="g21_slice"``) or ``build_shwtp_g21_slice_session()``.
    """
    workspace, build_model = _resolve_model(model, model_kwargs)
    if workspace.workspace_id != workspace_id:
        raise SessionError(
            f"workspace_id {workspace_id!r} does not match SH-WTP workspace "
            f"{workspace.workspace_id!r}"
        )

    def bridge_factory_ctx(context):
        # The attempt's own immutable context is the ONE identity source: the
        # model, its participants and every transfer carry THIS run id, so a
        # reset preserves the attempt identity and a new attempt / replay gets
        # the lifecycle-issued identity (no cross-attempt leakage).
        run_id = getattr(context, "run_id", None)
        if not isinstance(run_id, str) or not run_id.strip():
            raise SessionError(
                "SH-WTP requires the attempt run identity from the run context"
            )
        return ShwtpExecutionBridge(lambda: build_model(run_id))

    service = RunLifecycleService(
        workspace,
        _require_attempt_bound_bridge,
        bridge_factory_ctx=bridge_factory_ctx,
    )
    return RuntimeSession(service, workspace_id, scenario_id)


def build_shwtp_whole_plant_session(
    scenario_id: str = X2_SESSION_SCENARIO_ID,
    workspace_id: str = "shwtp",
    **model_kwargs,
) -> RuntimeSession:
    """Build the X2 whole-plant runtime session (16 scopes, 9 C1 controls)."""
    return build_shwtp_session(
        scenario_id=scenario_id,
        workspace_id=workspace_id,
        model=SHWTP_MODEL_WHOLE_PLANT_X2,
        **model_kwargs,
    )


def build_shwtp_g21_slice_session(
    scenario_id: str = G21_SESSION_SCENARIO_ID,
    workspace_id: str = "shwtp",
    **model_kwargs,
) -> RuntimeSession:
    """Compatibility factory for the accepted G21 5-scope slice session."""
    return build_shwtp_session(
        scenario_id=scenario_id,
        workspace_id=workspace_id,
        model=SHWTP_MODEL_G21_SLICE,
        **model_kwargs,
    )
