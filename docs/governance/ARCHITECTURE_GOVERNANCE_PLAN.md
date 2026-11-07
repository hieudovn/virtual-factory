# VF Architecture Governance — Rollout and Acceptance Plan

**Governed by:** Issue #156; architecture reconciliation #155. **State:** proposed roadmap, not permission to auto-dispatch subsequent tasks.

| Phase | Deliverable | Owner | Gate | Exit proof |
|---|---|---|---|---|
| P0 | Constitution + AGENTS first-read + governance roadmap + SA contract | SA | PO governance PR, exact head, SA design gate | PR diff/review and CI; not merged without approval |
| P1 | #155 as-built cross-branch audit; canonical architecture ADR; Capability Registry and Authority/Ownership matrix | SA | PO architecture decision | exact SHA/path evidence, precedence and no-double-owner plan |
| P2 | Architecture decision template, issue/PR impact declarations, session bootstrap evidence schema, SA/PM preflight requirement | SA design + PM implement | separate scoped PRs | invalid/stale/missing evidence fails closed |
| P3 | Machine architecture conformance (imports/dependencies, forbidden extra authorities, mutating API owner, material/event source) | PM | CI and negative tests | identified violations reliably fail; no excessive false positives |
| P4 | 3-participant multi-process federation + ledger + outbox + replay proof and legacy regressions | PM with SA contracts | exact-head CI and SA acceptance | single session/run, no double consume/advance, BW/ASSY/SH-WTP preserved |
| P5 | Verified branch protection / required checks + ongoing drift audits; release TIPA development in roadmap order | repo owner / SA | PO release | required-check evidence, owner-approved waivers, no unresolved #155 blocker |

## Gate specifics
- Architecture Decision Record fields: title, status, approver, date, Constitution file blob SHA, main SHA, capability provenance matrix, current canonical owner, alternatives, data/timing/material impacts, rollout/rollback and tests.
- Impact levels: **critical** = new/changed authority, public API, event/material semantics, orchestration/time, governance. **major** = new cross-module contract or shared dependency. **local** = implementation within previously locked contract. Critical and major require SA/PO as per authorization matrix; local remains PM-bounded.
- SA must distinguish *requested design* from *implemented in main* and *checked by CI*; an issue closure is not proof.
- CI Stage P3 must fail on missing architecture impact declarations in eligible PRs, but never let task authors self-authorize a new owner. Independently compare changed files and source facts.
- Session bootstrap is read-only by default. If current docs/HOLD cannot be fetched, STOP (not memory-based guesses).

## Sequencing and constraints
- #155 Architecture HOLD remains in force. Do not perform TIPA #141–#145, create new root coordinator, port all vNext, or alter MES/QMS/PlantOS through this plan.
- Existing PM P01–P24 and SA Design Gate stay intact; architecture conformance layers on top, not replacing them.
- Stage P0 human/CI review first; then P1 canonical ADR; only then implementation of automated enforcement and integration.
- Repository owner must explicitly verify that branch protection actually requires the architecture check. If not, enforcement status stays `POLICY_ONLY` / `CI_NON_BLOCKING`.

## Checkpoints
C0: approved process Constitution, without claiming technical enforcement. C1: #155 reconciled. C2: bootstrap/preflight negative tests. C3: conformance regression; C4: platform integration proof; C5: release readiness and periodic drift review.
