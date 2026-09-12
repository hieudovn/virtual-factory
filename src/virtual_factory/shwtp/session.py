"""SH-WTP runtime-session factory (VF-vNEXT-G22).

Builds a generic :class:`~virtual_factory.runcontrol.RuntimeSession` backed by
the accepted SH-WTP G21 plant slice. Lives in the SH-WTP package to preserve the
frozen G7 boundary (runcontrol never references SH-WTP).
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


def build_shwtp_session(
    scenario_id: str = "shwtp-g21-slice",
    workspace_id: str = "shwtp",
    **slice_kwargs,
) -> RuntimeSession:
    """Build a SH-WTP G21 plant-slice runtime session (5 scopes, one workspace)."""
    workspace = build_shwtp_plant_slice_workspace()
    if workspace.workspace_id != workspace_id:
        raise SessionError(
            f"workspace_id {workspace_id!r} does not match SH-WTP workspace "
            f"{workspace.workspace_id!r}"
        )

    def bridge_factory():
        return ShwtpExecutionBridge(lambda: build_shwtp_plant_slice(**slice_kwargs))

    service = RunLifecycleService(workspace, bridge_factory)
    return RuntimeSession(service, workspace_id, scenario_id)
