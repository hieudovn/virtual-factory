"""VF-vNEXT-G4 — deterministic composition coordinator tests.

Proves (Issue #49): deterministic validate/advance/stage/validate/commit;
independent cadences reach one boundary; cyclic graph staged exchange safe;
container-only cannot execute; no direct cross-scope mutation; failure semantics
fail closed without false rollback claims; undeclared exchange and multi-producer
input rejected.
"""

from __future__ import annotations

import pytest

from virtual_factory.composition import (
    BoundaryPort,
    BoundaryTransfer,
    CompositionBinding,
    CompositionGraph,
    CoordinationError,
    Coordinator,
    ParticipantError,
    PortCategory,
    PortDirection,
    PortRef,
)
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    build_workspace,
)

_W = "W"
_AREA = StructuralPath(("W", "AREA"))
_A = StructuralPath(("W", "AREA", "UNIT-A"))
_B = StructuralPath(("W", "AREA", "UNIT-B"))
_CONTAINER = StructuralPath(("W", "AREA", "UNIT-ONLY"))


def _workspace():
    return build_workspace("W", [
        ScopeSpec("AREA", ScopeMode.CONTAINER_ONLY),
        ScopeSpec("UNIT-A", ScopeMode.EXECUTABLE_CAPABLE, parent_path=_AREA),
        ScopeSpec("UNIT-B", ScopeMode.EXECUTABLE_CAPABLE, parent_path=_AREA),
        ScopeSpec("UNIT-ONLY", ScopeMode.CONTAINER_ONLY, parent_path=_AREA),
    ])


def _ports():
    return [
        BoundaryPort(PortRef(_A, "out"), PortDirection.OUT, PortCategory.MATERIAL, unit="m3/s"),
        BoundaryPort(PortRef(_A, "in"), PortDirection.IN, PortCategory.MATERIAL, unit="m3/s"),
        BoundaryPort(PortRef(_B, "out"), PortDirection.OUT, PortCategory.MATERIAL, unit="m3/s"),
        BoundaryPort(PortRef(_B, "in"), PortDirection.IN, PortCategory.MATERIAL, unit="m3/s"),
    ]


def _cycle_graph():
    return CompositionGraph(
        "W",
        bindings=[
            CompositionBinding("e1", PortRef(_A, "out"), PortRef(_B, "in")),
            CompositionBinding("e2", PortRef(_B, "out"), PortRef(_A, "in")),
        ],
        ports=_ports(),
    )


class Participant:
    """Mechanism-neutral test participant: fixed substeps or event cadence."""

    def __init__(self, scope_path, *, dt_s=None, events=()):
        self._scope = scope_path
        self._dt = dt_s
        self._events = sorted(events, key=lambda e: e[0])
        self._idx = 0
        self._time = 0.0
        self.received: list[BoundaryTransfer] = []
        self.fail_advance = False
        self.fail_commit = False

    @property
    def scope_path(self):
        return self._scope

    @property
    def current_time_s(self):
        return self._time

    def advance_to(self, target_time_s):
        if self.fail_advance:
            raise ParticipantError("injected advance failure")
        if target_time_s < self._time:
            raise ParticipantError("cannot move simulation time backward")
        staged = []
        if self._dt is not None:
            while self._time < target_time_s:
                self._time = min(self._time + self._dt, target_time_s)
                staged.extend(self._take_due(self._time))
        else:
            while self._idx < len(self._events) and self._events[self._idx][0] <= target_time_s:
                t, transfer = self._events[self._idx]
                self._time = max(self._time, t)
                staged.append(transfer)
                self._idx += 1
            self._time = max(self._time, target_time_s)
        return tuple(staged)

    def _take_due(self, upto):
        out = []
        while self._idx < len(self._events) and self._events[self._idx][0] <= upto:
            out.append(self._events[self._idx][1])
            self._idx += 1
        return out

    def commit_transfers(self, inbound):
        if self.fail_commit:
            raise ParticipantError("injected commit failure")
        self.received.extend(inbound)


