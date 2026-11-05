"""Typed contracts for the TIPA G2A-03 material/coordinator bridge.

The bridge is deliberately narrow: the material journal is the sole durable
authority for stock, reservations, genealogy and its committed outbox.  The
event ledger remains an in-memory projection.  These contracts keep the two
identities and the observable outcomes explicit instead of inferring them from
caller strings or outbox event types.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from virtual_factory.factory.event_ledger import canonical_digest
from virtual_factory.factory.module_contract import (
    DEFINITION_PROVENANCES,
    SOURCE_KINDS,
    freeze_payload,
    thaw_payload,
)
from virtual_factory.factory.run_context import (
    FactoryHeader,
    FactoryRunContext,
    RunMode,
)
from virtual_factory.factory.material.models import TransactionReceipt

CHECKPOINT_SCHEMA_VERSION = "vf-material-bridge-checkpoint-v1"


class BridgeError(ValueError):
    """Base error for the coordinator/material bridge."""


class BridgeContractError(BridgeError):
    """Raised when an intent or identity violates the pinned contract."""


class BridgeIdentityError(BridgeContractError):
    """Raised when run/header/material identity no longer agrees."""


class BridgeProjectionError(BridgeError):
    """Raised when a committed outbox entry cannot be projected safely."""


class BridgeRecoveryRequired(BridgeProjectionError):
    """Raised when an in-memory projection cannot be advanced safely."""


class BridgeCheckpointError(BridgeError):
    """Raised when a bridge checkpoint is malformed or incompatible."""


class BridgeStateError(BridgeError):
    """Raised when the coordinator lifecycle cannot satisfy an operation."""


class MaterialOutcomeStatus(str, Enum):
    COMMITTED = "COMMITTED"
    WAITING_FOR_MATERIAL = "WAITING_FOR_MATERIAL"
    WAITING_FOR_QUALITY = "WAITING_FOR_QUALITY"
    REJECTED_VERSION = "REJECTED_VERSION"
    REJECTED_CONTRACT = "REJECTED_CONTRACT"
    FAILED_TERMINAL = "FAILED_TERMINAL"


class ProjectionStatus(str, Enum):
    UP_TO_DATE = "UP_TO_DATE"
    PENDING = "PENDING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    INCOMPATIBLE = "INCOMPATIBLE"


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BridgeContractError(f"{name} must be a non-empty str")
    return value


def _require_int(
    value: object, name: str, *, minimum: int = 0
) -> int:
    if isinstance(value, bool):
        raise BridgeContractError(f"{name} must be int, not bool")
    if not isinstance(value, int) or value < minimum:
        raise BridgeContractError(f"{name} must be int >= {minimum}")
    return value


def _require_utc(value: object, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise BridgeContractError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise BridgeContractError(f"{name} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise BridgeContractError(f"{name} must be in UTC")
    return value


@dataclass(frozen=True, slots=True)
class BridgePolicy:
    """Immutable G1A source/provenance policy for projected events.

    Projected event source fields are never inferred from an outbox
    ``event_type`` or from caller-controlled strings.
    """

    source_kind: str = "SIMULATED"
    definition_provenance: str = "SYNTHETIC_ASSUMPTION"

    def __post_init__(self) -> None:
        _require_text(self.source_kind, "source_kind")
        _require_text(
            self.definition_provenance, "definition_provenance"
        )
        if self.source_kind not in SOURCE_KINDS:
            raise BridgeContractError(
                f"source_kind must be one of {sorted(SOURCE_KINDS)}"
            )
        if self.definition_provenance not in DEFINITION_PROVENANCES:
            raise BridgeContractError(
                "definition_provenance must be one of "
                f"{sorted(DEFINITION_PROVENANCES)}"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "source_kind": self.source_kind,
            "definition_provenance": self.definition_provenance,
        }


@dataclass(frozen=True, slots=True)
class BridgeIdentity:
    """Pinned run, header and material-definition identity.

    ``workspace_digest`` and ``definition_digest`` are intentionally separate
    fields.  They are never compared by name or silently coerced.
    """

    run_id: str
    generation: int
    workspace_digest: str
    definition_digest: str
    config_digest: str
    model_revision: str
    seed: int
    epoch_utc: datetime
    mode: RunMode = RunMode.STANDALONE

    def __post_init__(self) -> None:
        _require_text(self.run_id, "run_id")
        _require_int(self.generation, "generation", minimum=1)
        _require_text(self.workspace_digest, "workspace_digest")
        _require_text(self.definition_digest, "definition_digest")
        _require_text(self.config_digest, "config_digest")
        _require_text(self.model_revision, "model_revision")
        _require_int(self.seed, "seed")
        _require_utc(self.epoch_utc, "epoch_utc")
        if not isinstance(self.mode, RunMode):
            try:
                object.__setattr__(self, "mode", RunMode(self.mode))
            except ValueError as exc:
                raise BridgeContractError(
                    f"invalid run mode: {self.mode!r}"
                ) from exc

    @classmethod
    def from_context(
        cls, context: FactoryRunContext, definition_digest: str
    ) -> "BridgeIdentity":
        if not isinstance(context, FactoryRunContext):
            raise BridgeContractError(
                "context must be a FactoryRunContext"
            )
        return cls(
            run_id=context.run_id,
            generation=context.generation,
            workspace_digest=context.header.workspace_digest,
            definition_digest=definition_digest,
            config_digest=context.header.config_digest,
            model_revision=context.header.model_revision,
            seed=context.header.seed,
            epoch_utc=context.header.epoch_utc,
            mode=context.header.mode,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "generation": self.generation,
            "workspace_digest": self.workspace_digest,
            "definition_digest": self.definition_digest,
            "config_digest": self.config_digest,
            "model_revision": self.model_revision,
            "seed": self.seed,
            "epoch_utc": self.epoch_utc.isoformat(),
            "mode": self.mode.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BridgeIdentity":
        if not isinstance(data, Mapping):
            raise BridgeContractError("identity must be a mapping")
        expected = {
            "run_id",
            "generation",
            "workspace_digest",
            "definition_digest",
            "config_digest",
            "model_revision",
            "seed",
            "epoch_utc",
            "mode",
        }
        if set(data) != expected:
            raise BridgeContractError("identity fields mismatch")
        try:
            epoch = datetime.fromisoformat(str(data["epoch_utc"]))
        except ValueError as exc:
            raise BridgeContractError("invalid epoch_utc") from exc
        return cls(
            run_id=data["run_id"],
            generation=data["generation"],
            workspace_digest=data["workspace_digest"],
            definition_digest=data["definition_digest"],
            config_digest=data["config_digest"],
            model_revision=data["model_revision"],
            seed=data["seed"],
            epoch_utc=epoch,
            mode=data["mode"],
        )

    def header_payload(self) -> dict[str, Any]:
        """Digest payload for :class:`FactoryHeader` facts only."""

        return {
            "workspace_digest": self.workspace_digest,
            "config_digest": self.config_digest,
            "seed": self.seed,
            "model_revision": self.model_revision,
            "epoch_utc": self.epoch_utc.isoformat(),
            "mode": self.mode.value,
        }

    def header_digest(self) -> str:
        return canonical_digest(self.header_payload())

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialIntent:
    """One complete, immutable material transaction intent."""

    run_id: str
    generation: int
    tick_us: int
    origin_module_id: str
    local_sequence: int
    transaction_id: str
    idempotency_key: str
    transaction: Mapping[str, Any]
    expected_ledger_version: int

    def __post_init__(self) -> None:
        _require_text(self.run_id, "run_id")
        _require_int(self.generation, "generation", minimum=1)
        _require_int(self.tick_us, "tick_us")
        _require_text(self.origin_module_id, "origin_module_id")
        _require_int(self.local_sequence, "local_sequence")
        _require_text(self.transaction_id, "transaction_id")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_int(
            self.expected_ledger_version, "expected_ledger_version"
        )
        if not isinstance(self.transaction, Mapping):
            raise BridgeContractError("transaction must be a mapping")
        frozen = freeze_payload(dict(self.transaction))
        object.__setattr__(self, "transaction", frozen)
        tx = thaw_payload(frozen)
        if tx.get("contract_version") != "vf-material-transaction-v0.1":
            raise BridgeContractError(
                "transaction contract_version must be "
                "vf-material-transaction-v0.1"
            )
        expected = {
            "factory_run_id": self.run_id,
            "generation": self.generation,
            "simulation_tick_us": self.tick_us,
            "transaction_id": self.transaction_id,
            "idempotency_key": self.idempotency_key,
            "ledger_expected_version": self.expected_ledger_version,
        }
        for field, value in expected.items():
            if tx.get(field) != value:
                raise BridgeContractError(
                    f"transaction {field} does not match intent"
                )

    def transaction_payload(self) -> dict[str, Any]:
        return thaw_payload(self.transaction)

    def digest(self) -> str:
        return canonical_digest(self.transaction_payload())

    def order_key(self) -> tuple[int, str, int, str]:
        return (
            self.tick_us,
            self.origin_module_id,
            self.local_sequence,
            self.transaction_id,
        )


@dataclass(frozen=True, slots=True)
class MaterialOutcome:
    """Observable result of a validated material intent."""

    status: MaterialOutcomeStatus
    transaction_id: str
    idempotency_key: str
    receipt: TransactionReceipt | None = None
    outbox_ids: tuple[str, ...] = ()
    outbox_digests: tuple[str, ...] = ()
    causal_reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, MaterialOutcomeStatus):
            try:
                object.__setattr__(
                    self, "status", MaterialOutcomeStatus(self.status)
                )
            except ValueError as exc:
                raise BridgeContractError(
                    f"invalid outcome status: {self.status!r}"
                ) from exc
        _require_text(self.transaction_id, "transaction_id")
        _require_text(self.idempotency_key, "idempotency_key")
        object.__setattr__(self, "outbox_ids", tuple(self.outbox_ids))
        object.__setattr__(
            self, "outbox_digests", tuple(self.outbox_digests)
        )
        if len(self.outbox_ids) != len(self.outbox_digests):
            raise BridgeContractError(
                "outbox_ids and outbox_digests must have equal length"
            )
        if not isinstance(self.causal_reason, str):
            raise BridgeContractError("causal_reason must be a str")
        if self.status is MaterialOutcomeStatus.COMMITTED:
            if self.receipt is None:
                raise BridgeContractError(
                    "COMMITTED outcome requires the original receipt"
                )

    @property
    def committed(self) -> bool:
        return self.status is MaterialOutcomeStatus.COMMITTED


@dataclass(frozen=True, slots=True)
class BridgeCheckpoint:
    """Quiescent bridge checkpoint, additive to coordinator checkpoints."""

    schema_version: str
    identity: BridgeIdentity
    identity_digest: str
    header_digest: str
    material_ledger_version: int
    material_state_digest: str
    source_outbox_ids: tuple[str, ...]
    source_outbox_digests: tuple[str, ...]
    source_cursor: int
    projection_trace: tuple[Mapping[str, Any], ...]
    projection_trace_digest: str
    module_snapshot: Mapping[str, Any]
    module_snapshot_digest: str
    coordinator_checkpoint: Mapping[str, Any]
    checkpoint_digest: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != CHECKPOINT_SCHEMA_VERSION:
            raise BridgeCheckpointError(
                f"schema_version must be {CHECKPOINT_SCHEMA_VERSION}"
            )
        if not isinstance(self.identity, BridgeIdentity):
            raise BridgeCheckpointError(
                "identity must be a BridgeIdentity"
            )
        _require_text(self.identity_digest, "identity_digest")
        _require_text(self.header_digest, "header_digest")
        _require_int(
            self.material_ledger_version,
            "material_ledger_version",
        )
        _require_text(self.material_state_digest, "material_state_digest")
        object.__setattr__(
            self, "source_outbox_ids", tuple(self.source_outbox_ids)
        )
        object.__setattr__(
            self,
            "source_outbox_digests",
            tuple(self.source_outbox_digests),
        )
        if len(self.source_outbox_ids) != len(
            self.source_outbox_digests
        ):
            raise BridgeCheckpointError(
                "source outbox ids/digests length mismatch"
            )
        _require_int(self.source_cursor, "source_cursor")
        if self.source_cursor > len(self.source_outbox_ids):
            raise BridgeCheckpointError("source_cursor out of range")
        frozen_trace = tuple(
            freeze_payload(dict(item)) for item in self.projection_trace
        )
        object.__setattr__(self, "projection_trace", frozen_trace)
        if len(frozen_trace) != self.source_cursor:
            raise BridgeCheckpointError(
                "projection_trace length must equal source_cursor"
            )
        _require_text(
            self.projection_trace_digest, "projection_trace_digest"
        )
        object.__setattr__(
            self,
            "module_snapshot",
            freeze_payload(dict(self.module_snapshot)),
        )
        _require_text(
            self.module_snapshot_digest, "module_snapshot_digest"
        )
        object.__setattr__(
            self,
            "coordinator_checkpoint",
            freeze_payload(dict(self.coordinator_checkpoint)),
        )
        if self.identity_digest != self.identity.digest():
            raise BridgeCheckpointError("identity_digest mismatch")
        if self.header_digest != self.identity.header_digest():
            raise BridgeCheckpointError("header_digest mismatch")
        if self.projection_trace_digest != canonical_digest(
            [thaw_payload(item) for item in frozen_trace]
        ):
            raise BridgeCheckpointError(
                "projection_trace_digest mismatch"
            )
        if self.module_snapshot_digest != canonical_digest(
            thaw_payload(self.module_snapshot)
        ):
            raise BridgeCheckpointError(
                "module_snapshot_digest mismatch"
            )
        expected = self._digest_payload()
        if self.checkpoint_digest:
            if self.checkpoint_digest != canonical_digest(expected):
                raise BridgeCheckpointError("checkpoint_digest mismatch")
        else:
            object.__setattr__(
                self, "checkpoint_digest", canonical_digest(expected)
            )

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "identity_digest": self.identity_digest,
            "header_digest": self.header_digest,
            "material_ledger_version": self.material_ledger_version,
            "material_state_digest": self.material_state_digest,
            "source_outbox_ids": list(self.source_outbox_ids),
            "source_outbox_digests": list(self.source_outbox_digests),
            "source_cursor": self.source_cursor,
            "projection_trace": [
                thaw_payload(item) for item in self.projection_trace
            ],
            "projection_trace_digest": self.projection_trace_digest,
            "module_snapshot": thaw_payload(self.module_snapshot),
            "module_snapshot_digest": self.module_snapshot_digest,
            "coordinator_checkpoint": thaw_payload(
                self.coordinator_checkpoint
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        data = self._digest_payload()
        data["checkpoint_digest"] = self.checkpoint_digest
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BridgeCheckpoint":
        if not isinstance(data, Mapping):
            raise BridgeCheckpointError("checkpoint must be a mapping")
        expected = {
            "schema_version",
            "identity",
            "identity_digest",
            "header_digest",
            "material_ledger_version",
            "material_state_digest",
            "source_outbox_ids",
            "source_outbox_digests",
            "source_cursor",
            "projection_trace",
            "projection_trace_digest",
            "module_snapshot",
            "module_snapshot_digest",
            "coordinator_checkpoint",
            "checkpoint_digest",
        }
        if set(data) != expected:
            raise BridgeCheckpointError("checkpoint fields mismatch")
        try:
            return cls(
                schema_version=data["schema_version"],
                identity=BridgeIdentity.from_dict(data["identity"]),
                identity_digest=data["identity_digest"],
                header_digest=data["header_digest"],
                material_ledger_version=data["material_ledger_version"],
                material_state_digest=data["material_state_digest"],
                source_outbox_ids=tuple(data["source_outbox_ids"]),
                source_outbox_digests=tuple(
                    data["source_outbox_digests"]
                ),
                source_cursor=data["source_cursor"],
                projection_trace=tuple(data["projection_trace"]),
                projection_trace_digest=data[
                    "projection_trace_digest"
                ],
                module_snapshot=data["module_snapshot"],
                module_snapshot_digest=data[
                    "module_snapshot_digest"
                ],
                coordinator_checkpoint=data["coordinator_checkpoint"],
                checkpoint_digest=data["checkpoint_digest"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, BridgeCheckpointError):
                raise
            raise BridgeCheckpointError(
                f"malformed checkpoint: {exc}"
            ) from exc



def validate_header_against_identity(
    header: FactoryHeader, identity: BridgeIdentity
) -> None:
    """Fail closed unless the live header equals the pinned identity."""

    if header.workspace_digest != identity.workspace_digest:
        raise BridgeIdentityError("workspace_digest mismatch")
    if header.config_digest != identity.config_digest:
        raise BridgeIdentityError("config_digest mismatch")
    if header.seed != identity.seed:
        raise BridgeIdentityError("seed mismatch")
    if header.model_revision != identity.model_revision:
        raise BridgeIdentityError("model_revision mismatch")
    if header.epoch_utc != identity.epoch_utc:
        raise BridgeIdentityError("epoch_utc mismatch")
    if header.mode is not identity.mode:
        raise BridgeIdentityError("run mode mismatch")
