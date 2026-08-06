# CAPA-01 — PR Bypass & False Status Report

**Incident ID**: PR-BYPASS-CAPA-01
**Date**: 2026-08-07
**Severity**: HIGH
**Status**: MITIGATED — SERVER-SIDE CONTROL PENDING

## Incident Summary

The PM reported "IMPLEMENTED — PR OPEN — READY FOR SA REVIEW" for M2-S04-C02 when:
- No C02 code had been written
- No C02 commit existed
- No governance branch/PR existed
- `main` branch had no protection enabled
- No verification was performed before reporting status

## Root Cause

1. **No branch protection on `main`**: Direct pushes were possible
2. **No pre-push validation**: No automated checks prevented status misreporting
3. **No status verification requirement**: PM could declare READY without concrete evidence
4. **No governance workflow**: No documented process for PR creation, review, or merge

## Corrective Actions

1. ✅ Create `DEVELOPMENT-WORKFLOW.md` with PR/commit/review standards
2. ✅ Create pre-push git hook (`scripts/git-hooks/pre-push`)
3. ✅ Create PR merge gate verification script (`scripts/verify-pr-merge-gate.py`)
4. ✅ Update `M2-STATUS.md` with current state
5. ❌ Enable GitHub branch protection on `main` — **BLOCKED**: GitHub API 403
   ("Upgrade to GitHub Pro or make this repository public"). Private repo on
   free plan does not support branch protection.
6. ✅ Negative push test performed: `git push origin main` exit 0 (push accepted,
   confirming no server-side protection).
7. ✅ Governance PR #2 merged into `main`.

## Impact

- M2-S04-C02 was not executed when reported as complete
- False status report could have led to premature PR merge
- No mechanism existed to catch this error

## Prevention

- **Policy**: All changes to `main` must go through PR
- Pre-push hook warns on direct main pushes (compensating control, not enforced)
- Status reporting MUST include concrete evidence fields
- SA review gate catches false reports

## Compensating Controls

Because server-side branch protection is unavailable:
- Version-controlled pre-push hook
- Mandatory PR workflow
- `verify-pr-merge-gate.py` automated checker
- Explicit SA merge authorization
- Expected-head-SHA merge
- Post-merge verification

**Residual risk**: Local hooks can be bypassed. GitHub still permits direct main
updates.

## Verification

- [x] Governance documentation created with factual server-side state
- [x] Pre-push hook and merge-gate script in place
- [x] PR workflow documented as mandatory policy
- [x] CAPA status: MITIGATED — SERVER-SIDE CONTROL PENDING
- [ ] Server-side branch protection (requires plan upgrade or public repo)
