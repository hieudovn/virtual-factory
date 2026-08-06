# Correction Mapping — SA Findings → Corrected Files

**Date:** 2026-08-05  
**Maps:** SA Review F-001 through F-017 → Corrected v2 files

| SA Finding | Description | Correction ID | Corrected File | Section |
|------------|-------------|---------------|----------------|---------|
| F-001 | M2-S01 requires dispatch without dispatcher | C-001, C-014 | `15-prompt-vf-dm-m2-s01-v2.md` | All |
| F-001 | M2-S01 requires dispatch without dispatcher | C-001, C-014 | `04-...-architecture-v2.md` | §1, §3 |
| F-002 | Runtime state and assembly state conflated | C-002 | `04-...-architecture-v2.md` | §2 |
| F-002 | Runtime state and assembly state conflated | C-002 | `06-...-state-contracts-v2.md` | §4 |
| F-003 | Auto pacing incorrectly in engine | C-003 | `04-...-architecture-v2.md` | §3, §4 |
| F-003 | Auto pacing incorrectly in engine | C-003 | `05-...-control-modes-v2.md` | §8 |
| F-004 | Handler exposes scheduler twice | C-004 | `06-...-state-contracts-v2.md` | §1, §2, §4, §6 |
| F-005 | Run status and execution mode conflated | C-005 | `05-...-control-modes-v2.md` | §1, §2, §3 |
| F-006 | Hybrid injection uses epsilon | C-006 | `05-...-control-modes-v2.md` | §7 |
| F-007 | Topology contains behavior params | C-007 | `07-...-contracts-v2.md` | §1, §2, §3, §4 |
| F-008 | Routing conditions are unsafe strings | C-008 (conditions) | `07-...-contracts-v2.md` | §5 |
| F-009 | Layout edges cannot map route state | C-009 (bindings) | `07-...-contracts-v2.md` | §6 |
| F-010 | Shared UI extraction contradictory | C-008 (UI protection) | `09-...-api-plan-v2.md` | §2, §6 |
| F-011 | Service ownership conflicts with run limits | C-009 | `09-...-api-plan-v2.md` | §1 |
| F-012 | Snapshot/command contracts incomplete | C-010, C-011 | `08-...-snapshot-command-v2.md` | §1–§5 |
| F-013 | REST and WS both write commands | C-011 (transport) | `08-...-snapshot-command-v2.md` | §6, §7 |
| F-014 | Full snapshot needs adaptive publication | C-010 (adaptive) | `08-...-snapshot-command-v2.md` | §4 |
| F-015 | Performance thresholds weak/contradictory | C-012 | `10-...-performance-strategy-v2.md` | §1, §2 |
| F-016 | M2 drops approved safety slices | C-013 | `11-...-roadmap-v2.md` | M2 section |
| F-016 | M2 drops approved safety slices | C-013 | `14-...-slice-matrix-v2.md` | M2 section |
| F-017 | Prompt M2-S01 not executable | C-014 | `15-prompt-vf-dm-m2-s01-v2.md` | All |

---

## File Inventory

| v2 File | Replaces |
|---------|----------|
| `04-end-to-end-runtime-visualization-architecture-v2.md` | `04-...-architecture.md` |
| `05-run-lifecycle-and-control-modes-v2.md` | `05-...-control-modes.md` |
| `06-event-dispatch-and-state-contracts-v2.md` | `06-...-state-contracts.md` |
| `07-topology-routing-layout-contracts-v2.md` | `07-...-contracts.md` |
| `08-visualization-snapshot-and-command-contracts-v2.md` | `08-...-snapshot-command.md` |
| `09-api-websocket-security-and-audit-plan-v2.md` | `09-...-api-plan.md` |
| `10-test-ci-and-performance-strategy-v2.md` | `10-...-performance-strategy.md` |
| `11-updated-vf-dm-roadmap-v2.md` | `11-...-roadmap.md` |
| `12-decision-register-v2.md` | `12-...-register.md` |
| `13-risk-register-v2.md` | `13-...-register.md` |
| `14-implementation-slice-matrix-v2.md` | `14-...-matrix.md` |
| `15-prompt-vf-dm-m2-s01-v2.md` | `15-...-m2-s01.md` |
| `16-executive-summary-v2.md` | `16-...-summary.md` |
| `correction-mapping.md` | (new) |

---

## Unchanged Files (v1 stands)

- `01-current-repo-and-reuse-assessment.md` — no findings against it
- `02-product-scope-and-tipa-readiness.md` — no findings against it
- `03-shared-ui-foundation-and-dm-visualization-strategy.md` — superseded by 04-v2 + 09-v2
