"""Types and canonical quantity validation for the material ledger."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping


class MaterialError(ValueError):
    """Base error for material ledger invariants."""


class MaterialValidationError(MaterialError):
    """Raised when a transaction violates semantic constraints."""


class MaterialSchemaError(MaterialValidationError):
    """Raised when a transaction does not match the published schema."""


class QuantityError(MaterialValidationError):
    """Raised when a quantity is not canonical or violates UOM policy."""


class RecipeError(MaterialValidationError):
    """Raised when a transform does not match its declared recipe."""


class DuplicateMaterialError(MaterialValidationError):
    """Raised when a material identifier is created twice."""


class UnknownMaterialError(MaterialValidationError):
    """Raised when a material identifier is not owned by the ledger."""


class CapacityError(MaterialValidationError):
    """Raised when a destination buffer cannot accept the quantity."""


class IdempotencyConflictError(MaterialValidationError):
    """Raised when a key or transaction id is reused with different bytes."""


class VersionConflictError(MaterialError):
    """Raised when the caller's expected ledger version is stale."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"ledger version conflict: expected {expected}, actual {actual}"
        )


class TransferError(MaterialValidationError):
    """Raised when a transfer state transition is invalid."""


class ReservationError(MaterialValidationError):
    """Raised when a reservation cannot be found or used."""


class Unit(str, Enum):
    EA = "EA"
    KG = "KG"
    L = "L"
    M = "M"
    BATCH = "BATCH"


class QualityStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    ACCEPTED = "ACCEPTED"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


class MaterialLifecycle(str, Enum):
    PRODUCED = "PRODUCED"
    CONSUMED = "CONSUMED"
    SCRAPPED = "SCRAPPED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"


class MaterialScope(str, Enum):
    UNIT = "UNIT"
    LOT = "LOT"
    BATCH = "BATCH"


