"""Simplified upstream production for SSO2 and RSO2.

M6-S02: Minimal fidelity — only what ASSY needs.
SSO2: creates stator/shaft semi-finished WIP → ASSY PRE-ASSY.
RSO2: creates rotor semi-finished WIP → AP04 JOIN.

No thermal, press, turning, balancing, or sensor physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class UpstreamWip:
    """A simplified upstream semi-finished WIP."""

    wip_id: str
    source: str  # "SSO2" or "RSO2"
    created_at_s: float = 0.0

    def __str__(self) -> str:
        return f"{self.source}::{self.wip_id}"


@dataclass
class UpstreamConfig:
    """Configuration for simplified upstream production."""

    sso2_wip_prefix: str = "SSO2"
    rso2_wip_prefix: str = "RSO2"
    sso2_production_interval_s: float = 120.0
    rso2_production_interval_s: float = 120.0
    sso2_operation_type: str = "shrink_fit"  # PTC-01: configurable
    rso2_operation_type: str = "rotor_assembly"  # PTC-03


@dataclass
class UpstreamProducer:
    """Creates SSO2 and RSO2 semi-finished WIPs.

    Production is on-demand or time-driven (configurable).
    WIP IDs use sequential numbering per source.
    """

    config: UpstreamConfig = field(default_factory=UpstreamConfig)
    _sso2_seq: int = 0
    _rso2_seq: int = 0
    _sso2_last_time_s: float = -1.0
    _rso2_last_time_s: float = -1.0

    def produce_sso2(self, simulation_time_s: float) -> UpstreamWip:
        """Create one SSO2 semi-finished WIP."""
        self._sso2_seq += 1
        wip_id = f"{self.config.sso2_wip_prefix}-{self._sso2_seq:04d}"
        self._sso2_last_time_s = simulation_time_s
        return UpstreamWip(wip_id=wip_id, source="SSO2", created_at_s=simulation_time_s)

    def produce_rso2(self, simulation_time_s: float) -> UpstreamWip:
        """Create one RSO2 semi-finished WIP."""
        self._rso2_seq += 1
        wip_id = f"{self.config.rso2_wip_prefix}-{self._rso2_seq:04d}"
        self._rso2_last_time_s = simulation_time_s
        return UpstreamWip(wip_id=wip_id, source="RSO2", created_at_s=simulation_time_s)

    def can_produce_sso2(self, simulation_time_s: float) -> bool:
        """Check if enough time has passed since last SSO2 WIP."""
        if self._sso2_last_time_s < 0:
            return True
        return (simulation_time_s - self._sso2_last_time_s) >= self.config.sso2_production_interval_s

    def can_produce_rso2(self, simulation_time_s: float) -> bool:
        """Check if enough time has passed since last RSO2 WIP."""
        if self._rso2_last_time_s < 0:
            return True
        return (simulation_time_s - self._rso2_last_time_s) >= self.config.rso2_production_interval_s

    def reset(self) -> None:
        """Reset production counters."""
        self._sso2_seq = 0
        self._rso2_seq = 0
        self._sso2_last_time_s = -1.0
        self._rso2_last_time_s = -1.0
