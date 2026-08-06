# VF-DM M2 Planning Baseline

**Date:** 2026-08-06  
**Branch:** `docs/vf-dm-m2-planning-baseline` (docs-only)

---

## Document Precedence

1. **`final/`** — Authoritative v3 documents. These represent the SA-approved architecture after C01 and C02 corrections. Use for implementation reference.
2. **`archive/v2/`** — Intermediate v2 corrections (C01). Superseded by v3. Historical reference only.
3. **`archive/original/`** — Original v1 planning documents. Historical reference only.

---

## Structure

```
final/
  04-architecture-v3.md       End-to-end architecture (final)
  05-lifecycle-v3.md          Run lifecycle + control modes (final)
  06-dispatch-v3.md           Event dispatch + state contracts (final)
  07-contracts-v3.md          Topology/routing/layout (final)
  08-snapshot-v3.md           Snapshot + command contracts (final)
  09-api-v3.md                API/WS/security/audit (final)
  10-performance-v3.md        Test/CI/performance (final)
  11-roadmap-v3.md            M2-M7 roadmap (final)
  12-decisions-v3.md          29 decisions resolved (final)
  13-risks-v3.md              Risk register (final)
  14-slice-matrix-v3.md       Slice implementation matrix (final)
  15-m2-s01-prompt-v3.md      M2-S01 prompt (executed, historical)
  16-summary-v3.md            Executive summary (final)
  c02-correction-mapping.md   V2→V3 finding map

archive/original/             v1 documents (superseded)
archive/v2/                   v2 documents (C01 corrections, superseded)
```

---

## Status

M2-S00 architecture gate: **CLOSED**  
M2-S01 implementation: **COMPLETE** (merged to main)  
M2-S02 implementation: **IN PROGRESS**  
All test counts in v3 documents are historical. See `M2-STATUS.md` for current state.

## Historical Note

Test counts in planning documents (315 baseline, 341 after M2-S01) were accurate at time of writing. Current `main` has 356 tests after M2-S01 corrections. These counts are preserved as historical record.
