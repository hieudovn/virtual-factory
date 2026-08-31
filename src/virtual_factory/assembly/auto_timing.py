"""AUTO-TIME-01A — AUTO timing domain model (generic, config-driven).

Slice A only: pure timing domain + config parsing + deterministic seeded RNG.
ASSY runtime behavior is UNCHANGED in this slice — no ``execute_dwell()``,
``_advance_operation()``, ``OperationRegistry``, or ``OperationExecution``
changes. Runtime/dwell integration is deferred to AUTO-TIME-01B.

Design principles:
- Stochastic/config logic lives OUTSIDE the OperationExecution state machine.
- No AP-specific branches in the generic timing engine.
- Fail closed on invalid config — never silently repair.
- Isolated seeded RNG (``random.Random``); never global random state.

At the end of this slice the following chain works in isolation:

    YAML -> validated AutoTimingProfile -> TimingResolver resolves/samples
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from typing import Optional

import yaml


class TimingConfigError(ValueError):
    """Raised when a timing config invariant is violated (fail closed)."""


class TimingBehavior(str, enum.Enum):
    """Global timing behavior for AUTO mode."""

    DETERMINISTIC = "DETERMINISTIC"
    VARIABLE = "VARIABLE"


class DurationPolicyType(str, enum.Enum):
    """Supported duration policy kinds."""

    FIXED = "fixed"
    NORMAL = "normal"


def _opt_float(value: object, label: str) -> Optional[float]:
    """Coerce a config scalar to float, rejecting bool and non-numerics."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TimingConfigError(f"{label} must be a number, not bool")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TimingConfigError(
            f"{label} must be numeric, got {value!r}"
        ) from exc


@dataclass(frozen=True, slots=True)
class DurationPolicy:
    """One duration policy for a sub-action (FIXED or bounded NORMAL)."""

    type: DurationPolicyType
    # FIXED
    seconds: Optional[float] = None
    # NORMAL
    mean_s: Optional[float] = None
    stddev_s: Optional[float] = None
    min_s: Optional[float] = None
    max_s: Optional[float] = None

    def __post_init__(self) -> None:
        if self.type == DurationPolicyType.FIXED:
            if self.seconds is None:
                raise TimingConfigError(
                    "FIXED duration policy requires 'seconds'"
                )
            if not self.seconds > 0:
                raise TimingConfigError(
                    f"FIXED duration 'seconds' must be > 0, got {self.seconds!r}"
                )
        elif self.type == DurationPolicyType.NORMAL:
            for name, value in (
                ("mean_s", self.mean_s),
                ("stddev_s", self.stddev_s),
                ("min_s", self.min_s),
                ("max_s", self.max_s),
            ):
                if value is None:
                    raise TimingConfigError(
                        f"NORMAL duration policy requires '{name}'"
                    )
            if not self.mean_s > 0:
                raise TimingConfigError(
                    f"NORMAL 'mean_s' must be > 0, got {self.mean_s!r}"
                )
            if not self.stddev_s >= 0:
                raise TimingConfigError(
                    f"NORMAL 'stddev_s' must be >= 0, got {self.stddev_s!r}"
                )
            if not self.min_s > 0:
                raise TimingConfigError(
                    f"NORMAL 'min_s' must be > 0, got {self.min_s!r}"
                )
            if not self.max_s >= self.min_s:
                raise TimingConfigError(
                    f"NORMAL 'max_s' must be >= 'min_s' "
                    f"(max_s={self.max_s!r}, min_s={self.min_s!r})"
                )
            if not self.min_s <= self.mean_s <= self.max_s:
                raise TimingConfigError(
                    f"NORMAL 'mean_s' must be within [min_s, max_s] "
                    f"(mean_s={self.mean_s!r}, min_s={self.min_s!r}, "
                    f"max_s={self.max_s!r})"
                )
        else:
            raise TimingConfigError(
                f"Unknown duration policy type {self.type!r}"
            )

    def nominal_duration_s(self) -> float:
        """Nominal (expected) duration: FIXED -> seconds, NORMAL -> mean_s."""
        if self.type == DurationPolicyType.FIXED:
            return self.seconds
        return self.mean_s


