# 12 — Decision Register

**Date:** 2026-08-05

| ID | Question | Options | PM Recommendation | Rationale | SA Decision Required | Target Slice |
|----|----------|---------|-------------------|-----------|---------------------|-------------|
| D-001 | SVG MVP vs Canvas/WebGL? | a) SVG, b) Canvas, c) SVG+Canvas overlay | **a) SVG** | Small model, rich labels, existing experience. Thresholds for migration defined. | Confirm | M2-S00 |
| D-002 | Full snapshot vs delta? | a) Full only, b) Snapshot+delta | **a) Full only for MVP** | Simple, stateless client. Delta at M6 when snapshot >200KB. | Confirm | M2-S00 |
| D-003 | Separate FastAPI process vs shared? | a) Shared process, b) Separate process | **a) Shared process** | Existing deployment, simpler ops. Extract when DM endpoints >20. | Confirm | M2-S00 |
| D-004 | Step-one-event vs step-to-business-event? | a) One event, b) Next business event | **a) One event** | Scheduler should not know domain semantics. `step_to_event_type` can be added later. | Confirm | M2-S00 |
| D-005 | Live injection vs pause-then-inject? | a) Live, b) Pause-then-inject | **a) Live injection** | Commands become scheduled events. Deterministic. No mode switching needed. | Confirm | M2-S00 |
| D-006 | Handler mutation model? | a) Direct state mutation, b) Immutable state+replace | **a) Direct mutation** | Handlers are trusted code. Immutable state adds complexity without benefit for MVP. | Confirm | M2-S00 |
| D-007 | In-memory vs persistence for state? | a) In-memory only, b) File/SQLite | **a) In-memory** | MVP scope. Persistence at M6. | Confirm | M2-S00 |
| D-008 | TIPA layout location? | a) JS file, b) YAML config, c) Server endpoint | **a) JS + c) Server** | Fixed layout in JS for MVP. Server serves topology/routing as YAML. Layout file loaded by renderer. | Confirm | M2-S00 |
| D-009 | Topology/routing/layout contract location? | a) Python dataclasses, b) YAML files, c) Both | **c) Both** | Python models for validation + YAML for authoring. | Confirm | M2-S00 |
| D-010 | Command concurrency strategy? | a) Sequential, b) Concurrent with locking | **a) Sequential** | Single-threaded asyncio. Commands queued FIFO. | Confirm | M2-S00 |
| D-011 | Initial authentication mode? | a) None (demo), b) API key | **a) None** with `--unsafe-demo` flag. M6: API key. | MVP speed. Flag makes risk explicit. | Confirm | M2-S00 |
| D-012 | Operator/resource modeling depth? | a) Anonymous role, b) Named operator with skills | **a) Anonymous role** | "Operator available/unavailable" sufficient for flow simulation. Named operators at M6. | Confirm | M2-S00 |
| D-013 | First demo KPI set? | Throughput, cycle time, WIP, quality yield, rework rate, downtime | **All six** | Standard lean manufacturing metrics. Easy to compute from state. | Confirm | M2-S00 |
| D-014 | CI introduction timing? | a) M2-S01, b) M3 | **a) M2-S01** | CI from first engine code prevents regression accumulation. | Confirm | M2-S00 |
| D-015 | Shared UI extraction scope? | a) Extract all at once, b) Extract incrementally | **b) Incremental** | Extract icons+widgets+CSS first. Defer viewport extraction until DM renderer exists. | Confirm | M4-S01 |
| D-016 | Continuous renderer preservation? | a) Wrap with adapter, b) Leave unchanged, c) Extract shared core | **b) Leave unchanged + c) Extract shared utilities** | Minimal risk. Continuous renderer unchanged. Shared utilities extracted to new files. | Confirm | M4-S01 |
| D-017 | Vanilla JS vs framework? | a) Vanilla JS, b) Preact/Vue/Svelte | **a) Vanilla JS** for MVP. Re-evaluate at M6 thresholds. | Existing codebase is vanilla. Framework adds build chain complexity without clear MVP benefit. | Confirm | M2-S00 |
| D-018 | DM branch strategy? | a) Feature branches per slice, b) Long-lived DM branch | **a) Feature branches** | Per-slice branches → PR → SA review → merge. Clean rollback per slice. | Confirm | M2-S00 |
