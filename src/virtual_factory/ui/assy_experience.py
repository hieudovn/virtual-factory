"""VF-vNEXT-R2 — canonical same-session rich ASSY experience (projection adapter).

Restores the accepted rich TIPA ASSY experience (Frame A six-sub-line overview +
Frame B 2D physical line + station/WIP inspector read models) on top of the SAME
canonical TIPA ``RuntimeSession`` accepted in R1 (Issue #79 / Issue #80).

Frozen architecture (R0 / Issue #78, Issue #80):

- ONE active TIPA simulation authority:
  ``WorkspaceMonitor -> RuntimeSession -> RunLifecycleService ->
  AssyExecutionBridge -> TipaAssyFederation -> 6 x AssyLineRuntime``.
- This adapter NEVER constructs a session, federation, runtime, controller or
  any other simulation authority: it reads the live session from the same
  ``WorkspaceMonitor`` used by ``/workspaces`` (``monitor.live_session``).
- Projections are DETACHED: ``assembly.demo_snapshot.build_snapshot`` reads the
  canonical ``AssyLineRuntime`` public surface and returns a value object; no
  mutable runtime reference ever reaches the API/UI layer.
- ``positions[]`` stays the sole physical-position truth; quality/genealogy/
  operation data are read-only projections.
- Sub-line selection is PRESENTATION context only: it never resets,
  reconstructs, forks or mutates any runtime and never changes run identity.
- STEP/RESET delegate to the canonical ``RuntimeSession`` lifecycle, so the rich
  UI and ``/workspaces`` observe the same run id / time / step.
- R3 (Observation/MES/output) and legacy-authority-only capabilities (AP05
  jam/OEE, scenario mutation, run-to-terminal) are explicitly DEFERRED and fail
  closed: no legacy ``DemoController``/``AssyDemoComposition`` is ever
  instantiated on this path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from virtual_factory.workspace import StructuralPath

#: Canonical workspace served by the rich ASSY experience.
CANONICAL_TIPA_WORKSPACE = "TIPA"

#: Deferred capabilities -> the gate that owns them.
#: R3 output (observations / mes_messages / mes_trace) is NO LONGER deferred:
#: it is served read-only by ``virtual_factory.ui.assy_output``.
DEFERRED_FEATURES: dict[str, str] = {
    "jam": "R4",
    "recover": "R4",
    "run_to_terminal": "R4",
    "scenario_change": "R4",
}


class AssyExperienceError(ValueError):
    """Raised when the canonical rich ASSY experience cannot serve a request."""


class DeferredUnavailable(RuntimeError):
    """Explicit deferred-unavailable condition (fail closed, never legacy)."""

    def __init__(self, feature: str, reason: str) -> None:
        self.feature = feature
        self.gate = DEFERRED_FEATURES.get(feature, "R3/R4")
        self.reason = reason
        super().__init__(f"{feature} is deferred to {self.gate}: {reason}")


class SessionNotStarted(AssyExperienceError):
    """The canonical session exists but has no runtime projection yet."""


@dataclass(frozen=True, slots=True)
class _ScenarioValue:
    """Shim exposing the accepted ``effective_scenario`` value shape."""

    value: str


@dataclass
class _CanonicalLineContext:
    """Duck-typed ``AssyDemoContext`` surface for ``build_summary``.

    Read-only adapter over ONE canonical federated sub-line so the accepted
    projection helpers can be reused unchanged. It owns no runtime.
    """

    runtime: Any
    identity: Any
    effective_scenario: _ScenarioValue


class CanonicalAssyExperience:
    """Read-rich projection/control adapter over the selected TIPA session."""

    def __init__(self, monitor: Any) -> None:
        self._monitor = monitor
        self._selected_sub_line_id: str = ""

    # ── canonical session access (no second authority) ──────────

    @property
    def session(self):
        """The ONE live canonical TIPA ``RuntimeSession`` (monitor-owned)."""
        return self._monitor.live_session(CANONICAL_TIPA_WORKSPACE)

    def bridge(self):
        """The session's own execution bridge (``None`` before it is built)."""
        self.session  # fail closed on unknown workspace
        return self.session.record.bridge

    def federation(self):
        """The session's own federation (``None`` before the bridge exists)."""
        bridge = self.bridge()
        return getattr(bridge, "federation", None) if bridge is not None else None

    def sub_line_ids(self) -> tuple[str, ...]:
        from virtual_factory.federation import SUB_LINE_IDS

        return SUB_LINE_IDS

    def selected_sub_line_id(self) -> str:
        return self._selected_sub_line_id or self.sub_line_ids()[0]

    def _ensure_projection(self):
        """The canonical six-line projection, materialized without a second runtime.

        If the selected session has not yet built its own execution context and
        has never been stepped, one in-context ``reset`` materializes the
        session's OWN canonical federation at the fresh R1 profile baseline
        (t = 0). It never advances simulation time and never creates a second
        session/runtime; a session with real state is never reset here.
        """
        federation = self.federation()
        if federation is not None:
            return federation
        record = self.session.record
        if record.step_count == 0 and not record.last_time_s:
            self.session.reset()
        return self.federation()

    def _require_federation(self):
        federation = self._ensure_projection()
        if federation is None:
            raise SessionNotStarted(
                "the canonical TIPA session has no runtime projection yet"
            )
        return federation

    def require_federation(self):
        """Public R3 seam: the ONE canonical federation (never constructs one).

        Materializes the session's own runtime projection when it does not
        exist yet (no time advance, no second runtime) and fails closed with
        ``SessionNotStarted`` otherwise.
        """
        return self._require_federation()

    # ── identity envelope ──────────────────────────────────────

    def session_identity(self) -> dict:
        session = self.session
        record = session.record
        profile = None
        federation = self.federation()
        if federation is not None and federation.run_profile is not None:
            profile = federation.run_profile.to_dict()
        else:
            # The pinned profile is a pure resolution of the session scenario_id:
            # report it even before the canonical projection is materialized.
            try:
                from virtual_factory.assembly.assy_run_profile import (
                    build_tipa_run_profile,
                )

                profile = build_tipa_run_profile(session.scenario_id).to_dict()
            except Exception:
                profile = None
        return {
            "authority": "canonical_tipa_runtime_session",
            "workspace_id": session.workspace_id,
            "run_id": session.run_id,
            "scenario_id": session.scenario_id,
            "profile_id": session.profile_id,
            "run_state": session.state.value,
            "step_count": record.step_count,
            "simulation_time_s": record.last_time_s,
            "started": record.bridge is not None,
            "selected_sub_line_id": self.selected_sub_line_id(),
            "selection_is_presentation_only": True,
            "run_profile": profile,
            "site_truth": False,
            "note": (
                "Same canonical TIPA RuntimeSession as /workspaces: one run "
                "authority, six canonical AssyLineRuntime truths. Scenario/"
                "profile is pinned run input; projections are detached read "
                "models. No second simulation runtime exists."
            ),
        }

    def identity(self) -> dict:
        """Public identity/status payload (used by the UI identity bar)."""
        return {"canonical": self.session_identity()}

    # ── Frame A: six-sub-line overview ─────────────────────────

    def overview(self) -> dict:
        """Frame A projection: exactly the six canonical sub-lines."""
        from virtual_factory.assembly.demo_snapshot import build_summary, AssyOverviewSnapshot

        session = self.session
        record = session.record
        federation = self._ensure_projection()
        sub_lines: list = []

        if federation is not None:
            plant_id = "TIPA"
            if federation.identity is not None:
                plant_id = federation.identity.plant_id
            for sub_line_id in self.sub_line_ids():
                entry = federation.get(sub_line_id)
                summary = build_summary(
                    _CanonicalLineContext(
                        runtime=entry.runtime,
                        identity=entry.identity,
                        effective_scenario=_ScenarioValue(
                            entry.effective_scenario or "HAPPY_PATH"
                        ),
                    ),
                    plant_id,
                )
                row = summary.to_dict()
                row["scope"] = entry.path.as_string()
                row["run_state"] = "running" if record.step_count else "created"
                sub_lines.append(row)
            total_created = sum(r["motors_created"] for r in sub_lines)
            total_released = sum(r["motors_released"] for r in sub_lines)
            total_holds = sum(
                r["active_quality_holds"] + r["operator_holds"] for r in sub_lines
            )
            target = (
                federation.run_profile.target_sub_line_id
                if federation.run_profile is not None
                else ""
            )
        else:
            # Session exists but no runtime projection yet: report the six
            # canonical structural rows honestly (no runtime, no time advance).
            plant_id = "TIPA"
            for sub_line_id in self.sub_line_ids():
                sub_lines.append({
                    "plant_id": plant_id,
                    "production_line_id": "ASSY",
                    "sub_line_id": sub_line_id,
                    "variant": "",
                    "label": sub_line_id,
                    "effective_scenario": "",
                    "scope": StructuralPath(("TIPA", "ASSY", sub_line_id)).as_string(),
                    "line_state": "created",
                    "dwell_number": 0,
                    "simulation_time_s": 0.0,
                    "wips_on_line": 0,
                    "motors_created": 0,
                    "motors_released": 0,
                    "active_quality_holds": 0,
                    "operator_holds": 0,
                    "held_station": "",
                    "held_wip_id": "",
                    "is_exception": False,
                    "run_state": "created",
                })
            total_created = total_released = total_holds = 0
            target = ""

        snapshot = AssyOverviewSnapshot(
            demo_step_number=record.step_count,
            scenario=session.scenario_id,
            target_sub_line_id=target,
            selected_sub_line_id=self.selected_sub_line_id(),
            total_motors_created=total_created,
            total_motors_released=total_released,
            total_active_holds=total_holds,
            sub_lines=tuple(_FrozenRow(r) for r in sub_lines),
        )
        payload = snapshot.to_dict()
        payload["sub_lines"] = sub_lines
        payload["canonical"] = self.session_identity()
        return payload

    # ── Frame B: 2D physical line + inspector ──────────────────

    def detail(self, sub_line_id: str | None = None) -> dict:
        """Detached Frame B snapshot for one canonical sub-line."""
        from virtual_factory.assembly.demo_snapshot import build_snapshot

        federation = self._require_federation()
        sub_line_id = (sub_line_id or self.selected_sub_line_id()).strip()
        try:
            entry = federation.get(sub_line_id)
        except Exception as exc:  # fail closed on unknown sub-line
            raise AssyExperienceError(
                f"unknown ASSY sub-line {sub_line_id!r}: {exc}"
            ) from exc

        snapshot = build_snapshot(
            entry.runtime, entry.effective_scenario or "HAPPY_PATH"
        )
        payload = snapshot.to_dict()
        payload["sub_line_id"] = sub_line_id
        payload["scope"] = entry.path.as_string()
        payload["canonical_sub_line"] = {
            "sub_line_id": sub_line_id,
            "scope": entry.path.as_string(),
            "variant": entry.identity.variant if entry.identity is not None else "",
            "effective_scenario": entry.effective_scenario,
            "runtime_object_id": id(entry.runtime),
        }
        payload["canonical"] = self.session_identity()
        return payload

    def snapshot(self) -> dict:
        """Legacy-compatible POST /assy-demo/snapshot payload (selected line)."""
        return self.detail()

    # ── presentation selection (never runtime ownership) ───────

    def select(self, sub_line_id: str) -> dict:
        if not isinstance(sub_line_id, str) or not sub_line_id.strip():
            raise AssyExperienceError("sub_line_id is required")
        sub_line_id = sub_line_id.strip()
        if sub_line_id not in self.sub_line_ids():
            raise AssyExperienceError(
                f"unknown ASSY sub-line {sub_line_id!r}; "
                f"valid: {sorted(self.sub_line_ids())}"
            )
        # Presentation context only: no runtime is reset/reconstructed/forked.
        self._selected_sub_line_id = sub_line_id
        self._require_federation()
        return self.detail(sub_line_id)

    # ── canonical lifecycle controls ───────────────────────────

    def step(self) -> dict:
        """Advance the SELECTED canonical session (one coordination boundary)."""
        session = self.session
        session.advance()
        return self.detail()

    def reset(self) -> dict:
        """In-context reset of the SELECTED canonical session (R1-C01 semantics)."""
        session = self.session
        session.reset()
        return self.detail()

    # ── thin same-session OPS-03/OPS-04 bindings ───────────────

    def operation_command(
        self, sub_line_id: str, station_id: str, wip_id: str,
        command: str, payload: dict | None = None,
    ) -> dict:
        """OPS-03 thin binding: command the canonical sub-line runtime directly."""
        entry, detail = self._runtime_for(sub_line_id)
        entry.runtime.submit_operation_command(station_id, wip_id, command, payload)
        return self.detail(sub_line_id)

    def station_action(
        self, sub_line_id: str, station_id: str, wip_id: str, action: str,
    ) -> dict:
        """OPS-03/OPS-04 thin binding: station action on the canonical runtime."""
        entry, _ = self._runtime_for(sub_line_id)
        entry.runtime.submit_station_action(station_id, wip_id, action)
        return self.detail(sub_line_id)

    def set_run_mode(self, mode: str) -> dict:
        """Thin binding: set the effective run mode on the six canonical lines."""
        from virtual_factory.assembly.station_contracts import CompletionMode

        parsed = CompletionMode(mode)
        federation = self._require_federation()
        for sub_line_id in self.sub_line_ids():
            federation.get(sub_line_id).runtime.global_run_mode = parsed
        payload = self.detail()
        payload["run_mode"] = parsed.value
        return payload

    def _runtime_for(self, sub_line_id: str):
        federation = self._require_federation()
        sub_line_id = (sub_line_id or self.selected_sub_line_id()).strip()
        try:
            entry = federation.get(sub_line_id)
        except Exception as exc:
            raise AssyExperienceError(
                f"unknown ASSY sub-line {sub_line_id!r}: {exc}"
            ) from exc
        return entry, None

    # ── explicit deferred (fail closed, no legacy authority) ───

    @staticmethod
    def deferred(feature: str, reason: str) -> None:
        raise DeferredUnavailable(feature, reason)

    def assert_hold_state(self) -> dict:
        """Bounded hold/freeze read model (held-one / five-continue evidence)."""
        self._require_federation()
        bridge = self.bridge()
        if bridge is None:
            raise SessionNotStarted("no runtime projection yet")
        held = tuple(bridge.held_sub_line_ids)
        rows = {
            row["sub_line_id"]: {
                "simulation_time_s": row["simulation_time_s"],
                "wip_count": row["wip_count"],
                "motor_count": row["motor_count"],
                "held": row["sub_line_id"] in held,
            }
            for row in bridge.sub_line_views()
        }
        return {"held_sub_line_ids": list(held), "sub_lines": rows}


@dataclass(frozen=True, slots=True)
class _FrozenRow:
    """Minimal frozen row wrapper accepted by ``AssyOverviewSnapshot``."""

    _data: dict

    def to_dict(self) -> dict:
        return dict(self._data)
