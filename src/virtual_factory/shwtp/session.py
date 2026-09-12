"""SH-WTP runtime-session factory (VF-vNEXT-G22 / VF-SHW-X2 / VF-SHW-X3).

Builds a generic :class:`~virtual_factory.runcontrol.RuntimeSession` backed by an
accepted SH-WTP model. Lives in the SH-WTP package to preserve the frozen G7
boundary (runcontrol never references SH-WTP).

Three models are constructible through the SAME canonical seam:

- ``whole_plant_x3`` (**canonical default**, VF-SHW-X3): the X3 whole-plant runtime
  (16 admitted scopes, deterministic global 1-second windows, exactly the two
  admitted C2 PI loops, conservative pre-transfer flow limiting, closed water
  ledger and pump head/power feasibility);
- ``whole_plant_x2`` (compatibility, VF-SHW-X2): the accepted 60-second X2
  shallow model with zero C2 loops, reachable explicitly via
  ``model="whole_plant_x2"`` or :func:`build_shwtp_whole_plant_session`;
- ``g21_slice`` (compatibility): the accepted G21 5-scope runnable slice,
  reachable explicitly via ``model="g21_slice"`` or
  :func:`build_shwtp_g21_slice_session`.

Either way there is exactly ONE ``RunLifecycleService`` and ONE
``RuntimeSession`` per session instance: X3 adds no second session, run id,
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
from virtual_factory.shwtp.x3_whole_plant import build_shwtp_whole_plant_x3

SHWTP_MODEL_G21_SLICE = "g21_slice"
SHWTP_MODEL_WHOLE_PLANT_X2 = "whole_plant_x2"
SHWTP_MODEL_WHOLE_PLANT_X3 = "whole_plant_x3"
SHWTP_MODELS = (
    SHWTP_MODEL_G21_SLICE,
    SHWTP_MODEL_WHOLE_PLANT_X2,
    SHWTP_MODEL_WHOLE_PLANT_X3,
)

#: The canonical default model of the ``shwtp`` workspace (X3, VF-SHW-X3).
SHWTP_DEFAULT_MODEL = SHWTP_MODEL_WHOLE_PLANT_X3

X2_SESSION_SCENARIO_ID = "shwtp-x2-whole-plant"
X3_SESSION_SCENARIO_ID = "shwtp-x3-whole-plant"
G21_SESSION_SCENARIO_ID = "shwtp-g21-slice"

#: Session scenario id per model, so a compatibility session never inherits the
#: canonical scenario of a different model.
_DEFAULT_SCENARIO_BY_MODEL = {
    SHWTP_MODEL_G21_SLICE: G21_SESSION_SCENARIO_ID,
    SHWTP_MODEL_WHOLE_PLANT_X2: X2_SESSION_SCENARIO_ID,
    SHWTP_MODEL_WHOLE_PLANT_X3: X3_SESSION_SCENARIO_ID,
}


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
    if model == SHWTP_MODEL_WHOLE_PLANT_X3:
        return (
            build_shwtp_whole_plant_workspace(),
            lambda run_id: build_shwtp_whole_plant_x3(run_id=run_id, **model_kwargs),
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
    scenario_id: str | None = None,
    workspace_id: str = "shwtp",
    model: str = SHWTP_DEFAULT_MODEL,
    **model_kwargs,
) -> RuntimeSession:
    """Build the canonical SH-WTP runtime session over the selected model.

    The canonical default is the X3 whole-plant model (``whole_plant_x3``, 1-second
    windows + the two admitted PI loops); the accepted X2 60-second zero-C2 model
    and the G21 slice stay reachable through their explicit compatibility
    selectors (``model="whole_plant_x2"`` / ``model="g21_slice"``) or the
    dedicated factories. The session scenario id follows the selected model
    unless the caller declares one explicitly.
    """
    workspace, build_model = _resolve_model(model, model_kwargs)
    if scenario_id is None:
        scenario_id = _DEFAULT_SCENARIO_BY_MODEL[model]
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
    scenario_id: str = X2_SESSION_SCENARIO_ID,    workspace_id: str = "shwtp",
    **model_kwargs,
) -> RuntimeSession:
    """Compatibility factory for the accepted X2 whole-plant session.

    The X2 model stays fully constructible with zero C2 loops (60-second windows)
    so its accepted behaviour and tests remain reproducible; it is no longer the
    canonical default (the X3 profile is).
    """
    return build_shwtp_session(
        scenario_id=scenario_id,
        workspace_id=workspace_id,
        model=SHWTP_MODEL_WHOLE_PLANT_X2,
        **model_kwargs,
    )


def build_shwtp_whole_plant_x3_session(
    scenario_id: str = X3_SESSION_SCENARIO_ID,
    workspace_id: str = "shwtp",
    **model_kwargs,
) -> RuntimeSession:
    """Compatibility factory for the canonical X3 whole-plant session (1 s)."""
    return build_shwtp_session(
        scenario_id=scenario_id,
        workspace_id=workspace_id,
        model=SHWTP_MODEL_WHOLE_PLANT_X3,
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
