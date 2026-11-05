"""Narrow supervised coordinator ↔ material-ledger committed-fact bridge."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from virtual_factory.factory.event_ledger import canonical_digest
from virtual_factory.factory.integration.checkpoint import (
    build_bridge_checkpoint,
    validate_bridge_checkpoint,
)
from virtual_factory.factory.integration.contracts import (
    BridgeCheckpoint,
    BridgeCheckpointError,
    BridgeContractError,
    BridgeError,
    BridgeIdentity,
    BridgeIdentityError,
    BridgePolicy,
    BridgeProjectionError,
    MaterialIntent,
    MaterialOutcome,
    MaterialOutcomeStatus,
    ProjectionStatus,
    thaw_payload,
    validate_header_against_identity,
)
from virtual_factory.factory.integration.outbox_projection import (
    OutboxProjectionModule,
)
from virtual_factory.factory.material.journal import (
    CorruptJournalError,
    Journal,
    JournalError,
)
from virtual_factory.factory.material.ledger import MaterialFlowLedger
from virtual_factory.factory.material.models import (
    MATERIAL_TRANSACTION_SCHEMA,
    IdempotencyConflictError,
    MaterialSchemaError,
    MaterialValidationError,
    RequestStatus,
    VersionConflictError,
)
from virtual_factory.factory.run_context import (
    FactoryRunContext,
    LifecycleState,
    SimTick,
)
from virtual_factory.factory.scheduler_adapter import (
    CommitError,
    CoordinatorError,
    PastEventError,
    ProposalError,
    SchedulerError,
    SerialFactoryCoordinator,
)

_LEDGER_HEADER_FIELDS = {
    "factory_run_id": "run_id",
    "generation": "generation",
    "definition_digest": "definition_digest",
    "config_digest": "config_digest",
    "model_revision": "model_revision",
    "seed": "seed",
}

try:  # pragma: no cover - exercised by the runtime without the dev extra
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None


def read_ledger_header(ledger: MaterialFlowLedger) -> Mapping[str, Any]:
    """Read the durable journal header without acquiring the writer lock."""

    if not isinstance(ledger, MaterialFlowLedger):
        raise BridgeContractError(
            "ledger must be a MaterialFlowLedger"
        )
    try:
        records = Journal(ledger.journal_path.parent).read_records()
    except (JournalError, OSError) as exc:
        raise BridgeIdentityError(
            f"cannot read material journal header: {exc}"
        ) from exc
    if not records:
        raise BridgeIdentityError(
            "material journal has no durable header"
        )
    header = records[0]
    if not isinstance(header, Mapping) or header.get(
        "record_type"
    ) != "HEADER":
        raise BridgeIdentityError(
            "material journal first record is not a header"
        )
    return header


def _validate_transaction_schema(transaction: Mapping[str, Any]) -> None:
    if Draft202012Validator is None:  # pragma: no cover
        required = set(MATERIAL_TRANSACTION_SCHEMA["required"])
        properties = set(MATERIAL_TRANSACTION_SCHEMA["properties"])
        missing = sorted(required - set(transaction))
        extra = sorted(set(transaction) - properties)
        if missing:
            raise BridgeContractError(
                f"transaction missing fields: {missing}"
            )
        if extra:
            raise BridgeContractError(
                f"transaction has unknown fields: {extra}"
            )
        return
    validator = Draft202012Validator(MATERIAL_TRANSACTION_SCHEMA)
    errors = sorted(
        validator.iter_errors(dict(transaction)),
        key=lambda error: list(error.path),
    )
    if errors:
        raise BridgeContractError(
            f"transaction schema invalid: {errors[0].message}"
        )


class MaterialBridge:
    """Synchronous supervised bridge with explicit durable-first ordering."""

    def __init__(
        self,
        context: FactoryRunContext,
        ledger: MaterialFlowLedger,
        coordinator: SerialFactoryCoordinator,
        *,
        definition_digest: str,
        policy: BridgePolicy | None = None,
        horizon_us: int | None = None,
    ) -> None:
        if not isinstance(context, FactoryRunContext):
            raise BridgeContractError(
                "context must be a FactoryRunContext"
            )
        if not isinstance(ledger, MaterialFlowLedger):
            raise BridgeContractError(
                "ledger must be a MaterialFlowLedger"
            )
        if not isinstance(coordinator, SerialFactoryCoordinator):
            raise BridgeContractError(
                "coordinator must be a SerialFactoryCoordinator"
            )
        if coordinator.context is not context:
            raise BridgeIdentityError(
                "coordinator context is not the supplied context"
            )
        if context.generation < 1:
            raise BridgeIdentityError(
                "bridge generation must be >= 1; generation 0 is not "
                "a bridge generation"
            )
        if not isinstance(definition_digest, str) or not (
            definition_digest.strip()
        ):
            raise BridgeContractError(
                "definition_digest must be a non-empty str"
            )
        identity = BridgeIdentity.from_context(
            context, definition_digest
        )
        validate_header_against_identity(context.header, identity)
        if policy is None:
            policy = BridgePolicy()
        if not isinstance(policy, BridgePolicy):
            raise BridgeContractError("policy must be a BridgePolicy")
        if horizon_us is not None:
            if isinstance(horizon_us, bool) or not isinstance(
                horizon_us, int
            ):
                raise BridgeContractError(
                    "horizon_us must be int, not bool"
                )
            if horizon_us < context.tick_us:
                raise BridgeContractError(
                    "horizon_us must not precede the current tick"
                )

        if ledger.factory_run_id != identity.run_id:
            raise BridgeIdentityError(
                "material ledger run id does not match context"
            )
        if ledger.generation != identity.generation:
            raise BridgeIdentityError(
                "material ledger generation does not match context"
            )
        header = read_ledger_header(ledger)
        for journal_field, identity_field in _LEDGER_HEADER_FIELDS.items():
            if header.get(journal_field) != getattr(
                identity, identity_field
            ):
                raise BridgeIdentityError(
                    f"material journal {journal_field} does not match "
                    "the pinned bridge identity"
                )

        self._context = context
        self._ledger = ledger
        self._coordinator = coordinator
        self._identity = identity
        self._policy = policy
        self._horizon_us = horizon_us
        self._last_error = ""
        self._projection = OutboxProjectionModule(
            ledger, identity=identity, policy=policy
        )
        try:
            coordinator.register_module(self._projection)
        except CoordinatorError as exc:
            raise BridgeContractError(
                f"cannot register projection module: {exc}"
            ) from exc

    # -- properties ------------------------------------------------------
    @property
    def context(self) -> FactoryRunContext:
        return self._context

    @property
    def ledger(self) -> MaterialFlowLedger:
        return self._ledger

    @property
    def coordinator(self) -> SerialFactoryCoordinator:
        return self._coordinator

    @property
    def projection(self) -> OutboxProjectionModule:
        return self._projection

    @property
    def identity(self) -> BridgeIdentity:
        return self._identity

    @property
    def policy(self) -> BridgePolicy:
        return self._policy

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def header_digest(self) -> str:
        return self._identity.header_digest()

    def _assert_identity(self) -> None:
        if self._context.run_id != self._identity.run_id:
            raise BridgeIdentityError("factory run id changed")
        if self._context.generation != self._identity.generation:
            raise BridgeIdentityError(
                "factory run generation changed; rebind a fresh "
                "generation-specific ledger and bridge"
            )
        if self._ledger.factory_run_id != self._identity.run_id:
            raise BridgeIdentityError("material ledger run id changed")
        if self._ledger.generation != self._identity.generation:
            raise BridgeIdentityError(
                "material ledger generation no longer matches"
            )
        validate_header_against_identity(
            self._context.header, self._identity
        )

    # -- intent validation ----------------------------------------------
    def validate_intent(self, intent: MaterialIntent) -> MaterialIntent:
        """Validate an intent without mutating material or event state."""

        if not isinstance(intent, MaterialIntent):
            raise BridgeContractError(
                "intent must be a MaterialIntent"
            )
        self._assert_identity()
        if intent.run_id != self._identity.run_id:
            raise BridgeIdentityError("intent run id mismatch")
        if intent.generation != self._identity.generation:
            raise BridgeIdentityError("intent generation mismatch")
        existing = self._ledger.get_receipt(intent.idempotency_key)
        if existing is not None and existing.payload_digest == intent.digest():
            # An exact idempotent replay performs no new commit and therefore
            # does not move the outbox or the event clock.
            return intent
        if intent.tick_us < self._context.tick_us:
            raise BridgeContractError(
                "intent tick is older than the coordinator clock"
            )
        if (
            self._horizon_us is not None
            and intent.tick_us > self._horizon_us
        ):
            raise BridgeContractError(
                "intent tick is beyond the known simulation horizon"
            )
        transaction = intent.transaction_payload()
        _validate_transaction_schema(transaction)
        if transaction.get("factory_run_id") != self._identity.run_id:
            raise BridgeIdentityError(
                "transaction factory_run_id mismatch"
            )
        if transaction.get("generation") != self._identity.generation:
            raise BridgeIdentityError(
                "transaction generation mismatch"
            )
        if transaction.get("simulation_tick_us") != intent.tick_us:
            raise BridgeIdentityError(
                "transaction simulation_tick_us mismatch"
            )
        if transaction.get("source_kind") != (
            self._policy.source_kind
        ):
            raise BridgeContractError(
                "transaction source_kind violates bridge policy"
            )
        if transaction.get("definition_provenance") != (
            self._policy.definition_provenance
        ):
            raise BridgeContractError(
                "transaction definition_provenance violates bridge policy"
            )
        return intent

    # -- material commit -------------------------------------------------
    def commit_material_intent(
        self, intent: MaterialIntent
    ) -> MaterialOutcome:
        """Validate then durably commit one material transaction.

        This method never projects, advances time, retries at a new version
        or mutates module state.  Projection is a separate, observable step.
        """

        if not isinstance(intent, MaterialIntent):
            raise BridgeContractError(
                "intent must be a MaterialIntent"
            )
        try:
            self.validate_intent(intent)
        except BridgeContractError as exc:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.REJECTED_CONTRACT,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=str(exc),
            )
        except BridgeProjectionError as exc:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.FAILED_TERMINAL,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=str(exc),
            )
        except Exception as exc:  # fail closed during validation
            return MaterialOutcome(
                status=MaterialOutcomeStatus.FAILED_TERMINAL,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=f"{type(exc).__name__}: {exc}",
            )
        transaction = intent.transaction_payload()
        try:
            receipt = self._ledger.apply_transaction(
                transaction, intent.expected_ledger_version
            )
        except VersionConflictError as exc:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.REJECTED_VERSION,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=str(exc),
            )
        except IdempotencyConflictError as exc:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.FAILED_TERMINAL,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=str(exc),
            )
        except (MaterialSchemaError, MaterialValidationError) as exc:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.REJECTED_CONTRACT,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=str(exc),
            )
        except (CorruptJournalError, JournalError, OSError) as exc:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.FAILED_TERMINAL,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=str(exc),
            )
        except Exception as exc:  # fail closed, never claim success
            return MaterialOutcome(
                status=MaterialOutcomeStatus.FAILED_TERMINAL,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                causal_reason=f"{type(exc).__name__}: {exc}",
            )

        if receipt.status is RequestStatus.COMMITTED:
            outbox_by_id = {
                record.event_id: record
                for record in self._ledger.outbox
            }
            missing = [
                event_id
                for event_id in receipt.outbox_ids
                if event_id not in outbox_by_id
            ]
            if missing:
                return MaterialOutcome(
                    status=MaterialOutcomeStatus.FAILED_TERMINAL,
                    transaction_id=intent.transaction_id,
                    idempotency_key=intent.idempotency_key,
                    receipt=receipt,
                    outbox_ids=tuple(receipt.outbox_ids),
                    causal_reason=(
                        "committed receipt references missing outbox rows: "
                        f"{missing}"
                    ),
                )
            return MaterialOutcome(
                status=MaterialOutcomeStatus.COMMITTED,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                receipt=receipt,
                outbox_ids=tuple(receipt.outbox_ids),
                outbox_digests=tuple(
                    canonical_digest(
                        outbox_by_id[event_id].to_dict()
                    )
                    for event_id in receipt.outbox_ids
                ),
                causal_reason=receipt.reason or "material committed",
            )
        if receipt.status is RequestStatus.WAITING_FOR_MATERIAL:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.WAITING_FOR_MATERIAL,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                receipt=receipt,
                causal_reason=receipt.reason or "material unavailable",
            )
        if receipt.status is RequestStatus.WAITING_FOR_QUALITY:
            return MaterialOutcome(
                status=MaterialOutcomeStatus.WAITING_FOR_QUALITY,
                transaction_id=intent.transaction_id,
                idempotency_key=intent.idempotency_key,
                receipt=receipt,
                causal_reason=receipt.reason or "quality ineligible",
            )
        return MaterialOutcome(
            status=MaterialOutcomeStatus.FAILED_TERMINAL,
            transaction_id=intent.transaction_id,
            idempotency_key=intent.idempotency_key,
            receipt=receipt,
            causal_reason=(
                f"unexpected material receipt status: {receipt.status}"
            ),
        )

    def commit_material_intents(
        self, intents: Sequence[MaterialIntent]
    ) -> tuple[MaterialOutcome, ...]:
        """Commit a supervised batch in canonical request order."""

        if isinstance(intents, (str, bytes)) or not isinstance(
            intents, Sequence
        ):
            raise BridgeContractError(
                "intents must be a sequence of MaterialIntent"
            )
        items = tuple(intents)
        for item in items:
            if not isinstance(item, MaterialIntent):
                raise BridgeContractError(
                    "intents must contain only MaterialIntent values"
                )
        ordered = sorted(items, key=lambda item: item.order_key())
        return tuple(
            self.commit_material_intent(intent)
            for intent in ordered
        )

    # -- projection and reconciliation ----------------------------------
    def reconcile_committed_outbox(self) -> ProjectionStatus:
        """Verify projected events against committed source outbox rows."""

        try:
            self._assert_identity()
        except BridgeContractError as exc:
            self._last_error = str(exc)
            return ProjectionStatus.INCOMPATIBLE
        try:
            source = self._projection.source_records()
        except BridgeProjectionError as exc:
            self._last_error = str(exc)
            return ProjectionStatus.INCOMPATIBLE
        projected = self._projection.projected_items()
        if len(projected) != self._projection.source_cursor:
            self._last_error = "projection trace/cursor length mismatch"
            return ProjectionStatus.INCOMPATIBLE
        for index, item in enumerate(projected):
            if index >= len(source):
                self._last_error = "projection exceeds source outbox"
                return ProjectionStatus.INCOMPATIBLE
            record = source[index]
            if item.get("source_index") != index:
                self._last_error = "projection source order mismatch"
                return ProjectionStatus.INCOMPATIBLE
            if item.get("event_id") != record.event_id:
                self._last_error = "projection event id mismatch"
                return ProjectionStatus.INCOMPATIBLE
            if item.get("source_outbox_digest") != (
                self._projection.source_digest_at(index)
            ):
                self._last_error = "projection source digest mismatch"
                return ProjectionStatus.INCOMPATIBLE
            if item.get("tick_us") != record.tick_us:
                self._last_error = "projection tick mismatch"
                return ProjectionStatus.INCOMPATIBLE
            if item.get("transaction_id") != record.transaction_id:
                self._last_error = "projection transaction mismatch"
                return ProjectionStatus.INCOMPATIBLE

        module_id = self._projection.manifest.module_id
        ledger_events = tuple(
            event
            for event in self._coordinator.ledger.events
            if event.module_id == module_id
        )
        projected_ids = [item["event_id"] for item in projected]
        if len(set(projected_ids)) != len(projected_ids):
            self._last_error = "duplicate projected event id"
            return ProjectionStatus.INCOMPATIBLE
        ledger_ids = [event.event_id for event in ledger_events]
        if len(set(ledger_ids)) != len(ledger_ids):
            self._last_error = "duplicate coordinator projection event"
            return ProjectionStatus.INCOMPATIBLE
        if set(ledger_ids) != set(projected_ids):
            self._last_error = (
                "coordinator projection events do not match projection trace"
            )
            return ProjectionStatus.INCOMPATIBLE
        for item in projected:
            matches = [
                event
                for event in ledger_events
                if event.event_id == item["event_id"]
            ]
            if len(matches) != 1:
                self._last_error = (
                    "projected material event lacks exactly one committed "
                    "event-ledger row"
                )
                return ProjectionStatus.INCOMPATIBLE
            event = matches[0]
            payload = thaw_payload(event.payload)
            if payload.get("source_outbox_digest") != item.get(
                "source_outbox_digest"
            ):
                self._last_error = (
                    "committed event payload outbox digest mismatch"
                )
                return ProjectionStatus.INCOMPATIBLE
            if payload.get("transaction_id") != item.get(
                "transaction_id"
            ):
                self._last_error = (
                    "committed event transaction mismatch"
                )
                return ProjectionStatus.INCOMPATIBLE

        if len(projected) > len(source):
            self._last_error = "projection cursor exceeds source outbox"
            return ProjectionStatus.INCOMPATIBLE
        if len(projected) == len(source):
            return ProjectionStatus.UP_TO_DATE
        pending_tick = source[len(projected)].tick_us
        if pending_tick < self._context.tick_us:
            self._last_error = (
                "unprojected source outbox is older than the coordinator "
                f"clock: {pending_tick} < {self._context.tick_us}"
            )
            return ProjectionStatus.RECOVERY_REQUIRED
        return ProjectionStatus.PENDING

    def project_pending(
        self, horizon_us: int | None = None
    ) -> ProjectionStatus:
        """Run the existing coordinator until committed outbox is projected."""

        try:
            self._assert_identity()
        except BridgeContractError as exc:
            self._last_error = str(exc)
            return ProjectionStatus.INCOMPATIBLE
        if self._context.state is not LifecycleState.RUNNING:
            self._last_error = (
                "projection requires a RUNNING coordinator"
            )
            return ProjectionStatus.RECOVERY_REQUIRED
        if horizon_us is None:
            target_us = self._horizon_us
            if target_us is None:
                source = self._projection.source_records()
                target_us = (
                    source[-1].tick_us
                    if source
                    else self._context.tick_us
                )
        else:
            if isinstance(horizon_us, bool) or not isinstance(
                horizon_us, int
            ):
                raise BridgeContractError(
                    "horizon_us must be int, not bool"
                )
            target_us = horizon_us
        if target_us < self._context.tick_us:
            raise BridgeContractError(
                "horizon_us must not precede the coordinator clock"
            )
        first = self._projection.first_unprojected_tick()
        if first is None:
            return self.reconcile_committed_outbox()
        if first.tick_us < self._context.tick_us:
            self._last_error = (
                "source outbox is older than the coordinator clock; "
                "fresh coordinator replay is required"
            )
            return ProjectionStatus.RECOVERY_REQUIRED
        if first.tick_us > target_us:
            return ProjectionStatus.PENDING
        try:
            self._coordinator.run_until(SimTick(target_us))
        except PastEventError as exc:
            self._last_error = str(exc)
            return ProjectionStatus.RECOVERY_REQUIRED
        except (
            BridgeProjectionError,
            CommitError,
            ProposalError,
            SchedulerError,
            CoordinatorError,
        ) as exc:
            self._last_error = str(exc)
            return ProjectionStatus.PENDING
        except Exception as exc:  # preserve committed stock, fail closed
            self._last_error = f"{type(exc).__name__}: {exc}"
            return ProjectionStatus.PENDING
        return self.reconcile_committed_outbox()

    # -- checkpoint / restore --------------------------------------------
    def checkpoint(self) -> BridgeCheckpoint:
        """Create an additive checkpoint at a quiescent PAUSED boundary."""

        self._assert_identity()
        if self._context.state is not LifecycleState.PAUSED:
            raise BridgeCheckpointError(
                "bridge checkpoint requires a PAUSED safe boundary"
            )
        status = self.reconcile_committed_outbox()
        if status is not ProjectionStatus.UP_TO_DATE:
            raise BridgeCheckpointError(
                f"bridge checkpoint requires UP_TO_DATE, got {status.value}"
            )
        coordinator_checkpoint = self._coordinator.checkpoint()
        return build_bridge_checkpoint(
            identity=self._identity,
            ledger=self._ledger,
            projection=self._projection,
            coordinator_checkpoint=coordinator_checkpoint,
        )

    def restore_or_rebuild(
        self, checkpoint: BridgeCheckpoint | Mapping[str, Any] | None = None
    ) -> ProjectionStatus:
        """Restore a validated checkpoint or rebuild from source outbox."""

        if checkpoint is not None:
            if isinstance(checkpoint, Mapping):
                try:
                    checkpoint = BridgeCheckpoint.from_dict(checkpoint)
                except BridgeCheckpointError:
                    raise
                except (TypeError, ValueError) as exc:
                    raise BridgeCheckpointError(
                        f"malformed bridge checkpoint: {exc}"
                    ) from exc
            if not isinstance(checkpoint, BridgeCheckpoint):
                raise BridgeCheckpointError(
                    "checkpoint must be a BridgeCheckpoint or mapping"
                )
            self._assert_identity()
            validate_bridge_checkpoint(
                checkpoint,
                identity=self._identity,
                ledger=self._ledger,
                projection=self._projection,
            )
            self._coordinator.restore(
                thaw_payload(checkpoint.coordinator_checkpoint)
            )
            self._context = self._coordinator.context
            restored_snapshot = thaw_payload(
                self._projection.snapshot()
            )
            if restored_snapshot != thaw_payload(
                checkpoint.module_snapshot
            ):
                raise BridgeCheckpointError(
                    "restored projection snapshot differs from checkpoint"
                )
            status = self.reconcile_committed_outbox()
            if status is not ProjectionStatus.UP_TO_DATE:
                raise BridgeCheckpointError(
                    "restored checkpoint does not reconcile: "
                    f"{status.value}"
                )
            return status

        self._assert_identity()
        module_id = self._projection.manifest.module_id
        foreign = [
            event
            for event in self._coordinator.ledger.events
            if event.module_id != module_id
        ]
        if foreign:
            self._last_error = (
                "coordinator contains non-material events that cannot be "
                "reproduced from the material source journal"
            )
            return ProjectionStatus.RECOVERY_REQUIRED
        try:
            fresh_context = FactoryRunContext(
                self._identity.run_id,
                self._context.header,
                generation=self._identity.generation,
            )
            fresh_context.validate()
            fresh_context.initialize()
            fresh_coordinator = SerialFactoryCoordinator(fresh_context)
            fresh_projection = OutboxProjectionModule(
                self._ledger,
                identity=self._identity,
                policy=self._policy,
            )
            fresh_coordinator.register_module(fresh_projection)
            fresh_coordinator.initialize()
            fresh_context.mark_ready()
            fresh_context.start()
            source = fresh_projection.source_records()
            if source:
                fresh_coordinator.run_until(
                    SimTick(source[-1].tick_us)
                )
        except (BridgeError, CoordinatorError) as exc:
            self._last_error = str(exc)
            return ProjectionStatus.RECOVERY_REQUIRED
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            return ProjectionStatus.RECOVERY_REQUIRED
        self._context = fresh_context
        self._coordinator = fresh_coordinator
        self._projection = fresh_projection
        return self.reconcile_committed_outbox()
