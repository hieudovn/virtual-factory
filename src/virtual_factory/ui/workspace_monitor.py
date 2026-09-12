"""VF-vNEXT-G24 — Multi-Workspace UI switching + monitoring shell backend.

A headless, browser-free seam that drives a small multi-workspace UI shell
(selector + monitor + run control) on top of the accepted G23
:class:`~virtual_factory.runcontrol.WorkspaceRuntimeRegistry` and G22
:class:`~virtual_factory.runcontrol.RuntimeSession` seams.

Semantics:

- The workspace selector source is the G23 registry metadata (deterministic,
  registration-order independent): TIPA and shwtp are the accepted workspaces.
- Selecting a workspace returns/keeps ONE live ``RuntimeSession`` for that
  workspace only (created lazily via ``registry.select``). Switching never
  mutates, resets, or reuses the inactive workspace's session.
- Run control (step/reset/stop/new-attempt/replay) applies only to the selected
  workspace's session. Unknown workspace / session / action fails closed.
- The monitor view is read-only: workspace identity, run/session state,
  simulation time/step, scope/unit structure, key current values/status, and a
  small live trace. The domain runtime remains the truth owner; the shell is
  observer/controller only.
- SH-WTP assumed topology/fidelity is NEVER presented as site truth: every view
  carries explicit fidelity/status markers and a ``site_truth: false`` basis.
- TIPA reuses the existing six-sub-line ASSY UI/runtime: the view exposes the
  six-sub-line structure and points the shell at the existing demo page
  (``/assy-demo``) rather than re-implementing the visualization.

No gateway routing, no MQTT/Kafka/production export, no MES/PIM change, no G4
redesign, no domain semantics change, no T110/Line2/new physics here.
"""

from __future__ import annotations

from typing import Callable

from virtual_factory.runcontrol import (
    RuntimeSession,
    WorkspaceRegistryError,
    WorkspaceRuntimeRegistry,
)

# Accepted workspace ids (must match G22/G23 factories).
TIPA_WORKSPACE_ID = "TIPA"
SHWTP_WORKSPACE_ID = "shwtp"

# TIPA config path resolution mirrors api.py (`TIPA_ASSY_CONFIG` env override).
_DEFAULT_TIPA_CONFIG = "configs/plants/tipa_assy_demo.yaml"


class WorkspaceMonitorError(ValueError):
    """Raised when a workspace-monitor invariant is violated (fail closed)."""


def _resolve_tipa_config(tipa_config_path: str | None) -> str:
    import os
    from pathlib import Path

    if tipa_config_path:
        return tipa_config_path
    env = os.environ.get("TIPA_ASSY_CONFIG", "")
    if env:
        return env
    return str(
        Path(__file__).resolve().parent.parent.parent.parent
        / "configs" / "plants" / "tipa_assy_demo.yaml"
    )


def _tipa_session_factory(config_path: str) -> Callable[[], RuntimeSession]:
    from virtual_factory.runcontrol import build_tipa_session

    return lambda: build_tipa_session(config_path, "tipa-default")


#: Run states from which a fresh canonical run may be created without first
#: stopping the previous run (VF-vNEXT-R4 fresh-run/scenario semantics).
_TERMINAL_STATES = frozenset({"stopped", "failed"})


def _shwtp_session_factory() -> Callable[[], RuntimeSession]:
    from virtual_factory.shwtp import build_shwtp_session

    return lambda: build_shwtp_session()


def build_platform_registry(
    tipa_config_path: str | None = None,
) -> WorkspaceRuntimeRegistry:
    """Build the platform registry with the two accepted workspaces.

    Registration order is intentionally shwtp-first to prove enumeration is
    registration-order independent (mirrors the G23 registry test pattern).
    """
    registry = WorkspaceRuntimeRegistry()
    registry.register(
        SHWTP_WORKSPACE_ID,
        _shwtp_session_factory(),
        description="SH-WTP G21/G22 plant slice (5 scopes)",
    )
    registry.register(
        TIPA_WORKSPACE_ID,
        _tipa_session_factory(_resolve_tipa_config(tipa_config_path)),
        description="TIPA ASSY six sub-lines",
    )
    return registry


