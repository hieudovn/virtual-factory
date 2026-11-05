"""Side-effect-free projection of ledger-owned material outbox records.

The module only *reads* the durable material journal's immutable outbox.  It
never commits material, never publishes externally and never appends to the
event ledger itself; the existing serial coordinator remains the sole writer
of the in-memory event ledger.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from virtual_factory.factory.event_ledger import (
    CommittedEvent,
    ReadSnapshot,
    canonical_digest,
)
from virtual_factory.factory.integration.contracts import (
    BridgeContractError,
    BridgeIdentity,
    BridgePolicy,
    BridgeProjectionError,
    BridgeRecoveryRequired,
)
from virtual_factory.factory.material.models import (
    OutboxRecord,
    TransactionReceipt,
)
from virtual_factory.factory.module_contract import (
    CausalPhase,
    EventProposal,
    ISimulationModule,
    ModuleCapability,
    ModuleManifest,
    thaw_payload,
)
from virtual_factory.factory.run_context import SimTick, coerce_tick

PROJECTION_MODULE_ID = "vf.material.outbox-projection"
PROJECTION_MODULE_VERSION = "1.0"


def _material_ids(payload: Mapping[str, Any]) -> tuple[str, ...]:
    found: set[str] = set()
    for key in (
        "material_ids",
        "material_id",
        "parent_ids",
        "child_ids",
    ):
        value = payload.get(key)
        if isinstance(value, str):
            found.add(value)
        elif isinstance(value, (tuple, list)):
            for item in value:
                if isinstance(item, str):
                    found.add(item)
    for key in ("inputs", "outputs"):
        value = payload.get(key)
        if isinstance(value, (tuple, list)):
            for leg in value:
                if isinstance(leg, Mapping):
                    material_id = leg.get("material_id")
                    if isinstance(material_id, str):
                        found.add(material_id)
    return tuple(sorted(found))


class OutboxProjectionModule(ISimulationModule):
    """Deterministic, source-ordered projection of committed outbox rows."""

    def __init__(
        self,
        ledger: Any,
        *,
        identity: BridgeIdentity,
        policy: BridgePolicy,
    ) -> None:
        if not isinstance(identity, BridgeIdentity):
            raise BridgeContractError(
                "identity must be a BridgeIdentity"
            )
        if not isinstance(policy, BridgePolicy):
            raise BridgeContractError("policy must be a BridgePolicy")
        self._ledger = ledger
        self._identity = identity
        self._policy = policy
        self._cursor = 0
        self._trace: list[dict[str, Any]] = []
        self.manifest = ModuleManifest(
            module_id=PROJECTION_MODULE_ID,
            version=PROJECTION_MODULE_VERSION,
            fidelity="synthetic-reference",
            input_ports=(),
            output_ports=(),
            capabilities=frozenset(ModuleCapability),
            ownership="material-ledger-outbox",
        )
        if getattr(ledger, "factory_run_id", None) != identity.run_id:
            raise BridgeContractError(
                "material ledger run id does not match bridge identity"
            )
        if getattr(ledger, "generation", None) != identity.generation:
            raise BridgeContractError(
                "material ledger generation does not match bridge identity"
            )
        self._validate_source(self._source_records())

    # -- source snapshot -------------------------------------------------
    def _source_records(self) -> tuple[OutboxRecord, ...]:
        raw = getattr(self._ledger, "outbox", None)
        if raw is None:
            raise BridgeProjectionError(
                "material ledger does not expose an outbox"
            )
        records = tuple(raw)
        seen: set[str] = set()
        last_tick = -1
        for index, record in enumerate(records):
            if not isinstance(record, OutboxRecord):
                raise BridgeProjectionError(
                    f"outbox[{index}] is not an OutboxRecord"
                )
            if record.factory_run_id != self._identity.run_id:
                raise BridgeProjectionError(
                    f"outbox[{index}] run id mismatch"
                )
            if record.generation != self._identity.generation:
                raise BridgeProjectionError(
                    f"outbox[{index}] generation mismatch"
                )
            if record.event_id in seen:
                raise BridgeProjectionError(
                    f"duplicate outbox event_id {record.event_id!r}"
                )
            seen.add(record.event_id)
            if record.tick_us < last_tick:
                raise BridgeProjectionError(
                    "source outbox is not in nondecreasing tick order"
                )
            last_tick = record.tick_us
        return records

    @staticmethod
    def _source_digest(record: OutboxRecord) -> str:
        return canonical_digest(record.to_dict())

    def _validate_source(
        self, records: tuple[OutboxRecord, ...]
    ) -> None:
        for record in records:
            self._receipt_for(record)

    def _receipt_for(self, record: OutboxRecord) -> TransactionReceipt:
        receipt = self._ledger.get_receipt(record.idempotency_key)
        if not isinstance(receipt, TransactionReceipt):
            raise BridgeProjectionError(
                "committed outbox row has no original material receipt: "
                f"{record.event_id!r}"
            )
        if receipt.transaction_id != record.transaction_id:
            raise BridgeProjectionError(
                f"receipt transaction mismatch for {record.event_id!r}"
            )
        if receipt.tick_us != record.tick_us:
            raise BridgeProjectionError(
                f"receipt tick mismatch for {record.event_id!r}"
            )
        if receipt.outbox_ids and record.event_id not in receipt.outbox_ids:
            raise BridgeProjectionError(
                f"outbox id {record.event_id!r} absent from receipt"
            )
        return receipt

    def _expected_payload(
        self, record: OutboxRecord, receipt: TransactionReceipt
    ) -> dict[str, Any]:
        return {
            "transaction_id": record.transaction_id,
            "idempotency_key": record.idempotency_key,
            "ledger_version": receipt.ledger_version,
            "source_outbox_id": record.event_id,
            "source_outbox_digest": self._source_digest(record),
            "source_tick_us": record.tick_us,
            "source_material_ids": list(
                _material_ids(record.payload)
            ),
        }

    def _expected_proposal(
        self,
        record: OutboxRecord,
        index: int,
        receipt: TransactionReceipt,
    ) -> EventProposal:
        return EventProposal(
            tick=SimTick(record.tick_us),
            causal_phase=CausalPhase.PROCESS,
            module_id=self.manifest.module_id,
            local_sequence=index,
            event_id=record.event_id,
            event_type=record.event_type,
            definition_digest=self._identity.definition_digest,
            payload=self._expected_payload(record, receipt),
            source_id=record.event_id,
            source_kind=self._policy.source_kind,
            definition_provenance=(
                self._policy.definition_provenance
            ),
        )

    # -- ISimulationModule ----------------------------------------------
    def initialize(self) -> None:
        self._cursor = 0
        self._trace = []
        self._validate_source(self._source_records())

    def next_event_time(self, horizon: SimTick) -> SimTick | None:
        target = coerce_tick(horizon)
        records = self._source_records()
        if self._cursor >= len(records):
            return None
        tick = SimTick(records[self._cursor].tick_us)
        return tick if tick <= target else None

    def propose(
        self, horizon: SimTick, read_snapshot: ReadSnapshot
    ) -> tuple[EventProposal, ...]:
        target = coerce_tick(horizon)
        if not isinstance(read_snapshot, ReadSnapshot):
            raise BridgeProjectionError(
                "read_snapshot must be a ReadSnapshot"
            )
        if read_snapshot.factory_run_id != self._identity.run_id:
            raise BridgeProjectionError("read snapshot run id mismatch")
        if read_snapshot.generation != self._identity.generation:
            raise BridgeProjectionError(
                "read snapshot generation mismatch"
            )
        records = self._source_records()
        if self._cursor >= len(records):
            return ()
        current = read_snapshot.tick
        first = records[self._cursor]
        if first.tick_us < current.tick_us:
            raise BridgeRecoveryRequired(
                "unprojected source outbox is older than the coordinator "
                f"clock: {first.tick_us} < {current.tick_us}"
            )
        if first.tick_us > target.tick_us:
            return ()
        proposals: list[EventProposal] = []
        index = self._cursor
        while index < len(records):
            record = records[index]
            if record.tick_us != current.tick_us:
                break
            proposals.append(
                self._expected_proposal(
                    record, index, self._receipt_for(record)
                )
            )
            index += 1
        return tuple(proposals)

    def apply_committed(
        self, event: CommittedEvent, read_snapshot: ReadSnapshot
    ) -> None:
        if not isinstance(event, CommittedEvent):
            raise BridgeProjectionError(
                "event must be a CommittedEvent"
            )
        records = self._source_records()
        if self._cursor >= len(records):
            raise BridgeProjectionError(
                "coordinator committed an unexpected projection event"
            )
        record = records[self._cursor]
        expected = self._expected_proposal(
            record, self._cursor, self._receipt_for(record)
        )
        if event.factory_run_id != self._identity.run_id:
            raise BridgeProjectionError("committed event run id mismatch")
        if event.generation != self._identity.generation:
            raise BridgeProjectionError(
                "committed event generation mismatch"
            )
        if event.event_id != expected.event_id:
            raise BridgeProjectionError(
                "projected event_id does not match source outbox"
            )
        if event.tick != expected.tick:
            raise BridgeProjectionError(
                "projected event tick does not match source outbox"
            )
        if event.local_sequence != expected.local_sequence:
            raise BridgeProjectionError(
                "projected local_sequence does not match source index"
            )
        if event.event_type != expected.event_type:
            raise BridgeProjectionError(
                "projected event_type does not match source outbox"
            )
        if event.definition_digest != expected.definition_digest:
            raise BridgeProjectionError(
                "projected definition_digest mismatch"
            )
        if event.source_kind != expected.source_kind:
            raise BridgeProjectionError(
                "projected source_kind violates bridge policy"
            )
        if (
            event.definition_provenance
            != expected.definition_provenance
        ):
            raise BridgeProjectionError(
                "projected definition_provenance violates bridge policy"
            )
        if canonical_digest(thaw_payload(event.payload)) != (
            canonical_digest(thaw_payload(expected.payload))
        ):
            raise BridgeProjectionError(
                "projected payload does not match committed outbox"
            )
        self._trace.append(
            {
                "source_index": self._cursor,
                "event_id": record.event_id,
                "outbox_id": record.event_id,
                "tick_us": record.tick_us,
                "transaction_id": record.transaction_id,
                "idempotency_key": record.idempotency_key,
                "source_outbox_digest": self._source_digest(record),
                "event_sequence": event.sequence,
            }
        )
        self._cursor += 1

    def snapshot(self) -> Mapping[str, Any]:
        trace = [dict(item) for item in self._trace]
        return {
            "module_id": self.manifest.module_id,
            "factory_run_id": self._identity.run_id,
            "generation": self._identity.generation,
            "definition_digest": self._identity.definition_digest,
            "source_cursor": self._cursor,
            "projection": trace,
            "projection_trace_digest": canonical_digest(trace),
        }

    def restore(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping):
            raise BridgeProjectionError(
                "projection snapshot must be a mapping"
            )
        expected_keys = {
            "module_id",
            "factory_run_id",
            "generation",
            "definition_digest",
            "source_cursor",
            "projection",
            "projection_trace_digest",
        }
        if set(state) != expected_keys:
            raise BridgeProjectionError(
                "projection snapshot fields mismatch"
            )
        if state["module_id"] != self.manifest.module_id:
            raise BridgeProjectionError("projection module id mismatch")
        if state["factory_run_id"] != self._identity.run_id:
            raise BridgeProjectionError("projection run id mismatch")
        if state["generation"] != self._identity.generation:
            raise BridgeProjectionError("projection generation mismatch")
        if state["definition_digest"] != self._identity.definition_digest:
            raise BridgeProjectionError(
                "projection definition digest mismatch"
            )
        cursor = state["source_cursor"]
        if isinstance(cursor, bool) or not isinstance(cursor, int):
            raise BridgeProjectionError(
                "projection source_cursor must be int"
            )
        trace = state["projection"]
        if not isinstance(trace, (tuple, list)):
            raise BridgeProjectionError(
                "projection trace must be a sequence"
            )
        trace_items = tuple(dict(item) for item in trace)
        if len(trace_items) != cursor:
            raise BridgeProjectionError(
                "projection cursor does not match trace length"
            )
        if canonical_digest(trace_items) != state[
            "projection_trace_digest"
        ]:
            raise BridgeProjectionError(
                "projection trace digest mismatch"
            )
        records = self._source_records()
        if cursor > len(records):
            raise BridgeProjectionError(
                "projection cursor exceeds source outbox"
            )
        previous_index = -1
        for item in trace_items:
            index = item.get("source_index")
            if isinstance(index, bool) or not isinstance(index, int):
                raise BridgeProjectionError(
                    "projection source_index must be int"
                )
            if index <= previous_index or index >= len(records):
                raise BridgeProjectionError(
                    "projection source order is not a strict prefix"
                )
            previous_index = index
            record = records[index]
            if item.get("event_id") != record.event_id:
                raise BridgeProjectionError(
                    "projection event_id does not match source outbox"
                )
            if item.get("source_outbox_digest") != self._source_digest(
                record
            ):
                raise BridgeProjectionError(
                    "projection outbox digest mismatch"
                )
        if cursor and previous_index != cursor - 1:
            raise BridgeProjectionError(
                "projection trace is not a contiguous source prefix"
            )
        self._cursor = cursor
        self._trace = list(trace_items)

    # -- bridge helpers --------------------------------------------------
    def projected_items(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self._trace)

    @property
    def source_cursor(self) -> int:
        return self._cursor

    @property
    def identity(self) -> BridgeIdentity:
        return self._identity

    @property
    def policy(self) -> BridgePolicy:
        return self._policy

    def source_records(self) -> tuple[OutboxRecord, ...]:
        return self._source_records()

    def first_unprojected_tick(self) -> SimTick | None:
        records = self._source_records()
        if self._cursor >= len(records):
            return None
        return SimTick(records[self._cursor].tick_us)

    def source_digest_at(self, index: int) -> str:
        return self._source_digest(self._source_records()[index])
