"""Factory run identity, lifecycle, pinned clock, and shift calendar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo


class FactoryRunError(ValueError):
    """Base error for factory run context invariants."""


class HeaderError(FactoryRunError):
    """Raised when the immutable factory header is invalid."""


class LifecycleError(FactoryRunError):
    """Raised when a lifecycle transition is not allowed."""


class ClockError(FactoryRunError):
    """Raised when a simulation tick is invalid or moves backwards."""


class RunMode(str, Enum):
    STANDALONE = "STANDALONE"
    INTEGRATED = "INTEGRATED"


class LifecycleState(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    INITIALIZED = "INITIALIZED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class Shift(str, Enum):
    A = "A"
    B = "B"
    C = "C"


_SHIFT_TIMEZONE = "Asia/Ho_Chi_Minh"
_UNSET = object()


@dataclass(frozen=True, order=True, slots=True)
class SimTick:
    """Nonnegative integer microseconds from the pinned UTC epoch."""

    tick_us: int

    def __post_init__(self) -> None:
        if isinstance(self.tick_us, bool):
            raise ClockError("SimTick must be int, not bool")
        if not isinstance(self.tick_us, int):
            raise ClockError(
                f"SimTick must be int, got {type(self.tick_us).__name__}"
            )
        if self.tick_us < 0:
            raise ClockError(f"SimTick must be >= 0, got {self.tick_us}")

    def __int__(self) -> int:
        return self.tick_us

    def __index__(self) -> int:
        return self.tick_us


def coerce_tick(value: SimTick | int) -> SimTick:
    if isinstance(value, SimTick):
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise ClockError(f"tick must be SimTick or int, got {type(value).__name__}")
    return SimTick(value)


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HeaderError(f"{name} must be a non-empty str")
    return value


def _require_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise HeaderError(f"{name} must be int, not bool")
    if not isinstance(value, int) or value < 0:
        raise HeaderError(f"{name} must be int >= 0")
    return value


@dataclass(frozen=True, slots=True)
class FactoryHeader:
    """Immutable facts pinned for the lifetime of one factory run."""

    workspace_digest: str
    config_digest: str
    seed: int
    model_revision: str
    epoch_utc: datetime
    mode: RunMode = RunMode.STANDALONE
    shift_timezone: str = _SHIFT_TIMEZONE

    def __post_init__(self) -> None:
        _require_text(self.workspace_digest, "workspace_digest")
        _require_text(self.config_digest, "config_digest")
        _require_nonnegative_int(self.seed, "seed")
        _require_text(self.model_revision, "model_revision")
        if not isinstance(self.epoch_utc, datetime):
            raise HeaderError("epoch_utc must be a datetime")
        if self.epoch_utc.tzinfo is None or self.epoch_utc.utcoffset() is None:
            raise HeaderError("epoch_utc must be timezone-aware")
        if self.epoch_utc.utcoffset() != timedelta(0):
            raise HeaderError("epoch_utc must be in UTC")
        if not isinstance(self.mode, RunMode):
            try:
                object.__setattr__(self, "mode", RunMode(self.mode))
            except ValueError as exc:
                raise HeaderError(f"invalid run mode: {self.mode!r}") from exc
        if self.shift_timezone != _SHIFT_TIMEZONE:
            raise HeaderError(f"shift_timezone must be {_SHIFT_TIMEZONE!r}")


_VALID_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.CREATED: frozenset({LifecycleState.VALIDATED}),
    LifecycleState.VALIDATED: frozenset({LifecycleState.INITIALIZED}),
    LifecycleState.INITIALIZED: frozenset({LifecycleState.READY}),
    LifecycleState.READY: frozenset({LifecycleState.RUNNING}),
    LifecycleState.RUNNING: frozenset(
        {LifecycleState.PAUSED, LifecycleState.STOPPED, LifecycleState.FAILED}
    ),
    LifecycleState.PAUSED: frozenset(
        {LifecycleState.RUNNING, LifecycleState.STOPPED, LifecycleState.FAILED}
    ),
    LifecycleState.STOPPED: frozenset(),
    LifecycleState.FAILED: frozenset(),
}


class FactoryRunContext:
    """Lifecycle and pinned clock for a single factory run generation."""

    def __init__(
        self,
        run_id: str,
        header: FactoryHeader,
        *,
        generation: int = 0,
        state: LifecycleState = LifecycleState.CREATED,
        tick: SimTick | int = SimTick(0),
    ) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise FactoryRunError("run_id must be a non-empty str")
        if not isinstance(header, FactoryHeader):
            raise FactoryRunError("header must be a FactoryHeader")
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise FactoryRunError("generation must be int, not bool")
        if generation < 0:
            raise FactoryRunError("generation must be >= 0")
        if not isinstance(state, LifecycleState):
            try:
                state = LifecycleState(state)
            except ValueError as exc:
                raise LifecycleError(f"invalid lifecycle state: {state!r}") from exc

        self._run_id = run_id
        self._header = header
        self._generation = generation
        self._state = state
        self._tick = coerce_tick(tick)
        self._failure_reason: str | None = None

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def header(self) -> FactoryHeader:
        return self._header

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def state(self) -> LifecycleState:
        return self._state

    @property
    def tick(self) -> SimTick:
        return self._tick

    @property
    def tick_us(self) -> int:
        return self._tick.tick_us

    @property
    def failure_reason(self) -> str | None:
        return self._failure_reason

    def _require_state(self, expected: LifecycleState, action: str) -> None:
        if self._state is not expected:
            raise LifecycleError(
                f"cannot {action} from state {self._state.value}; "
                f"expected {expected.value}"
            )

    def transition(self, target: LifecycleState) -> None:
        if not isinstance(target, LifecycleState):
            try:
                target = LifecycleState(target)
            except ValueError as exc:
                raise LifecycleError(f"invalid lifecycle state: {target!r}") from exc
        if target not in _VALID_TRANSITIONS[self._state]:
            raise LifecycleError(
                f"invalid transition {self._state.value} -> {target.value}"
            )
        self._state = target

    def validate(self) -> None:
        self._require_state(LifecycleState.CREATED, "validate")
        self.transition(LifecycleState.VALIDATED)

    def initialize(self) -> None:
        self._require_state(LifecycleState.VALIDATED, "initialize")
        self.transition(LifecycleState.INITIALIZED)

    def mark_ready(self) -> None:
        self._require_state(LifecycleState.INITIALIZED, "mark ready")
        self.transition(LifecycleState.READY)

    def start(self) -> None:
        self._require_state(LifecycleState.READY, "start")
        self.transition(LifecycleState.RUNNING)

    def pause(self) -> None:
        self._require_state(LifecycleState.RUNNING, "pause")
        self.transition(LifecycleState.PAUSED)

    def resume(self) -> None:
        self._require_state(LifecycleState.PAUSED, "resume")
        self.transition(LifecycleState.RUNNING)

    def stop(self) -> None:
        if self._state not in (LifecycleState.RUNNING, LifecycleState.PAUSED):
            raise LifecycleError(f"cannot stop from state {self._state.value}")
        self.transition(LifecycleState.STOPPED)

    def fail(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise FactoryRunError("failure reason must be a non-empty str")
        if self._state not in (LifecycleState.RUNNING, LifecycleState.PAUSED):
            raise LifecycleError(f"cannot fail from state {self._state.value}")
        self._failure_reason = reason
        self.transition(LifecycleState.FAILED)

    def reset(self) -> None:
        self._generation += 1
        self._state = LifecycleState.CREATED
        self._tick = SimTick(0)
        self._failure_reason = None

    def advance_to(self, tick: SimTick | int) -> None:
        target = coerce_tick(tick)
        if self._state is not LifecycleState.RUNNING:
            raise LifecycleError("clock can advance only while RUNNING")
        if target < self._tick:
            raise ClockError(
                f"tick cannot decrease: {target.tick_us} < {self._tick.tick_us}"
            )
        self._tick = target

    def wire_time(self, tick: SimTick | int | None = None) -> datetime:
        target = self._tick if tick is None else coerce_tick(tick)
        return self._header.epoch_utc + timedelta(microseconds=target.tick_us)

    def local_time(self, tick: SimTick | int | None = None) -> datetime:
        return self.wire_time(tick).astimezone(
            ZoneInfo(self._header.shift_timezone)
        )

    def shift_at(self, tick: SimTick | int | None = None) -> Shift:
        hour = self.local_time(tick).hour
        if 6 <= hour < 14:
            return Shift.A
        if 14 <= hour < 22:
            return Shift.B
        return Shift.C

    def production_day(self, tick: SimTick | int | None = None) -> date:
        local = self.local_time(tick)
        if local.hour < 6:
            return (local - timedelta(days=1)).date()
        return local.date()