@dataclass(frozen=True, slots=True)
class SubActionTiming:
    """One sub-action timing element within an AutoTimingProfile."""

    id: str
    duration: DurationPolicy


@dataclass(frozen=True, slots=True)
class AutoTimingProfile:
    """Frozen per-station AUTO timing profile composed of sub-actions."""

    profile_id: str
    station_id: str
    sub_actions: tuple[SubActionTiming, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise TimingConfigError("profile_id must be a non-empty string")
        if not isinstance(self.station_id, str) or not self.station_id.strip():
            raise TimingConfigError("station_id must be a non-empty string")
        if not self.sub_actions:
            raise TimingConfigError(
                f"Profile {self.profile_id!r} requires at least one sub-action"
            )
        ids = [sa.id for sa in self.sub_actions]
        if len(set(ids)) != len(ids):
            raise TimingConfigError(
                f"Profile {self.profile_id!r} has duplicate sub-action ids: {ids}"
            )
        for sa in self.sub_actions:
            if not isinstance(sa.id, str) or not sa.id.strip():
                raise TimingConfigError("sub-action id must be a non-empty string")

    def nominal_duration_s(self) -> float:
        """Profile nominal duration = sum of nominal sub-action durations."""
        return float(sum(sa.duration.nominal_duration_s() for sa in self.sub_actions))


@dataclass(frozen=True, slots=True)
class TimingSubActionSample:
    """Frozen resolved sample for one sub-action (with policy provenance)."""

    id: str
    policy: DurationPolicyType
    nominal_duration_s: float
    effective_duration_s: float
    # Policy provenance (raw config values)
    seconds: Optional[float] = None
    mean_s: Optional[float] = None
    stddev_s: Optional[float] = None
    min_s: Optional[float] = None
    max_s: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy": self.policy.value,
            "nominal_duration_s": self.nominal_duration_s,
            "effective_duration_s": self.effective_duration_s,
            "seconds": self.seconds,
            "mean_s": self.mean_s,
            "stddev_s": self.stddev_s,
            "min_s": self.min_s,
            "max_s": self.max_s,
        }


@dataclass(frozen=True, slots=True)
class TimingSample:
    """Frozen resolved timing for one profile under one TimingBehavior."""

    profile_id: str
    timing_behavior: TimingBehavior
    nominal_duration_s: float
    effective_duration_s: float
    sub_actions: tuple[TimingSubActionSample, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "timing_behavior": self.timing_behavior.value,
            "nominal_duration_s": self.nominal_duration_s,
            "effective_duration_s": self.effective_duration_s,
            "sub_actions": [sa.to_dict() for sa in self.sub_actions],
        }


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


