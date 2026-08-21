"""M6-S04 / M6-S04B — Demo Controller for TIPA ASSY visualization.

Wraps AssyLineRuntime / AssyDemoComposition with control actions:
RESET, STEP, AUTO, PAUSE, SPEED, SCENARIO.

As of M6-S04B-I02, internally delegates to AssyDemoComposition
for multi-context management while preserving the existing S04
public API and backward compatibility.

All control flow routes through this controller.
UI never directly mutates runtime state.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.line_runtime import (
    AssyLineRuntime,
)
from virtual_factory.assembly.station_contracts import CompletionMode
from virtual_factory.assembly.demo_snapshot import (
    AssyDemoSnapshot,
    AssyOverviewSnapshot,
    build_overview,
)
from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    AssyDemoContext,
    DemoScenario,
    SCENARIO_QUALITY_OVERRIDES,
)
from virtual_factory.assembly.observation_bridge import (
    AssyObservationBridge,
)
from virtual_factory.assembly.assy_mes_bridge import (
    AssyMesBridge,
)


# Re-export for backward compatibility
DemoScenario = DemoScenario
SCENARIO_QUALITY_OVERRIDES = SCENARIO_QUALITY_OVERRIDES


@dataclass
class DemoController:
    """Controls the TIPA ASSY demo lifecycle.

    M6-S04B-I02: Internally delegates to AssyDemoComposition.
    Public API preserved for backward compatibility.

    Public API:
    - reset()
    - step() → snapshot
    - snapshot() → AssyDemoSnapshot
    - start_auto() / stop_auto() / is_running
    - set_speed(multiplier)
    - set_scenario(scenario)

    All timing is simulated — no wall-clock sleep in runtime.
    Auto-run uses presentation timer for step pacing.
    """

    config_path: str
    scenario: DemoScenario = DemoScenario.HAPPY_PATH
    presentation_speed: float = 1.0

    _composition: Optional[AssyDemoComposition] = None
    _auto_running: bool = False
    _last_step_time: float = 0.0

    # M6-INT-01 — optional downstream observation bridge (never mutates runtime)
    observation_bridge: Optional[AssyObservationBridge] = None

    # VF-DM-DEMO-ASSY-MES-02 — optional six-sub-line MES contract bridge
    mes_bridge: Optional[AssyMesBridge] = None

    # --- Initialization ---

    def initialize(self) -> AssyDemoSnapshot:
        """Load config, create composition with 6 contexts, seed WIPs."""
        self._composition = AssyDemoComposition(
            config_path=self.config_path,
            scenario=self.scenario,
            selected_sub_line_id="ASSY-SL01",
        )
        self._composition.initialize()
        return self.snapshot()

    # --- Control Actions ---

    def reset(self) -> AssyDemoSnapshot:
        """Full reset: rebuild all 6 contexts from scratch.

        VF-DM-DEMO-ASSY-MES-02: also bumps the MES bridge generation so new
        runs never reuse idempotency keys.
        """
        result = self.initialize()
        if self.mes_bridge is not None:
            self.mes_bridge.reset_all()
        self._poll_bridge()
        return result

    def step(self) -> AssyDemoSnapshot:
        """Execute one demo cycle across all contexts.

        Returns snapshot for the currently selected context.
        """
        if self._composition is None:
            return AssyDemoSnapshot()

        self._composition.step_all()
        self._poll_bridge()
        return self.snapshot()

    def snapshot(self) -> AssyDemoSnapshot:
        """Build detached snapshot for the currently selected context."""
        if self._composition is None:
            return AssyDemoSnapshot()
        return self._composition.snapshot()

    # --- Auto-run ---

    @property
    def is_running(self) -> bool:
        return self._auto_running

    def start_auto(self) -> None:
        self._auto_running = True

    def stop_auto(self) -> None:
        self._auto_running = False

    def set_speed(self, multiplier: float) -> None:
        """Set presentation speed multiplier (does NOT change manufacturing config)."""
        self.presentation_speed = max(0.1, min(20.0, multiplier))

    def set_scenario(self, scenario: DemoScenario) -> None:
        """Set scenario. Takes effect on next reset()/initialize()."""
        self.scenario = scenario
        if self._composition is not None:
            self._composition.set_scenario(scenario)

    # --- Backward-compatible helpers ---

    @property
    def runtime(self) -> Optional[AssyLineRuntime]:
        """The runtime for the currently selected context (backward compat)."""
        if self._composition is None:
            return None
        ctx = self._composition.selected_context
        return ctx.runtime if ctx else None

    @property
    def cycle(self) -> int:
        """Demo step number (presentation clock)."""
        if self._composition is None:
            return 0
        return self._composition.demo_step_number

    @property
    def completed_motors(self) -> int:
        """Motors released in the selected context (S04 backward compat)."""
        if self._composition is None:
            return 0
        ctx = self._composition.selected_context
        if ctx is None:
            return 0
        # Count RELEASED WIPs in selected context
        count = 0
        for wip_id in ctx.runtime.wip_ids:
            ws = ctx.runtime.get_wip(wip_id)
            if ws and ws.lifecycle.value == "released":
                count += 1
        return count

    # --- M6-S04B composition access (additive) ---

    @property
    def composition(self) -> Optional[AssyDemoComposition]:
        """The underlying composition (M6-S04B additive API)."""
        return self._composition

    def select_sub_line(self, sub_line_id: str) -> None:
        """Select a sub-line for detail view (M6-S04B)."""
        if self._composition is None:
            raise RuntimeError("Composition not initialized")
        self._composition.select_sub_line(sub_line_id)

    def overview(self) -> AssyOverviewSnapshot:
        """Build six-sub-line overview projection (M6-S04B-I03)."""
        if self._composition is None:
            raise RuntimeError("Composition not initialized")
        return build_overview(self._composition)

    def detail_for(self, sub_line_id: str) -> AssyDemoSnapshot:
        """Build detailed snapshot for a specific sub-line by ID.

        Does NOT mutate selected_sub_line_id.  Read-only access.
        """
        if self._composition is None:
            raise RuntimeError("Composition not initialized")
        ctx = self._composition.get_context(sub_line_id)
        if ctx is None:
            raise ValueError(f"Unknown sub_line_id: {sub_line_id!r}")
        from virtual_factory.assembly.demo_snapshot import build_snapshot
        snap = build_snapshot(ctx.runtime, ctx.effective_scenario.value)
        # Canonical identity from composition
        plant_id = "TIPA"
        if self._composition.identity:
            plant_id = self._composition.identity.plant_id
        snap.plant_id = plant_id
        snap.production_line_id = ctx.identity.production_line_id
        snap.sub_line_id = ctx.identity.sub_line_id
        snap.variant = ctx.identity.variant
        return snap

    # --- OPS-03: interaction binding (thin adapter — no domain logic) ---

    def submit_operation_command(
        self,
        station_id: str,
        wip_id: str,
        command: str,
        payload: Optional[dict] = None,
    ) -> AssyDemoSnapshot:
        """Submit an operation command to the selected context runtime.

        Thin adapter: UI → controller → AssyLineRuntime.submit_operation_command.
        Runtime decides; the returned snapshot is authoritative.
        """
        rt = self.runtime
        if rt is None:
            raise RuntimeError("Composition not initialized")
        rt.submit_operation_command(station_id, wip_id, command, payload)
        self._poll_bridge()
        return self.snapshot()

    @property
    def run_mode(self) -> Optional[CompletionMode]:
        """Effective global run mode of the selected context."""
        if self._composition is None:
            return None
        ctx = self._composition.selected_context
        return ctx.runtime.global_run_mode if ctx else None

    def set_run_mode(self, mode: CompletionMode) -> AssyDemoSnapshot:
        """Set global run mode on all contexts (additive, UI binding)."""
        if self._composition is None:
            raise RuntimeError("Composition not initialized")
        self._composition.set_run_mode(mode)
        return self.snapshot()

    def submit_station_action(
        self, station_id: str, wip_id: str, action: str,
    ) -> AssyDemoSnapshot:
        """OPS-03-C02: exception station action (thin adapter)."""
        rt = self.runtime
        if rt is None:
            raise RuntimeError("Composition not initialized")
        rt.submit_station_action(station_id, wip_id, action)
        self._poll_bridge()
        return self.snapshot()

    # --- M6-INT-01: downstream observation bridge (additive) ---

    def attach_observation_bridge(self, bridge: AssyObservationBridge) -> None:
        """Attach the outbound observation bridge (read-only consumer)."""
        self.observation_bridge = bridge
        # Capture any pre-existing authoritative facts (late-start discovery).
        self._poll_bridge()

    # --- VF-DM-DEMO-ASSY-MES-02: MES contract bridge (additive) ---

    def attach_mes_bridge(self, bridge: AssyMesBridge) -> None:
        """Attach the six-sub-line MES contract bridge (read-only consumer)."""
        self.mes_bridge = bridge
        self._poll_bridge()

    def trigger_jam(
        self, sub_line_id: Optional[str] = None,
    ) -> AssyDemoSnapshot:
        """Deterministic AP05_JAM on the exception target sub-line."""
        target = sub_line_id or (
            self._composition.target_sub_line_id if self._composition else "ASSY-SL03"
        )
        if self.mes_bridge is not None:
            self.mes_bridge.trigger_jam(target)
        self._poll_bridge()
        return self.snapshot()

    def recover(
        self, sub_line_id: Optional[str] = None,
    ) -> AssyDemoSnapshot:
        """Resolve the AP05_JAM after the deterministic 120 s downtime."""
        target = sub_line_id or (
            self._composition.target_sub_line_id if self._composition else "ASSY-SL03"
        )
        if self.mes_bridge is not None:
            self.mes_bridge.recover(target)
        self._poll_bridge()
        return self.snapshot()

    def run_to_terminal(self, max_steps: int = 80) -> AssyDemoSnapshot:
        """Run the demo to its terminal outcome (fixed deterministic horizon),
        then emit the per-sub-line OEE summary."""
        if self._composition is None:
            return AssyDemoSnapshot()
        for _ in range(max_steps):
            self._composition.step_all()
            self._poll_bridge()
        if self.mes_bridge is not None:
            for sl, ctx in self._composition.contexts.items():
                self.mes_bridge.emit_oee(sl, ctx.runtime)
            self._poll_bridge()
        return self.snapshot()

    def _poll_bridge(self) -> None:
        """Poll any attached observation / MES bridges after a runtime mutation."""
        if self._composition is None:
            return
        if self.observation_bridge is not None:
            self.observation_bridge.poll(self._composition)
        if self.mes_bridge is not None:
            self.mes_bridge.poll(self._composition)

    @property
    def outbound_trace(self) -> list[dict]:
        """Ordered outbound observation trace (M6-INT-01 evidence view)."""
        if self.observation_bridge is None:
            return []
        return list(self.observation_bridge.outbound_trace)

    @property
    def mes_outbound_trace(self) -> list[dict]:
        """Ordered MES contract bridge trace (VF-DM-DEMO-ASSY-MES-02)."""
        if self.mes_bridge is None:
            return []
        return list(self.mes_bridge.outbound_trace)

    @property
    def mes_messages(self) -> list[dict]:
        """Delivered MES-compatible ProjectedMessages (evidence view)."""
        if self.mes_bridge is None:
            return []
        return [
            {
                "message_key": m.key,
                "message_type": m.message_type,
                "schema_name": m.schema_name,
                "schema_version": m.schema_version,
                "headers": dict(m.headers),
                "payload": dict(m.payload),
            }
            for m in self.mes_bridge.projected_messages
        ]
