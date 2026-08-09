"""Consumer-neutral identity model for the observation/integration boundary.

M5-S03: EntityRef, ExternalIdentityRef, IdentityLink.
No external system/DB dependency. In-memory mapping only.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════
# EntityRef — internal simulation entity identity
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class EntityRef:
    """Identity known inside the simulation/integration boundary.

    Examples:
        EntityRef(entity_type="wip", entity_id="MOTOR-000123")
        EntityRef(entity_type="carrier", entity_id="PALLET-027")
        EntityRef(entity_type="station", entity_id="AP06")
    """

    entity_type: str
    entity_id: str

    def __post_init__(self) -> None:
        if not self.entity_type or not isinstance(self.entity_type, str):
            raise ValueError("entity_type must be a non-empty str")
        if not self.entity_id or not isinstance(self.entity_id, str):
            raise ValueError("entity_id must be a non-empty str")


# ═══════════════════════════════════════════════════
# ExternalIdentityRef — identity in another namespace
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ExternalIdentityRef:
    """Identity in an external namespace/system.

    Examples:
        ExternalIdentityRef(namespace="serial", entity_type="material_lot",
                            external_id="SN-260808-0128")
        ExternalIdentityRef(namespace="mes", entity_type="production_order",
                            external_id="MO-001")
    """

    namespace: str
    entity_type: str
    external_id: str

    def __post_init__(self) -> None:
        if not self.namespace or not isinstance(self.namespace, str):
            raise ValueError("namespace must be a non-empty str")
        if not self.entity_type or not isinstance(self.entity_type, str):
            raise ValueError("entity_type must be a non-empty str")
        if not self.external_id or not isinstance(self.external_id, str):
            raise ValueError("external_id must be a non-empty str")


# ═══════════════════════════════════════════════════
# IdentityLink — semantic correspondence at boundary
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class IdentityLink:
    """Semantic correspondence between internal and external identity.

    Mapping type examples:
        "serial_mapping", "lot_mapping", "order_mapping",
        "carrier_mapping", "station_mapping"
    """

    internal: EntityRef
    external: ExternalIdentityRef
    mapping_type: str = "identity_link"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.internal, EntityRef):
            raise ValueError("internal must be EntityRef")
        if not isinstance(self.external, ExternalIdentityRef):
            raise ValueError("external must be ExternalIdentityRef")
        if not self.mapping_type or not isinstance(self.mapping_type, str):
            raise ValueError("mapping_type must be a non-empty str")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(
                f"confidence must be 0.0–1.0, got {self.confidence}"
            )


# ═══════════════════════════════════════════════════
# IdentityResolver — minimal in-memory lookup
# ═══════════════════════════════════════════════════

@dataclass
class IdentityResolver:
    """Minimal in-memory identity mapping registry.

    No database, graph DB, Odoo, PlantOS, or network.
    """

    _links: list[IdentityLink] = field(default_factory=list)

    def register(self, link: IdentityLink) -> None:
        """Register an identity link."""
        if not isinstance(link, IdentityLink):
            raise TypeError(f"expected IdentityLink, got {type(link).__name__}")
        self._links.append(link)

    def resolve_internal(
        self, entity_type: str, entity_id: str
    ) -> list[IdentityLink]:
        """Find all links for a given internal entity."""
        return [
            link for link in self._links
            if link.internal.entity_type == entity_type
            and link.internal.entity_id == entity_id
        ]

    def resolve_external(
        self, namespace: str, entity_type: str, external_id: str
    ) -> list[IdentityLink]:
        """Find all links for a given external identity."""
        return [
            link for link in self._links
            if link.external.namespace == namespace
            and link.external.entity_type == entity_type
            and link.external.external_id == external_id
        ]

    @property
    def links(self) -> tuple[IdentityLink, ...]:
        """Return all registered links as an immutable tuple."""
        return tuple(self._links)