class TimingResolver:
    """Resolve an AutoTimingProfile into a TimingSample.

    - DETERMINISTIC: FIXED -> seconds; NORMAL -> mean_s (no random draw).
    - VARIABLE:      FIXED -> seconds; NORMAL -> seeded bounded normal sample
                     clamped to [min_s, max_s].

    Owns an isolated ``random.Random``. Never touches global random state.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        if seed is not None and rng is not None:
            raise TimingConfigError(
                "TimingResolver accepts either 'seed' or 'rng', not both"
            )
        if seed is not None:
            if isinstance(seed, bool):
                raise TimingConfigError("seed must be int, not bool")
            if not isinstance(seed, int) or seed < 0:
                raise TimingConfigError(
                    f"seed must be a non-negative int, got {seed!r}"
                )
            self._seed: Optional[int] = seed
            self._rng: Optional[random.Random] = random.Random(seed)
        elif rng is not None:
            if not isinstance(rng, random.Random):
                raise TimingConfigError(
                    f"rng must be a random.Random instance, got {type(rng).__name__}"
                )
            self._seed = None
            self._rng = rng
        else:
            # No seed and no RNG: DETERMINISTIC resolution still works.
            # VARIABLE NORMAL sampling will fail closed (see _sample).
            self._seed = None
            self._rng = None

    @property
    def seed(self) -> Optional[int]:
        return self._seed

    def resolve(
        self,
        profile: AutoTimingProfile,
        behavior: TimingBehavior,
    ) -> TimingSample:
        """Resolve one profile into a frozen sample (sample-once semantics)."""
        if not isinstance(profile, AutoTimingProfile):
            raise TimingConfigError(
                f"profile must be AutoTimingProfile, got {type(profile).__name__}"
            )
        if not isinstance(behavior, TimingBehavior):
            raise TimingConfigError(
                f"behavior must be TimingBehavior, got {behavior!r}"
            )

        sub_samples: list[TimingSubActionSample] = []
        for sa in profile.sub_actions:
            effective = self._sample(sa.duration, behavior)
            sub_samples.append(TimingSubActionSample(
                id=sa.id,
                policy=sa.duration.type,
                nominal_duration_s=sa.duration.nominal_duration_s(),
                effective_duration_s=effective,
                seconds=sa.duration.seconds,
                mean_s=sa.duration.mean_s,
                stddev_s=sa.duration.stddev_s,
                min_s=sa.duration.min_s,
                max_s=sa.duration.max_s,
            ))

        nominal = float(sum(s.nominal_duration_s for s in sub_samples))
        effective = float(sum(s.effective_duration_s for s in sub_samples))
        return TimingSample(
            profile_id=profile.profile_id,
            timing_behavior=behavior,
            nominal_duration_s=nominal,
            effective_duration_s=effective,
            sub_actions=tuple(sub_samples),
        )

    def _sample(self, policy: DurationPolicy, behavior: TimingBehavior) -> float:
        if behavior == TimingBehavior.DETERMINISTIC:
            # FIXED -> seconds; NORMAL -> mean_s. No random draw.
            if policy.type == DurationPolicyType.FIXED:
                return policy.seconds
            return policy.mean_s

        # VARIABLE
        if policy.type == DurationPolicyType.FIXED:
            return policy.seconds
        if self._rng is None:
            raise TimingConfigError(
                "VARIABLE NORMAL sampling requires a seeded TimingResolver"
            )
        draw = self._rng.normalvariate(policy.mean_s, policy.stddev_s)
        return _clamp(draw, policy.min_s, policy.max_s)


# ═══════════════════════════════════════════════════════════
# Config parsing (YAML -> validated domain objects)
# ═══════════════════════════════════════════════════════════

def parse_timing_behavior(value: object) -> TimingBehavior:
    """Parse simulation.timing_behavior. Default DETERMINISTIC. Fails closed."""
    if value is None or value == "":
        return TimingBehavior.DETERMINISTIC
    raw = str(value).strip().upper()
    try:
        return TimingBehavior(raw)
    except ValueError as exc:
        raise TimingConfigError(
            f"Invalid timing_behavior {value!r} "
            f"(allowed: {[b.value for b in TimingBehavior]})"
        ) from exc


def parse_random_seed(value: object) -> int:
    """Parse simulation.random_seed. Default 42. Non-negative int, not bool."""
    if value is None:
        return 42
    if isinstance(value, bool):
        raise TimingConfigError("random_seed must be int, not bool")
    if not isinstance(value, int) or value < 0:
        raise TimingConfigError(
            f"random_seed must be a non-negative int, got {value!r}"
        )
    return value


def parse_duration_policy(data: dict) -> DurationPolicy:
    """Parse one duration policy dict. Fails closed on unknown/malformed input."""
    if not isinstance(data, dict):
        raise TimingConfigError(
            f"duration policy must be a mapping, got {type(data).__name__}"
        )
    raw_type = data.get("type")
    if not isinstance(raw_type, str) or raw_type.strip() == "":
        raise TimingConfigError("duration policy requires a non-empty 'type'")
    try:
        policy_type = DurationPolicyType(str(raw_type).strip().lower())
    except ValueError as exc:
        raise TimingConfigError(
            f"Invalid duration policy type {raw_type!r} "
            f"(allowed: {[t.value for t in DurationPolicyType]})"
        ) from exc

    return DurationPolicy(
        type=policy_type,
        seconds=_opt_float(data.get("seconds"), "seconds"),
        mean_s=_opt_float(data.get("mean_s"), "mean_s"),
        stddev_s=_opt_float(data.get("stddev_s"), "stddev_s"),
        min_s=_opt_float(data.get("min_s"), "min_s"),
        max_s=_opt_float(data.get("max_s"), "max_s"),
    )


def parse_sub_action_timing(data: dict) -> SubActionTiming:
    """Parse one sub-action timing dict."""
    if not isinstance(data, dict):
        raise TimingConfigError(
            f"sub-action must be a mapping, got {type(data).__name__}"
        )
    sid = data.get("id")
    if not isinstance(sid, str) or not sid.strip():
        raise TimingConfigError("sub-action requires a non-empty 'id'")
    duration = parse_duration_policy(data.get("duration") or {})
    return SubActionTiming(id=sid, duration=duration)


def parse_auto_timing_profile(
    station_key: str,
    data: dict,
) -> AutoTimingProfile:
    """Parse one per-station profile dict (station_key -> profile mapping)."""
    if not isinstance(station_key, str) or not station_key.strip():
        raise TimingConfigError("profile station key must be a non-empty string")
    if not isinstance(data, dict):
        raise TimingConfigError(
            f"profile for {station_key!r} must be a mapping, "
            f"got {type(data).__name__}"
        )
    profile_id = data.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id.strip():
        raise TimingConfigError(
            f"profile for {station_key!r} requires a non-empty 'profile_id'"
        )
    sub_data = data.get("sub_actions")
    if not isinstance(sub_data, list) or not sub_data:
        raise TimingConfigError(
            f"profile {profile_id!r} requires a non-empty 'sub_actions' list"
        )
    sub_actions = tuple(parse_sub_action_timing(sa) for sa in sub_data)
    return AutoTimingProfile(
        profile_id=profile_id,
        station_id=station_key,
        sub_actions=sub_actions,
    )


def parse_auto_timing_profiles(
    data: object,
) -> dict[str, AutoTimingProfile]:
    """Parse the auto_timing_profiles mapping. Empty/None -> {}."""
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TimingConfigError(
            f"auto_timing_profiles must be a mapping, got {type(data).__name__}"
        )
    return {
        str(station_key): parse_auto_timing_profile(str(station_key), profile_data)
        for station_key, profile_data in data.items()
    }


def check_profiles_against_positions(
    profiles: dict[str, AutoTimingProfile],
    positions: object,
) -> None:
    """Fail closed if a profile key is not a configured conveyor position.

    Positions may be a sequence of position ids (or None, which skips the
    cross-check). This check is additive; AUTO-TIME-01B will consume it when
    wiring profiles into the runtime.
    """
    if positions is None:
        return
    if not isinstance(positions, (list, tuple)):
        raise TimingConfigError(
            f"positions must be a sequence, got {type(positions).__name__}"
        )
    allowed = {str(p) for p in positions}
    for station_key in profiles:
        if station_key not in allowed:
            raise TimingConfigError(
                f"auto_timing_profile key {station_key!r} is not a configured "
                f"conveyor position (positions: {sorted(allowed)})"
            )


def parse_timing_config(
    data: dict,
) -> tuple[TimingBehavior, int, dict[str, AutoTimingProfile]]:
    """Parse timing config from an already-loaded YAML mapping.

    Reads (additive, all optional):
      simulation.timing_behavior  (default DETERMINISTIC)
      simulation.random_seed      (default 42)
      auto_timing_profiles        (default {})

    Cross-checks profile keys against conveyor.positions when present.
    Returns (timing_behavior, random_seed, profiles).
    """
    if not isinstance(data, dict):
        raise TimingConfigError(
            f"timing config must be a mapping, got {type(data).__name__}"
        )

    simulation = data.get("simulation") or {}
    behavior = parse_timing_behavior(simulation.get("timing_behavior"))
    seed = parse_random_seed(simulation.get("random_seed"))
    profiles = parse_auto_timing_profiles(data.get("auto_timing_profiles"))

    conveyor = data.get("conveyor") or {}
    positions = conveyor.get("positions")
    check_profiles_against_positions(profiles, positions)

    return behavior, seed, profiles


def load_auto_timing_config(
    path: str,
) -> tuple[TimingBehavior, int, dict[str, AutoTimingProfile]]:
    """Load simulation timing config + profiles from a TIPA ASSY YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return parse_timing_config(data)
