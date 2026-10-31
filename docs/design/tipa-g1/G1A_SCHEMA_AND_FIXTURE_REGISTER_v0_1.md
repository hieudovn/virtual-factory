# G1A Machine-Readable Contract & Oracle Register v0.1

**Design state:** SA TECHNICAL DRAFT; proposed typed payloads only, *not* accepted external wire contracts. Design authority [#123](https://github.com/hieudovn/virtual-factory/issues/123), publication [#125](https://github.com/hieudovn/virtual-factory/issues/125), implementation task #127/#128 gated.

## Schema inventory
- `factory-run-v0.1.schema.json`: immutable Run identity, generation, definitions, deterministic seed/epoch, calendar, mode.
- `module-manifest-v0.1.schema.json`: module capabilities and typed material ports / declared fidelity.
- `factory-event-v0.1.schema.json`: committed append-only, run-scoped event envelope, separate simulation and outer transport time.
- `material-transaction-v0.1.schema.json`: atomic ledger transaction with many material legs and parent/child genealogy.
- `factory-scenario-fixture-v0.1.schema.json`: reusable test contract for expected events and negative/positive oracles.
- `fixtures/T01_TWO_PRODUCERS_JOIN.json`: healthy generic chain; **hypothesis**, not runtime output.
- `fixtures/T02_UPSTREAM_STARVATION.json`: missing Rotor blocks AP04, zero phantom feed; **hypothesis**, not runtime output.

**No schema here is C1/C2/C3/C4/C5 external contract.** Any projection must use G1B mapping approval; schemas deliberately forbid unknown top-level fields, require stable source-provenance and distinct run generation. Format validation is necessary but not sufficient for business-causal correctness.

## Invariants not captured by JSON Schema
1. Cross-document: module_id unique, port_id unique within module, all reference IDs and material_types registered; only one committed authority for each material inventory.
2. Chronology: tick_us monotonic, UTC time exactly run epoch + tick; stable same-timestamp ordering. Never alter historic events on reset/restore.
3. Reservation: serializable ledger version, eligible available qty and capacity; same WIP consumed no more than once; all-or-none multi-input commit; no negative stock.
4. Material accounting: per-material class and UOM, BOM conversions, yield/scrap explicit; no mixing BATCH and EA without explicit recipe.
5. Transfers: produce/source ownership → shipment → received acknowledgment → reserve/consume; a broker event does not make the inventory real.
6. Genealogy: output child linked to all committed parent WIPs; parent edges created atomically with output.
7. Operation boundary: consumptions at declared START or COMPLETION, not implicit to UI events; AP04 child only after successful operation COMPLETE.
8. Idempotency: identical transaction ID and digest repeat is no-op; conflicting payload with same key rejects; crash/replay cannot double publish or consume.
9. Module: propose purity, no mutation of shared committed state; same seed/manifest yields same canonical commit event trace under serial and parallel proposal schedulers.
10. Quality: observation != evaluation != effective hold != disposition != release. Material physically present but held is not eligible. Machine FAULT != product HOLD != material WAITING.
11. Legacy: standalone ASSY and Water Bottle unchanged; integrated ASSY must disable all local SSO2/RSO2 produce/replenish paths.
12. Provenance: static demo synthetic numbers only, no claim of actual TIPA cycle times, QA tolerances, physical layout, BOM.

## Negative and destructive test-oracle minimums
- duplicate/event_id conflict; same key/different payload; invalid unit or nonpositive qty; unknown material/port; wrong WIP source; unqualified/QC unknown input.
- two consumers concurrent reservation same Rotor; exactly one accepted, deterministic tie; no partial multi-parent join.
- transfer receive before ship/production; receive after expiration; buffer overflow; missing acknowledgment; retry after checkpoint and outage.
- event in past / zero-time loop; independent ASSY local clock drift; source time with timezone missing; Shift C at local midnight and 06:00 cutoff.
- replay after committed transaction, sender outbox restart, reset generation; compare canonical trace digests.

## Design Lock to implementation
**G1A-core design can be frozen by SA**, but code execution is blocked until precise reference fixtures are agreed with PM and #126 shows the ASSY integration seam. G2A-01 (#127) must not implement material engine in the first slice; G2A-02 (#128) requires transaction semantics acceptance. G1B/C consumer QMS authority remains cross-SA DRAFT. PM is forbidden to fill empty schema semantics with private guesses.

## Schema normalization choices requiring validation
- Numeric material quantity is permitted for units across EA/KG/L; runtime must enforce integer EA and deterministic decimal accounting policy. Float rounding cannot silently alter inventory.
- `definition_digest` in examples uses a placeholder all-zero SHA: it must be recomputed from canonical manifest/config before execution.
- JSON Schema refs are relative and can be checked with jsonschema Draft 2020-12 resolver; this document is not a Python API.
- These fixtures are **specification examples**. Exact event IDs, step durations, serialized byte-level oracle and lineage digest still need G1A fixture freeze; do not mark G2 READY until then.


## SA DD-01 contract clarification (2026-10-31)
Authoritative material quantities and buffer capacities in the draft JSON Schemas are now decimal strings, never binary float; semantic validator must check positive, UOM-specific precision and BOM conversions. SourceKind (SIMULATED/REPLAYED_SOURCE) is separate from DefinitionProvenance (PDF_EXPLICIT etc.); a synthetic event is SIMULATED even if its process model is sourced from the permit PDF. See [G1A Core DD-01](G1A_CORE_DETAILED_DESIGN_DECISION_DD01.md). The original T01/T02 fixtures are **non-executable specification examples** with placeholder zero digest. Contract QA is an explicit gate prior to PM G2A development.
