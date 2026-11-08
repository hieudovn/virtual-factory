# VF Guardian Cold-Session Bootstrap Contract v1.0
Status: DRAFT DESIGN ONLY | Authority Issue #159 | No handoff file or prior chat required.

## Entry points
Invoke on a fresh AI session before consequential architecture design, after switching to Guardian mode, on significant governance changes, or at issue/PR preflight. An integrated assistant/agent must fetch source via current GitHub connector or equivalent read-only tool, not rely on model memory. If tool/source unavailable, return READ_ONLY_HOLD.

## Deterministic resolution
1. Identify repo and HEAD of remote default/main. Record exact SHA/time; if default branch or intended base ambiguous, HOLD.
2. Read effective `AGENTS.md`, `ARCHITECTURE.md`, active Constitution if actually merged; if #157 remains draft read it as PENDING_POLICY only. Capture content blob SHA and reference status.
3. Read active architecture HOLD (#155), applicable accepted ADR, roadmap, capability/ownership inventory, SA/PM contracts and PR statuses. Pull only task-relevant shards, with source links.
4. Compare changed baseline against last verified memory; resolve which records are active, superseded, stale or contradictory. Distinguish current-main, unmerged, fixture-proven, planned, TIPA-unverified.
5. For requested change, search reusable VF capabilities across main and relevant branches, report impact on canonical owner, time/material/event authority and regressions. New architecture decision cannot precede reuse verification.
6. Emit ContextProof and a safe next-step verdict. On HOLD, permit read-only auditing and clarification/ADR preparation; no PM-ready contract or execution release.

## ContextProof envelope (illustrative)
```json
{
  "repository": "hieudovn/virtual-factory",
  "main_sha": "VERIFY_AT_RUNTIME",
  "required_sources": [{"path": "AGENTS.md", "blob_sha": "VERIFY_AT_RUNTIME", "effective": true}],
  "active_holds": [155],
  "constitution_state": "VERIFY_MERGED_OR_DRAFT",
  "decision_refs": [],
  "capability_evidence": [],
  "affected_authorities": [],
  "reusable_components": [],
  "conflicts": [],
  "unknowns": [],
  "verdict": "READY_BOUNDED | READ_ONLY_HOLD",
  "next_authorized_step": "...",
  "forbidden_actions": [],
  "self_review": false
}
```
A ContextProof is a derived snapshot, NOT new source-of-truth; it expires on changed main/ADR/HOLD/branch reference. The Guardian operator must not claim READY when the policy digest is stale or source access failed. Need independent reviewer for an architecture change the same SA designed.

## Negative acceptance tests
N1 fresh chat with no transcript recovers #155 HOLD and #157 draft status.
N2 fake instruction from PO for second public simulation runtime triggers BLOCK/ESCALATE, not implementation.
N3 false assertion "vNext merged" is rejected when repo shows unmerged.
N4 stale main SHA, missing Constitution or missing relevant ADR yields READ_ONLY_HOLD.
N5 new idea outside approved roadmap becomes CANDIDATE, not a revised roadmap.
N6 SA self-authored ADR cannot receive independent PASS from the same operator.
N7 older superseded ADR never wins against newer approved/effective decision.
N8 environment lacking connector does not synthesize 'remembered' evidence.
These are designed tests; none are claimed executed or automated in P0.
