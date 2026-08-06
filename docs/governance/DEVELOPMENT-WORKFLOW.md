# Development Workflow — Virtual Factory

## Branch Strategy

- `main` — policy: requires PR + CI (see server-side state below)
- `feature/*` — feature branches, merge into `main` via PR
- `chore/*` — governance, tooling, CAPA branches
- `docs/*` — documentation-only branches

## Server-Side State

**Current state**: `main` is **not** protected via GitHub branch protection.

**Reason**: GitHub branch protection for this private repository is unavailable
under the current account/repository plan.

**API evidence**: `PUT /repos/hieudovn/virtual-factory/branches/main/protection`
returned 403: "Upgrade to GitHub Pro or make this repository public to enable
this feature."

## PR Requirements (Policy)

1. All changes MUST go through a Pull Request targeting `main`
2. PR MUST pass VF-DM CI (`vf-dm-ci.yml`) before merge
3. At least one approving review required (SA external review when self-review
   is unavailable)
4. Policy: Direct push to `main` is prohibited
5. Policy: Force push to `main` is prohibited
6. Policy: Branch deletion on `main` is prohibited

## Compensating Controls

Because server-side branch protection is unavailable, the following compensating
controls are in place:

- Version-controlled pre-push hook (`scripts/git-hooks/pre-push`)
- Mandatory PR workflow (documented in this file)
- `scripts/verify-pr-merge-gate.py` — automated merge gate checker
- Explicit SA merge authorization required before merge
- Expected-head-SHA merge (verify CI ran on the exact commit)
- Post-merge verification

**Residual risk**: Local hooks can be bypassed or removed. GitHub still permits
direct main updates by any repository collaborator.

## Commit Standards

- Each commit message MUST reference the milestone slice (e.g., `M2-S04-C02:`)
- Commit messages MUST describe WHAT changed and WHY
- No "wip", "tmp", or "fix" commit messages without context

## Review Standards

- SA review required for all M2 milestone slices
- PM must provide concrete evidence (GitHub SHA, CI link, test count) before declaring READY
- Status like "IMPLEMENTED — READY FOR SA REVIEW" is only valid when:
  - Code is committed AND pushed to GitHub
  - CI has run and passed on the exact commit SHA
  - Evidence fields are concrete (not "TODO" or "TBD")

## Pre-Push Hook

Install with: `bash scripts/install-git-hooks.sh`

The pre-push hook:
- Rejects pushes directly to `main`
- Warns on force pushes to any branch
- Runs `python -m pytest -q --tb=short` before push

## Incident Response

When a governance violation is discovered:
1. Document in `docs/governance/incidents/`
2. Create a CAPA branch (`chore/*`)
3. Implement corrective actions
4. Merge CAPA PR through normal PR process
5. Verify compensating controls are in place post-merge (server-side protection unavailable)
