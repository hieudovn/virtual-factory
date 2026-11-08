# VF Strategic Memory — Data and Lifecycle Contract v1.0
Status: DRAFT DESIGN ONLY | Authority #159 | Source of truth: versioned repo plus immutable issue/PR/commit links.
Memory is NOT a long transcript or implicit ChatGPT memory; it is a repository-backed evidence index. A memory record never supersedes a Constitution or ADR.

## Layered authoritative model
L0 POLICY: effective Constitution, AGENTS, governing authority, approval and SHA.
L1 STRATEGY: product mission, scope, domain boundaries, non-negotiable invariants, explicitly rejected alternatives, design goals.
L2 DECISIONS: architecture ADR and design lock, supersession lineage, ownership/dependencies, approved rationale.
L3 LIVE_STATE_POINTERS: current roadmap, active HOLD, PR, branch, CI, current-main SHA, current next safe action. L3 is ephemeral derived data; always refetch.
L4 EVIDENCE: exact commit/path/blob, issue/PR, verification date, fixture-vs-main-vs-deployment distinction.

## Required machine-readable record fields (future implementation)
```yaml
id: VF-STRAT-0001
type: invariant | goal | architecture_decision | dependency | constraint | roadmap_choice
statement: "..."
status: CANDIDATE | PROPOSED | APPROVED | EFFECTIVE | SUPERSEDED | REJECTED | HOLD
authority: {role: PO | SA, issue: 0, approver_ref: "..."}
scope: {components: [], projects: [virtual-factory]}
provenance:
  - {repo: hieudovn/virtual-factory, ref: "...", path: "...", blob_sha: "...", evidence_kind: verified_source}
created_at: "YYYY-MM-DD"
last_verified_at: "YYYY-MM-DD"
valid_from: null
supersedes: []
dependencies: []
verification: VERIFIED | PARTIAL | UNVERIFIED | CONTRADICTED
merge_state: IMPLEMENTED_AND_MERGED | IMPLEMENTED_UNMERGED | PROVEN_IN_FIXTURE | PENDING_INTEGRATION | PENDING_TIPA | NOT_APPLICABLE
```
An absent value is null/UNKNOWN, not guessed. Every APPROVED/EFFECTIVE state must include an authority reference and effective commit or explicitly scoped approval evidence. Do not make open issue text by itself a constitutional grant.

## Initial memory seed: evidence-index, not fictional baseline
- Mission and boundaries: `ARCHITECTURE.md` on main, e.g. config-driven plant graph, typed ports, measurable sensor outputs vs hidden truth. Source must be checked per bootstrap.
- Governance: `AGENTS.md` main; Constitution #156/PR #157 is DRAFT, NOT_EFFECTIVE until merged.
- Architectural incident: #155 HOLD: vNext Workspace/RuntimeSession/G4 federation code exists in unmerged technical lineage; G2A coordinator/material journal in main has different ownership semantics. Preferred selective reuse is a proposed direction, not merged canonical adoption.
- Integration: TIPA #141–#145 blocked by #155. No unverified physical routing facts can be elevated to source truth.
No source of truth may be synthesized from a stale session summary. Index files should be compact and topic-sharded; content can be resolved by references to exact Git objects. Secrets/credentials, private personal data and raw discussions never belong in strategic memory.

## Update algorithm
(1) detect meaningful event (approved ADR, merge, roadmap change, newly verified capability, revoked decision);
(2) fetch current source and confirm authority;
(3) write proposed delta with before/after, impacted records, supersession, risk;
(4) independent review when own changes, PO approval where required;
(5) merge governed PR, then mark EFFECTIVE with actual revision;
(6) invalidate stale L3 caches by revision and never delete history.
A conflict yields HOLD records with both provenance lines; no last-writer-wins. Compaction must preserve references, rejection rationale, and supersession chain.

## Cross-project
Only consume externally approved and version-pinned interfaces; store a dependency pointer, never copy another repo's normative decisions as local authority. An MES/QMS/PlantOS change requires each project's own authority review.
