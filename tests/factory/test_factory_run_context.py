from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from virtual_factory.factory import (
    ClockError,
    FactoryHeader,
    FactoryRunContext,
    HeaderError,
    LifecycleError,
    LifecycleState,
    RunMode,
    Shift,
    SimTick,
)

EPOCH = datetime(2025, 12, 31, 0, 0, tzinfo=timezone.utc)


def _header(**overrides):
    values = {
        "workspace_digest": "sha256:workspace",
        "config_digest": "sha256:config",
        "seed": 42,
        "model_revision": "model-r1",
        "epoch_utc": EPOCH,
        "mode": RunMode.STANDALONE,
    }
    values.update(overrides)
    return FactoryHeader(**values)


def _us(delta):
    return int(delta / timedelta(microseconds=1))


def _context():
    return FactoryRunContext("run-1", _header())


def test_valid_lifecycle_and_generation_reset():
    ctx = _context()
    assert ctx.state is LifecycleState.CREATED
    ctx.validate()
    ctx.initialize()
    ctx.mark_ready()
    ctx.start()
    ctx.advance_to(SimTick(10))
    ctx.pause()
    ctx.resume()
    ctx.stop()
    assert ctx.state is LifecycleState.STOPPED
    assert ctx.generation == 0
    ctx.reset()
    assert ctx.state is LifecycleState.CREATED
    assert ctx.generation == 1
    assert ctx.tick_us == 0


def test_invalid_lifecycle_transitions_raise():
    ctx = _context()
    with pytest.raises(LifecycleError):
        ctx.start()
    ctx.validate()
    with pytest.raises(LifecycleError):
        ctx.mark_ready()
    ctx.initialize()
    ctx.mark_ready()
    ctx.start()
    ctx.stop()
    with pytest.raises(LifecycleError):
        ctx.resume()


def test_header_and_mode_are_immutable():
    header = _header()
    ctx = FactoryRunContext("run-1", header)
    assert ctx.header is header
    assert ctx.header.mode is RunMode.STANDALONE
    with pytest.raises(FrozenInstanceError):
        header.seed = 99
    with pytest.raises(FrozenInstanceError):
        header.mode = RunMode.INTEGRATED


def test_header_requires_aware_utc_epoch_and_valid_mode():
    with pytest.raises(HeaderError):
        _header(epoch_utc=datetime(2025, 12, 31, 0, 0))
    with pytest.raises(HeaderError):
        _header(epoch_utc=datetime(2025, 12, 31, 7, 0, tzinfo=timezone(timedelta(hours=7))))
    with pytest.raises(HeaderError):
        _header(mode="NOT_A_MODE")


def test_pinned_clock_is_aware_utc_and_monotonic():
    ctx = _context()
    ctx.validate()
    ctx.initialize()
    ctx.mark_ready()
    ctx.start()
    ctx.advance_to(SimTick(1_500_000))
    assert ctx.wire_time() == EPOCH + timedelta(microseconds=1_500_000)
    assert ctx.wire_time().utcoffset() == timedelta(0)
    with pytest.raises(ClockError):
        ctx.advance_to(SimTick(1_499_999))
    with pytest.raises(ClockError):
        SimTick(-1)
    with pytest.raises(ClockError):
        SimTick(True)
    with pytest.raises(LifecycleError):
        _context().advance_to(SimTick(1))


def test_shifts_include_c_midnight_and_six_am_boundary():
    ctx = _context()
    noon = _us(timedelta(hours=5))
    afternoon = _us(timedelta(hours=8))
    midnight = _us(timedelta(hours=17))
    before_six = _us(timedelta(hours=22, minutes=59, seconds=59, microseconds=999999))
    six_am = _us(timedelta(hours=23))
    assert ctx.shift_at(SimTick(noon)) is Shift.A
    assert ctx.shift_at(SimTick(afternoon)) is Shift.B
    assert ctx.shift_at(SimTick(midnight)) is Shift.C
    assert ctx.shift_at(SimTick(before_six)) is Shift.C
    assert ctx.shift_at(SimTick(six_am)) is Shift.A


def test_production_day_rolls_at_six_am_local():
    ctx = _context()
    before_six = _us(timedelta(hours=22, minutes=59))
    six_am = _us(timedelta(hours=23))
    assert ctx.production_day(SimTick(before_six)).isoformat() == "2025-12-31"
    assert ctx.production_day(SimTick(six_am)).isoformat() == "2026-01-01"