def _transfer(tid, src, tgt, binding_id, window="w1", time_s=1.0, payload=None):
    return BoundaryTransfer(
        transfer_id=tid,
        source=PortRef(*src),
        target=PortRef(*tgt),
        binding_id=binding_id,
        window_id=window,
        simulation_time_s=time_s,
        workspace_id="W",
        payload=payload or {"v": tid},
    )


def _coordinator(workspace=None, graph=None):
    return Coordinator(workspace or _workspace(), graph or _cycle_graph())


def test_deterministic_order_independent_of_registration_order() -> None:
    a = Participant(_A, dt_s=1.0)
    b = Participant(_B, dt_s=2.0)
    c1 = _coordinator()
    c1.register(a)
    c1.register(b)
    o1 = c1.run_window("w1", 4.0)
    c2 = _coordinator()
    c2.register(b)
    c2.register(a)
    o2 = c2.run_window("w1", 4.0)
    assert o1.participants == o2.participants
    assert o1.participants == ("W/AREA/UNIT-A", "W/AREA/UNIT-B")


def test_cycle_staged_exchange_is_deterministic() -> None:
    a = Participant(_A, dt_s=1.0, events=[(1.0, _transfer("tA", (_A, "out"), (_B, "in"), "e1"))])
    b = Participant(_B, dt_s=1.0, events=[(1.0, _transfer("tB", (_B, "out"), (_A, "in"), "e2"))])
    c = _coordinator()
    c.register(a)
    c.register(b)
    outcome = c.run_window("w1", 2.0)
    assert outcome.status == "completed"
    # Deterministic commit order: by target scope path (A < B), then transfer id.
    assert outcome.committed == ("tB", "tA")
    # Consumers receive only staged/detached values; no recursive edge execution.
    assert [t.transfer_id for t in a.received] == ["tB"]
    assert [t.transfer_id for t in b.received] == ["tA"]


def test_different_cadences_reach_one_boundary() -> None:
    fixed = Participant(_A, dt_s=0.5)  # fixed substeps
    event = Participant(_B, dt_s=None, events=[(1.5, _transfer("t", (_B, "out"), (_A, "in"), "e2"))])
    c = Coordinator(_workspace(), CompositionGraph(
        "W",
        bindings=[CompositionBinding("e2", PortRef(_B, "out"), PortRef(_A, "in"))],
        ports=_ports(),
    ))
    c.register(fixed)
    c.register(event)
    outcome = c.run_window("w1", 3.0)
    assert outcome.status == "completed"
    assert fixed.current_time_s == 3.0
    assert event.current_time_s == 3.0


def test_container_only_scope_cannot_execute() -> None:
    c = _coordinator()
    with pytest.raises(CoordinationError):
        c.register(Participant(_CONTAINER, dt_s=1.0))


def test_dangling_participant_scope_fails_closed() -> None:
    c = _coordinator()
    foreign = StructuralPath(("W", "AREA", "DOES-NOT-EXIST"))
    with pytest.raises(CoordinationError):
        c.register(Participant(foreign, dt_s=1.0))


def test_already_at_boundary_is_no_op() -> None:
    a = Participant(_A, dt_s=1.0)
    c = _coordinator()
    c.register(a)
    c.run_window("w1", 5.0)
    outcome = c.run_window("w2", 5.0)  # already at boundary
    assert outcome.status == "completed"
    assert outcome.committed == ()
    assert a.current_time_s == 5.0


def test_failure_after_another_participant_advanced_is_not_rolled_back() -> None:
    a = Participant(_A, dt_s=1.0)
    b = Participant(_B, dt_s=1.0)
    b.fail_advance = True  # B (later in deterministic order) fails
    c = _coordinator()
    c.register(a)
    c.register(b)
    outcome = c.run_window("w1", 4.0)
    assert outcome.status == "failed"
    assert outcome.committed == ()
    # A (earlier in order) already advanced; it is NOT rolled back.
    assert a.current_time_s == 4.0
    assert b.current_time_s == 0.0