class WorkspaceMonitor:
    """One small shell authority: registry + one live session per workspace.

    Orchestration only. Sessions are isolated per workspace and created lazily
    via ``registry.select``; selecting/controlling TIPA never touches the shwtp
    session and vice-versa.
    """

    def __init__(
        self,
        registry: WorkspaceRuntimeRegistry | None = None,
        *,
        tipa_config_path: str | None = None,
    ) -> None:
        self._tipa_config_path = _resolve_tipa_config(tipa_config_path)
        self._registry = registry or build_platform_registry(tipa_config_path)
        self._sessions: dict[str, RuntimeSession] = {}
        self._selected: str | None = None
        # VF-vNEXT-R4: identities of runs replaced by a fresh-run operation.
        # History is READ-ONLY metadata; replaced runs are never mutated.
        self._run_history: dict[str, list[dict]] = {}
        # VF-vNEXT-R4: ONE TIPA run-id authority for this monitor. Every TIPA
        # run (initial and fresh scenario runs) is created through this factory,
        # so successive runs get fresh canonical run ids.
        self._tipa_run_factory: Callable[[str], RuntimeSession] | None = None

    # ── registry / selector source ─────────────────────────────

    @property
    def tipa_config_path(self) -> str:
        """The TIPA ASSY config path this monitor's registry factory uses."""
        return self._tipa_config_path

    def workspace_ids(self) -> tuple[str, ...]:
        return self._registry.workspace_ids()

    def workspace_list(self) -> dict:
        """Registry metadata: the deterministic selector source."""
        return self._registry.metadata()

    def has(self, workspace_id: str) -> bool:
        return self._registry.has(workspace_id)

    def selected(self) -> str | None:
        return self._selected

    # ── session lifecycle (one live session per workspace) ──────

    def _session_for(self, workspace_id: str) -> RuntimeSession:
        if not self._registry.has(workspace_id):
            raise WorkspaceMonitorError(f"unknown workspace {workspace_id!r}")
        session = self._sessions.get(workspace_id)
        if session is None:
            if workspace_id == TIPA_WORKSPACE_ID:
                session = self._tipa_factory()("tipa-default")
            else:
                session = self._registry.select(workspace_id)
            self._sessions[workspace_id] = session
        return session

    def _tipa_factory(self) -> Callable[[str], RuntimeSession]:
        """The monitor's ONE TIPA run-id authority (lazily built)."""
        if self._tipa_run_factory is None:
            from virtual_factory.runcontrol.session import (
                build_tipa_scenario_run_factory,
            )

            self._tipa_run_factory = build_tipa_scenario_run_factory(
                self._tipa_config_path, TIPA_WORKSPACE_ID
            )
        return self._tipa_run_factory

    def select(self, workspace_id: str) -> dict:
        """Select a workspace and return its monitor view.

        Keeps (does not reset) the existing live session for that workspace;
        never mutates the other workspace's session.
        """
        session = self._session_for(workspace_id)
        self._selected = workspace_id
        return self.view(workspace_id)

    def session_identity(self, workspace_id: str) -> dict:
        session = self._session_for(workspace_id)
        return _session_identity_dict(session)

    def live_session(self, workspace_id: str) -> RuntimeSession:
        """Explicit public seam: the ONE live session for a workspace.

        Returns the SAME object used by ``view``/``control``/``select`` (created
        lazily through the G23 registry). Rich projections/adapters MUST use
        this accessor instead of keeping their own session cache: one workspace
        run authority, no second session/federation/runtime.
        """
        return self._session_for(workspace_id)

    def new_run(self, workspace_id: str, scenario_id: str | None = None) -> dict:
        """Start a FRESH canonical run for one workspace (R4 scenario semantics).

        Never mutates an active run's pinned identity: the previous session
        identity is recorded as read-only history and the workspace's ONE live
        session is replaced by a newly built canonical session pinned to the
        requested scenario (TIPA only). Unknown workspace/scenario fails closed.
        """
        if not self._registry.has(workspace_id):
            raise WorkspaceMonitorError(f"unknown workspace {workspace_id!r}")
        if scenario_id is not None and workspace_id != TIPA_WORKSPACE_ID:
            raise WorkspaceMonitorError(
                f"scenario selection is only supported for {TIPA_WORKSPACE_ID!r}"
            )
        previous = self._sessions.get(workspace_id)
        if previous is not None:
            self._run_history.setdefault(workspace_id, []).append(
                _session_identity_dict(previous)
            )
        if scenario_id is not None:
            factory = self._tipa_factory()
            if previous is not None and previous.state.value not in _TERMINAL_STATES:
                # The replaced run is stopped (terminal) and preserved as
                # history; its identity is never mutated.
                previous.stop()
            session = factory(scenario_id)
        else:
            session = self._registry.select(workspace_id)
        self._sessions[workspace_id] = session
        return self.view(workspace_id)

    def run_history(self, workspace_id: str) -> list[dict]:
        """READ-ONLY identities of runs replaced by ``new_run`` (historical)."""
        return [dict(row) for row in self._run_history.get(workspace_id, ())]

    # ── run control (only the selected workspace/session) ───────

    def control(self, workspace_id: str, action: str) -> dict:
        """Apply one run-control action to that workspace's session only."""
        if not self._registry.has(workspace_id):
            raise WorkspaceMonitorError(f"unknown workspace {workspace_id!r}")
        session = self._session_for(workspace_id)
        _apply_action(session, action)
        return self.view(workspace_id)

    # ── monitor views ───────────────────────────────────────────

    def view(self, workspace_id: str) -> dict:
        session = self._session_for(workspace_id)
        info = next(
            (i for i in self._registry.enumerate() if i.workspace_id == workspace_id),
            None,
        )
        description = info.description if info is not None else ""
        base = _base_view(session, description)
        if workspace_id == SHWTP_WORKSPACE_ID:
            base.update(_shwtp_view_extra(session))
        else:
            base.update(_tipa_view_extra(session))
        base["run_history"] = self.run_history(workspace_id)
        return base


