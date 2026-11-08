# VF Context Resolver — Bounded Design Contract v1
**Status:** DESIGN DRAFT, issue #161. This is not a running plugin, daemon, autonomous agent, CI job, or branch protection.

## Inputs
Repository locator, requested decision/task scope, current remote head, governance policy paths, strategic seed index, decision issue refs, active PR/branch refs, and relevant capability sources. Do not accept manual handoff, conversational memory, or prior summary as required authoritative input.

## Resolution and precedence
1. Fetch `main` SHA and required file blob SHAs from GitHub at retrieval time. Resolve whether PR #157 Constitution is merged before treating it as active.
2. Resolve active #155 HOLD and pertinent approved ADRs, roadmap, contracts, issue/PR merge state and independent reviewer state. On unavailable authority, return READ_ONLY_HOLD.
3. Parse strategic seed only as a cache/index; every critical assertion must link and verify actual policy/ADR/source. Never infer from a missing repository artifact that the component is absent.
4. Build an explicit authority matrix (single public run/session, lifecycle, clock, material, event projection, side-effectful API), identify current-main vs unmerged vs fixture-only vs proposed.
5. Classify proposed PO/SA/PM change as LOCAL, MAJOR, CRITICAL; detect conflict with approved direction, roadmap, governance and existing capabilities. For unverified canonical run ownership (#155), return HOLD.
6. Produce a machine-consumable ContextProof and a human-readable 10-line brief. A brief summarizes resolved context, not a 'handoff' written by previous session.

## ContextProof required fields
`repository, main_sha, fetched_at, source_hashes, constitution_status, active_holds, accepted_decisions, pending_decisions, affected_components, capability_provenance, ownership_state, missing_evidence, contradictions, reviewer_independence, authorized_next_step, forbidden_actions, status`.
Allowed final status: READY_BOUNDED or READ_ONLY_HOLD. On stale SHA, missing policy, contradictory ADR, blocked dependency, or self-approval, fail closed.

## Acceptance fixtures — specify now, implement later
| Test | Input fault | Expected |
| --- | --- | --- |
| CS-01 | Brand-new AI session, zero chat history | Finds repo, #155 HOLD, #157/#160 proposal state, and verified next action |
| CS-02 | PO proposes second independently advancing RuntimeSession | BLOCK_CONFLICT + ESCALATE_PO |
| CS-03 | SA proposes replacing G4 without reuse audit | HOLD_MISSING_EVIDENCE |
| CS-04 | PM proposes feature branch claimed merged | READ_ONLY_HOLD until actual main proof |
| CS-05 | stale main SHA | READ_ONLY_HOLD |
| CS-06 | missing Constitution or inaccessible GitHub | READ_ONLY_HOLD, no hallucinated policy |
| CS-07 | designer reviews own architecture | SELF_REVIEW_NON_INDEPENDENT; no PASS |
| CS-08 | outdated ADR conflicts newer approved ADR | use effective version or HOLD if legitimacy unresolved |
| CS-09 | new roadmap idea lacking explicit PO approval | CANDIDATE, roadmap unchanged |
| CS-10 | memory seed claims #155 resolved but issue remains HOLD | treat seed stale, HOLD and repair proposal |
All expected outputs remain test **specifications**, not executed test results.

## Future implementation gate
Machine resolver and CI integration require a separate PM issue/contract, exact-head tests (including CS-01..10), verified required GitHub checks, no silent code architecture changes, and Independent Guardian review. No permanent in-chat agent runtime is assumed.
