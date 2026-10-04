# DDAY-B6 — 01. Baseline and scope

## Baseline

| Field | Value |
|---|---|
| SA-closed B5 head | `449685a3c4c394b4e0654b720ff11f77205b4b48` |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Preflight | `PRECHECK PASSED` on the contract commit, clean tree |
| Live Issue #110 | unread (GitHub App 403 / GraphQL unresolved / public 404) |

Contract: `.ai-harness/tasks/DDAY-B6.json`, authored from B1 §7/§8/§10,
the B5 CLOSED authorization, and the explicit Lightweight Whole Factory
Overview update.

## What this slice did

- Workspace-local mapper from the existing factory snapshot to B1 MQTT JSON.
- In-memory PlantOS-compatible ingestion (current values, historian, events).
- Lightweight overview page over `GET /bottled-water-demo/factory`.
- BW-FP drill-down to the existing Filling & Packaging UI.

## What this slice did not do

- No second simulator or duplicate topology/state.
- No PlantOS-owned KPI calculation.
- No full HMI product.
- No PlantOS production-code edits.
- No generic `protocols/` or `telemetry/` edits (`git diff` vs `449685a` is empty).
- No Capper/Compressor helper edits.
- No B7 deployment. No merge.
