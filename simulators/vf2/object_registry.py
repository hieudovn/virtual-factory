"""Dynamic object registry — built from a VF-2 PIM package at load time.

No hardcoded object IDs.  Everything comes from the package.
"""

from __future__ import annotations

from .models import VF2Package, VF2SimulationObject


class ObjectRegistry:
    """Queryable store of VF-2 simulation objects.

    Provides lookup by ``simulation_object_id``, ``canonical_id``,
    ``object_type``, and ``unit_id``.
    """

    def __init__(self, pkg: VF2Package) -> None:
        self._by_id: dict[str, VF2SimulationObject] = {}
        self._by_canonical: dict[str, VF2SimulationObject] = {}
        for obj in pkg.objects:
            self._by_id[obj.simulation_object_id] = obj
            self._by_canonical[obj.canonical_id] = obj

    # ──────────────────────────────────────────────────────────────────
    # Basic lookup
    # ──────────────────────────────────────────────────────────────────

    def get(self, simulation_object_id: str) -> VF2SimulationObject | None:
        """Get an object by its ``simulation_object_id``, or ``None``."""
        return self._by_id.get(simulation_object_id)

    def get_by_canonical(self, canonical_id: str) -> VF2SimulationObject | None:
        """Get an object by its PIM ``canonical_id``."""
        return self._by_canonical.get(canonical_id)

    # ──────────────────────────────────────────────────────────────────
    # Filters
    # ──────────────────────────────────────────────────────────────────

    def filter_by_type(self, object_type: str) -> list[VF2SimulationObject]:
        """Return all objects of a given type (e.g. ``"centrifugal_pump"``)."""
        return [obj for obj in self._by_id.values() if obj.object_type == object_type]

    def filter_by_unit(self, unit_id: str) -> list[VF2SimulationObject]:
        """Return all objects in a given unit."""
        return [obj for obj in self._by_id.values() if obj.unit_id == unit_id]

    # ──────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────

    @property
    def all_objects(self) -> list[VF2SimulationObject]:
        return list(self._by_id.values())

    @property
    def object_count(self) -> int:
        return len(self._by_id)

    @property
    def object_ids(self) -> list[str]:
        """All ``simulation_object_id`` strings."""
        return list(self._by_id.keys())

    @property
    def object_types(self) -> set[str]:
        """Distinct object types present in the package."""
        return {obj.object_type for obj in self._by_id.values()}
