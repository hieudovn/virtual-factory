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
from virtual_factory.assembly.demo_snapshot import (
    AssyDemoSnapshot,
)
from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    AssyDemoContext,
    DemoScenario,
    SCENARIO_QUALITY_OVERRIDES,
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
        """Full reset: rebuild all 6 contexts from scratch."""
        return self.initialize()

    def step(self) -> AssyDemoSnapshot:
        """Execute one demo cycle across all contexts.

        Returns snapshot for the currently selected context.
        """
        if self._composition is None:
            return AssyDemoSnapshot()

        self._composition.step_all()
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
        """Total motors released across all contexts (S04 backward compat: selected context)."""
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
