## Mandatory Architecture Constitution — FIRST READ (PO directive 2026-11-08; Issue #156)

**STOP BEFORE ARCHITECTURE DECISIONS.** At the start of every AI session, SA design task, PM task interpretation, or architecture-significant review, read in order:
1. `docs/governance/ARCHITECTURE_CONSTITUTION.md` (binding architecture decision process).
2. `ARCHITECTURE.md` (existing approved foundation, not proof of all current runtime features).
3. `docs/governance/ARCHITECTURE_GOVERNANCE_PLAN.md`, active architecture ADR/ownership/capability registers *when published*, and relevant HOLD/decision issues (currently #155).
4. Existing role-specific contracts below; PM must still obey local preflight and P01–P24, SA still obeys remote design gate.

**Evidence:** Record the exact Constitution Git blob SHA (or verifiable content digest), the remote `main` SHA, related architecture decision/ADR, existing-capability reuse assessment, owner-impact assessment, and any unresolved conflicts **before** deciding or issuing an implementation contract. A checkbox or merely claiming “read” does not prove enforcement. On inaccessible/stale/conflicting artifacts, missing ownership, or architectural uncertainty, mark `ARCHITECTURE_HOLD`, perform read-only audit, and DO NOT design-lock/dispatch/merge. New root session, scheduler, lifecycle, material authority, event writer or mutating API requires explicit ADR and PO approval. #155 one-platform HOLD takes precedence over older TIPA assumptions.

The process Constitution does not by itself establish CI enforcement or settle #155. Any changes to these rules follow the existing governance PR process and human review; never modify `main` directly.

# Repository Agent Instructions

Two separate governed roles operate in this repository.

## PM / coding-agent execution (unchanged)

Before any PM implementation, code change, execution/test, deployment, or runtime operation:

1. Read .ai-harness/PM-EXECUTION-CONTRACT.md.
2. Require the PM task contract under .ai-harness/tasks/.
3. Run the existing local harness preflight before modifying tracked files.
4. STOP on failed preflight, mismatched baseline, ambiguous task, or unavailable mandatory tool.
5. Follow the PM task allowlist, full run_task_gate.py evidence flow, exact-head CI, and machine-derived status.
6. No direct main push; no merge without explicit SA authorization on the exact PR head; no silent next slice.
7. PM cannot self-approve design, production readiness, task closure, or merge.

## SA / Lead Designer remote design workflow

SA may write **only approved design-domain artifacts** (plans, architecture, design/contract specifications and reports) using a remote GitHub connector/API when local git is unavailable, provided that:

1. An issue records the relevant SA/PO authority and task scope. A machine-readable SA task contract is included under .ai-harness/sa-design/tasks/ in the *same atomic change*.
2. Before mutation SA verifies remote repository/permissions, current main SHA, absence of conflicting branch/PR, planned file allowlist, and expected baseline; publishes the remote-preflight evidence in the issue. Unknown => STOP.
3. SA uses a dedicated sa/design/* branch, never main, and publishes a PR with a full diff. SA records distinction between approved decisions and pending draft designs; source code, tests, runtime configuration, deployment and PM harness implementation are forbidden in ordinary SA design tasks.
4. The separate SA Design Gate validates the changed paths and task authority on the exact PR head. SA verifies remote commit/PR SHA equality and exact-head CI status before reporting readiness.
5. The complete design workflow and permitted paths are defined in .ai-harness/SA-DESIGN-WORKFLOW.md. Its gate is distinct from and does **not** replace PM run_task_gate.py.
6. Any change to AGENTS.md, the harness, or CI must use a dedicated sa/governance/* PR with **explicit PO authorization**, restricted governance allowlist, human review, and CI proof. SA design permissions alone are not permission to change governance.
7. Merges of any class still require explicit SA authorization for the exact current PR head SHA, with PO involvement where a governance/domain decision requires it. No automatic merge or deploy.

**Bootstrap exception (Issue #130):** PO explicitly authorized the initial creation of this remote-only SA workflow. Issue #130 contains connector-derived remote preflight evidence made *before* any branch/file mutation. This one-time exception does not waive exact-head PR review, branch isolation, or code/PM restrictions.

**Status vocabulary:** SA may record design DRAFT / APPROVED as a **document decision**, not PM implementation readiness. Never claim GitHub merge, runtime execution, or CI PASS without matching remote evidence.
