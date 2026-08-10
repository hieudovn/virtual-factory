"""M6-S04 — Demo Controller for TIPA ASSY visualization.

Wraps AssyLineRuntime with control actions:
RESET, STEP, AUTO, PAUSE, SPEED, SCENARIO.

All control flow routes through this controller.
UI never directly mutates runtime state.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional

from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    ConveyorState,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.demo_snapshot import (
    AssyDemoSnapshot,
    build_snapshot,
)
from virtual_factory.assembly.quality_records import QualityStatus


class DemoScenario(str, enum.Enum):
    HAPPY_PATH = "HAPPY_PATH"
    AP06_FAIL_RETEST_PASS = "AP06_FAIL_RETEST_PASS"
    AP08_NG_REINSPECT_PASS = "AP08_NG_REINSPECT_PASS"
    FAILED_FINAL = "FAILED_FINAL"


SCENARIO_QUALITY_OVERRIDES: dict[DemoScenario, dict] = {
    DemoScenario.HAPPY_PATH: {
        "ap06": {"scenario": "PASS", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
    DemoScenario.AP06_FAIL_RETEST_PASS: {
        "ap06": {"scenario": "PASS", "overrides": {1: ["PASS"], 2: ["FAIL", "PASS"]}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
    DemoScenario.AP08_NG_REINSPECT_PASS: {
        "ap06": {"scenario": "PASS", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {1: ["PASS"], 2: ["NG", "PASS"]}},
    },
    DemoScenario.FAILED_FINAL: {
        "ap06": {"scenario": "ALWAYS_FAIL", "overrides": {}},
        "ap08": {"scenario": "PASS", "overrides": {}},
    },
}


@dataclass
class DemoController:
    """Controls the TIPA ASSY demo lifecycle.

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
    _runtime: Optional[AssyLineRuntime] = None
    _config: Optional[AssyLineConfig] = None
    _auto_running: bool = False
    _cycle: int = 0
    _sso2_idx: int = 0
    _carrier_seq: int = 1
    _completed_motors: int = 0
    _sso2_ids: list[str] = field(default_factory=list)
    _last_step_time: float = 0.0

    # --- Initialization ---

    def initialize(self) -> AssyDemoSnapshot:
        """Load config, create runtime, produce upstream, introduce first WIP."""
        self._config = load_assy_config_from_yaml(self.config_path)
        self._apply_scenario_quality()
        self._runtime = AssyLineRuntime(config=self._config)
        self._cycle = 0
        self._carrier_seq = 1
        self._sso2_idx = 0
        self._completed_motors = 0
        self._sso2_ids = []

        # Produce upstream WIPs (enough for 3 motors)
        total = 7
        for _ in range(total):
            self._sso2_ids.append(self._runtime.produce_sso2_wip())
        for _ in range(total):
            self._runtime.produce_rso2_wip()

        # Introduce first WIP
        self._introduce_next_sso2()
        return self.snapshot()

    def _apply_scenario_quality(self) -> None:
        """Apply scenario-specific quality overrides."""
        if not self._config:
            return
        overrides = SCENARIO_QUALITY_OVERRIDES.get(self.scenario, {})
        for station_key, cfg in overrides.items():
            sqc = getattr(self._config.quality, station_key, None)
            if sqc:
                sqc.scenario = cfg.get("scenario", "PASS")
                sqc.overrides = cfg.get("overrides", {})
                # Adjust max_attempts for FAILED_FINAL
                if self.scenario == DemoScenario.FAILED_FINAL:
                    sqc.max_attempts = 2

    def _introduce_next_sso2(self) -> None:
        if self._sso2_idx < len(self._sso2_ids) and self._runtime:
            wip = self._sso2_ids[self._sso2_idx]
            self._sso2_idx += 1
            cid = f"PAL-{self._carrier_seq:03d}"
            self._carrier_seq += 1
            self._runtime.introduce_to_assy(wip, cid)

    # --- Control Actions ---

    def reset(self) -> AssyDemoSnapshot:
        """Full reset: new runtime, re-initialize."""
        return self.initialize()

    def step(self) -> AssyDemoSnapshot:
        """Execute one cycle: dwell + index if ready."""
        if not self._runtime:
            return AssyDemoSnapshot()

        self._cycle += 1

        # On-demand RSO2
        if self._runtime.conveyor.wip_at("AP04") and self._runtime.rso2_buffer_size == 0:
            self._runtime.produce_rso2_wip()

        # Execute dwell
        self._runtime.execute_dwell()

        # Check for RELEASED motors
        for pos in self._runtime.conveyor.occupied_positions():
            wip = self._runtime.conveyor.wip_at(pos)
            if wip and pos == "AP11":
                ws = self._runtime.get_wip(wip)
                if ws and ws.lifecycle.value == "released":
                    self._completed_motors += 1

        # Index if ready
        if self._runtime.conveyor.state == ConveyorState.READY_TO_INDEX:
            self._runtime.index_line()
            # Introduce next SSO2
            self._introduce_next_sso2()

        return self.snapshot()

    def snapshot(self) -> AssyDemoSnapshot:
        """Build current detached snapshot."""
        if not self._runtime:
            return AssyDemoSnapshot()
        return build_snapshot(self._runtime, self.scenario.value)

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
        self.scenario = scenario

    # --- Helpers ---

    @property
    def runtime(self) -> Optional[AssyLineRuntime]:
        return self._runtime

    @property
    def cycle(self) -> int:
        return self._cycle

    @property
    def completed_motors(self) -> int:
        return self._completed_motors
