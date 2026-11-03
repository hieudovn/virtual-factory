# SA Remote Design Workflow — VF

Version 1.0 | Governance authority: PO directive 2026-10-31, Issue #130.
Applies to SA/Lead Designer documentation work in hieudovn/virtual-factory. PM contract and tests remain unchanged.

## Authorization matrix
| Role | May author | Required workflow | Must not |
|---|---|---|---|
| SA, design | docs/architecture, docs/design, docs/plans, docs/reports, docs/governance; contract specifications kept under docs | sa/design/*, remote preflight, atomic SA task+docs commit, PR, SA Design Gate CI, exact-head review | src, tests, configs/runtime, deployment, PM harness, live systems |
| SA, governance | AGENTS, SA workflow policy, exact SA checker/action, specified harness SA tests | sa/governance/*, explicit PO governance issue, exact file allowlist, independent review | weaken PM gates; make undocumented CI/security changes |
| PM / executor | Specific code/config/tests/task/evidence named in PM contract | .ai-harness/PM-EXECUTION-CONTRACT.md; local preflight; full run_task_gate.py | override SA decisions; self-approve design; merge without exact-head SA authorization |

## Remote preflight — before ANY write
1. Read AGENTS.md, current governance and target issue. Confirm issue has SA/PO approval scope and desired state (APPROVED or DRAFT).
2. From GitHub remote connector check repo full name, push capability and exact current main commit SHA. Also check active PRs and that the intended branch does not already exist; if exists use explicit update protocol with expected_sha lease (never silently overwrite).
3. Pin expected_base_sha in SA task contract; specify branch, task_id, class, approval_issue, authority, allowed_paths, and forbidden operations. Prepare complete diff **before** write, classify every path. An SA design change must not include executables, application configs or PM harness files.
4. Post verified preflight to approval issue before mutation; if any fact is unavailable or contradictory, STOP. Remote API checks substitute only for a local worktree preflight in the SA docs workflow; they do not attest a local checkout or tests.

## Atomic change and post-write checks
1. Create a dedicated branch from pinned main; create one Git tree/commit containing both the SA task contract and documents, then update the branch ref with an expected-old-head lease. No file writes directly to main. A fresh design branch has an immutable base; do not force update.
2. Fetch branch commit, PR metadata and changed-file list; compare remote branch head = PR head = reported SHA. Unexpected paths or baseline movement STOP.
3. SA Design Gate workflow independently checks repository, branch/type/authority/task manifest, SHA ancestry and exact scoped diff; unit checks validate checker logic. Verify exact-head CI if available; UNKNOWN is not PASS.
4. Place durable report under docs/reports/ and link to authority issue and PR. Report statuses separately: committed to branch, PR opened, CI pass/unknown, design approved/draft, merged (only if evidence).
5. Merge only after a positive exact-head gate, applicable human approvals and explicit SA exact-head merge authorization. Do not use automatic merge. Recheck main after merging.

## SA task contract fields
File .ai-harness/sa-design/tasks/<TASK-ID>.json (included in the exact PR diff):
- task_id, class (design|governance), repository, branch, expected_base_sha, approval_issue (positive integer), authority (SA_DESIGN_DRAFT|SA_APPROVED_DESIGN|PO_APPROVED_GOVERNANCE), allowed_paths (explicit exact paths), description/status.
- Design authority may use draft for review; cannot claim APPROVED unless authorized. Governance requires PO_APPROVED_GOVERNANCE, issue proof and human review. Tool does not independently establish human identity or approval authenticity.

## Enforcement boundaries
Hardcoded safe path families in checker: docs/architecture, docs/design, docs/plans, docs/reports, docs/governance and SA task/report entries. Governance extras are precisely named. Contract allowlist further restricts files; a contract cannot expand beyond the hardcoded policy. Existing PM task and CI are not modified.
SA checker runs on PR head and full Git diff, not task-provided changed-path claims; no empty diff, missing task, wrong base SHA, untrusted path, unrecognized authority or skipped check can count as PASS.
Security is ultimately enforced by repository permissions/branch protection/required checks and human reviews. A PR check alone does not prove GitHub main protection exists: if not configured, risk owner is repository owner and main remains guarded procedurally. No GitHub admin or branch protection settings are altered here.

## Bootstrap
Initial implementation from Issue #130 uses remote connector preflight plus PO approval because the SA gate does not yet exist on main. Commit must go through sa/governance/* and a PR, with exact-head check and review before merge. This exception cannot be reused for PM implementation.
