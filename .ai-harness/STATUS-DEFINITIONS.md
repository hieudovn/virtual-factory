# Status Definitions

Allowed machine-derived statuses with entry conditions, required evidence, forbidden claims, and allowed next actions.

---

## Machine-Derived Statuses

### PRECHECK FAILED
- **Entry**: Preflight check returned non-zero
- **Required evidence**: Preflight output, mismatch details
- **Forbidden claims**: IMPLEMENTED, READY
- **Allowed next action**: Fix preflight issues, retry
- **Human authorization**: None (automatic stop)

### NOT STARTED
- **Entry**: Task contract validated, baseline verified, no work done
- **Required evidence**: Baseline verification record
- **Forbidden claims**: Any implementation claim
- **Allowed next action**: Begin implementation
- **Human authorization**: None

### IN PROGRESS
- **Entry**: Work has begun, not yet complete
- **Required evidence**: Current state of changed files
- **Forbidden claims**: READY, COMPLETE, CLOSED
- **Allowed next action**: Continue implementation
- **Human authorization**: None

### IMPLEMENTED LOCALLY
- **Entry**: Required changes exist locally, possibly uncommitted
- **Required evidence**: File listing, test results
- **Forbidden claims**: READY FOR SA REVIEW, remote completion
- **Allowed next action**: Commit and push
- **Human authorization**: None

### IMPLEMENTED — NOT COMMITTED
- **Entry**: Changes exist but no commit created
- **Required evidence**: `git status`, diff listing
- **Forbidden claims**: READY, remote presence
- **Allowed next action**: Create commit
- **Human authorization**: None

### IMPLEMENTED — NOT PUSHED
- **Entry**: Local commit exists but not on remote
- **Required evidence**: Local commit SHA, remote absence
- **Forbidden claims**: READY FOR SA REVIEW
- **Allowed next action**: Push to remote
- **Human authorization**: None

### PUSHED — PR MISSING
- **Entry**: Remote branch exists, no PR found
- **Required evidence**: Remote branch SHA, PR absence
- **Forbidden claims**: READY FOR SA REVIEW
- **Allowed next action**: Open PR
- **Human authorization**: None

### PR OPEN — CI PENDING
- **Entry**: PR exists, CI not yet completed
- **Required evidence**: PR number, CI pending status
- **Forbidden claims**: READY
- **Allowed next action**: Wait for CI
- **Human authorization**: None

### NOT READY — TEST FAILURE
- **Entry**: Tests fail
- **Required evidence**: Failed test output
- **Forbidden claims**: READY
- **Allowed next action**: Fix tests
- **Human authorization**: None

### NOT READY — SMOKE FAILURE
- **Entry**: Smoke checks fail
- **Required evidence**: Smoke failure output
- **Forbidden claims**: READY
- **Allowed next action**: Fix smoke issues
- **Human authorization**: None

### NOT READY — STALE CI
- **Entry**: CI head SHA ≠ PR head SHA
- **Required evidence**: Mismatched SHAs
- **Forbidden claims**: READY, "CI passed"
- **Allowed next action**: Trigger new CI on correct head
- **Human authorization**: None

### NOT READY — REMOTE STATE MISMATCH
- **Entry**: PR head ≠ remote branch head
- **Required evidence**: Mismatched SHAs
- **Forbidden claims**: READY
- **Allowed next action**: Push correct commit, update PR
- **Human authorization**: None

### NOT READY — ACCEPTANCE FAILURE
- **Entry**: One or more acceptance items are FAIL
- **Required evidence**: Acceptance matrix with FAIL items
- **Forbidden claims**: READY
- **Allowed next action**: Fix failing acceptance items
- **Human authorization**: None

### NOT READY — INSUFFICIENT EVIDENCE
- **Entry**: Required evidence is UNKNOWN or missing
- **Required evidence**: List of missing/unknown evidence
- **Forbidden claims**: READY, any PASS for unknown items
- **Allowed next action**: Collect missing evidence
- **Human authorization**: None

### NOT READY — GOVERNANCE FAILURE
- **Entry**: Forbidden action performed, or governance policy violated
- **Required evidence**: Violation details
- **Forbidden claims**: READY
- **Allowed next action**: Remediate, report CAPA
- **Human authorization**: SA review recommended

### IMPLEMENTED — PR OPEN — READY FOR SA REVIEW
- **Entry**: All pre-merge acceptance items PASS
- **Required evidence**: Full evidence record
- **Forbidden claims**: COMPLETE, CLOSED, SA APPROVED, MERGE AUTHORIZED
- **Allowed next action**: SA review
- **Human authorization**: SA review required

### MERGED — READY FOR POST-MERGE REVIEW
- **Entry**: PR merged, post-merge evidence incomplete
- **Required evidence**: Merge confirmation
- **Forbidden claims**: COMPLETE, CLOSED
- **Allowed next action**: Post-merge verification
- **Human authorization**: SA review

### POST-MERGE VERIFIED — READY FOR SA CLOSURE
- **Entry**: All post-merge evidence PASS
- **Required evidence**: Full post-merge evidence
- **Forbidden claims**: COMPLETE, CLOSED (still requires SA)
- **Allowed next action**: SA closure review
- **Human authorization**: SA closure decision required

### BLOCKED — PLATFORM LIMITATION
- **Entry**: Required platform capability unavailable
- **Required evidence**: API error, plan limitation
- **Forbidden claims**: Protection active
- **Allowed next action**: Document compensating controls
- **Human authorization**: SA acceptance of residual risk

### STOPPED — BASELINE MISMATCH
- **Entry**: Expected baseline ≠ actual baseline
- **Required evidence**: Mismatched SHAs
- **Forbidden claims**: Any implementation status
- **Allowed next action**: Resolve baseline discrepancy
- **Human authorization**: SA may provide updated baseline

### STOPPED — BASELINE ADVANCED
- **Entry**: Remote main advanced beyond expected baseline
- **Required evidence**: New main SHA
- **Forbidden claims**: Any implementation status
- **Allowed next action**: Rebase or update baseline
- **Human authorization**: SA must confirm new baseline

### STOPPED — TASK AMBIGUITY
- **Entry**: Task contract has ambiguity affecting governed scope
- **Required evidence**: Ambiguity description
- **Forbidden claims**: Any status implying clarity
- **Allowed next action**: Request SA clarification
- **Human authorization**: SA clarification required

---

## Non-Machine-Derived Statuses (Human-Authorized Only)

These statuses must NOT be derived by automated tools:

- **COMPLETE** — Requires explicit SA decision
- **CLOSED** — Requires explicit SA decision
- **SA APPROVED** — Requires explicit SA statement
- **MERGE AUTHORIZED** — Requires explicit SA merge authorization with exact head SHA
- **NEXT SLICE AUTHORIZED** — Requires explicit SA authorization
