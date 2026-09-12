"""SH-WTP runtime-session factory (VF-vNEXT-G22 / VF-SHW-X2).

Builds a generic :class:`~virtual_factory.runcontrol.RuntimeSession` backed by an
accepted SH-WTP model. Lives in the SH-WTP package to preserve the frozen G7
boundary (runcontrol never references SH-WTP).

Two models are constructible through the SAME canonical seam:

- ``g21_slice`` (default, unchanged): the accepted G21 5-scope runnable slice;
- ``whole_plant_x2``: the X2 whole-plant shallow runnable model (16 admitted
  scopes + the 9 frozen C1 controls).

Either way there is exactly ONE ``RunLifecycleService`` and ONE
``RuntimeSession`` per session instance: X2 adds no second session, run id,
clock or lifecycle authority.
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

X2_SESSION_SCENARIO_ID = "shwtp-x2-whole-plant"


def _resolve_model(model: str, model_kwargs: dict):
    if model == SHWTP_MODEL_G21_SLICE:
        return build_shwtp_plant_slice_workspace(), lambda: build_shwtp_plant_slice(**model_kwargs)
    if model == SHWTP_MODEL_WHOLE_PLANT_X2:
        return build_shwtp_whole_plant_workspace(), lambda: build_shwtp_whole_plant(**model_kwargs)
    raise SessionError(f"unknown SH-WTP model {model!r}; expected one of {SHWTP_MODELS}")


def build_shwtp_session(
    scenario_id: str = "shwtp-g21-slice",
    workspace_id: str = "shwtp",
    model: str = SHWTP_MODEL_G21_SLICE,
    **model_kwargs,
) -> RuntimeSession:
    """Build a SH-WTP runtime session over the selected frozen model."""
    workspace, builder = _resolve_model(model, model_kwargs)
    if workspace.workspace_id != workspace_id:
        raise SessionError(
            f"workspace_id {workspace_id!r} does not match SH-WTP workspace "
            f"{workspace.workspace_id!r}"
        )

    def bridge_factory():
        return ShwtpExecutionBridge(builder)

    service = RunLifecycleService(workspace, bridge_factory)
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
