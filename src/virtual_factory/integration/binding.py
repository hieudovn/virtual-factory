"""Generic gateway/workstation observation binding (VF-vNEXT-G20).

A dependency-light, immutable, deterministic, READ-ONLY declaration of which
logical gateway/workstation components observe which simulation scopes.

This is the architectural SEAM between simulation scopes and integration
gateways — not a transport, broker, or truth owner:

- Simulation runtime remains the sole source of simulation/domain truth.
- A gateway/workstation is a read-only observer/adapter/forwarding boundary.
- A gateway NEVER mutates participant/runtime state (this module has no runtime
  imports and no mutation path).
- Gateway identity is distinct from G1 Workspace/Scope identity and from PIM
  canonical identity.
- Gateway topology is NOT execution order and NOT containment hierarchy: it is
  a plain deterministic set of ``scope -> gateway`` bindings.

Frozen semantics:

- ``n scopes -> 1 gateway`` is supported (fan-in).
- ``1 scope -> n gateways`` is supported (fan-out); there is deliberately NO
  one-gateway-per-scope invariant.
- Fail closed on: unknown scope, unknown gateway, duplicate binding id,
  duplicate/ambiguous exact logical binding ``(gateway_id, scope_path)``, and
  identity mismatch (gateway id impersonating a Scope path or PIM canonical id).
- Deterministic enumeration/serialization independent of declaration order.
- Each semantic message stays independently identifiable/idempotent; batching is
  a transport-level optimization only (preserved by the existing observation
  envelope/projection/message primitives this seam composes with).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from virtual_factory.workspace import SimulationScope, StructuralPath, Workspace

GATEWAY_BINDING_SCHEMA = "vf.vnext.g20.gateway_observation_binding.v1"

_GATEWAY_KINDS = ("gateway", "workstation")

# PIM canonical identity prefixes that a gateway id must NEVER impersonate.
_PIM_ID_PREFIXES = ("PROC-", "UNIT-", "REL-", "SIG-", "PROC_", "UNIT_", "REL_", "SIG_")

# A gateway id must not look like a G1 structural path (which uses '/').
_PATH_SEPARATOR = "/"


class GatewayBindingError(ValueError):
    """Raised when a gateway-observation-binding invariant is violated."""


def _require_nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GatewayBindingError(f"{name} must be a non-empty str")


@dataclass(frozen=True, slots=True)
class GatewayWorkstation:
    """A logical gateway/workstation identity (read-only observer/adapter).

    ``gateway_id`` is a VF integration identity ONLY. It must never equal or
    impersonate a G1 ``StructuralPath`` (no ``/``) or a PIM canonical id
    (``PROC-``/``UNIT-``/``REL-``/``SIG-`` prefixes are rejected fail-closed).
    """

    gateway_id: str
    kind: str = "gateway"
    display_name: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.gateway_id, "gateway_id")
        if self.kind not in _GATEWAY_KINDS:
            raise GatewayBindingError(
                f"kind must be one of {_GATEWAY_KINDS!r}, got {self.kind!r}"
            )
        if _PATH_SEPARATOR in self.gateway_id:
            raise GatewayBindingError(
                f"gateway_id {self.gateway_id!r} must not contain "
                f"{_PATH_SEPARATOR!r}: it is integration identity, not a "
                f"G1 StructuralPath"
            )
        if self.gateway_id.startswith(_PIM_ID_PREFIXES):
            raise GatewayBindingError(
                f"gateway_id {self.gateway_id!r} must not impersonate a PIM "
                f"canonical id prefix {_PIM_ID_PREFIXES!r}"
            )
        if self.display_name is not None:
            _require_nonempty(self.display_name, "display_name")

    def to_dict(self) -> dict:
        return {
            "gateway_id": self.gateway_id,
            "kind": self.kind,
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GatewayWorkstation":
        if not isinstance(data, dict):
            raise GatewayBindingError("gateway must be a dict")
        return cls(
            gateway_id=data.get("gateway_id", ""),
            kind=data.get("kind", "gateway"),
            display_name=data.get("display_name"),
        )


@dataclass(frozen=True, slots=True)
class GatewayScopeBinding:
    """One explicit, deterministic ``scope -> gateway`` observation binding.

    ``scope_path`` is a VF G1 ``StructuralPath`` string (e.g.
    ``TIPA/ASSY/ASSY-SL01``). ``domain`` is a consumer-neutral domain
    discriminator preserved into provenance.
    """

    binding_id: str
    gateway_id: str
    scope_path: str
    domain: str

    def __post_init__(self) -> None:
        _require_nonempty(self.binding_id, "binding_id")
        _require_nonempty(self.gateway_id, "gateway_id")
        _require_nonempty(self.scope_path, "scope_path")
        _require_nonempty(self.domain, "domain")

    @property
    def logical_key(self) -> tuple[str, str]:
        """Frozen duplicate/ambiguous logical binding identity."""
        return (self.gateway_id, self.scope_path)

    @property
    def sort_key(self) -> tuple[str, str, str]:
        """Deterministic canonical sort key independent of declaration order."""
        return (self.gateway_id, self.scope_path, self.binding_id)

    def to_dict(self) -> dict:
        return {
            "binding_id": self.binding_id,
            "gateway_id": self.gateway_id,
            "scope_path": self.scope_path,
            "domain": self.domain,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GatewayScopeBinding":
        if not isinstance(data, dict):
            raise GatewayBindingError("binding must be a dict")
        return cls(
            binding_id=data.get("binding_id", ""),
            gateway_id=data.get("gateway_id", ""),
            scope_path=data.get("scope_path", ""),
            domain=data.get("domain", ""),
        )


@dataclass(frozen=True, slots=True)
class GatewayBindingTable:
    """Immutable, deterministic set of scope->gateway bindings.

    Built fail-closed from any iteration order. Enumeration is deterministic
    (identity order only) and never implies execution order or containment.
    """

    table_id: str
    version: str
    gateways: tuple[GatewayWorkstation, ...] = field(default=())
    bindings: tuple[GatewayScopeBinding, ...] = field(default=())
    known_scope_paths: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        _require_nonempty(self.table_id, "table_id")
        _require_nonempty(self.version, "version")

        gateways_by_id: dict[str, GatewayWorkstation] = {}
        for gw in self.gateways:
            if not isinstance(gw, GatewayWorkstation):
                raise GatewayBindingError(
                    f"gateways must be GatewayWorkstation, got {type(gw).__name__}"
                )
            if gw.gateway_id in gateways_by_id:
                raise GatewayBindingError(
                    f"duplicate gateway_id {gw.gateway_id!r}"
                )
            if self.known_scope_paths and gw.gateway_id in self.known_scope_paths:
                raise GatewayBindingError(
                    f"gateway_id {gw.gateway_id!r} collides with a known scope "
                    f"path (identity mismatch)"
                )
            gateways_by_id[gw.gateway_id] = gw

        by_binding_id: dict[str, GatewayScopeBinding] = {}
        by_logical: dict[tuple[str, str], GatewayScopeBinding] = {}
        for binding in self.bindings:
            if not isinstance(binding, GatewayScopeBinding):
                raise GatewayBindingError(
                    f"bindings must be GatewayScopeBinding, got "
                    f"{type(binding).__name__}"
                )
            if binding.gateway_id not in gateways_by_id:
                raise GatewayBindingError(
                    f"binding {binding.binding_id!r} references unknown gateway "
                    f"{binding.gateway_id!r}"
                )
            if binding.scope_path not in self.known_scope_paths:
                raise GatewayBindingError(
                    f"binding {binding.binding_id!r} references unknown scope "
                    f"{binding.scope_path!r}"
                )
            if binding.binding_id in by_binding_id:
                raise GatewayBindingError(
                    f"duplicate binding id {binding.binding_id!r}"
                )
            if binding.logical_key in by_logical:
                raise GatewayBindingError(
                    f"ambiguous binding: scope {binding.scope_path!r} is "
                    f"already bound to gateway {binding.gateway_id!r}"
                )
            by_binding_id[binding.binding_id] = binding
            by_logical[binding.logical_key] = binding

        object.__setattr__(
            self, "gateways",
            tuple(sorted(self.gateways, key=lambda g: g.gateway_id)),
        )
        object.__setattr__(
            self, "bindings",
            tuple(sorted(self.bindings, key=lambda b: b.sort_key)),
        )

    @property
    def gateway_ids(self) -> tuple[str, ...]:
        return tuple(g.gateway_id for g in self.gateways)

    @property
    def binding_count(self) -> int:
        return len(self.bindings)

    def gateways_for_scope(self, scope_path: str) -> tuple[str, ...]:
        """Deterministic gateway ids observing ``scope_path`` (fan-out)."""
        return tuple(sorted(
            b.gateway_id for b in self.bindings if b.scope_path == scope_path
        ))

    def scopes_for_gateway(self, gateway_id: str) -> tuple[str, ...]:
        """Deterministic scope paths observed by ``gateway_id`` (fan-in)."""
        return tuple(sorted(
            b.scope_path for b in self.bindings if b.gateway_id == gateway_id
        ))

    def serialize(self) -> dict:
        """Deterministic machine-readable inspection of the binding table."""
        return {
            "schema": GATEWAY_BINDING_SCHEMA,
            "table_id": self.table_id,
            "version": self.version,
            "gateway_count": len(self.gateways),
            "binding_count": self.binding_count,
            "gateways": [g.to_dict() for g in self.gateways],
            "bindings": [b.to_dict() for b in self.bindings],
            "known_scope_paths": tuple(sorted(self.known_scope_paths)),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GatewayBindingTable":
        if not isinstance(data, dict):
            raise GatewayBindingError("binding table must be a dict")
        if data.get("schema") != GATEWAY_BINDING_SCHEMA:
            raise GatewayBindingError(
                f"table schema must be {GATEWAY_BINDING_SCHEMA!r}; got "
                f"{data.get('schema')!r}"
            )
        gateways = tuple(
            GatewayWorkstation.from_dict(g) for g in data.get("gateways", [])
        )
        bindings = tuple(
            GatewayScopeBinding.from_dict(b) for b in data.get("bindings", [])
        )
        return cls(
            table_id=data.get("table_id", ""),
            version=data.get("version", ""),
            gateways=gateways,
            bindings=bindings,
            known_scope_paths=frozenset(data.get("known_scope_paths", [])),
        )


def collect_executable_scope_paths(workspace: Workspace) -> frozenset[str]:
    """Collect every executable-capable scope path from a G1 Workspace."""
    if not isinstance(workspace, Workspace):
        raise GatewayBindingError(
            f"workspace must be a G1 Workspace, got {type(workspace).__name__}"
        )
    paths: list[str] = []

    def _walk(scope: SimulationScope) -> None:
        if scope.is_executable_capable:
            paths.append(scope.path.as_string())
        for child in scope.children:
            _walk(child)

    for top in workspace.top_level_scopes:
        _walk(top)
    return frozenset(paths)


def build_assy_gateway_binding(
    gateway_id: str = "ASSY-GW-01",
    table_id: str = "assy-gateway-observation-binding",
    version: str = "1",
) -> GatewayBindingTable:
    """Bounded TIPA ASSY example: bind ASSY-SL01..06 to one gateway/workstation.

    Read-only declaration only; never rewrites the ASSY runtime or MES contract.
    """
    from virtual_factory.federation.tipa_workspace import (
        SUB_LINE_IDS,
        sub_line_path,
    )

    scope_paths = [sub_line_path(sid).as_string() for sid in SUB_LINE_IDS]
    gateway = GatewayWorkstation(
        gateway_id=gateway_id,
        kind="workstation",
        display_name="ASSY gateway/workstation 01",
    )
    bindings = tuple(
        GatewayScopeBinding(
            binding_id=f"b-{i:02d}",
            gateway_id=gateway_id,
            scope_path=sp,
            domain="assy",
        )
        for i, sp in enumerate(scope_paths)
    )
    return GatewayBindingTable(
        table_id=table_id,
        version=version,
        gateways=(gateway,),
        bindings=bindings,
        known_scope_paths=frozenset(scope_paths),
    )
