"""Deterministic journal-backed MaterialFlowLedger reference."""

from __future__ import annotations

import copy
import os
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

from virtual_factory.factory.material.accounting import (
    active_reserved_quantities,
    available_quantity,
    check_buffer_capacity,
    validate_recipe_legs,
)
from virtual_factory.factory.material.journal import (
    CorruptJournalError,
    Journal,
    canonical_digest,
)
from virtual_factory.factory.material.models import (
    Buffer,
    CapacityError,
    DuplicateMaterialError,
    GenealogyEdge,
    IdempotencyConflictError,
    MATERIAL_TRANSACTION_SCHEMA,
    MaterialItem,
    MaterialLifecycle,
    MaterialSchemaError,
    MaterialScope,
    MaterialValidationError,
    OutboxRecord,
    QualityStatus,
    QuantityError,
    Recipe,
    RecipeError,
    RequestStatus,
    Reservation,
    ReservationError,
    ReservationLeg,
    ReservationState,
    TransactionReceipt,
    TransactionType,
    TransferError,
    TransferRecord,
    TransferState,
    UnknownMaterialError,
    Unit,
    VersionConflictError,
    canonical_request_key,
    format_quantity,
    parse_quantity,
)
from virtual_factory.factory.material.transfer import (
    TransferPolicy,
    in_transit_location,
)


_CONTRACT_VERSION = "vf-material-transaction-v0.1"
_JOURNAL_CONTRACT_VERSION = "vf-material-journal-v0.1"
_COMMITTED_LIFECYCLES = frozenset(
    {MaterialLifecycle.PRODUCED, MaterialLifecycle.RETURNED}
)
_TRANSFER_TYPES = frozenset(
    {
        TransactionType.SHIP,
        TransactionType.RECEIVE,
        TransactionType.RETURN,
    }
)


@dataclass(frozen=True)
class _Leg:
    material_id: str
    material_type: str
    quantity: Decimal
    unit: Unit
    from_location: str | None
    to_location: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_id": self.material_id,
            "material_type": self.material_type,
            "quantity": format_quantity(self.quantity),
            "unit": self.unit.value,
            "from_location": self.from_location,
            "to_location": self.to_location,
        }


@dataclass
class _LedgerState:
    version: int = 0
    last_tick_us: int = -1
    items: dict[str, MaterialItem] = field(default_factory=dict)
    reservations: dict[str, Reservation] = field(default_factory=dict)
    transfers: dict[str, TransferRecord] = field(default_factory=dict)
    genealogy: list[GenealogyEdge] = field(default_factory=list)
    outbox: list[OutboxRecord] = field(default_factory=list)
    receipts: dict[str, TransactionReceipt] = field(default_factory=dict)
    idempotency: dict[str, tuple[str, TransactionReceipt]] = field(
        default_factory=dict
    )
    tx_index: dict[str, tuple[str, str, TransactionReceipt]] = field(
        default_factory=dict
    )


