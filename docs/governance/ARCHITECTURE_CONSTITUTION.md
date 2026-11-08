# Virtual Factory — Architecture Constitution

**Status:** PROPOSED IN GOVERNANCE PR #156 (not active until approved/merged)  
**Authority:** PO directive 2026-11-08; existing `AGENTS.md`, `ARCHITECTURE.md` and SA/PM contracts remain applicable.  
**Scope:** All Virtual Factory design decisions, new sessions, agent roles, code and integration work.  
**Change control:** PO approval + dedicated `sa/governance/*` PR + checks + human review. Never self-amend as part of an implementation issue.

## Article 1 — First-read obligation (non-negotiable)
Before any **architecture-significant decision**, SA, PM or any coding agent MUST open/read the exact current Constitution, `ARCHITECTURE.md`, relevant ADRs and ownership/capability registers, plus all active architecture HOLD decisions. Reading must happen again on **every new chat/session**, agent handoff and after governance baseline changes. Memory, chat summaries, cached excerpts or past attendance do not substitute for repository reads. The first output of a new session is a **bootstrap evidence record**, not a new design proposal.

An architecture-significant decision includes adding/replacing execution engines, lifecycle managers, run/time owners, material or event authorities, workspace/scope identities, data contracts, inter-module connectivity, APIs with side effects, gateways, schema/format compatibility, deployment boundaries, or changing an existing architecture rule. Treat ambiguous changes as significant (fail closed).

## Article 2 — Evidence bound to source, not assertions
Prior to a design decision or executable PM task, attach: `repository`, current remote `main_sha`, Constitution `path + blob_sha` (or approved SHA256), `ARCHITECTURE.md` reference, relevant ADR/HOLD issue numbers, current source/branch provenance, reuse inventory, authority/ownership impact, scenario/regression impact, decision alternatives, and SA verdict. If a field cannot be verified: `UNKNOWN` and `ARCHITECTURE_HOLD`. An acknowledgment checkbox alone is not proof; automation must verify file revision and PR/branch association.

## Article 3 — Reuse-first and single ownership
Search all current-main and active-unmerged VF capabilities before designing anything new. Evaluate `REUSE / PORT / ADAPT / RETAIN-KERNEL / DEAUTHORIZE / RETIRE / HOLD`, with exact SHA/file/merge state. One platform and API/UI entrypoint; one *public* RuntimeSession/lifecycle and orchestration owner per run; one material inventory/reservation/genealogy owner and one committed event projection authority. Domain-specific schedulers may exist only as subordinate kernels with explicit owners. **No dual controlling runtimes, duplicate writers or competing inventory authority.** Multiple independent workspaces are allowed within the one management platform. This clause is an architectural constraint; canonical component adoption remains governed by #155.

## Article 4 — Product behavior and truth fidelity
Preserve `ARCHITECTURE.md` boundaries: config-driven plant, graph/typed ports, measurable signal vs hidden ground truth, physically defensible process behavior and provenance. Do not invent TIPA physical or routing facts. Explicitly distinguish `IMPLEMENTED_AND_MERGED`, `IMPLEMENTED_UNMERGED`, `PROVEN_IN_FIXTURE`, `PENDING_INTEGRATION`, `PENDING_TIPA`. A historical closed issue or a passing fixture does not prove a current-main integrated runtime.

## Article 5 — Time, material and causality
At exchange boundaries use explicit scoped identity, run generation, event provenance and deterministic time; no silent float-to-microsecond rounding, timewarp or false same-window transfer. Material journal controls committed stock and genealogy; downstream events must derive from committed facts. No claim of cross-ledger/global atomicity without a tested commit boundary. Mixed discrete/continuous coupling requires declared window/lag policy and failure semantics. Protect legacy ASSY, SH-WTP and Bottled Water behavior through regression.

## Article 6 — Decision hierarchy and conflict handling
Priority: (1) current PO-approved Constitution/process + explicit active PO architecture HOLD, (2) approved ADR and current canonical ownership/architecture baseline, (3) architecture contracts, (4) issue-specific Design Lock, (5) task contract, (6) implementation interpretation. A newer **explicit approved** ADR can supersede an older design, but an open PR, chat inference, feature branch or task description cannot silently supersede it. On contradictory documents, STOP and request a single reconciled ADR/PO verdict. Current #155 HOLD blocks independent TIPA #141–#145 execution.

## Article 7 — Mandatory decision workflow
1. **BOOTSTRAP:** Read required sources at exact revision, report conflicts and latest authoritative status.
2. **DISCOVER:** Inspect current main, unmerged branches, PRs and Capability Registry; cite code-level evidence.
3. **IMPACT:** Write ownership boundary, API contracts, simulation time/material/data effects and regression matrix.
4. **DECIDE:** Record alternatives, preference, why reuse is insufficient, approval identity and ADR; PO approves constitutional/core-ownership changes.
5. **DESIGN LOCK:** SA publishes precise bounded contracts and fail/stop cases. PM may not infer architecture.
6. **IMPLEMENT:** PM uses existing VF task allowlist/preflight, exact-head CI and evidence; only approved paths.
7. **VERIFY:** CI dependency/ownership/conformance tests where implemented and SA review of non-automatable semantics. No merge/deploy without separate authorization.

## Article 8 — Fail-closed entry criteria
No architecture-significant Issue marked PM READY and no merge authorization when Constitution version is UNKNOWN/stale, existing capability not audited, authority duplicated, impacted integration not reconciled, #155 HOLD unresolved, ADR absent for a core change, or CI required evidence missing. Documentation-only updates can proceed on their own governed branch, explicitly marked non-executable. No session-local emergency exception. Exception/waiver requires time-bounded PO-signed ADR with scope, risk owner, proof and expiry; cannot waive branch protection or live safety controls by text alone.

## Article 9 — Enforcement maturity and limits
**Stage 0 (this PR):** normative rules and repository-first cold-session bootstrap policy. No manual session handoff requirement. **Not machine enforced yet.**
**Stage 1:** canonical capability/ownership register and ADR after #155, task/PR evidence schema.
**Stage 2:** CI/agent harness verify required artifacts, exact blob SHA, architecture impact evidence and negative fail-closed tests; checks must be required by actual GitHub protection to be merge-blocking.
**Stage 3:** module dependency, duplicate-authority and integration regression rules; periodically audit and reconcile exceptions.
Any claim that an article is mechanically enforced must cite the exact test, workflow, branch-protection setting and successful negative test, or mark it `NOT_ENFORCED`.

## Article 10 — Persistent institutional memory and cold-session continuity
Every new session MUST reconstruct its scoped project context from current repository sources and durable evidence, without requiring the previous session or PO to write, copy, or supply a manual handoff. A replaceable Guardian AI may perform this retrieval as DESIGNER, GUARDIAN_REVIEWER or GUARDIAN_OPERATOR; mode switches never confer approval authority. The resolver records remote main SHA, effective Constitution path + blob SHA, active ADR/HOLD issues, canonical ownership status, actual merged/unmerged capabilities, current roadmap and PR/CI, SA/PM gate, next safe step, forbidden actions and source provenance. Strategic Memory is a versioned index of approved long-horizon decisions, not a chat summary or independent authority; ephemeral context snapshots must be revalidated against GitHub before use. On stale/unavailable sources, disputed approval, or unverified capabilities, fail closed to read-only audit. Guardian implementation, independent approval and machine enforcement require separate scoped gates; this article does not claim an always-on agent is deployed.