class ReservationState(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CONSUMED = "CONSUMED"


class TransferState(str, Enum):
    REQUESTED = "REQUESTED"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"
    LOST = "LOST"


class RequestStatus(str, Enum):
    COMMITTED = "COMMITTED"
    WAITING_FOR_MATERIAL = "WAITING_FOR_MATERIAL"
    WAITING_FOR_QUALITY = "WAITING_FOR_QUALITY"


class TransactionType(str, Enum):
    PRODUCE = "PRODUCE"
    RESERVE = "RESERVE"
    RELEASE_RESERVATION = "RELEASE_RESERVATION"
    SHIP = "SHIP"
    RECEIVE = "RECEIVE"
    CONSUME = "CONSUME"
    TRANSFORM = "TRANSFORM"
    SCRAP = "SCRAP"
    REJECT = "REJECT"
    RETURN = "RETURN"


INTEGRAL_UNITS = frozenset({Unit.EA, Unit.BATCH})
DEFAULT_PRECISION = {"KG": 3, "L": 3, "M": 3}
DEFAULT_QUALITY = QualityStatus.UNKNOWN


_CANONICAL_INTEGER = re.compile(r"^(?:0|[1-9][0-9]*)$")
_CANONICAL_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _coerce_unit(value: Unit | str) -> Unit:
    if isinstance(value, Unit):
        return value
    try:
        return Unit(value)
    except ValueError as exc:
        raise QuantityError(f"unknown unit: {value!r}") from exc


def _coerce_quality(value: QualityStatus | str) -> QualityStatus:
    if isinstance(value, QualityStatus):
        return value
    try:
        return QualityStatus(value)
    except ValueError as exc:
        raise MaterialValidationError(f"unknown quality status: {value!r}") from exc


def _coerce_lifecycle(value: MaterialLifecycle | str) -> MaterialLifecycle:
    if isinstance(value, MaterialLifecycle):
        return value
    try:
        return MaterialLifecycle(value)
    except ValueError as exc:
        raise MaterialValidationError(f"unknown lifecycle: {value!r}") from exc


def _coerce_scope(value: MaterialScope | str) -> MaterialScope:
    if isinstance(value, MaterialScope):
        return value
    try:
        return MaterialScope(value)
    except ValueError as exc:
        raise MaterialValidationError(f"unknown material scope: {value!r}") from exc


def _coerce_transfer_state(value: TransferState | str) -> TransferState:
    if isinstance(value, TransferState):
        return value
    try:
        return TransferState(value)
    except ValueError as exc:
        raise MaterialValidationError(f"unknown transfer state: {value!r}") from exc


def _coerce_reservation_state(
    value: ReservationState | str,
) -> ReservationState:
    if isinstance(value, ReservationState):
        return value
    try:
        return ReservationState(value)
    except ValueError as exc:
        raise MaterialValidationError(
            f"unknown reservation state: {value!r}"
        ) from exc


def _precision_for(unit: Unit, precision: int | None) -> int | None:
    if unit in INTEGRAL_UNITS:
        return 0
    if precision is None:
        return DEFAULT_PRECISION[unit.value]
    if isinstance(precision, bool) or not isinstance(precision, int):
        raise QuantityError("unit precision must be an integer")
    if precision < 0:
        raise QuantityError("unit precision must be >= 0")
    return precision


def parse_quantity(
    value: object,
    unit: Unit | str,
    *,
    precision: int | None = None,
    allow_zero: bool = False,
    name: str = "quantity",
) -> Decimal:
    """Parse a canonical positive decimal string for a specific UOM."""
    if not isinstance(value, str):
        raise QuantityError(f"{name} must be a canonical decimal string")
    parsed_unit = _coerce_unit(unit)
    if not _CANONICAL_DECIMAL.fullmatch(value):
        raise QuantityError(
            f"{name} {value!r} is not a canonical nonnegative decimal string"
        )
    effective_precision = _precision_for(parsed_unit, precision)
    if parsed_unit in INTEGRAL_UNITS:
        if not _CANONICAL_INTEGER.fullmatch(value):
            raise QuantityError(
                f"{name} {value!r} must be an integer for {parsed_unit.value}"
            )
    elif "." in value:
        fraction = value.split(".", 1)[1]
        if effective_precision == 0 or len(fraction) != effective_precision:
            raise QuantityError(
                f"{name} {value!r} must use exactly {effective_precision} "
                f"fractional digits for {parsed_unit.value}"
            )
    amount = Decimal(value)
    if not amount.is_finite():
        raise QuantityError(f"{name} must be finite")
    if amount < 0 or (amount == 0 and not allow_zero):
        raise QuantityError(f"{name} must be strictly positive")
    return amount


def format_quantity(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        raise QuantityError("quantity must be Decimal")
    if not value.is_finite():
        raise QuantityError("quantity must be finite")
    return format(value, "f")


def canonical_request_key(transaction: Mapping[str, Any]) -> tuple[int, str, str]:
    """Stable same-tick ordering for competing synthetic clients."""
    return (
        int(transaction["simulation_tick_us"]),
        str(transaction.get("operation_execution_id") or ""),
        str(transaction["transaction_id"]),
    )


@dataclass
class MaterialItem:
    material_id: str
    material_type: str
    unit: Unit
    quantity: Decimal
    location: str
    quality: QualityStatus
    lifecycle: MaterialLifecycle
    scope: MaterialScope = MaterialScope.UNIT
    source_operation: str | None = None
    recipe_revision: str | None = None
    created_tick_us: int = 0
    parent_ids: tuple[str, ...] = ()
    quality_provenance: str = "SYNTHETIC_ASSUMPTION"

    def __post_init__(self) -> None:
        if not isinstance(self.material_id, str) or not self.material_id.strip():
            raise MaterialValidationError("material_id must be a non-empty str")
        if (
            not isinstance(self.material_type, str)
            or not self.material_type.strip()
        ):
            raise MaterialValidationError(
                "material_type must be a non-empty str"
            )
        self.unit = _coerce_unit(self.unit)
        if not isinstance(self.quantity, Decimal):
            raise MaterialValidationError("quantity must be Decimal")
        if not self.quantity.is_finite() or self.quantity < 0:
            raise MaterialValidationError("quantity must be finite and >= 0")
        if not isinstance(self.location, str) or not self.location.strip():
            raise MaterialValidationError("location must be a non-empty str")
        self.quality = _coerce_quality(self.quality)
        self.lifecycle = _coerce_lifecycle(self.lifecycle)
        self.scope = _coerce_scope(self.scope)
        if isinstance(self.created_tick_us, bool) or not isinstance(
            self.created_tick_us, int
        ):
            raise MaterialValidationError("created_tick_us must be int")
        if self.created_tick_us < 0:
            raise MaterialValidationError("created_tick_us must be >= 0")
        self.parent_ids = tuple(str(item) for item in self.parent_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_id": self.material_id,
            "material_type": self.material_type,
            "unit": self.unit.value,
            "quantity": format_quantity(self.quantity),
            "location": self.location,
            "quality": self.quality.value,
            "lifecycle": self.lifecycle.value,
            "scope": self.scope.value,
            "source_operation": self.source_operation,
            "recipe_revision": self.recipe_revision,
            "created_tick_us": self.created_tick_us,
            "parent_ids": list(self.parent_ids),
            "quality_provenance": self.quality_provenance,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MaterialItem:
        return cls(
            material_id=data["material_id"],
            material_type=data["material_type"],
            unit=Unit(data["unit"]),
            quantity=Decimal(data["quantity"]),
            location=data["location"],
            quality=QualityStatus(data["quality"]),
            lifecycle=MaterialLifecycle(data["lifecycle"]),
            scope=MaterialScope(data["scope"]),
            source_operation=data.get("source_operation"),
            recipe_revision=data.get("recipe_revision"),
            created_tick_us=data["created_tick_us"],
            parent_ids=tuple(data.get("parent_ids", ())),
            quality_provenance=data.get(
                "quality_provenance", "SYNTHETIC_ASSUMPTION"
            ),
        )


@dataclass(frozen=True)
class ReservationLeg:
    material_id: str
    quantity: Decimal
    unit: Unit
    location: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_id": self.material_id,
            "quantity": format_quantity(self.quantity),
            "unit": self.unit.value,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReservationLeg:
        return cls(
            material_id=data["material_id"],
            quantity=Decimal(data["quantity"]),
            unit=Unit(data["unit"]),
            location=data["location"],
        )


@dataclass
class Reservation:
    reservation_id: str
    owner_operation_id: str
    tick_us: int
    ledger_version: int
    legs: tuple[ReservationLeg, ...]
    state: ReservationState = ReservationState.ACTIVE

    def __post_init__(self) -> None:
        if not isinstance(self.reservation_id, str) or not self.reservation_id:
            raise MaterialValidationError(
                "reservation_id must be a non-empty str"
            )
        if (
            not isinstance(self.owner_operation_id, str)
            or not self.owner_operation_id
        ):
            raise MaterialValidationError(
                "owner_operation_id must be a non-empty str"
            )
        self.state = _coerce_reservation_state(self.state)
        self.legs = tuple(self.legs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "owner_operation_id": self.owner_operation_id,
            "tick_us": self.tick_us,
            "ledger_version": self.ledger_version,
            "legs": [leg.to_dict() for leg in self.legs],
            "state": self.state.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Reservation:
        return cls(
            reservation_id=data["reservation_id"],
            owner_operation_id=data["owner_operation_id"],
            tick_us=data["tick_us"],
            ledger_version=data["ledger_version"],
            legs=tuple(
                ReservationLeg.from_dict(item) for item in data["legs"]
            ),
            state=ReservationState(data["state"]),
        )


@dataclass
class TransferRecord:
    transfer_id: str
    material_id: str
    origin_material_id: str
    material_type: str
    unit: Unit
    quantity: Decimal
    sender_location: str
    destination_location: str
    sender_operation_id: str
    receiver_operation_id: str | None
    requested_tick_us: int
    ship_tick_us: int
    delivery_tick_us: int
    state: TransferState
    received_tick_us: int | None = None
    transaction_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.unit = _coerce_unit(self.unit)
        self.state = _coerce_transfer_state(self.state)
        self.transaction_ids = tuple(self.transaction_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "material_id": self.material_id,
            "origin_material_id": self.origin_material_id,
            "material_type": self.material_type,
            "unit": self.unit.value,
            "quantity": format_quantity(self.quantity),
            "sender_location": self.sender_location,
            "destination_location": self.destination_location,
            "sender_operation_id": self.sender_operation_id,
            "receiver_operation_id": self.receiver_operation_id,
            "requested_tick_us": self.requested_tick_us,
            "ship_tick_us": self.ship_tick_us,
            "delivery_tick_us": self.delivery_tick_us,
            "state": self.state.value,
            "received_tick_us": self.received_tick_us,
            "transaction_ids": list(self.transaction_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TransferRecord:
        return cls(
            transfer_id=data["transfer_id"],
            material_id=data["material_id"],
            origin_material_id=data["origin_material_id"],
            material_type=data["material_type"],
            unit=Unit(data["unit"]),
            quantity=Decimal(data["quantity"]),
            sender_location=data["sender_location"],
            destination_location=data["destination_location"],
            sender_operation_id=data["sender_operation_id"],
            receiver_operation_id=data.get("receiver_operation_id"),
            requested_tick_us=data["requested_tick_us"],
            ship_tick_us=data["ship_tick_us"],
            delivery_tick_us=data["delivery_tick_us"],
            state=TransferState(data["state"]),
            received_tick_us=data.get("received_tick_us"),
            transaction_ids=tuple(data.get("transaction_ids", ())),
        )


@dataclass(frozen=True)
class GenealogyEdge:
    parent_material_id: str
    child_material_id: str
    transaction_id: str
    recipe_revision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_material_id": self.parent_material_id,
            "child_material_id": self.child_material_id,
            "transaction_id": self.transaction_id,
            "recipe_revision": self.recipe_revision,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GenealogyEdge:
        return cls(
            parent_material_id=data["parent_material_id"],
            child_material_id=data["child_material_id"],
            transaction_id=data["transaction_id"],
            recipe_revision=data.get("recipe_revision"),
        )


@dataclass(frozen=True)
class OutboxRecord:
    event_id: str
    factory_run_id: str
    generation: int
    transaction_id: str
    event_type: str
    tick_us: int
    payload: Mapping[str, Any]
    idempotency_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "factory_run_id": self.factory_run_id,
            "generation": self.generation,
            "transaction_id": self.transaction_id,
            "event_type": self.event_type,
            "tick_us": self.tick_us,
            "payload": dict(self.payload),
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OutboxRecord:
        return cls(
            event_id=data["event_id"],
            factory_run_id=data["factory_run_id"],
            generation=data["generation"],
            transaction_id=data["transaction_id"],
            event_type=data["event_type"],
            tick_us=data["tick_us"],
            payload=dict(data["payload"]),
            idempotency_key=data["idempotency_key"],
        )


@dataclass(frozen=True)
class RecipeLeg:
    material_type: str
    unit: Unit
    quantity: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.material_type, str)
            or not self.material_type.strip()
        ):
            raise RecipeError("recipe material_type must be non-empty")
        object.__setattr__(self, "unit", _coerce_unit(self.unit))
        if not isinstance(self.quantity, Decimal):
            raise RecipeError("recipe quantity must be Decimal")
        if not self.quantity.is_finite() or self.quantity <= 0:
            raise RecipeError("recipe quantity must be finite and positive")

    @classmethod
    def from_mapping(
        cls, data: Mapping[str, Any], precision: Mapping[str, int] | None
    ) -> RecipeLeg:
        unit = Unit(data["unit"])
        quantity = parse_quantity(
            data["quantity"],
            unit,
            precision=(precision or {}).get(unit.value),
        )
        return cls(data["material_type"], unit, quantity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_type": self.material_type,
            "unit": self.unit.value,
            "quantity": format_quantity(self.quantity),
        }


@dataclass(frozen=True)
class Recipe:
    recipe_revision: str
    inputs: tuple[RecipeLeg, ...]
    outputs: tuple[RecipeLeg, ...]
    scrap: tuple[RecipeLeg, ...] = ()
    yield_ratio: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if not isinstance(self.recipe_revision, str) or not self.recipe_revision:
            raise RecipeError("recipe_revision must be a non-empty str")
        if not self.inputs:
            raise RecipeError("recipe must declare at least one input")
        if not self.outputs:
            raise RecipeError("recipe must declare at least one output")
        if not isinstance(self.yield_ratio, Decimal):
            raise RecipeError("yield_ratio must be Decimal")
        if not self.yield_ratio.is_finite() or not (
            Decimal("0") < self.yield_ratio <= Decimal("1")
        ):
            raise RecipeError("yield_ratio must be > 0 and <= 1")

    @classmethod
    def from_mapping(
        cls, data: Mapping[str, Any], precision: Mapping[str, int] | None
    ) -> Recipe:
        return cls(
            recipe_revision=data["recipe_revision"],
            inputs=tuple(
                RecipeLeg.from_mapping(item, precision)
                for item in data["inputs"]
            ),
            outputs=tuple(
                RecipeLeg.from_mapping(item, precision)
                for item in data["outputs"]
            ),
            scrap=tuple(
                RecipeLeg.from_mapping(item, precision)
                for item in data.get("scrap", ())
            ),
            yield_ratio=Decimal(str(data.get("yield_ratio", "1"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_revision": self.recipe_revision,
            "inputs": [leg.to_dict() for leg in self.inputs],
            "outputs": [leg.to_dict() for leg in self.outputs],
            "scrap": [leg.to_dict() for leg in self.scrap],
            "yield_ratio": format_quantity(self.yield_ratio),
        }


@dataclass(frozen=True)
class Buffer:
    location_id: str
    capacity: Decimal | None
    unit: Unit | None = None
    allowed_material_types: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.location_id, str) or not self.location_id:
            raise MaterialValidationError(
                "buffer location_id must be a non-empty str"
            )
        if self.capacity is not None:
            if not isinstance(self.capacity, Decimal):
                raise MaterialValidationError("buffer capacity must be Decimal")
            if not self.capacity.is_finite() or self.capacity < 0:
                raise MaterialValidationError(
                    "buffer capacity must be finite and >= 0"
                )
            if self.unit is None:
                raise MaterialValidationError(
                    "finite buffer capacity requires a unit"
                )
        if self.unit is not None:
            object.__setattr__(self, "unit", _coerce_unit(self.unit))
        if self.allowed_material_types is not None:
            object.__setattr__(
                self,
                "allowed_material_types",
                frozenset(self.allowed_material_types),
            )

    @classmethod
    def from_mapping(
        cls, data: Mapping[str, Any], precision: Mapping[str, int] | None
    ) -> Buffer:
        unit = data.get("unit")
        capacity = data.get("capacity")
        parsed_capacity = None
        if capacity is not None:
            if unit is None:
                raise MaterialValidationError(
                    "finite buffer capacity requires a unit"
                )
            parsed_unit = Unit(unit)
            parsed_capacity = parse_quantity(
                capacity,
                parsed_unit,
                precision=(precision or {}).get(parsed_unit.value),
                allow_zero=True,
                name="capacity",
            )
        return cls(
            location_id=data["location_id"],
            capacity=parsed_capacity,
            unit=Unit(unit) if unit is not None else None,
            allowed_material_types=(
                frozenset(data["allowed_material_types"])
                if data.get("allowed_material_types") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class TransactionReceipt:
    status: RequestStatus
    transaction_id: str
    idempotency_key: str
    payload_digest: str
    ledger_version: int
    tick_us: int
    event_ids: tuple[str, ...] = ()
    outbox_ids: tuple[str, ...] = ()
    reservation_id: str | None = None
    child_ids: tuple[str, ...] = ()
    reason: str | None = None
    idempotent_replay: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "transaction_id": self.transaction_id,
            "idempotency_key": self.idempotency_key,
            "payload_digest": self.payload_digest,
            "ledger_version": self.ledger_version,
            "tick_us": self.tick_us,
            "event_ids": list(self.event_ids),
            "outbox_ids": list(self.outbox_ids),
            "reservation_id": self.reservation_id,
            "child_ids": list(self.child_ids),
            "reason": self.reason,
            "idempotent_replay": self.idempotent_replay,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TransactionReceipt:
        return cls(
            status=RequestStatus(data["status"]),
            transaction_id=data["transaction_id"],
            idempotency_key=data["idempotency_key"],
            payload_digest=data["payload_digest"],
            ledger_version=data["ledger_version"],
            tick_us=data["tick_us"],
            event_ids=tuple(data.get("event_ids", ())),
            outbox_ids=tuple(data.get("outbox_ids", ())),
            reservation_id=data.get("reservation_id"),
            child_ids=tuple(data.get("child_ids", ())),
            reason=data.get("reason"),
            idempotent_replay=data.get("idempotent_replay", False),
        )


MATERIAL_TRANSACTION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://factorix.vn/contracts/vf/tipa-g1/material-transaction-v0.1.schema.json",
    "title": "material-transaction-v0.1.schema.json",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "contract_version",
        "factory_run_id",
        "generation",
        "transaction_id",
        "idempotency_key",
        "simulation_tick_us",
        "ledger_expected_version",
        "transaction_type",
        "operation_execution_id",
        "transfer_id",
        "recipe_revision",
        "legs",
        "parent_refs",
        "child_refs",
        "source_kind",
        "definition_provenance",
    ],
    "properties": {
        "contract_version": {"const": "vf-material-transaction-v0.1"},
        "factory_run_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 256,
        },
        "generation": {"type": "integer", "minimum": 1},
        "transaction_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 256,
        },
        "idempotency_key": {
            "type": "string",
            "minLength": 1,
            "maxLength": 256,
        },
        "simulation_tick_us": {"type": "integer", "minimum": 0},
        "ledger_expected_version": {
            "type": "integer",
            "minimum": 0,
        },
        "transaction_type": {
            "enum": [item.value for item in TransactionType]
        },
        "operation_execution_id": {"type": ["string", "null"]},
        "transfer_id": {"type": ["string", "null"]},
        "recipe_revision": {"type": ["string", "null"]},
        "legs": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "material_id",
                    "material_type",
                    "quantity",
                    "unit",
                    "from_location",
                    "to_location",
                ],
                "properties": {
                    "material_id": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 256,
                    },
                    "material_type": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 256,
                    },
                    "quantity": {
                        "type": "string",
                        "pattern": "^(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?$",
                        "minLength": 1,
                    },
                    "unit": {"enum": [item.value for item in Unit]},
                    "from_location": {"type": ["string", "null"]},
                    "to_location": {"type": ["string", "null"]},
                },
            },
        },
        "parent_refs": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
        },
        "child_refs": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
        },
        "source_kind": {"enum": ["SIMULATED", "REPLAYED_SOURCE"]},
        "definition_provenance": {
            "enum": [
                "PDF_EXPLICIT",
                "VF_ACCEPTED_BASELINE",
                "MES_AS_BUILT",
                "SA_INFERENCE",
                "SYNTHETIC_ASSUMPTION",
                "PENDING_TIPA",
            ]
        },
    },
}
