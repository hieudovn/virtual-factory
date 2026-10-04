# DDAY-B6-C01 — PlantOS ingestion/historian gap

## What was proven

- VF selected envelopes are versioned, fail-closed, and durable.
- `PlantosLocalIngestion` buffers current values / history / events as a VF
  adapter and unit-test aid.
- That adapter is **not** PlantOS ingestion and **not** a PlantOS historian.

## What was attempted

- Environment repos: only `github.com/hieudovn/virtual-factory`.
- `gh repo list hieudovn` does not include a PlantOS repository.
  Visible non-PlantOS repos: `NOVA-knowledge-hub`,
  `manufacturing-data-platform` (Avenue MDP), `testrepo`.
- No local PlantOS checkout or importable PlantOS test/runtime ingest
  interface exists in this workspace.
- WTP `POST /api/v1/measurements/ingest` was **not** used. It is a different
  plant and is not a PlantOS substitute.

## Exact minimal gap for SA authorization

Actual PlantOS ingestion and historian query cannot be proven from this
environment without one of the following:

1. Grant this agent read access to the current PlantOS repo and the exact
   Track A branch/SHA.
2. If that branch already accepts the B6 MQTT JSON envelope
   (`contract_version`, `workspace_id`, `plant_source_id`, `source_id`, UTC
   `timestamp`, unit/quality/provenance, selected dictionary keys) **without
   PlantOS production-code changes**, authorize a follow-up proof-only slice
   to ingest and query those samples.
3. If that branch cannot accept the envelope, authorize the exact minimal
   PlantOS adapter/ingest change. That change is **out of DDAY-B6-C01
   scope**.

Until SA authorizes (1) plus either (2) or (3):

- `plantos_ingestion_proven = false`
- `plantos_historian_proven = false`
- `requires_plantos_production_changes = UNKNOWN_UNTIL_REPO_ACCESS`

C01 stops the PlantOS-historian claim here. It does not edit PlantOS.