def test_backward_time_fails_closed() -> None:
    a = Participant(_A, dt_s=1.0)
    c = _coordinator()
    c.register(a)
    c.run_window("w1", 5.0)
    outcome = c.run_window("w2", 3.0)  # target behind current time
    assert outcome.status == "failed"
    assert "backward" in (outcome.failure or "")


def test_advance_failure_stops_window_before_exchange() -> None:
    a = Participant(_A, dt_s=1.0, events=[(1.0, _transfer("tA", (_A, "out"), (_B, "in"), "e1"))])
    b = Participant(_B, dt_s=1.0)
    b.fail_advance = True
    c = _coordinator()
    c.register(a)
    c.register(b)
    outcome = c.run_window("w1", 2.0)
    assert outcome.status == "failed"
    assert outcome.committed == ()
    assert b.received == []  # no commit happened


def test_undeclared_exchange_fails_closed() -> None:
    a = Participant(_A, dt_s=1.0, events=[
        (1.0, BoundaryTransfer(
            transfer_id="tX",
            source=PortRef(_A, "out"),
            target=PortRef(_B, "in"),  # exists but binding id wrong below
            binding_id="e9",
            window_id="w1",
            simulation_time_s=1.0,
            workspace_id="W",
        ))
    ])
    c = _coordinator()
    c.register(a)
    c.register(Participant(_B, dt_s=1.0))
    outcome = c.run_window("w1", 2.0)
    assert outcome.status == "failed"


def test_multi_producer_input_rejected() -> None:
    # Two distinct source ports (same scope) both bound to the same target port:
    # this is an implicit many-to-one merge and must be rejected.
    graph = CompositionGraph(
        "W",
        bindings=[
            CompositionBinding("e1", PortRef(_A, "out"), PortRef(_B, "in")),
            CompositionBinding("e3", PortRef(_A, "out2"), PortRef(_B, "in")),
        ],
        ports=_ports()
        + [BoundaryPort(PortRef(_A, "out2"), PortDirection.OUT, PortCategory.MATERIAL, unit="m3/s")],
    )
    a = Participant(_A, dt_s=1.0, events=[
        (1.0, _transfer("tA", (_A, "out"), (_B, "in"), "e1")),
        (1.0, _transfer("tA2", (_A, "out2"), (_B, "in"), "e3")),
    ])
    c = Coordinator(_workspace(), graph)
    c.register(a)
    c.register(Participant(_B, dt_s=1.0))
    outcome = c.run_window("w1", 2.0)
    assert outcome.status == "failed"
    assert "multi-producer" in (outcome.failure or "")


def test_commit_failure_stops_further_commits_without_rollback() -> None:
    a = Participant(_A, dt_s=1.0, events=[(1.0, _transfer("tA", (_A, "out"), (_B, "in"), "e1"))])
    b = Participant(_B, dt_s=1.0)
    b.fail_commit = True
    c = _coordinator()
    c.register(a)
    c.register(b)
    outcome = c.run_window("w1", 2.0)
    assert outcome.status == "failed"
    assert outcome.committed == ()
    # Honest semantics: participants already advanced are NOT rolled back.
    assert a.current_time_s == 2.0
    assert b.current_time_s == 2.0


def test_no_direct_cross_scope_state_mutation_via_payload() -> None:
    producer_state = {"level": 5.0}
    a = Participant(_A, dt_s=1.0, events=[(1.0, _transfer("tA", (_A, "out"), (_B, "in"), "e1", payload=producer_state))])
    b = Participant(_B, dt_s=1.0)
    c = _coordinator()
    c.register(a)
    c.register(b)
    c.run_window("w1", 2.0)
    # The committed payload is detached: mutating the producer's original dict
    # after the window does not change what the consumer received.
    producer_state["level"] = 999.0
    received = b.received[0].payload
    assert received["level"] == 5.0
    # Consumer cannot mutate the frozen payload.
    with pytest.raises(TypeError):
        received["level"] = -1.0  # type: ignore[index]
