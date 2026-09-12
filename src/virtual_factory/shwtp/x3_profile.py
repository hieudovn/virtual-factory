"""SH-WTP X3 execution profile: versioned parameters + hard validation (VF-SHW-X3).

Implements the SA design freeze (Issue #97 D1-D9) for the profile/parameter
surface only:

- **D2** global deterministic 1-second windows (``time.tick_s``) with
  ``explicit_lagged`` coupling;
- **D3** one explicit internal unit convention (m3, s, m3/s, m, Pa, W, J) with
  named conversions for the existing m3/h, %, bar and kPa interfaces; every
  parameter finite and positive where required; ``Hmax = Vmax/A``,
  ``0 <= Vinitial <= Vmax`` and ``0 < LALL < LAL < LAH < LAHH < Hmax`` validated
  BEFORE execution; invalid configuration fails closed with a reason.

The profile is a NEW versioned X3 artefact: no X1/X2 contract or config file is
modified by this module. It contains no equation, ownership or topology decision
- it is the numeric parameterization the design authorizes the PM to choose
(D8), with units and rationale recorded.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

X3_PROFILE_SCHEMA = "vf.shwtp.x3.profile.v1"
X3_PROFILE_PATH = Path("configs/vnext/shwtp/shwtp_x3_profile_v1.json")

X3_DEFAULT_TICK_S = 1.0
X3_COUPLING_POLICY = "explicit_lagged"

#: The two C2 PI loops the design admits (D1). Everything else stays C1/deferred.
X3_ACTIVE_C2_LOOP_IDS: tuple[str, ...] = (
    "vf-shw-ctrl-f106-inlet-flow-pi",
    "vf-shw-ctrl-t108-level-pi",
)


class X3ProfileError(ValueError):
    """Raised when the X3 profile is invalid or inconsistent (fail closed)."""


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise X3ProfileError(f"{name} must be a finite number, got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise X3ProfileError(f"{name} must be a finite number, got {value!r}")
    return out


def _positive(value: Any, name: str) -> float:
    out = _num(value, name)
    if out <= 0.0:
        raise X3ProfileError(f"{name} must be > 0, got {out!r}")
    return out


def _nonneg(value: Any, name: str) -> float:
    out = _num(value, name)
    if out < 0.0:
        raise X3ProfileError(f"{name} must be >= 0, got {out!r}")
    return out


def _fraction(value: Any, name: str) -> float:
    out = _num(value, name)
    if not 0.0 < out <= 1.0:
        raise X3ProfileError(f"{name} must be within (0, 1], got {out!r}")
    return out


@dataclass(frozen=True, slots=True)
class X3Units:
    """The ONE internal unit convention + named conversions (D3)."""

    rho_kg_m3: float = 1000.0
    g_m_s2: float = 9.81
    bar_pa: float = 100_000.0

    def m3h_to_m3s(self, value_m3h: float) -> float:
        return _num(value_m3h, "value_m3h") / 3600.0

    def m3s_to_m3h(self, value_m3s: float) -> float:
        return _num(value_m3s, "value_m3s") * 3600.0

    def bar_to_pa(self, value_bar: float) -> float:
        return _num(value_bar, "value_bar") * self.bar_pa

    def pa_to_bar(self, value_pa: float) -> float:
        return _num(value_pa, "value_pa") / self.bar_pa

    def head_m_to_pa(self, head_m: float) -> float:
        return self.rho_kg_m3 * self.g_m_s2 * _num(head_m, "head_m")

    def pa_to_head_m(self, value_pa: float) -> float:
        return _num(value_pa, "value_pa") / (self.rho_kg_m3 * self.g_m_s2)

    def pct_to_fraction(self, value_pct: float) -> float:
        return _num(value_pct, "value_pct") / 100.0

    def fraction_to_pct(self, value: float) -> float:
        return _num(value, "value") * 100.0


@dataclass(frozen=True, slots=True)
class X3Tank:
    scope_id: str
    area_m2: float
    capacity_m3: float
    initial_volume_m3: float
    level_band_m: tuple[float, float, float, float]

    @property
    def max_level_m(self) -> float:
        return self.capacity_m3 / self.area_m2

    @property
    def initial_level_m(self) -> float:
        return self.initial_volume_m3 / self.area_m2


@dataclass(frozen=True, slots=True)
class X3EdgeRating:
    binding_id: str
    max_flow_m3_s: float
    trunk_id: str | None = None


@dataclass(frozen=True, slots=True)
class X3Valve:
    scope_id: str
    q_valve_max_m3_s: float
    slew_pct_per_s: float
    min_open_pct: float = 0.0
    max_open_pct: float = 100.0


@dataclass(frozen=True, slots=True)
class X3Pump:
    pump_id: str
    scope_id: str
    signal: str
    powered: bool
    h0_m: float
    k_s2_m5: float
    h_static_m: float
    r_s2_m5: float
    q_rated_m3_s: float
    speed_min_pct: float
    speed_max_pct: float
    slew_pct_per_s: float
    eta_total: float
    no_load_w: float
    motor_rating_w: float


@dataclass(frozen=True, slots=True)
class X3PIConfig:
    """One PI loop parameter set (D7)."""

    controller_id: str
    pv_signal: str
    mv_signal: str
    sp: float
    sp_admissible: tuple[float, float]
    kp: float
    ki: float
    kb: float
    bias: float
    manual_default: float
    tracking_time_s: float
    output_min: float
    output_max: float
    slew_per_s: float
    unit: str


@dataclass(frozen=True, slots=True)
class X3QueueLimits:
    max_transfers_per_edge: int
    max_queued_volume_m3: float


@dataclass(frozen=True, slots=True)
class X3Acceptance:
    flow_steady_error_frac_of_sp: float
    level_steady_error_m: float
    nominal_settling_window_s: int
    oscillation_check_s: int


@dataclass(frozen=True, slots=True)
class X3Profile:
    """A validated X3 execution profile (immutable)."""

    profile_id: str
    version: str
    tick_s: float
    coupling_policy: str
    units: X3Units
    tanks: Mapping[str, X3Tank]
    edges: Mapping[str, X3EdgeRating]
    trunks: Mapping[str, float]
    valves: Mapping[str, X3Valve]
    pumps: Mapping[str, X3Pump]
    controllers: Mapping[str, X3PIConfig]
    queue: X3QueueLimits
    acceptance: X3Acceptance
    energy_unavailable: tuple[str, ...] = ()
    deferred_loops: Mapping[str, str] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def active_c2_loop_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.controllers))

    def tank(self, scope_id: str) -> X3Tank:
        tank = self.tanks.get(scope_id)
        if tank is None:
            raise X3ProfileError(f"scope {scope_id!r} has no X3 tank parameters")
        return tank

    def edge(self, binding_id: str) -> X3EdgeRating:
        rating = self.edges.get(binding_id)
        if rating is None:
            raise X3ProfileError(f"binding {binding_id!r} has no X3 edge rating")
        return rating

    def pump_for_scope(self, scope_id: str, signal: str) -> X3Pump:
        for pump in self.pumps.values():
            if pump.scope_id == scope_id and pump.signal == signal:
                return pump
        raise X3ProfileError(f"no X3 pump declares scope {scope_id!r} signal {signal!r}")


def _validate_tanks(raw: Mapping[str, Any], units: X3Units) -> dict[str, X3Tank]:
    tanks: dict[str, X3Tank] = {}
    for scope_id, entry in raw.items():
        if not isinstance(entry, Mapping):  # documentation keys (e.g. "note")
            continue
        area = _positive(entry["area_m2"], f"{scope_id}.area_m2")
        capacity = _positive(entry["capacity_m3"], f"{scope_id}.capacity_m3")
        initial = _nonneg(entry["initial_volume_m3"], f"{scope_id}.initial_volume_m3")
        band = entry["level_band_m"]
        if not isinstance(band, (list, tuple)) or len(band) != 4:
            raise X3ProfileError(f"{scope_id}.level_band_m must declare four thresholds")
        lall, lal, lah, lahh = (_num(value, f"{scope_id}.level_band_m") for value in band)
        hmax = capacity / area
        if not 0.0 <= initial <= capacity:
            raise X3ProfileError(
                f"{scope_id}: initial volume {initial!r} must be within [0, {capacity!r}]"
            )
        if not 0.0 < lall < lal < lah < lahh < hmax:
            raise X3ProfileError(
                f"{scope_id}: level bands must satisfy 0 < LALL < LAL < LAH < LAHH < Hmax "
                f"= {hmax!r}, got {band!r}"
            )
        tanks[scope_id] = X3Tank(
            scope_id=scope_id,
            area_m2=area,
            capacity_m3=capacity,
            initial_volume_m3=initial,
            level_band_m=(lall, lal, lah, lahh),
        )
    if not tanks:
        raise X3ProfileError("the X3 profile declares no tanks")
    del units
    return tanks


def _validate_edges(raw: Mapping[str, Any]) -> tuple[dict[str, X3EdgeRating], dict[str, float]]:
    edges: dict[str, X3EdgeRating] = {}
    for binding_id, entry in raw.items():
        if not isinstance(entry, Mapping):  # documentation keys (e.g. "note")
            continue
        rating = _nonneg(entry["max_flow_m3_s"], f"{binding_id}.max_flow_m3_s")
        trunk = entry.get("trunk")
        edges[binding_id] = X3EdgeRating(
            binding_id=binding_id, max_flow_m3_s=rating, trunk_id=trunk
        )
    if not edges:
        raise X3ProfileError("the X3 profile declares no edge ratings")
    return edges, {}


def _validate_trunks(raw: Mapping[str, Any]) -> dict[str, float]:
    return {
        trunk_id: _positive(entry["max_flow_m3_s"], f"{trunk_id}.max_flow_m3_s")
        for trunk_id, entry in raw.items()
        if isinstance(entry, Mapping)
    }


def _validate_valves(raw: Mapping[str, Any]) -> dict[str, X3Valve]:
    valves: dict[str, X3Valve] = {}
    for scope_id, entry in raw.items():
        if not isinstance(entry, Mapping):
            continue
        valves[scope_id] = X3Valve(
            scope_id=scope_id,
            q_valve_max_m3_s=_positive(entry["q_valve_max_m3_s"], f"{scope_id}.q_valve_max_m3_s"),
            slew_pct_per_s=_positive(entry["slew_pct_per_s"], f"{scope_id}.slew_pct_per_s"),
            min_open_pct=_num(entry.get("min_open_pct", 0.0), f"{scope_id}.min_open_pct"),
            max_open_pct=_num(entry.get("max_open_pct", 100.0), f"{scope_id}.max_open_pct"),
        )
    return valves


def _validate_pumps(raw: Mapping[str, Any]) -> dict[str, X3Pump]:
    pumps: dict[str, X3Pump] = {}
    for pump_id, entry in raw.items():
        if not isinstance(entry, Mapping):
            continue
        powered = bool(entry.get("powered", True))
        speed_min = _nonneg(entry.get("speed_min_pct", 0.0), f"{pump_id}.speed_min_pct")
        speed_max = _num(entry.get("speed_max_pct", 100.0), f"{pump_id}.speed_max_pct")
        if not 0.0 <= speed_min < speed_max <= 100.0:
            raise X3ProfileError(f"{pump_id}: speed range must satisfy 0 <= min < max <= 100")
        pump = X3Pump(
            pump_id=pump_id,
            scope_id=str(entry["scope_id"]),
            signal=str(entry["signal"]),
            powered=powered,
            h0_m=_positive(entry["h0_m"], f"{pump_id}.h0_m"),
            k_s2_m5=_nonneg(entry["k_s2_m5"], f"{pump_id}.k_s2_m5"),
            h_static_m=_nonneg(entry["h_static_m"], f"{pump_id}.h_static_m"),
            r_s2_m5=_nonneg(entry["r_s2_m5"], f"{pump_id}.r_s2_m5"),
            q_rated_m3_s=_positive(entry["q_rated_m3_s"], f"{pump_id}.q_rated_m3_s"),
            speed_min_pct=speed_min,
            speed_max_pct=speed_max,
            slew_pct_per_s=_positive(entry["slew_pct_per_s"], f"{pump_id}.slew_pct_per_s"),
            eta_total=_fraction(entry["eta_total"], f"{pump_id}.eta_total"),
            no_load_w=_nonneg(entry["no_load_w"], f"{pump_id}.no_load_w"),
            motor_rating_w=_positive(entry["motor_rating_w"], f"{pump_id}.motor_rating_w"),
        )
        h_max = pump.h0_m * (pump.speed_max_pct / 100.0) ** 2
        if h_max < pump.h_static_m:
            raise X3ProfileError(
                f"{pump_id}: the maximum pump head {h_max!r} m cannot reach the declared "
                f"static requirement {pump.h_static_m!r} m at any speed"
            )
        if pump.no_load_w >= pump.motor_rating_w:
            raise X3ProfileError(
                f"{pump_id}: the no-load loss cannot exceed the motor rating"
            )
        pumps[pump_id] = pump
    return pumps


def _validate_controllers(
    raw: Mapping[str, Any], *, loop_ids: tuple[str, ...]
) -> dict[str, X3PIConfig]:
    controllers: dict[str, X3PIConfig] = {}
    for controller_id, entry in raw.items():
        if not isinstance(entry, Mapping):
            continue
        if controller_id not in loop_ids:
            raise X3ProfileError(
                f"{controller_id!r} is not one of the two X3-admitted C2 PI loops {loop_ids}"
            )
        if str(entry.get("kind")) != "C2_PI":
            raise X3ProfileError(f"{controller_id}: only C2_PI loops are admitted in X3")
        if controller_id == "vf-shw-ctrl-f106-inlet-flow-pi":
            admissible = entry["sp_admissible_m3_s"]
            unit = "m3/s"
            output_min = _num(entry["output_min_pct"], f"{controller_id}.output_min_pct")
            output_max = _num(entry["output_max_pct"], f"{controller_id}.output_max_pct")
        else:
            admissible = entry["sp_admissible_m"]
            unit = "m"
            output_min = _num(entry["output_min_pct"], f"{controller_id}.output_min_pct")
            output_max = _num(entry["output_max_pct"], f"{controller_id}.output_max_pct")
        if not isinstance(admissible, (list, tuple)) or len(admissible) != 2:
            raise X3ProfileError(f"{controller_id}: the admissible SP range must declare two bounds")
        low = _num(admissible[0], f"{controller_id}.sp_low")
        high = _num(admissible[1], f"{controller_id}.sp_high")
        if not 0.0 < low < high:
            raise X3ProfileError(f"{controller_id}: the admissible SP range must satisfy 0 < low < high")
        sp = _num(entry["sp_m3_s"] if unit == "m3/s" else entry["sp_m"], f"{controller_id}.sp")
        if not low <= sp <= high:
            raise X3ProfileError(
                f"{controller_id}: the configured SP {sp!r} is outside the admissible range "
                f"[{low!r}, {high!r}]"
            )
        if not output_min < output_max:
            raise X3ProfileError(f"{controller_id}: output range must satisfy min < max")
        controller = X3PIConfig(
            controller_id=controller_id,
            pv_signal=str(entry["pv"]),
            mv_signal=str(entry["mv"]),
            sp=sp,
            sp_admissible=(low, high),
            kp=_positive(entry["kp_pct_per_m3_s"] if unit == "m3/s" else entry["kp_pct_per_m"], f"{controller_id}.kp"),
            ki=_positive(
                entry["ki_pct_per_m3_s_s"] if unit == "m3/s" else entry["ki_pct_per_m_s"],
                f"{controller_id}.ki",
            ),
            kb=_positive(entry["kb_per_s"], f"{controller_id}.kb"),
            bias=_num(entry["bias_pct"], f"{controller_id}.bias"),
            manual_default=_num(entry["manual_default_pct"], f"{controller_id}.manual_default"),
            tracking_time_s=_positive(entry["tracking_time_s"], f"{controller_id}.tracking_time_s"),
            output_min=output_min,
            output_max=output_max,
            slew_per_s=_positive(entry["slew_pct_per_s"], f"{controller_id}.slew_pct_per_s"),
            unit=unit,
        )
        if not output_min <= controller.bias <= output_max:
            raise X3ProfileError(f"{controller_id}: the bias must lie inside the output range")
        controllers[controller_id] = controller
    missing = sorted(set(loop_ids) - set(controllers))
    if missing:
        raise X3ProfileError(f"the X3 profile is missing the admitted C2 PI loop(s) {missing}")
    return controllers


def validate_x3_profile(raw: Mapping[str, Any]) -> X3Profile:
    """Validate a raw X3 profile document (fail closed, D3)."""
    if not isinstance(raw, Mapping):
        raise X3ProfileError("the X3 profile must be a mapping")
    if raw.get("schema") != X3_PROFILE_SCHEMA:
        raise X3ProfileError(
            f"unexpected X3 profile schema {raw.get('schema')!r}; expected {X3_PROFILE_SCHEMA!r}"
        )
    constants = raw["constants"]
    units = X3Units(
        rho_kg_m3=_positive(constants["rho_kg_m3"], "rho_kg_m3"),
        g_m_s2=_positive(constants["g_m_s2"], "g_m_s2"),
        bar_pa=_positive(constants["bar_pa"], "bar_pa"),
    )
    time_block = raw["time"]
    tick_s = _positive(time_block["tick_s"], "tick_s")
    if tick_s != X3_DEFAULT_TICK_S:
        raise X3ProfileError(
            f"the X3 execution profile requires global 1-second windows, got tick_s={tick_s!r}"
        )
    coupling = str(time_block["coupling_policy"])
    if coupling != X3_COUPLING_POLICY:
        raise X3ProfileError(
            f"the X3 execution profile requires {X3_COUPLING_POLICY!r} coupling, got {coupling!r}"
        )
    tanks = _validate_tanks(raw["tanks"], units)
    edges, _ = _validate_edges(raw["edges"])
    trunks = _validate_trunks(raw["trunks"])
    for rating in edges.values():
        if rating.trunk_id is not None and rating.trunk_id not in trunks:
            raise X3ProfileError(f"edge {rating.binding_id!r} references unknown trunk {rating.trunk_id!r}")
    valves = _validate_valves(raw["valves"])
    pumps = _validate_pumps(raw["pumps"])
    controllers = _validate_controllers(raw["controllers"], loop_ids=X3_ACTIVE_C2_LOOP_IDS)
    queue_block = raw["queue"]
    max_transfers = int(queue_block["max_transfers_per_edge"])
    if max_transfers < 1:
        raise X3ProfileError("queue.max_transfers_per_edge must be >= 1")
    queue = X3QueueLimits(
        max_transfers_per_edge=max_transfers,
        max_queued_volume_m3=_positive(queue_block["max_queued_volume_m3"], "queue.max_queued_volume_m3"),
    )
    acceptance_block = raw["acceptance"]
    acceptance = X3Acceptance(
        flow_steady_error_frac_of_sp=_fraction(
            acceptance_block["flow_steady_error_frac_of_sp"], "flow_steady_error_frac_of_sp"
        ),
        level_steady_error_m=_positive(acceptance_block["level_steady_error_m"], "level_steady_error_m"),
        nominal_settling_window_s=int(acceptance_block["nominal_settling_window_s"]),
        oscillation_check_s=int(acceptance_block["oscillation_check_s"]),
    )
    deferred = {key: str(value) for key, value in raw.get("deferred_loops", {}).items()}
    for loop_id in X3_ACTIVE_C2_LOOP_IDS:
        if deferred.get(loop_id, "").upper() != "ACTIVE IN X3":
            raise X3ProfileError(f"{loop_id!r} must be declared ACTIVE in X3 in deferred_loops")
    energy = tuple(str(entry) for entry in raw.get("energy", {}).get("unavailable", ()))
    return X3Profile(
        profile_id=str(raw["profile_id"]),
        version=str(raw["version"]),
        tick_s=tick_s,
        coupling_policy=coupling,
        units=units,
        tanks=tanks,
        edges=edges,
        trunks=trunks,
        valves=valves,
        pumps=pumps,
        controllers=controllers,
        queue=queue,
        acceptance=acceptance,
        energy_unavailable=energy,
        deferred_loops=deferred,
        raw=raw,
    )


def load_x3_profile(path: str | Path | None = None) -> X3Profile:
    """Load and validate the versioned X3 execution profile."""
    target = Path(path) if path is not None else X3_PROFILE_PATH
    if not target.is_absolute():
        root = Path(__file__).resolve()
        while not (root / "pyproject.toml").exists():
            root = root.parent
        target = root / target
    if not target.exists():
        raise X3ProfileError(f"X3 profile not found at {target}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed file
        raise X3ProfileError(f"X3 profile {target} is not valid JSON: {exc}") from exc
    return validate_x3_profile(raw)
