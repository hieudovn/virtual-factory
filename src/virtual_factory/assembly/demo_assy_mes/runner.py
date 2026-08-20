"""TIPA ASSY Customer Demo Scenario v1 — deterministic runner.

VF-DM-DEMO-ASSY-MES-01. Drives the scenario facts through the M5 bridge.
Supports reset / start / pause / step / jam / recover and an OEE summary.

Deterministic: identical input produces identical facts and identical message
order.  Reset leaves no runtime state (only the monotonic run generation
increments).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from virtual_factory.assembly.demo_assy_mes.bridge import (
    DemoPipeline,
    build_demo_pipeline,
    fact_to_reality,
)
from virtual_factory.assembly.demo_assy_mes.model import (
    SUB_LINE_ID,
    FactKind,
    DemoFact,
    LineState,
    ScenarioSpec,
)
from virtual_factory.assembly.demo_assy_mes.oee import OeeSummary, compute_oee
from virtual_factory.assembly.demo_assy_mes.scenario import build_scenario_facts
from virtual_factory.integration.gateway import DeliveryResult
from virtual_factory.integration.gateways.memory import InMemoryObsGateway
from virtual_factory.observation.projection import ProjectedMessage


@dataclass
class DemoRunner:
    """Deterministic, resettable single-sub-line demo runner."""

    spec: ScenarioSpec = field(default_factory=ScenarioSpec)
    pipeline: DemoPipeline = field(default_factory=build_demo_pipeline)

    _generation: int = field(default=0, init=False)
    _facts: list[DemoFact] = field(default_factory=list, init=False)
    _cursor: int = field(default=0, init=False)
    _line_state: LineState = field(default=LineState.STOPPED, init=False)
    _running: bool = field(default=False, init=False)
    _fault_triggered: bool = field(default=False, init=False)
    _sim_time_s: float = field(default=0.0, init=False)
    _oee: OeeSummary | None = field(default=None, init=False)
    _delivered: list[ProjectedMessage] = field(default_factory=list, init=False)
    _recent_events: list[dict] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.reset()

    # ── identity ──

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def run_id(self) -> str:
        return f"{SUB_LINE_ID}:R{self._generation}"

    @property
    def line_state(self) -> LineState:
        return self._line_state

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def simulation_time_s(self) -> float:
        return self._sim_time_s

    @property
    def oee(self) -> OeeSummary | None:
        return self._oee

    @property
    def total_facts(self) -> int:
        return len(self._facts)

    # ── control surface ──

    def reset(self) -> None:
        """Full reset: rebuild facts, bump generation, clear all runtime state."""
        self._generation += 1
        self._facts = build_scenario_facts()
        self._cursor = 0
        self._line_state = LineState.STOPPED
        self._running = False
        self._fault_triggered = False
        self._sim_time_s = 0.0
        self._oee = None
        self._recent_events = []
        # Reset in-memory gateways so prior-run messages do not persist.
        for gw in self.pipeline.gateways:
            if isinstance(gw, InMemoryObsGateway):
                gw._messages = []

    def start(self) -> None:
        """Begin the run.  Does NOT process the timeline synchronously —
        advancement happens one fact at a time via step()."""
        self._running = True

    def pause(self) -> None:
        """Stop advancement.  Prevents the next step()."""
        self._running = False

    def trigger_jam(self) -> None:
        """Deterministically advance the scenario to the AP05 jam.

        Emits facts one at a time until the line enters FAULT, then one more
        fact to STOPPED, so the jam is observable via the snapshot.
        """
        self._running = True
        while self._cursor < len(self._facts) and self._line_state != LineState.FAULT:
            self._step_once()
        if self._line_state == LineState.FAULT and self._cursor < len(self._facts):
            self._step_once()  # FAULT → STOPPED

    def recover(self) -> None:
        """Resume after fault/stop.  Only effective once the jam has occurred.

        Advances through the recovery facts (EXCEPTION_RESOLVED,
        LINE_STATE_CHANGED→running, DOWNTIME_END) until the line is RUNNING.
        """
        if not self._fault_triggered:
            return
        if self._line_state not in (LineState.FAULT, LineState.STOPPED):
            return
        self._running = True
        while (self._cursor < len(self._facts)
               and self._line_state != LineState.RUNNING):
            self._step_once()

    # ── stepping ──

    def _emit_fact(self, fact: DemoFact) -> list[DeliveryResult]:
        results = self.pipeline.emit(fact_to_reality(fact, self.run_id))
        self._sim_time_s = fact.simulation_time_s
        if fact.fact_kind == FactKind.RUN_STATUS:
            self._line_state = LineState(fact.detail.get("line_state", "running"))
            if self._line_state == LineState.FAULT:
                self._fault_triggered = True
        self._recent_events.append(fact.to_dict())
        return results

    def _step_once(self) -> list[DeliveryResult]:
        """Emit the next fact (internal; does not check _running)."""
        if self._cursor < len(self._facts):
            fact = self._facts[self._cursor]
            self._cursor += 1
            return self._emit_fact(fact)
        if self._oee is None:
            return self._emit_fact(self._oee_fact())
        return []

    def step(self) -> list[DeliveryResult]:
        """Advance exactly one fact (only while running).  Returns DeliveryResults."""
        if not self._running:
            return []
        return self._step_once()

    def run(self) -> list[DeliveryResult]:
        """Run the full scenario to completion (batch mode; includes OEE)."""
        results: list[DeliveryResult] = []
        self._running = True
        while self._cursor < len(self._facts):
            results.extend(self.step())
        if self._oee is None:
            results.extend(self.step())  # emit OEE fact
        self._running = False
        return results

    def run_to_completion(self) -> list[ProjectedMessage]:
        """Run the full scenario and return all delivered ProjectedMessages."""
        self.run()
        return self.delivered_messages()

    # ── OEE ──

    def _compute_oee(self) -> OeeSummary:
        line_outs = [f for f in self._facts if f.fact_kind == FactKind.LINE_OUT]
        actual = len(line_outs)
        good = sum(1 for f in line_outs if f.disposition == "good")
        reject = sum(1 for f in line_outs if f.disposition == "reject")
        downtime = sum(e - s for s, e in self.spec.downtime_intervals)
        return compute_oee(
            planned_s=self.spec.planned_s,
            downtime_s=downtime,
            ideal_cycle_s=self.spec.ideal_cycle_s,
            actual_count=actual,
            good_count=good,
            reject_count=reject,
        )

    def _oee_fact(self) -> DemoFact:
        oee = self._compute_oee()
        self._oee = oee
        d = oee.to_dict()
        return DemoFact(
            fact_kind=FactKind.OEE_SUMMARY,
            source_event_id="OEE:SUMMARY",
            simulation_time_s=self.spec.planned_s,
            event_type="OEE_SUMMARY",
            station_id=SUB_LINE_ID,
            detail=d,
        )

    # ── read model ──

    def delivered_messages(self) -> list[ProjectedMessage]:
        """All delivered ProjectedMessages across in-memory gateways."""
        messages: list[ProjectedMessage] = []
        for gw in self.pipeline.gateways:
            if isinstance(gw, InMemoryObsGateway):
                messages.extend(gw.messages)
        return messages

    def wip_tokens(self) -> dict[str, str]:
        """WIP id → current station (last fact per WIP)."""
        tokens: dict[str, str] = {}
        for fact in self._facts[:self._cursor]:
            if fact.wip_id:
                tokens[fact.wip_id] = fact.station_id or "?"
        return tokens

    def snapshot(self) -> dict:
        return {
            "run_id": self.run_id,
            "generation": self._generation,
            "subline_id": SUB_LINE_ID,
            "contract_version": "tipa-assy-demo-v1",
            "line_state": self._line_state.value,
            "running": self._running,
            "simulation_time_s": self._sim_time_s,
            "total_facts": len(self._facts),
            "cursor": self._cursor,
            "wip_tokens": self.wip_tokens(),
            "oee": self._oee.to_dict() if self._oee else None,
            "recent_events": self._recent_events[-10:],
        }
