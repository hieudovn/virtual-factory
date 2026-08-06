# 13-v2 — Risk Register (Corrected)

**Date:** 2026-08-05  
**Replaces:** `13-risk-register.md`  

Key changes from v1: Updated risks R05, R09, R10, R12, R17, R19, R20 to reflect corrected architecture. Added R23–R25.

| # | Risk | L | I | Mitigation | Gate |
|---|------|---|---|------------|------|
| R01 | TIPA assumptions hardcoded into engine | M | H | Engine is domain-neutral. Separate topology/process/scenario contracts. | M3 |
| R02 | UI becomes source of truth | M | C | Command model enforced. Snapshot is read-only projection. | M4 |
| R03 | Routing and layout conflated | M | H | Five separate contracts. Validation rejects conflation. | M3 |
| R04 | Runtime/UI coupling | M | H | Snapshot projection only data path. Immutable snapshot. | M2 |
| R05 | Event storms | L | H | Scheduler cap, max events/sec in controller, loop detection in routing conditions. | M3 |
| R06 | Non-deterministic hybrid | M | H | Safe-point application with server sequence. Command log for replay. | M2 |
| R07 | Stale WebSocket clients | M | M | Resync protocol: client sends last message_sequence. | M4 |
| R08 | Command races | L | M | Sequential FIFO per run. Server-assigned command_sequence. | M2 |
| R09 | Snapshot bloat | L | M | Target <100KB. Delta at M6 if exceeded. Paginate entity lists. | M5 |
| R10 | Animation desync | M | M | CSS transition only. Simulation time authoritative. | M4 |
| R11 | Unbounded event trace | M | M | 1M hard limit. 1K ring buffer for WS. | M2 |
| R12 | MES/PIM identity mismatch | L | H | Separate internal/external IDs. Mapping layer at M7. | M7 |
| R13 | Incomplete TIPA info | H | M | All values marked PLACEHOLDER. Readiness matrix. | M2-S00 |
| R14 | Fake-data becomes production | M | H | Fake provider in demo/ only. Contract test validates equivalence. | M4-S00 |
| R15 | No auth exploited | L | C | --unsafe-demo flag. API key at M6. | M6 |
| R16 | DM breaks continuous | M | C | Separate packages. CI runs both suites. Characterization tests. | All |
| R17 | DM UI contaminates continuous | L | H | Separate /discrete page. No renames of continuous files. Separate globals. | M4 |
| R18 | Premature framework rewrite | L | M | Thresholds defined (D-017). ADR required. | M6 |
| R19 | SVG jank from full rebuild | H | M | Keyed incremental updates. No replaceChildren(). | M4 |
| R20 | Extraction without tests | M | H | Characterization tests before extraction. Gate enforced. | M4-S01 |
| R21 | SignalValue reused as DM snapshot | L | H | Separate RuntimeSnapshot and DMVisualizationSnapshot. | M2 |
| R22 | Overengineering before demo | M | M | Strict slice boundaries. SA gate per slice. | All |
| R23 | Engine receives handler scheduler | — | — | **Resolved:** C-004 removes scheduler from handler contract. | M2-S01 |
| R24 | Routing conditions use eval() | — | — | **Resolved:** C-008 uses closed declarative vocabulary. | M3 |
| R25 | Continuous files renamed prematurely | — | — | **Resolved:** C-008 protects continuous files. | M4 |

L = Likelihood (L/M/H), I = Impact (L/M/H/Critical)