# ═══════════════════════════════════════════════════════════════
# Monitor view builders (read-only projections)
# ═══════════════════════════════════════════════════════════════

def _session_identity_dict(session: RuntimeSession) -> dict:
    return {
        "workspace_id": session.workspace_id,
        "run_id": session.run_id,
        "scenario_id": session.scenario_id,
        "state": session.state.value,
    }


def _base_view(session: RuntimeSession, description: str) -> dict:
    record = session.record
    return {
        "workspace_id": session.workspace_id,
        "description": description,
        "identity": {
            "workspace_id": session.workspace_id,
            "run_id": session.run_id,
            "scenario_id": session.scenario_id,
        },
        "session": {
            **_session_identity_dict(session),
            "step_count": record.step_count,
            "last_time_s": record.last_time_s,
            "last_result": record.last_result,
        },
        "simulation": {
            "time_s": record.last_time_s,
            "step": record.step_count,
            "state": session.state.value,
        },
        "structure": [],
        "values": [],
        "trace": [_step_dict(r) for r in session.trace()[-8:]],
        "site_truth": True,   # overridden to False for SH-WTP below
    }


def _step_dict(result) -> dict:
    return {
        "status": result.status,
        "target_time_s": result.target_time_s,
        "participants": list(result.participants),
        "committed": list(result.committed),
        "failure": result.failure,
    }


