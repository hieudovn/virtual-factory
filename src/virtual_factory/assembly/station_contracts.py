"""OPS-02 — Station capability contracts for the ASSY line.

Design authority: docs/design/OPS-01_OPERATION_EXECUTION_CONTRACT.md
Schema: .ai-harness/schemas/station-contract.schema.json
Example: docs/design/station-contracts.example.yaml

A station contract declares WHAT decisions physically/business-wise belong to a
station. Runtime completion gating and interaction semantics are derived from
the contract capabilities — never from a hard-coded `if AP03 / if AP06` branch
table. Station-specific *domain* operations (AP04 JOIN, AP06/AP08 quality
resolution, AP11 release) remain station-specific handlers invoked through the
contract.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

import yaml


class CompletionMode(str, enum.Enum):
    """Run/completion mode (OPS-01 §5)."""

    MANUAL = "MANUAL"
    AUTO = "AUTO"
    ASSISTED = "ASSISTED"


class StationCommand(str, enum.Enum):
    """User/system-invoked action vocabulary (OPS-01 §7 model A)."""

    DONE = "DONE"
    CONFIRM = "CONFIRM"
    CONFIRM_AND_COMPLETE = "CONFIRM_AND_COMPLETE"
    JOIN_COMPLETE = "JOIN_COMPLETE"
    RELEASE = "RELEASE"


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Generic station capability flags (additive in future)."""

    execution: bool = True
    checklist: bool = False
    measurement: bool = False
    quality_decision: bool = False
    exception: bool = False
    identity_transformation: bool = False
    final_disposition: bool = False


@dataclass(frozen=True, slots=True)
class StationContract:
    """Frozen capability contract for one station."""

    station_id: str
    capabilities: Capabilities = field(default_factory=Capabilities)
    default_mode: CompletionMode = CompletionMode.AUTO
    mode_override: Optional[CompletionMode] = None
    normal_action: Optional[StationCommand] = None
    required_action: Optional[StationCommand] = None
    work_duration_s: Optional[float] = None  # DEMO/ILLUSTRATIVE, not verified TIPA
    prerequisites: tuple[str, ...] = ()

    @property
    def allowed_commands(self) -> tuple[StationCommand, ...]:
        """Commands this station contract may accept."""
        commands: list[StationCommand] = []
        for cmd in (self.normal_action, self.required_action):
            if cmd is not None and cmd not in commands:
                commands.append(cmd)
        return tuple(commands)

    def to_dict(self) -> dict:
        return {
            "station_id": self.station_id,
            "capabilities": {
                "execution": self.capabilities.execution,
                "checklist": self.capabilities.checklist,
                "measurement": self.capabilities.measurement,
                "quality_decision": self.capabilities.quality_decision,
                "exception": self.capabilities.exception,
                "identity_transformation": self.capabilities.identity_transformation,
                "final_disposition": self.capabilities.final_disposition,
            },
            "default_mode": self.default_mode.value,
            "mode_override": self.mode_override.value if self.mode_override else None,
            "normal_action": self.normal_action.value if self.normal_action else None,
            "required_action": self.required_action.value if self.required_action else None,
            "work_duration_s": self.work_duration_s,
            "prerequisites": list(self.prerequisites),
        }


# ═══════════════════════════════════════════════════════════════
# Canonical ASSY station contracts (OPS-01 §9 — frozen mapping)
# ═══════════════════════════════════════════════════════════════