class MaterialFlowLedger:
    """Standalone material authority over a durable local journal."""

    def __init__(
        self,
        journal_dir: str | Path,
        *,
        factory_run_id: str,
        generation: int,
        definition_digest: str,
        config_digest: str,
        model_revision: str,
        seed: int = 0,
        buffers: Mapping[str, Buffer | Mapping[str, Any]] | None = None,
        recipes: Mapping[str, Recipe | Mapping[str, Any]] | None = None,
        quality_fixture: Mapping[str, QualityStatus | str] | None = None,
        scope_fixture: Mapping[str, MaterialScope | str] | None = None,
        unit_precision: Mapping[str, int] | None = None,
        transfer_policy: TransferPolicy | None = None,
    ) -> None:
        if not isinstance(factory_run_id, str) or not factory_run_id.strip():
            raise MaterialValidationError(
                "factory_run_id must be a non-empty str"
            )
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise MaterialValidationError("generation must be int")
        if generation < 1:
            raise MaterialValidationError("generation must be >= 1")
        for name, value in (
            ("definition_digest", definition_digest),
            ("config_digest", config_digest),
            ("model_revision", model_revision),
        ):
            if not isinstance(value, str) or not value.strip():
                raise MaterialValidationError(f"{name} must be a non-empty str")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise MaterialValidationError("seed must be int")

        self._factory_run_id = factory_run_id
        self._generation = generation
        self._definition_digest = definition_digest
        self._config_digest = config_digest
        self._model_revision = model_revision
        self._seed = seed
        self._precision = dict(unit_precision or {})
        self._quality_fixture = {
            str(key): QualityStatus(str(value))
            for key, value in (quality_fixture or {}).items()
        }
        self._scope_fixture = {
            str(key): MaterialScope(str(value))
            for key, value in (scope_fixture or {}).items()
        }
        self._buffers = self._coerce_buffers(buffers or {})
        self._recipes = self._coerce_recipes(recipes or {})
        self._transfer_policy = transfer_policy or TransferPolicy()
        if not isinstance(self._transfer_policy, TransferPolicy):
            raise MaterialValidationError(
                "transfer_policy must be a TransferPolicy"
            )
        self._header = {
            "record_type": "HEADER",
            "contract_version": _JOURNAL_CONTRACT_VERSION,
            "factory_run_id": factory_run_id,
            "generation": generation,
            "definition_digest": definition_digest,
            "config_digest": config_digest,
            "model_revision": model_revision,
            "seed": seed,
        }
        self._journal = Journal(journal_dir)
        self._state = _LedgerState()
        self._journal.acquire_writer()
        try:
            for record in self._journal.initialize(self._header):
                self._replay(record)
        except Exception:
            self._journal.release_writer()
            raise

    def _coerce_buffers(
        self, buffers: Mapping[str, Buffer | Mapping[str, Any]]
    ) -> dict[str, Buffer]:
        result: dict[str, Buffer] = {}
        for key, value in buffers.items():
            if isinstance(value, Buffer):
                buffer = value
                if buffer.location_id != key:
                    raise MaterialValidationError(
                        "buffer key must equal location_id"
                    )
            else:
                data = dict(value)
                data.setdefault("location_id", key)
                buffer = Buffer.from_mapping(data, self._precision)
            result[key] = buffer
        return result

    def _coerce_recipes(
        self, recipes: Mapping[str, Recipe | Mapping[str, Any]]
    ) -> dict[str, Recipe]:
        result: dict[str, Recipe] = {}
        for key, value in recipes.items():
            if isinstance(value, Recipe):
                recipe = value
                if recipe.recipe_revision != key:
                    raise RecipeError(
                        "recipe key must equal recipe_revision"
                    )
            else:
                data = dict(value)
                data.setdefault("recipe_revision", key)
                recipe = Recipe.from_mapping(data, self._precision)
            result[key] = recipe
        return result

    @property
    def factory_run_id(self) -> str:
        return self._factory_run_id

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def version(self) -> int:
        return self._state.version

    @property
    def journal_path(self) -> Path:
        return self._journal.path

    def close(self) -> None:
        self._journal.release_writer()

    @property
    def items(self) -> Mapping[str, MaterialItem]:
        return MappingProxyType(dict(self._state.items))

    @property
    def reservations(self) -> Mapping[str, Reservation]:
        return MappingProxyType(dict(self._state.reservations))

    @property
    def transfers(self) -> Mapping[str, TransferRecord]:
        return MappingProxyType(dict(self._state.transfers))

    @property
    def genealogy(self) -> tuple[GenealogyEdge, ...]:
        return tuple(self._state.genealogy)

    @property
    def outbox(self) -> tuple[OutboxRecord, ...]:
        return tuple(self._state.outbox)

    def get_item(self, material_id: str) -> MaterialItem | None:
        return self._state.items.get(material_id)

    def stock(self, material_id: str) -> Decimal:
        item = self._state.items.get(material_id)
        return item.quantity if item is not None else Decimal("0")

    def get_receipt(self, idempotency_key: str) -> TransactionReceipt | None:
        return self._state.receipts.get(idempotency_key)

    def state_digest(self) -> str:
        return self._state_digest(self._state)

    def _state_digest(self, state: _LedgerState) -> str:
        payload = {
            "version": state.version,
            "last_tick_us": state.last_tick_us,
            "items": [
                state.items[key].to_dict() for key in sorted(state.items)
            ],
            "reservations": [
                state.reservations[key].to_dict()
                for key in sorted(state.reservations)
            ],
            "transfers": [
                state.transfers[key].to_dict()
                for key in sorted(state.transfers)
            ],
            "genealogy": [edge.to_dict() for edge in state.genealogy],
            "outbox": [record.to_dict() for record in state.outbox],
            "receipts": [
                state.receipts[key].to_dict() for key in sorted(state.receipts)
            ],
            "idempotency": [
                {"key": key, "digest": state.idempotency[key][0]}
                for key in sorted(state.idempotency)
            ],
            "tx_index": [
                {
                    "transaction_id": key,
                    "idempotency_key": state.tx_index[key][0],
                    "digest": state.tx_index[key][1],
                }
                for key in sorted(state.tx_index)
            ],
        }
        return canonical_digest(payload)

    def _validate_schema(self, transaction: Mapping[str, Any]) -> None:
        if Draft202012Validator is None:
            required = set(MATERIAL_TRANSACTION_SCHEMA["required"])
            missing = sorted(required - set(transaction))
            extra = sorted(
                set(transaction) - set(MATERIAL_TRANSACTION_SCHEMA["properties"])
            )
            if missing:
                raise MaterialSchemaError(
                    f"transaction missing fields: {missing}"
                )
            if extra:
                raise MaterialSchemaError(
                    f"transaction has unknown fields: {extra}"
                )
            return
        validator = Draft202012Validator(MATERIAL_TRANSACTION_SCHEMA)
        errors = sorted(
            validator.iter_errors(dict(transaction)),
            key=lambda error: list(error.path),
        )
        if errors:
            raise MaterialSchemaError(errors[0].message)

    def _parse_legs(self, transaction: Mapping[str, Any]) -> tuple[_Leg, ...]:
        parsed: list[_Leg] = []
        for raw in transaction["legs"]:
            unit = Unit(raw["unit"])
            quantity = parse_quantity(
                raw["quantity"],
                unit,
                precision=self._precision.get(unit.value),
            )
            parsed.append(
                _Leg(
                    material_id=raw["material_id"],
                    material_type=raw["material_type"],
                    quantity=quantity,
                    unit=unit,
                    from_location=raw["from_location"],
                    to_location=raw["to_location"],
                )
            )
        return tuple(parsed)

    def _quality_for(self, material_id: str, material_type: str) -> QualityStatus:
        return self._quality_fixture.get(
            material_id,
            self._quality_fixture.get(material_type, QualityStatus.UNKNOWN),
        )

    def _scope_for(self, material_id: str) -> MaterialScope:
        return self._scope_fixture.get(material_id, MaterialScope.UNIT)

    def _buffer_for(self, location: str) -> Buffer | None:
        return self._buffers.get(location)

    def _check_capacity(
        self,
        items: Mapping[str, MaterialItem],
        leg: _Leg,
        location: str,
    ) -> None:
        buffer = self._buffer_for(location)
        if buffer is None:
            return
        check_buffer_capacity(
            buffer,
            items,
            leg.unit,
            leg.quantity,
            leg.material_type,
        )

    def _check_refs(
        self,
        transaction: Mapping[str, Any],
        parents: list[str],
        children: list[str],
    ) -> None:
        declared_parents = list(transaction["parent_refs"])
        declared_children = list(transaction["child_refs"])
        if declared_parents and set(declared_parents) != set(parents):
            raise MaterialValidationError(
                "parent_refs do not match material parent legs"
            )
        if len(set(declared_parents)) != len(declared_parents):
            raise MaterialValidationError("parent_refs must be unique")
        if declared_children and set(declared_children) != set(children):
            raise MaterialValidationError(
                "child_refs do not match created material legs"
            )
        if len(set(declared_children)) != len(declared_children):
            raise MaterialValidationError("child_refs must be unique")

    def _add_outbox(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        event_type: str,
        payload: Mapping[str, Any],
    ) -> str:
        sequence = len(state.outbox) + 1
        event_id = (
            f"{transaction['factory_run_id']}:{transaction['generation']}:"
            f"{transaction['transaction_id']}:{event_type}:{sequence}"
        )
        state.outbox.append(
            OutboxRecord(
                event_id=event_id,
                factory_run_id=transaction["factory_run_id"],
                generation=transaction["generation"],
                transaction_id=transaction["transaction_id"],
                event_type=event_type,
                tick_us=transaction["simulation_tick_us"],
                payload=dict(payload),
                idempotency_key=transaction["idempotency_key"],
            )
        )
        return event_id

    def _store_receipt(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        *,
        event_ids: tuple[str, ...] = (),
        outbox_ids: tuple[str, ...] = (),
        reservation_id: str | None = None,
        child_ids: tuple[str, ...] = (),
        reason: str | None = None,
    ) -> TransactionReceipt:
        receipt = TransactionReceipt(
            status=RequestStatus.COMMITTED,
            transaction_id=transaction["transaction_id"],
            idempotency_key=transaction["idempotency_key"],
            payload_digest=digest,
            ledger_version=state.version,
            tick_us=transaction["simulation_tick_us"],
            event_ids=event_ids,
            outbox_ids=outbox_ids,
            reservation_id=reservation_id,
            child_ids=child_ids,
            reason=reason,
        )
        key = transaction["idempotency_key"]
        state.receipts[key] = receipt
        state.idempotency[key] = (digest, receipt)
        state.tx_index[transaction["transaction_id"]] = (key, digest, receipt)
        return receipt

    def _commit(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        *,
        event_ids: tuple[str, ...] = (),
        outbox_ids: tuple[str, ...] = (),
        reservation_id: str | None = None,
        child_ids: tuple[str, ...] = (),
    ) -> TransactionReceipt:
        state.version += 1
        state.last_tick_us = transaction["simulation_tick_us"]
        return self._store_receipt(
            state,
            transaction,
            digest,
            event_ids=event_ids,
            outbox_ids=outbox_ids,
            reservation_id=reservation_id,
            child_ids=child_ids,
        )

    def _waiting(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        status: RequestStatus,
        reason: str,
    ) -> TransactionReceipt:
        return TransactionReceipt(
            status=status,
            transaction_id=transaction["transaction_id"],
            idempotency_key=transaction["idempotency_key"],
            payload_digest=digest,
            ledger_version=state.version,
            tick_us=transaction["simulation_tick_us"],
            reason=reason,
        )

    def _reserved(self, state: _LedgerState) -> dict[str, Decimal]:
        return active_reserved_quantities(state.reservations)

    def _owned_reserved(
        self, state: _LedgerState, operation_id: str, material_id: str
    ) -> Decimal:
        total = Decimal("0")
        for reservation in state.reservations.values():
            if (
                reservation.state is not ReservationState.ACTIVE
                or reservation.owner_operation_id != operation_id
            ):
                continue
            for leg in reservation.legs:
                if leg.material_id == material_id:
                    total += leg.quantity
        return total

    def _available_to_operation(
        self,
        state: _LedgerState,
        operation_id: str,
        item: MaterialItem,
    ) -> Decimal:
        reserved = self._reserved(state)
        own = self._owned_reserved(
            state, operation_id, item.material_id
        )
        return item.quantity - (
            reserved.get(item.material_id, Decimal("0")) - own
        )

    def _consume_owned_reservations(
        self,
        state: _LedgerState,
        operation_id: str,
        material_id: str,
        quantity: Decimal,
    ) -> None:
        remaining = quantity
        for reservation_id, reservation in list(state.reservations.items()):
            if (
                reservation.state is not ReservationState.ACTIVE
                or reservation.owner_operation_id != operation_id
                or remaining <= 0
            ):
                continue
            new_legs: list[ReservationLeg] = []
            changed = False
            for leg in reservation.legs:
                if leg.material_id == material_id and remaining > 0:
                    taken = min(leg.quantity, remaining)
                    left = leg.quantity - taken
                    remaining -= taken
                    changed = True
                    if left > 0:
                        new_legs.append(replace(leg, quantity=left))
                else:
                    new_legs.append(leg)
            if changed:
                new_state = (
                    ReservationState.CONSUMED
                    if not new_legs
                    else reservation.state
                )
                state.reservations[reservation_id] = replace(
                    reservation,
                    legs=tuple(new_legs),
                    state=new_state,
                )

    def _execute(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
    ) -> TransactionReceipt:
        tick = transaction["simulation_tick_us"]
        if tick < state.last_tick_us:
            raise MaterialValidationError(
                f"simulation tick {tick} is older than ledger tick "
                f"{state.last_tick_us}"
            )
        tx_type = TransactionType(transaction["transaction_type"])
        legs = self._parse_legs(transaction)
        if tx_type is TransactionType.PRODUCE:
            return self._produce(state, transaction, digest, legs)
        if tx_type is TransactionType.RESERVE:
            return self._reserve(state, transaction, digest, legs)
        if tx_type is TransactionType.RELEASE_RESERVATION:
            return self._release(state, transaction, digest, legs)
        if tx_type is TransactionType.CONSUME:
            return self._consume(state, transaction, digest, legs)
        if tx_type is TransactionType.TRANSFORM:
            return self._transform(state, transaction, digest, legs)
        if tx_type is TransactionType.SHIP:
            return self._ship(state, transaction, digest, legs)
        if tx_type is TransactionType.RECEIVE:
            return self._receive(state, transaction, digest, legs)
        if tx_type is TransactionType.RETURN:
            return self._return_transfer(state, transaction, digest, legs)
        if tx_type in (TransactionType.SCRAP, TransactionType.REJECT):
            return self._remove(state, transaction, digest, legs, tx_type)
        raise MaterialValidationError(
            f"unsupported transaction type {tx_type.value}"
        )

    def _produce(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        if transaction["parent_refs"]:
            raise MaterialValidationError(
                "PRODUCE cannot declare parent_refs"
            )
        created: list[str] = []
        for leg in legs:
            if leg.from_location is not None or leg.to_location is None:
                raise MaterialValidationError(
                    "PRODUCE legs require null from_location and a destination"
                )
            if leg.material_id in state.items:
                raise DuplicateMaterialError(
                    f"material identifier already exists: {leg.material_id!r}"
                )
            self._check_capacity(state.items, leg, leg.to_location)
            state.items[leg.material_id] = MaterialItem(
                material_id=leg.material_id,
                material_type=leg.material_type,
                unit=leg.unit,
                quantity=leg.quantity,
                location=leg.to_location,
                quality=self._quality_for(
                    leg.material_id, leg.material_type
                ),
                lifecycle=MaterialLifecycle.PRODUCED,
                scope=self._scope_for(leg.material_id),
                source_operation=transaction["operation_execution_id"],
                recipe_revision=transaction["recipe_revision"],
                created_tick_us=transaction["simulation_tick_us"],
            )
            created.append(leg.material_id)
        self._check_refs(transaction, [], created)
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_PRODUCED",
            {
                "transaction_id": transaction["transaction_id"],
                "material_ids": created,
                "legs": [leg.to_dict() for leg in legs],
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            child_ids=tuple(created),
        )

    def _reserve(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        operation_id = transaction["operation_execution_id"]
        if not operation_id:
            raise MaterialValidationError(
                "RESERVE requires operation_execution_id"
            )
        if transaction["child_refs"]:
            raise MaterialValidationError(
                "RESERVE cannot declare child_refs"
            )
        if len({leg.material_id for leg in legs}) != len(legs):
            raise MaterialValidationError(
                "RESERVE material legs must be unique"
            )
        reserved = self._reserved(state)
        quality_blocked = False
        material_blocked = False
        reservation_legs: list[ReservationLeg] = []
        for leg in legs:
            if leg.to_location is not None:
                raise MaterialValidationError(
                    "RESERVE legs require null to_location"
                )
            item = state.items.get(leg.material_id)
            if item is None:
                raise UnknownMaterialError(
                    f"unknown material {leg.material_id!r}"
                )
            if (
                leg.from_location is not None
                and leg.from_location != item.location
            ):
                raise MaterialValidationError(
                    f"material {leg.material_id!r} is not at "
                    f"{leg.from_location!r}"
                )
            if item.unit is not leg.unit:
                raise MaterialValidationError(
                    f"material {leg.material_id!r} uses {item.unit.value}"
                )
            if item.quality is not QualityStatus.ACCEPTED:
                quality_blocked = True
            if item.lifecycle not in _COMMITTED_LIFECYCLES:
                material_blocked = True
            if available_quantity(item, reserved) < leg.quantity:
                material_blocked = True
            reservation_legs.append(
                ReservationLeg(
                    material_id=leg.material_id,
                    quantity=leg.quantity,
                    unit=leg.unit,
                    location=item.location,
                )
            )
        if quality_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_QUALITY,
                "requested material is not quality-eligible",
            )
        if material_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_MATERIAL,
                "requested eligible material is not available",
            )
        reservation_id = transaction["transaction_id"]
        state.reservations[reservation_id] = Reservation(
            reservation_id=reservation_id,
            owner_operation_id=operation_id,
            tick_us=transaction["simulation_tick_us"],
            ledger_version=state.version + 1,
            legs=tuple(reservation_legs),
        )
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_RESERVED",
            {
                "transaction_id": transaction["transaction_id"],
                "reservation_id": reservation_id,
                "operation_execution_id": operation_id,
                "material_ids": [leg.material_id for leg in legs],
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            reservation_id=reservation_id,
        )

    def _release(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        operation_id = transaction["operation_execution_id"]
        if not operation_id:
            raise MaterialValidationError(
                "RELEASE_RESERVATION requires operation_execution_id"
            )
        material_ids = {leg.material_id for leg in legs}
        candidates = [
            reservation
            for reservation in state.reservations.values()
            if reservation.state is ReservationState.ACTIVE
            and reservation.owner_operation_id == operation_id
            and any(
                leg.material_id in material_ids for leg in reservation.legs
            )
        ]
        if not candidates:
            raise ReservationError("no active reservation to release")
        for reservation in candidates:
            reservation.state = ReservationState.RELEASED
        released_ids = [item.reservation_id for item in candidates]
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_RESERVATION_RELEASED",
            {
                "transaction_id": transaction["transaction_id"],
                "reservation_ids": released_ids,
                "material_ids": sorted(material_ids),
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            reservation_id=released_ids[0],
        )

    def _consume(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        operation_id = transaction["operation_execution_id"]
        if not operation_id:
            raise MaterialValidationError(
                "CONSUME requires operation_execution_id"
            )
        quality_blocked = False
        material_blocked = False
        for leg in legs:
            if leg.to_location is not None:
                raise MaterialValidationError(
                    "CONSUME legs require null to_location"
                )
            item = state.items.get(leg.material_id)
            if item is None:
                raise UnknownMaterialError(
                    f"unknown material {leg.material_id!r}"
                )
            if (
                leg.from_location is not None
                and leg.from_location != item.location
            ):
                raise MaterialValidationError(
                    f"material {leg.material_id!r} is not at "
                    f"{leg.from_location!r}"
                )
            if item.unit is not leg.unit:
                raise MaterialValidationError(
                    f"material {leg.material_id!r} uses {item.unit.value}"
                )
            if item.quality is not QualityStatus.ACCEPTED:
                quality_blocked = True
            if (
                self._available_to_operation(state, operation_id, item)
                < leg.quantity
            ):
                material_blocked = True
        if quality_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_QUALITY,
                "requested material is not quality-eligible",
            )
        if material_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_MATERIAL,
                "requested material is not available",
            )
        consumed: list[str] = []
        for leg in legs:
            item = state.items[leg.material_id]
            item.quantity -= leg.quantity
            if item.quantity == 0:
                item.lifecycle = MaterialLifecycle.CONSUMED
            self._consume_owned_reservations(
                state, operation_id, leg.material_id, leg.quantity
            )
            consumed.append(leg.material_id)
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_CONSUMED",
            {
                "transaction_id": transaction["transaction_id"],
                "operation_execution_id": operation_id,
                "material_ids": consumed,
                "legs": [leg.to_dict() for leg in legs],
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
        )

    def _transform(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        operation_id = transaction["operation_execution_id"]
        if not operation_id:
            raise MaterialValidationError(
                "TRANSFORM requires operation_execution_id"
            )
        recipe_revision = transaction["recipe_revision"]
        if not recipe_revision:
            raise MaterialValidationError(
                "TRANSFORM requires recipe_revision"
            )
        recipe = self._recipes.get(recipe_revision)
        if recipe is None:
            raise RecipeError(f"unknown recipe {recipe_revision!r}")
        inputs = tuple(leg for leg in legs if leg.from_location is not None)
        outputs = tuple(leg for leg in legs if leg.from_location is None)
        if not inputs or not outputs:
            raise MaterialValidationError(
                "TRANSFORM requires parent and child legs"
            )
        for output in outputs:
            if output.to_location is None:
                raise MaterialValidationError(
                    "TRANSFORM child legs require a destination"
                )
        validate_recipe_legs(
            recipe,
            [(leg.material_type, leg.unit, leg.quantity) for leg in inputs],
            [
                (leg.material_type, leg.unit, leg.quantity)
                for leg in outputs
            ],
        )
        self._check_refs(
            transaction,
            [leg.material_id for leg in inputs],
            [leg.material_id for leg in outputs],
        )
        quality_blocked = False
        material_blocked = False
        for leg in inputs:
            item = state.items.get(leg.material_id)
            if item is None:
                material_blocked = True
                continue
            if leg.from_location != item.location:
                raise MaterialValidationError(
                    f"material {leg.material_id!r} is not at "
                    f"{leg.from_location!r}"
                )
            if item.unit is not leg.unit:
                raise MaterialValidationError(
                    f"material {leg.material_id!r} uses {item.unit.value}"
                )
            if item.quality is not QualityStatus.ACCEPTED:
                quality_blocked = True
            if (
                self._available_to_operation(state, operation_id, item)
                < leg.quantity
            ):
                material_blocked = True
        for output in outputs:
            if output.material_id in state.items:
                raise DuplicateMaterialError(
                    f"material identifier already exists: "
                    f"{output.material_id!r}"
                )
        if quality_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_QUALITY,
                "a transform parent is not quality-eligible",
            )
        if material_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_MATERIAL,
                "a transform parent is missing or unavailable",
            )
        parent_ids = [leg.material_id for leg in inputs]
        for leg in inputs:
            item = state.items[leg.material_id]
            item.quantity -= leg.quantity
            if item.quantity == 0:
                item.lifecycle = MaterialLifecycle.CONSUMED
            self._consume_owned_reservations(
                state, operation_id, leg.material_id, leg.quantity
            )
        created: list[str] = []
        for output in outputs:
            self._check_capacity(state.items, output, output.to_location)
            state.items[output.material_id] = MaterialItem(
                material_id=output.material_id,
                material_type=output.material_type,
                unit=output.unit,
                quantity=output.quantity,
                location=output.to_location,
                quality=self._quality_for(
                    output.material_id, output.material_type
                ),
                lifecycle=MaterialLifecycle.PRODUCED,
                scope=self._scope_for(output.material_id),
                source_operation=operation_id,
                recipe_revision=recipe_revision,
                created_tick_us=transaction["simulation_tick_us"],
                parent_ids=tuple(parent_ids),
            )
            for parent_id in parent_ids:
                state.genealogy.append(
                    GenealogyEdge(
                        parent_material_id=parent_id,
                        child_material_id=output.material_id,
                        transaction_id=transaction["transaction_id"],
                        recipe_revision=recipe_revision,
                    )
                )
            created.append(output.material_id)
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_TRANSFORMED",
            {
                "transaction_id": transaction["transaction_id"],
                "operation_execution_id": operation_id,
                "recipe_revision": recipe_revision,
                "parent_ids": parent_ids,
                "child_ids": created,
                "inputs": [leg.to_dict() for leg in inputs],
                "outputs": [leg.to_dict() for leg in outputs],
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            child_ids=tuple(created),
        )

    def _ship(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        if len(legs) != 1:
            raise MaterialValidationError(
                "SHIP requires exactly one material leg"
            )
        leg = legs[0]
        transfer_id = transaction["transfer_id"]
        if not transfer_id:
            raise MaterialValidationError("SHIP requires transfer_id")
        if transfer_id in state.transfers:
            raise TransferError(
                f"transfer {transfer_id!r} already exists"
            )
        if leg.from_location is None or leg.to_location is None:
            raise MaterialValidationError(
                "SHIP requires sender and destination locations"
            )
        item = state.items.get(leg.material_id)
        if item is None:
            raise UnknownMaterialError(
                f"unknown material {leg.material_id!r}"
            )
        if item.location != leg.from_location:
            raise TransferError(
                f"material {leg.material_id!r} is not at sender "
                f"{leg.from_location!r}"
            )
        if item.unit is not leg.unit:
            raise MaterialValidationError(
                f"material {leg.material_id!r} uses {item.unit.value}"
            )
        if item.lifecycle not in _COMMITTED_LIFECYCLES:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_MATERIAL,
                "material is not physically available to ship",
            )
        reserved = self._reserved(state)
        if available_quantity(item, reserved) < leg.quantity:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_MATERIAL,
                "material is reserved or unavailable",
            )
        item.quantity -= leg.quantity
        transit_id = f"{leg.material_id}#in-transit:{transfer_id}"
        if transit_id in state.items:
            raise TransferError(
                f"in-transit material {transit_id!r} already exists"
            )
        ship_tick = transaction["simulation_tick_us"]
        latency = self._transfer_policy.latency_us(
            leg.from_location, leg.to_location
        )
        state.items[transit_id] = MaterialItem(
            material_id=transit_id,
            material_type=leg.material_type,
            unit=leg.unit,
            quantity=leg.quantity,
            location=in_transit_location(transfer_id),
            quality=item.quality,
            lifecycle=MaterialLifecycle.PRODUCED,
            scope=item.scope,
            source_operation=transaction["operation_execution_id"],
            recipe_revision=item.recipe_revision,
            created_tick_us=ship_tick,
            parent_ids=(leg.material_id,),
        )
        state.transfers[transfer_id] = TransferRecord(
            transfer_id=transfer_id,
            material_id=transit_id,
            origin_material_id=leg.material_id,
            material_type=leg.material_type,
            unit=leg.unit,
            quantity=leg.quantity,
            sender_location=leg.from_location,
            destination_location=leg.to_location,
            sender_operation_id=transaction["operation_execution_id"] or "",
            receiver_operation_id=None,
            requested_tick_us=ship_tick,
            ship_tick_us=ship_tick,
            delivery_tick_us=ship_tick + latency,
            state=TransferState.IN_TRANSIT,
            transaction_ids=(transaction["transaction_id"],),
        )
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_SHIPPED",
            {
                "transaction_id": transaction["transaction_id"],
                "transfer_id": transfer_id,
                "material_id": transit_id,
                "quantity": format_quantity(leg.quantity),
                "unit": leg.unit.value,
                "destination_location": leg.to_location,
                "delivery_tick_us": ship_tick + latency,
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            child_ids=(transit_id,),
        )

    def _receive(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        if len(legs) != 1:
            raise MaterialValidationError(
                "RECEIVE requires exactly one material leg"
            )
        leg = legs[0]
        transfer_id = transaction["transfer_id"]
        if not transfer_id:
            raise MaterialValidationError("RECEIVE requires transfer_id")
        transfer = state.transfers.get(transfer_id)
        if transfer is None:
            raise TransferError(
                f"cannot receive before ship: unknown transfer "
                f"{transfer_id!r}"
            )
        if transfer.state is not TransferState.IN_TRANSIT:
            raise TransferError(
                f"cannot receive transfer in state {transfer.state.value}"
            )
        if leg.material_id != transfer.material_id:
            raise TransferError(
                "RECEIVE material does not match the in-transit transfer"
            )
        if leg.unit is not transfer.unit:
            raise MaterialValidationError(
                f"transfer uses {transfer.unit.value}"
            )
        if leg.quantity != transfer.quantity:
            raise TransferError(
                "RECEIVE quantity must equal the owned in-transit quantity"
            )
        if leg.to_location != transfer.destination_location:
            raise TransferError("RECEIVE destination does not match the port")
        if (
            leg.from_location is not None
            and leg.from_location
            != in_transit_location(transfer_id)
        ):
            raise TransferError("RECEIVE source is not the transfer transit")
        if transaction["simulation_tick_us"] < transfer.delivery_tick_us:
            raise TransferError(
                "RECEIVE is earlier than the declared delivery tick"
            )
        item = state.items.get(transfer.material_id)
        if item is None:
            raise TransferError("in-transit material is missing")
        self._check_capacity(state.items, leg, leg.to_location)
        item.location = leg.to_location
        transfer.state = TransferState.RECEIVED
        transfer.receiver_operation_id = transaction[
            "operation_execution_id"
        ]
        transfer.received_tick_us = transaction["simulation_tick_us"]
        transfer.transaction_ids = transfer.transaction_ids + (
            transaction["transaction_id"],
        )
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_RECEIVED",
            {
                "transaction_id": transaction["transaction_id"],
                "transfer_id": transfer_id,
                "material_id": transfer.material_id,
                "destination_location": transfer.destination_location,
                "quantity": format_quantity(transfer.quantity),
                "unit": transfer.unit.value,
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            child_ids=(transfer.material_id,),
        )

    def _return_transfer(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
    ) -> TransactionReceipt:
        if len(legs) != 1:
            raise MaterialValidationError(
                "RETURN requires exactly one material leg"
            )
        leg = legs[0]
        transfer_id = transaction["transfer_id"]
        if not transfer_id:
            raise MaterialValidationError("RETURN requires transfer_id")
        transfer = state.transfers.get(transfer_id)
        if transfer is None:
            raise TransferError(f"unknown transfer {transfer_id!r}")
        if transfer.state is not TransferState.IN_TRANSIT:
            raise TransferError(
                f"cannot return transfer in state {transfer.state.value}"
            )
        if leg.material_id != transfer.material_id:
            raise TransferError(
                "RETURN material does not match the in-transit transfer"
            )
        if leg.quantity != transfer.quantity:
            raise TransferError(
                "RETURN requires the full owned in-transit quantity"
            )
        if leg.to_location != transfer.sender_location:
            raise TransferError("RETURN destination must be the sender")
        if (
            leg.from_location is not None
            and leg.from_location
            != in_transit_location(transfer_id)
        ):
            raise TransferError("RETURN source is not the transfer transit")
        item = state.items.get(transfer.material_id)
        if item is None:
            raise TransferError("in-transit material is missing")
        item.location = transfer.sender_location
        item.lifecycle = MaterialLifecycle.RETURNED
        transfer.state = TransferState.RETURNED
        transfer.receiver_operation_id = transaction[
            "operation_execution_id"
        ]
        transfer.transaction_ids = transfer.transaction_ids + (
            transaction["transaction_id"],
        )
        outbox_id = self._add_outbox(
            state,
            transaction,
            "MATERIAL_RETURNED",
            {
                "transaction_id": transaction["transaction_id"],
                "transfer_id": transfer_id,
                "material_id": transfer.material_id,
                "sender_location": transfer.sender_location,
                "quantity": format_quantity(transfer.quantity),
                "unit": transfer.unit.value,
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
            child_ids=(transfer.material_id,),
        )

    def _remove(
        self,
        state: _LedgerState,
        transaction: Mapping[str, Any],
        digest: str,
        legs: tuple[_Leg, ...],
        tx_type: TransactionType,
    ) -> TransactionReceipt:
        reserved = self._reserved(state)
        material_blocked = False
        for leg in legs:
            if leg.to_location is not None:
                raise MaterialValidationError(
                    f"{tx_type.value} legs require null to_location"
                )
            item = state.items.get(leg.material_id)
            if item is None:
                raise UnknownMaterialError(
                    f"unknown material {leg.material_id!r}"
                )
            if (
                leg.from_location is not None
                and leg.from_location != item.location
            ):
                raise MaterialValidationError(
                    f"material {leg.material_id!r} is not at "
                    f"{leg.from_location!r}"
                )
            if item.unit is not leg.unit:
                raise MaterialValidationError(
                    f"material {leg.material_id!r} uses {item.unit.value}"
                )
            if available_quantity(item, reserved) < leg.quantity:
                material_blocked = True
        if material_blocked:
            return self._waiting(
                state,
                transaction,
                digest,
                RequestStatus.WAITING_FOR_MATERIAL,
                "material is reserved or unavailable",
            )
        target_lifecycle = (
            MaterialLifecycle.SCRAPPED
            if tx_type is TransactionType.SCRAP
            else MaterialLifecycle.REJECTED
        )
        transfer_id = transaction["transfer_id"]
        for leg in legs:
            item = state.items[leg.material_id]
            was_in_transit = item.location == (
                in_transit_location(transfer_id) if transfer_id else None
            )
            item.quantity -= leg.quantity
            if item.quantity == 0:
                item.lifecycle = target_lifecycle
            if tx_type is TransactionType.REJECT:
                item.quality = QualityStatus.REJECTED
            if was_in_transit and transfer_id in state.transfers:
                transfer = state.transfers[transfer_id]
                if transfer.material_id == item.material_id:
                    transfer.state = TransferState.LOST
        outbox_id = self._add_outbox(
            state,
            transaction,
            (
                "MATERIAL_SCRAPPED"
                if tx_type is TransactionType.SCRAP
                else "MATERIAL_REJECTED"
            ),
            {
                "transaction_id": transaction["transaction_id"],
                "material_ids": [leg.material_id for leg in legs],
                "legs": [leg.to_dict() for leg in legs],
            },
        )
        return self._commit(
            state,
            transaction,
            digest,
            event_ids=(outbox_id,),
            outbox_ids=(outbox_id,),
        )

    def _crash_point(
        self, stage: str, transaction: Mapping[str, Any]
    ) -> None:
        expected_stage = os.environ.get("VF_MATERIAL_CRASH_STAGE")
        if expected_stage != stage:
            return
        expected_type = os.environ.get("VF_MATERIAL_CRASH_TYPE")
        if expected_type and expected_type != transaction["transaction_type"]:
            return
        os._exit(23)

    def apply_transaction(
        self, transaction: Mapping[str, Any], expected_version: int
    ) -> TransactionReceipt:
        if not isinstance(transaction, Mapping):
            raise MaterialSchemaError("transaction must be a mapping")
        if isinstance(expected_version, bool) or not isinstance(
            expected_version, int
        ):
            raise MaterialValidationError(
                "expected_version must be an integer"
            )
        tx = dict(transaction)
        self._validate_schema(tx)
        if tx["contract_version"] != _CONTRACT_VERSION:
            raise MaterialSchemaError(
                f"contract_version must be {_CONTRACT_VERSION}"
            )
        if tx["factory_run_id"] != self._factory_run_id:
            raise MaterialValidationError(
                "transaction factory_run_id does not match this ledger"
            )
        if tx["generation"] != self._generation:
            raise MaterialValidationError(
                "transaction generation does not match this ledger"
            )
        if tx["generation"] < 1:
            raise MaterialValidationError("generation must be >= 1")
        digest = canonical_digest(tx)
        key = tx["idempotency_key"]
        existing = self._state.idempotency.get(key)
        if existing is not None:
            existing_digest, existing_receipt = existing
            if existing_digest != digest:
                raise IdempotencyConflictError(
                    f"idempotency key {key!r} was reused with different bytes"
                )
            return replace(existing_receipt, idempotent_replay=True)
        tx_existing = self._state.tx_index.get(tx["transaction_id"])
        if tx_existing is not None:
            existing_key, existing_digest, existing_receipt = tx_existing
            if existing_key != key or existing_digest != digest:
                raise IdempotencyConflictError(
                    f"transaction id {tx['transaction_id']!r} was reused "
                    f"with different bytes"
                )
            return replace(existing_receipt, idempotent_replay=True)
        if tx["ledger_expected_version"] != expected_version:
            raise MaterialValidationError(
                "transaction ledger_expected_version must equal the "
                "caller's expected_version"
            )
        if expected_version != self._state.version:
            raise VersionConflictError(expected_version, self._state.version)
        working = copy.deepcopy(self._state)
        receipt = self._execute(working, tx, digest)
        if receipt.status is not RequestStatus.COMMITTED:
            return receipt
        self._crash_point("precommit", tx)
        record = {
            "record_type": "TRANSACTION",
            "contract_version": _JOURNAL_CONTRACT_VERSION,
            "expected_version": expected_version,
            "version": receipt.ledger_version,
            "transaction": tx,
            "receipt": receipt.to_dict(),
            "result_digest": self._state_digest(working),
        }
        self._journal.append(record)
        self._crash_point("postdurable", tx)
        tx_type = TransactionType(tx["transaction_type"])
        if tx_type in _TRANSFER_TYPES:
            self._crash_point("transfer-postdurable", tx)
        if tx_type is TransactionType.TRANSFORM:
            self._crash_point("join-postdurable", tx)
        self._state = working
        return receipt

    def _replay(self, record: Mapping[str, Any]) -> None:
        if record.get("record_type") != "TRANSACTION":
            raise CorruptJournalError("unknown journal record type")
        try:
            transaction = dict(record["transaction"])
            expected_version = record["expected_version"]
            stored_version = record["version"]
            stored_digest = record["result_digest"]
            stored_receipt = TransactionReceipt.from_dict(record["receipt"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CorruptJournalError(
                f"malformed transaction journal record: {exc}"
            ) from exc
        if stored_receipt.status is not RequestStatus.COMMITTED:
            raise CorruptJournalError(
                "journal contains a non-committed transaction"
            )
        if self._state.version != expected_version:
            raise CorruptJournalError(
                "journal expected version does not match replay state"
            )
        working = copy.deepcopy(self._state)
        digest = canonical_digest(transaction)
        receipt = self._execute(working, transaction, digest)
        if receipt.status is not RequestStatus.COMMITTED:
            raise CorruptJournalError(
                "journal transaction did not replay as committed"
            )
        if working.version != stored_version:
            raise CorruptJournalError(
                "journal version does not match replayed state"
            )
        if receipt.to_dict() != stored_receipt.to_dict():
            raise CorruptJournalError(
                "journal receipt does not match replayed receipt"
            )
        if self._state_digest(working) != stored_digest:
            raise CorruptJournalError(
                "journal state digest does not match replayed state"
            )
        self._state = working

    def apply_transactions(
        self, transactions: list[Mapping[str, Any]]
    ) -> tuple[TransactionReceipt, ...]:
        ordered = sorted(transactions, key=canonical_request_key)
        receipts: list[TransactionReceipt] = []
        for transaction in ordered:
            expected_version = transaction["ledger_expected_version"]
            receipts.append(
                self.apply_transaction(transaction, expected_version)
            )
        return tuple(receipts)
