"""Additive bridge checkpoint construction and strict restore validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from virtual_factory.factory.event_ledger import canonical_digest
from virtual_factory.factory.integration.contracts import (
    CHECKPOINT_SCHEMA_VERSION,
    BridgeCheckpoint,
    BridgeCheckpointError,
    BridgeIdentity,
    thaw_payload,
)
from virtual_factory.factory.integration.outbox_projection import (
    OutboxProjectionModule,
)


def build_bridge_checkpoint(
    *,
    identity: BridgeIdentity,
    ledger: Any,
    projection: OutboxProjectionModule,
    coordinator_checkpoint: Mapping[str, Any],
) -> BridgeCheckpoint:
    """Build the additive checkpoint at a quiescent, fully projected point."""

    source = projection.source_records()
    ids = tuple(record.event_id for record in source)
    digests = tuple(
        projection.source_digest_at(index)
        for index in range(len(source))
    )
    cursor = projection.source_cursor
    if cursor != len(ids):
        raise BridgeCheckpointError(
            "bridge checkpoint requires zero pending outbox rows"
        )
    trace = projection.projected_items()
    module_snapshot = projection.snapshot()
    return BridgeCheckpoint(
        schema_version=CHECKPOINT_SCHEMA_VERSION,
        identity=identity,
        identity_digest=identity.digest(),
        header_digest=identity.header_digest(),
        material_ledger_version=ledger.version,
        material_state_digest=ledger.state_digest(),
        source_outbox_ids=ids,
        source_outbox_digests=digests,
        source_cursor=cursor,
        projection_trace=trace,
        projection_trace_digest=canonical_digest(
            [dict(item) for item in trace]
        ),
        module_snapshot=module_snapshot,
        module_snapshot_digest=canonical_digest(
            thaw_payload(module_snapshot)
        ),
        coordinator_checkpoint=coordinator_checkpoint,
    )


def validate_bridge_checkpoint(
    checkpoint: BridgeCheckpoint,
    *,
    identity: BridgeIdentity,
    ledger: Any,
    projection: OutboxProjectionModule,
) -> None:
    """Fail closed unless a gate checkpoint matches live durable facts."""

    if not isinstance(checkpoint, BridgeCheckpoint):
        raise BridgeCheckpointError(
            "checkpoint must be a BridgeCheckpoint"
        )
    if checkpoint.schema_version != CHECKPOINT_SCHEMA_VERSION:
        raise BridgeCheckpointError("checkpoint schema version mismatch")
    if checkpoint.identity != identity:
        raise BridgeCheckpointError("checkpoint identity mismatch")
    if checkpoint.identity_digest != identity.digest():
        raise BridgeCheckpointError("checkpoint identity digest mismatch")
    if checkpoint.header_digest != identity.header_digest():
        raise BridgeCheckpointError("checkpoint header digest mismatch")
    if checkpoint.material_ledger_version != ledger.version:
        raise BridgeCheckpointError(
            "checkpoint material ledger version is stale"
        )
    if checkpoint.material_state_digest != ledger.state_digest():
        raise BridgeCheckpointError(
            "checkpoint material state digest mismatch"
        )

    source = projection.source_records()
    live_ids = tuple(record.event_id for record in source)
    live_digests = tuple(
        projection.source_digest_at(index)
        for index in range(len(source))
    )
    if checkpoint.source_outbox_ids != live_ids:
        raise BridgeCheckpointError(
            "checkpoint source outbox ids/order mismatch"
        )
    if checkpoint.source_outbox_digests != live_digests:
        raise BridgeCheckpointError(
            "checkpoint source outbox digest mismatch"
        )
    if checkpoint.source_cursor != len(live_ids):
        raise BridgeCheckpointError(
            "checkpoint has pending or unknown source cursor"
        )

    trace = [
        thaw_payload(item) for item in checkpoint.projection_trace
    ]
    if canonical_digest(trace) != checkpoint.projection_trace_digest:
        raise BridgeCheckpointError(
            "checkpoint projection trace digest mismatch"
        )
    module_snapshot = thaw_payload(checkpoint.module_snapshot)
    if canonical_digest(module_snapshot) != (
        checkpoint.module_snapshot_digest
    ):
        raise BridgeCheckpointError(
            "checkpoint module snapshot digest mismatch"
        )
    if module_snapshot.get("projection") != trace:
        raise BridgeCheckpointError(
            "checkpoint module snapshot trace mismatch"
        )
    if module_snapshot.get("source_cursor") != checkpoint.source_cursor:
        raise BridgeCheckpointError(
            "checkpoint module snapshot cursor mismatch"
        )
    if module_snapshot.get("factory_run_id") != identity.run_id:
        raise BridgeCheckpointError(
            "checkpoint module snapshot run id mismatch"
        )
    if module_snapshot.get("generation") != identity.generation:
        raise BridgeCheckpointError(
            "checkpoint module snapshot generation mismatch"
        )
    if module_snapshot.get("definition_digest") != (
        identity.definition_digest
    ):
        raise BridgeCheckpointError(
            "checkpoint module snapshot definition mismatch"
        )

    coordinator_checkpoint = thaw_payload(
        checkpoint.coordinator_checkpoint
    )
    if not isinstance(coordinator_checkpoint, Mapping):
        raise BridgeCheckpointError(
            "checkpoint coordinator payload must be a mapping"
        )
    if coordinator_checkpoint.get("factory_run_id") != identity.run_id:
        raise BridgeCheckpointError(
            "checkpoint coordinator run id mismatch"
        )
    if coordinator_checkpoint.get("generation") != identity.generation:
        raise BridgeCheckpointError(
            "checkpoint coordinator generation mismatch"
        )
    coordinator_tick = coordinator_checkpoint.get("tick_us")
    if isinstance(coordinator_tick, bool) or not isinstance(
        coordinator_tick, int
    ):
        raise BridgeCheckpointError(
            "checkpoint coordinator tick must be int"
        )
    projected_ticks = [
        item.get("tick_us") for item in trace
    ]
    if projected_ticks and coordinator_tick < projected_ticks[-1]:
        raise BridgeCheckpointError(
            "checkpoint coordinator tick precedes projected material events"
        )
    pending = coordinator_checkpoint.get("pending_events")
    if pending not in (None, []):
        raise BridgeCheckpointError(
            "checkpoint has unknown pending events"
        )