def build_default_assy_contracts(
    durations: Optional[dict[str, float]] = None,
) -> dict[str, StationContract]:
    """Build the canonical ASSY station contracts.

    `durations` (DEMO/ILLUSTRATIVE) may be supplied to keep the contracts
    aligned with `AssyLineConfig.station_durations`. Values are NOT verified
    TIPA cycle times.
    """
    d = durations or {}

    def _duration(station_id: str, fallback: float) -> float:
        return float(d.get(station_id, fallback))

    def _exec_only(station_id: str, dur: float) -> StationContract:
        return StationContract(
            station_id=station_id,
            capabilities=Capabilities(execution=True),
            normal_action=StationCommand.DONE,
            required_action=StationCommand.DONE,
            work_duration_s=dur,
        )

    contracts: dict[str, StationContract] = {
        "PRE-ASSY": _exec_only("PRE-ASSY", _duration("PRE-ASSY", 30.0)),
        "AP01": _exec_only("AP01", _duration("AP01", 60.0)),
        "AP02": _exec_only("AP02", _duration("AP02", 75.0)),
        # AP03 — execution + checklist gate. NO quality decision (OPS-01 final cleanup).
        "AP03": StationContract(
            station_id="AP03",
            capabilities=Capabilities(execution=True, checklist=True, exception=True),
            default_mode=CompletionMode.AUTO,
            normal_action=StationCommand.CONFIRM_AND_COMPLETE,
            required_action=StationCommand.CONFIRM_AND_COMPLETE,
            work_duration_s=_duration("AP03", 45.0),
        ),
        "AP04": StationContract(
            station_id="AP04",
            capabilities=Capabilities(execution=True, identity_transformation=True),
            normal_action=StationCommand.JOIN_COMPLETE,
            required_action=StationCommand.JOIN_COMPLETE,
            work_duration_s=_duration("AP04", 60.0),
            prerequisites=("AP03",),
        ),
        "AP05": _exec_only("AP05", _duration("AP05", 90.0)),
        "AP06": StationContract(
            station_id="AP06",
            capabilities=Capabilities(execution=True, measurement=True, quality_decision=True),
            normal_action=StationCommand.CONFIRM,
            required_action=StationCommand.CONFIRM,
            work_duration_s=_duration("AP06", 60.0),
        ),
        "AP07": _exec_only("AP07", _duration("AP07", 30.0)),
        "AP08": StationContract(
            station_id="AP08",
            capabilities=Capabilities(execution=True, quality_decision=True),
            normal_action=StationCommand.CONFIRM,
            required_action=StationCommand.CONFIRM,
            work_duration_s=_duration("AP08", 30.0),
        ),
        "AP09": _exec_only("AP09", _duration("AP09", 45.0)),
        "AP10": _exec_only("AP10", _duration("AP10", 45.0)),
        "AP11": StationContract(
            station_id="AP11",
            capabilities=Capabilities(
                execution=True,
                checklist=True,
                quality_decision=True,
                final_disposition=True,
                exception=True,
            ),
            default_mode=CompletionMode.AUTO,
            normal_action=StationCommand.RELEASE,
            required_action=StationCommand.RELEASE,
            work_duration_s=_duration("AP11", 30.0),
        ),
    }
    return contracts


def load_station_contracts_from_yaml(path: str) -> dict[str, StationContract]:
    """Load station contracts from the approved example-YAML structure.

    Expected shape (see docs/design/station-contracts.example.yaml):
        stations:
          - station_id: AP03
            capabilities: { ... }
            default_mode: MANUAL
            ...
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    contracts: dict[str, StationContract] = {}
    for entry in (data or {}).get("stations", []):
        caps_data = entry.get("capabilities", {})
        capabilities = Capabilities(
            execution=bool(caps_data.get("execution", True)),
            checklist=bool(caps_data.get("checklist", False)),
            measurement=bool(caps_data.get("measurement", False)),
            quality_decision=bool(caps_data.get("quality_decision", False)),
            exception=bool(caps_data.get("exception", False)),
            identity_transformation=bool(caps_data.get("identity_transformation", False)),
            final_disposition=bool(caps_data.get("final_disposition", False)),
        )
        mode_override = entry.get("mode_override")
        contract = StationContract(
            station_id=str(entry["station_id"]),
            capabilities=capabilities,
            default_mode=CompletionMode(str(entry.get("default_mode", "AUTO"))),
            mode_override=CompletionMode(mode_override) if mode_override else None,
            normal_action=_cmd(entry.get("normal_action")),
            required_action=_cmd(entry.get("required_action")),
            work_duration_s=_maybe_float(entry.get("work_duration_s")),
            prerequisites=tuple(str(p) for p in entry.get("prerequisites", [])),
        )
        contracts[contract.station_id] = contract
    return contracts


def _cmd(value: object) -> Optional[StationCommand]:
    if value is None:
        return None
    return StationCommand(str(value))


def _maybe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    return float(value)
