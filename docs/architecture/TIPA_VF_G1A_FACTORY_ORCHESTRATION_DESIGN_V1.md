# G1A — TIPA Factory Orchestration: Detailed Architecture & Contracts v0.2

**Design state:** the architectural *direction* is PO/SA APPROVED by [#123](https://github.com/hieudovn/virtual-factory/issues/123); specific API/data schemas/atomicity choices below are **SA DETAIL DRAFT, pending schema/fixture review and Design Lock**.  
**Origin:** VF `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe` audit; existing ASSY/discrete/Water Bottle must remain backward compatible.  
**Phase:** Design only. None of the new `factory/` interfaces below is claimed implemented. PM blocked pending Design Lock.

## 1. Architectural decomposition

```text
TIPA Workspace Definition (hierarchy + process graph + resource + BOM + scope/provenance)
              │ version-pinned immutable read
              ▼
FactoryRunContext ─── FactoryFutureEventScheduler ─── Deterministic Commit Coordinator
      │                          │                              │
      ├──── ModuleHost / typed ports: SSO2, RSO2, ASSY SL01..06, others
      │                          │                              │
      └──── Shared Authorities: MaterialFlowLedger │ Event/GenealogyLedger │ Resource reservations
                                                                 │
                                                   Transactional Outbox / Projections
                                                       ├── PlantOS/IIoT
                                                       ├── MES C1–C4 mapping
                                                       └── QMS C5 (NEW; draft)
```

State authority table:
| State | Authoritative owner | Not an owner |
|---|---|---|
| Factory clock, event order, run lifecycle | FactoryRunContext / Coordinator | module-local wall clock |
| Module operation internals, temperature, machine simulation | The module itself | shared event bus |
| Material inventory/locations, allocations, reservations, transfers | MaterialFlowLedger | module producer event/MQTT |
| Shared equipment/resource allocations | Resource ledger | competing module |
| Committed event timeline + material genealogy | Factory Event/Genealogy Ledger transaction | UI derived read model |
| Quality measurement observation | originating module/test device | reconstructed dashboard |
| Operational effective hold/release decision | explicitly contracted simulation policy or external QMS authority | raw NG observation |
| External MES/QMS/PlantOS records | owning target system after versioned projection | VF's internal material state |

Physical hierarchy and process/material/semantic graphs are separately versioned. Equipment↔physical line membership does not establish BOM flow. An aggregation F1 module and F3 module may coexist and should expose explicit fidelity/source to projections.

## 2. G1A-01 FactoryRunContext / lifecycle
Candidate immutable header:
```json
{
  "factory_run_id": "TIPA-P0-RUN-0001",
  "generation": 1,
  "workspace_id": "tipa-manufacturing-p0",
  "definition_revision": "unverified-demo-v1",
  "definition_digest": "sha256:<pinned-digest>",
  "seed": 42,
  "epoch_utc": "2026-10-31T00:00:00Z",
  "timezone": "Asia/Ho_Chi_Minh",
  "production_day_start": "06:00",
  "shift_calendar_revision": "TIPA-ASSY-3SHIFT-v1",
  "mode": "INTEGRATED",
  "model_revisions": {"SSO2": "v0.1", "RSO2": "v0.1", "ASSY": "legacy-adapter-v0.1"},
  "scenario_revision": "SC-01-v0.1"
}
```
`definition_digest` is computed from exact canonical UTF-8 bytes, not human-friendly string or current wall clock; seed plus digest and all relevant fixture revisions pinned at run initialization. `factory_run_id` and `generation` qualify event IDs. Never reuse a generation after reset.

Lifecycle: `CREATED → VALIDATED → INITIALIZED → READY → RUNNING ↔ PAUSED → STOPPED`, with `FAILED` from execution states and `ARCHIVED` after terminal evidence. `RESET` creates a *new generation* and returns to `INITIALIZED`; it does not mutate a running generation's event identities. Unexpected transition fail closed. `REPLAY` is a new read/verification operation on frozen run history, not silent state rewrite.

Time: internally a monotonic **integer microsecond offset** from `epoch_utc` (proposal). Legacy float `simulation_time_s` conversion is controlled at one adapter boundary, with fixed decimal rounding and no negative/past events. Human-shift classification uses timezone/effective calendar; TIPA three shifts A 06–14, B 14–22, C 22–06 and production day 06→06 across midnight.

## 3. G1A-02 ModuleManifest & ISimulationModule
Declared capabilities (candidate): `F0_DEFINITION`, `F1_AGGREGATE`, `F2_OPERATION`, `F3_EQUIPMENT`; `STANDALONE` / `INTEGRATED`; `EXTERNAL_MATERIAL_INPUT`, `SNAPSHOT_RESTORE`, `ADVANCE_TO_EVENT_BOUNDARY`.

```python
class ISimulationModule(Protocol):
    def initialize(self, context: FactoryRunView, definition: ModuleDefinition) -> None: ...
    def next_event_time(self) -> SimTick | None: ...
    def propose(self, horizon: SimTick, snapshot: ReadOnlyFactorySnapshot) -> EventBatch: ...
    def apply_committed(self, result: CommitReceipt) -> None: ...
    def snapshot(self) -> ModuleCheckpoint: ...
    def restore(self, checkpoint: ModuleCheckpoint) -> None: ...
```
A `ModuleManifest` includes `module_id`, type/model version, fidelity, input/output ports, resource needs, event vocab, accepted time semantics, replay support and safe advancement capability.

**Critical purity contract:** `propose()` must not modify committed module/shared state and must be deterministic given snapshot, module checkpoint, seed and horizon. Internal temporary calculations are discarded unless committed. If exact event-bounded advancement is unsupported, integration must STOP rather than stamp an independent line step with a fabricated common timestamp.

Module owns detail of how a step executes; Coordinator validates only cross-module events/availability/authority. Standalone runs use explicitly configured synthetic feeds; integrated runs use only declared external ports and shared authorities.

## 4. G1A-03 Factory future-event scheduler / concurrency
- Base reused concept: `src/virtual_factory/discrete/scheduler.py` stable heap by time, priority, sequence, deterministic single clock.
- Candidate tie order: `(time_tick, phase_priority, stable_module_id, module_local_sequence, event_id)`; event IDs must remain stable, no random thread completion order. Priority policy fixed in schema.
- The reference algorithm executes **serially** and provides event-trace oracle. Parallel module proposal may be enabled later only if it yields byte-equivalent canonical commit trace.
- Proposal/validation/commit: at each safe horizon snapshot all prerequisite material/resources; collect proposals; select sorted next events; stage resource/material transactions; fail atomically on invalid edges; write committed event and genealogy to one transaction/outbox; deliver commit receipt to module.
- `advance_to` may only advance through complete safe-event boundaries. Zero-time cycles are bounded by per-tick event budget and causality graph checks; runaway events fail with structured evidence.
- Transfer latency is simulated (not transport-network wall-clock). Cross-module causality requires `input_received_at ≤ operation_start_at`; release/quality must be effective as-of reservation.
- Fault handling: module throw/timeout leads to deterministic FAILED or stop at safe checkpoint; partial commit cannot be published as success. Do not silently retry non-idempotent operations.

## 5. G1A-04 MaterialFlowLedger & physical flow contract
Candidate aggregate entities:
| Entity | Mandatory semantic identity |
|---|---|
| MaterialUnit | globally unique within `(factory_run_id, generation)`; `material_class`; source lot/WO/route |
| MaterialLot/Batch | batch identity, UOM/quantity, recipe/spec revision, individual unit linkage when expanded |
| Buffer | physical/logical location, capacity, allowed material types, occupancy version, input policy |
| Transfer | transfer ID, producer/consumer port, reservation/ship/receive timestamps, qty, loss/reject reason |
| Reservation | owner operation, item/lot and exact quantity, quality eligibility snapshot/version, expiration in sim-time |
| MaterialTransaction | idempotency key, ordered legs, BOM conversion, scrap/yield, causation event IDs, per-type balancing |
| GenealogyEdge | immutable input parent(s) → output child, transformation id, valid source event |

Allowed basic flow `PRODUCED → AVAILABLE → RESERVED → [IN_TRANSIT → RECEIVED] → CONSUMED`, with controlled branches `HOLD`, `REJECT`, `RETURN`, `REWORK`, `SCRAP`. **These are not a single enum:** material location/ownership, reservation and quality eligibility are independent state dimensions. For example, a WIP may remain physically in ASSY buffer while under Quality Hold and not consumable.

Material invariants:
1. `stock + reserved + in_transit + consumed + scrap` reconciles via explicit per-type transaction legs, BOM and declared yield/conversion; never sum physically different material classes 1:1.
2. `reserved_qty ≤ available_eligible_qty` under version-checked atomic reservation; no negative quantities or double reservation/consumption.
3. Parent WIP cannot be created by a message alone. `MaterialProduced` must result from an authoritative committed operation or explicit seed fixture with provenance.
4. N-input join is **all-or-nothing**. For AP04, exactly one eligible SSO2 parent and one eligible RSO2 parent must be reserved/consumed with no clone. A Motor child only becomes AVAILABLE on committed successful join completion; genealogy edges exist in same transaction.
5. `TransferPort` validates MaterialType, unit conversion, capacity/queue, destination, qualified status and simulated transport time. Lost/duplicated/delayed acknowledgments cannot multiply inventory; accept idempotent replay.
6. Operation processing contract declares explicit `input_consumption_point` (`START | COMPLETION`) and `output_production_point`; an accepted START may consume parents into WIP in process, but must not promise final child before completion. Exceptions preserve actual consumed units and rework/hold outcomes.
7. Equipment downtime, Material Hold and Quality Hold are distinct events; only contracted equipment unavailability counts as machine downtime.

### AP04 causal sequence
```text
SSO2 produces qualified parent A  ─┐
                                    ├─ transfer/receive ─ eligible buffer
RSO2 produces qualified parent B ──┘
→ AP04 requests reservation for A and B
→ Coordinator grants both or none (competing lines deterministic)
→ AP04 operation START: selected input consumption policy applied
→ AP04 operation COMPLETE: Motor child produced + A/B genealogy committed
→ downstream AP06 electrical/other test attempts, AP11 final record, Finished
```
`WAITING_FOR_MATERIAL` is operational waiting state, **not a fault or automatically a quality hold**. In integrated mode local backup feeds are forbidden even if timeout occurs.

## 6. G1A-05 ASSY ExternalInputAdapter
Existing `AssyDemoComposition` owns six independent contexts; legacy `AssyLineRuntime` already runs AP04 join, AP06/08 evidence and AP11; `demo_composition.py` seeds 7 SSO2 and 7 RSO2 WIPs per subline, `ContinuousFeedPolicy` replenishes, and `AssyDemoContext.step_context()` may produce RSO2 on demand. This makes whole-factory causality false without an explicit mode change.

Adapter (candidate) `AssyExternalInputPort`:
- `STANDALONE`: keep original default seed/replenish and original `tipa-assy-demo-v1.1` C4 wire format.
- `INTEGRATED`: disable **all** local produce/seed/replenish paths before initialization. Bind SSO2 to pre-ASSY intake and RSO2 to AP04 join only through Ledger-issued receipt/reservation and exact original parent IDs; no quantity=1 inferred from motor number.
- One `factory_run_id` with scoped subline `run_id` and stable mapping to physical AA10 lines (mapping explicit, not guessed). Six lines can propose independently but commit through same Factory clock.
- No rewriting AP03, AP04, AP06, AP08, AP11 logic/quality history; map legacy float internal time by checked adapter; stop if no safe event-time advance seam exists.
- First PM gate #126 is read-only proof and code callgraph. Follow-on production code change needs bounded separate issue and SA acceptance.

## 7. G1A-06 Event ledger, genealogy, replay and outbox
Candidate event envelope fields: `schema_version`, `factory_run_id`, `generation`, `event_id`, `module_id`, `event_type`, `simulation_tick_us`, `occurred_at_utc`, `source_event_id`, `causation_id`, `correlation_id`, `operation_execution_id`, `wip_id/lot_id`, `equipment_id`, `source_provenance`, `definition_digest`, `payload`.

Store raw observations and evaluations as different events; retest/reinspect append immutable attempts with distinct attempt IDs, never mutate original records. Commit module state, material legs, genealogy and event/outbox cursor atomically, or use proven equivalent with crash/replay test. External publish is at-least-once; consumer idempotency key includes `source_system+source_event_id+destination+contract_version`; never assume exactly-once broker transport.

Checkpoints must include event sequence, ledger state and version, committed module checkpoints, pending scheduled events and outbox cursor. Restoring a checkpoint in the same run cannot duplicate material, messages or genealogy. Reset creates new run generation.

## 8. G1A-07 frozen test oracles needed before PM G2
| ID | Deterministic oracle / failure |
|---|---|
| T01 | 2 independent producer modules + 1 consumer, single factory timeline and stable event digest |
| T02 | competing ASSY-SL01 vs ASSY-SL02 for one Rotor WIP, exactly one reservation/consumption |
| T03 | absent/ineligible SSO2 or RSO2 parent blocks AP04; 0 phantom WIP |
| T04 | same-time tie, shuffled module registration, late/past event, bounded zero-time loop |
| T05 | transit latency/buffer capacity; cannot consume before Received |
| T06 | crash/replay at RESERVED, IN_TRANSIT, JOIN committed; no duplicate outputs |
| T07 | one upstream Shaft outage causally reduces RSO2 supply, ASSY throughput |
| T08 | shift C 22–06 event-time local conversion, production day 06–06 |
| T09 | NG observation vs effective hold and actual downtime separated |
| T10 | untouched legacy ASSY standalone + Bottled Water CI/regression exact-head |

G2A-01 (#127) covers clock/modules/event ledger only, after G1A schema freeze; G2A-02 (#128) covers material ledger with atomic join after #127 acceptance. G3-A external input is separate, after #126 feasibility evidence and G2 ledger gate.

## 9. Issue-to-gate and unresolved decisions
- #126 must identify exact ASSY clock-advance seam and all internal WIP replenish paths. If no safe seam, return STOPPED / scoped design escalation; do not assume adapter works.
- #129 verifies C1–C4 allowlist/mappings and hold source ownership.
- Pending Design Lock choices: typed schemas and canonical serialization/digest; journal persistence/snapshot boundary; reservation expiration and input consumption per operation type; real vs synthetic quality authority; G1B identity crosswalk and device calibration provenance; exact fixture expected event traces.
- All production code changes forbidden until SA supplies testable machine-readable schema, accepted fixtures and exact PM task contract.

**No production implementation, deployment, performance proof or as-built TIPA certification is claimed.**
