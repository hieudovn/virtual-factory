"""Genealogy record for AP04 JOIN operation.

M6-S02: Immutable genealogy relationship.
Parent A (SSO2-derived) + Parent B (RSO2) + components → Child MOTOR WIP.

PROVISIONAL_FOR_DEMO: Exact TIPA production identity semantics pending.
The join/identity policy is isolated so future clarification can change
"create new child" to "retain identity + attach genealogy" without
redesigning the line runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class GenealogyRecord:
    """Immutable record of an AP04 assembly join.

    Captures the relationship between parent WIPs, components,
    and the resulting child MOTOR WIP.
    """

    child_wip_id: str
    parent_wip_ids: tuple[str, ...]
    component_ids: tuple[str, ...]
    join_station: str = "AP04"
    join_time_s: float = 0.0
    relationship_type: str = "assembly_join"

    def __post_init__(self) -> None:
        if not self.child_wip_id:
            raise GenealogyError("child_wip_id must not be empty")
        if len(self.parent_wip_ids) < 1:
            raise GenealogyError("at least one parent_wip_id is required")
        if not self.join_station:
            raise GenealogyError("join_station must not be empty")

    @property
    def parent_count(self) -> int:
        return len(self.parent_wip_ids)

    def to_dict(self) -> dict:
        """Convert to plain dict for trace/serialization."""
        return {
            "child_wip_id": self.child_wip_id,
            "parent_wip_ids": list(self.parent_wip_ids),
            "component_ids": list(self.component_ids),
            "join_station": self.join_station,
            "join_time_s": self.join_time_s,
            "relationship_type": self.relationship_type,
        }


@dataclass
class GenealogyStore:
    """Mutable store of genealogy records indexed by child WIP ID."""

    _records: dict[str, GenealogyRecord] = field(default_factory=dict)

    def record(self, genealogy: GenealogyRecord) -> None:
        """Store a genealogy record."""
        if genealogy.child_wip_id in self._records:
            raise GenealogyError(
                f"Genealogy already exists for {genealogy.child_wip_id}"
            )
        self._records[genealogy.child_wip_id] = genealogy

    def get(self, child_wip_id: str) -> Optional[GenealogyRecord]:
        """Retrieve genealogy for a child WIP."""
        return self._records.get(child_wip_id)

    def parents_of(self, child_wip_id: str) -> tuple[str, ...]:
        """Return parent WIP IDs for a child, or empty tuple."""
        r = self._records.get(child_wip_id)
        return r.parent_wip_ids if r else ()

    def all_records(self) -> list[GenealogyRecord]:
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)


class GenealogyError(ValueError):
    """Raised when a genealogy invariant is violated."""