def _tipa_view_extra(session: RuntimeSession) -> dict:
    """TIPA monitor: live per-sub-line projection + explicit legacy-UI label.

    The per-sub-line state/status/key values come READ-ONLY from the selected
    G22 ``RuntimeSession``'s own execution bridge (built lazily on first step).
    The shell never creates a second runtime. ``/assy-demo`` is the RICH
    PROJECTION of this SAME canonical session (R2): it renders the six canonical
    runtimes (Frame A overview + Frame B 2D line) and its STEP/RESET act on this
    same session, so shell and rich UI always show the same run/time.
    """
    from virtual_factory.assembly.assy_run_profile import SESSION_SCENARIO_ALIASES
    from virtual_factory.federation import SUB_LINE_IDS, sub_line_path

    record = session.record
    structure = [
        {"scope": sub_line_path(sid).as_string(), "kind": "sub_line", "sub_line_id": sid}
        for sid in SUB_LINE_IDS
    ]

    # Live per-sub-line values from the SELECTED session's own bridge (none
    # until the session has stepped; never build a second runtime here).
    bridge = record.bridge
    sub_lines: list[dict] = []
    if bridge is not None and hasattr(bridge, "sub_line_views"):
        sub_lines = list(bridge.sub_line_views())

    values = [
        {"scope": "session", "key": "run_state", "value": session.state.value},
        {"scope": "session", "key": "simulation_time_s", "value": record.last_time_s},
        {"scope": "session", "key": "step", "value": record.step_count},
    ]
    for row in sub_lines:
        values.extend([
            {"scope": row["scope"], "sub_line_id": row["sub_line_id"],
             "key": "simulation_time_s", "value": row["simulation_time_s"]},
            {"scope": row["scope"], "sub_line_id": row["sub_line_id"],
             "key": "conveyor_state", "value": row["conveyor_state"]},
            {"scope": row["scope"], "sub_line_id": row["sub_line_id"],
             "key": "wip_count", "value": row["wip_count"]},
            {"scope": row["scope"], "sub_line_id": row["sub_line_id"],
             "key": "motor_count", "value": row["motor_count"]},
        ])

    return {
        "runtime": "TIPA ASSY (six sub-lines)",
        "runtime_kind": "selected_g22_session",
        "structure": structure,
        "sub_lines": sub_lines,
        "values": values,
        "site_truth": False,
        "legacy_demo": {
            "page": "/assy-demo",
            "shares_session": True,
            "shares_identity": True,
            "note": (
                "/assy-demo is the SAME canonical TIPA RuntimeSession as this "
                "shell view (one run authority, six canonical sub-lines). It is "
                "a rich projection of the selected session; opening it creates "
                "no second ASSY runtime."
            ),
        },
        "ui_page": "/assy-demo",
        "ui_note": (
            "Same canonical session: /assy-demo projects this shell's selected "
            "G22 TIPA RuntimeSession (same workspace_id/run_id/scenario). "
            "STEP/RESET act on that same session."
        ),
        # VF-vNEXT-R5 (audit I1): the shell can start a FRESH canonical run for a
        # selected scenario through the SAME canonical seam as /assy-demo
        # (WorkspaceMonitor.new_run -> build_tipa_scenario_run_factory, one
        # run-id authority). Scenario ids come from the accepted profile
        # registry; each run is pinned to its own immutable run context.
        "scenario_ids": list(SESSION_SCENARIO_ALIASES),
        "default_scenario_id": (
            session.scenario_id
            if session.scenario_id in SESSION_SCENARIO_ALIASES
            else "tipa-default"
        ),
    }


def _shwtp_view_extra(session: RuntimeSession) -> dict:
    """SH-WTP monitor: accepted G21 5-scope slice + key flow/tank values.

    Assumed topology/fidelity is carried explicitly and never labelled as site
    truth: the view sets ``site_truth: false`` and lists every scope's
    fidelity/status. Flow/tank values come from the live slice (read-only) when
    it exists, otherwise the structure is still shown.
    """
    from virtual_factory.shwtp.expansion import PLANT_SLICE_SCOPES

    record = session.record
    structure = [scope.to_dict() for scope in PLANT_SLICE_SCOPES]
    values: list[dict] = []
    assumed: list[dict] = []

    for scope in PLANT_SLICE_SCOPES:
        row: dict = {
            "scope": scope.vf_path,
            "canonical_id": scope.canonical_id,
            "role": scope.role,
            "fidelity": scope.fidelity,
            "status": scope.status,
            "inbound_link_assumed": scope.inbound_link_assumed,
        }
        if scope.status == "scenario_assumed" or scope.inbound_link_assumed:
            assumed.append(row)
        values.append(row)

    # Live current values (read-only) when the session has built its slice.
    bridge = record.bridge
    if bridge is not None and getattr(bridge, "slice", None) is not None:
        slice_ = bridge.slice
        rows = slice_.monitor_rows()
        for row in rows:
            scope_path = row.get("vf_path")
            for item in values:
                if item["scope"] == scope_path:
                    item["time_s"] = row.get("time_s")
                    item["current_values"] = row.get("values", {})
                    break

    return {
        "runtime": "SH-WTP G21 plant slice",
        "structure": structure,
        "values": values,
        "site_truth": False,
        "assumed_topology": assumed,
        "ui_page": None,
        "ui_note": (
            "VF simulated SH-WTP slice only. Assumed/scenario topology and "
            "fidelity labels are NOT site truth; PIM remains authoritative."
        ),
    }


def _apply_action(session: RuntimeSession, action: str) -> None:
    """Map a run-control action to one session method (fail closed)."""
    normalized = action.strip().lower()
    if normalized == "step":
        session.advance()
    elif normalized == "reset":
        session.reset()
    elif normalized == "stop":
        session.stop()
    elif normalized == "new_attempt":
        session.new_attempt()
    elif normalized == "replay":
        session.replay()
    else:
        raise WorkspaceMonitorError(
            f"unknown run-control action {action!r}; supported: "
            f"step, reset, stop, new_attempt, replay"
        )
