# 13 — Risk Register

**Date:** 2026-08-05

| # | Risk | Likelihood | Impact | Early Signal | Mitigation | Owner | Gate |
|---|------|-----------|--------|-------------|------------|-------|------|
| R01 | TIPA assumptions hardcoded into engine | Medium | High | Engine references "AP01" or "TIPA" | Separate topology/routing from engine. Engine is generic. | PM | M3-S01 |
| R02 | UI becomes source of truth for simulation state | Medium | Critical | UI directly mutates state instead of sending commands | Command model enforced. No state mutation from UI layer. | PM | M4-S02 |
| R03 | Routing and layout conflated into one object | Medium | High | Visual edge defines execution path | Three separate contracts from day one. Validation rejects conflation. | PM | M3-S02 |
| R04 | Runtime/UI coupling through shared mutable state | Medium | High | UI reads engine internals directly | Snapshot projection is the only UI data path. Immutable snapshot. | PM | M2-S03 |
| R05 | Event storms (handler schedules 1000s of events) | Low | High | Run never reaches completion, UI freezes | Scheduler capacity cap (100K). Max events/sec in auto mode. Loop detection in routing. | PM | M3-S03 |
| R06 | Non-deterministic hybrid interventions | Medium | High | Same scenario produces different results | Commands become scheduled events with known simulation time. Audit trail records all. | PM | M2-S04 |
| R07 | Stale/disconnected WebSocket clients | Medium | Medium | Client shows old state after reconnect | Resync protocol: client sends last version, server sends full snapshot. | PM | M4-S03 |
| R08 | Command races in hybrid mode | Low | Medium | Two commands conflict on same target | Sequential command processing. FIFO queue per run. | PM | M2-S04 |
| R09 | Snapshot bloat (>200KB) | Low | Medium | Snapshot size grows with entity count | Cap visible entities. Paginate large lists. Delta at M6. | PM | M5 |
| R10 | Visual animation desync from simulation time | Medium | Medium | Token position disagrees with entity state | Animation is CSS transition only. Simulation time is authoritative. | PM | M4-S02 |
| R11 | Unbounded event trace memory | Medium | Medium | Memory grows linearly with run duration | Cap at 1M events per run. Circular buffer for event history. | PM | M2-S04 |
| R12 | Identity mismatch with MES/PIM | Low | High | External system IDs don't match internal entity IDs | Separate internal IDs from external references. Mapping layer at M7. | PM | M7 |
| R13 | Incomplete TIPA information leads to wrong domain model | High | Medium | Customer feedback contradicts implemented behavior | Mark all TIPA facts in readiness matrix. Placeholder values clearly labeled. | PM | M2-S00 |
| R14 | Fake-data prototype becomes production code | Medium | High | Fake provider imported in production path | Fake provider in `tests/` or `demo/` only. Contract test validates real vs fake output matches. | PM | M4-S00 |
| R15 | Lack of authentication exploited in production | Low | Critical | Unauthorized commands accepted | `--unsafe-demo` flag required. Document as demo-only. API key at M6. | PM | M6 |
| R16 | DM changes break continuous simulator | Medium | Critical | Continuous tests fail after DM merge | Separate packages. Characterization tests before extraction. CI runs both suites. | PM | All |
| R17 | DM branches contaminate continuous renderer | Medium | High | `editor.js` modified in DM branch | Separate directories. Code review gate. Continuous characterization tests. | PM | M4 |
| R18 | Premature frontend framework rewrite | Low | Medium | Proposal to adopt React/Vue before thresholds met | Thresholds defined (D-017). ADR required for any framework change. | SA | M6 |
| R19 | Full SVG rebuild causes visual jank | High | Medium | Flicker on every snapshot update | Keyed incremental updates from day one. No `replaceChildren()`. | PM | M4-S02 |
| R20 | Shared utility extraction without characterization tests | Medium | High | Extraction PR has no tests | Characterization tests required before any extraction. Gate in extraction sequence. | PM | M4-S01 |
| R21 | Reuse of `SignalValue` as DM snapshot contract | Low | High | DM snapshot inherits from SignalValue | Separate `VisualizationSnapshot` with DM-specific fields. No shared base class. | PM | M2-S03 |
| R22 | Overengineering before first demo | Medium | Medium | M2 scope expands beyond engine+dispatch | Strict slice boundaries. Deferred features list enforced. SA gate per slice. | PM | All |
