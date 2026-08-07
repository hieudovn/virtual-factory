# PM Execution Contract

**Version**: 1.0.0
**Governs**: All AI PM and coding agent tasks in `hieudovn/virtual-factory`

This contract is mandatory. Convenience, speed, inferred intent and similarity to previous tasks do not override it.

---

## 1. Mandatory Execution Lifecycle

### Phase 1: Task Interpretation

Before any modification, record:

| Field | Required |
|-------|----------|
| Task ID | Yes |
| Repository | Yes |
| Task objective | Yes |
| Explicit deliverables | Yes |
| Explicit non-deliverables | Yes |
| Required branch | Yes |
| Expected baseline SHA | Yes |
| Allowed paths | Yes |
| Forbidden paths | Yes |
| Required tests | Yes |
| Required smoke checks | Yes |
| Required remote evidence | Yes |
| Forbidden actions | Yes |
| Stop conditions | Yes |
| SA authorization boundary | Yes |

The PM must not silently broaden or narrow the task.

When ambiguity affects architecture, public API, data contract, security, governance, scope, or milestone boundary → `STOPPED — TASK AMBIGUITY`.

For minor implementation choices within an explicit contract, choose the safest conservative interpretation and record it.

### Phase 2: Baseline Verification

Before modifying anything, verify and record:

- Repository root
- Current branch
- Working-tree status (must be clean or explicitly authorized)
- Local HEAD
- `origin/main` HEAD
- Target branch HEAD
- Expected baseline SHA
- Existing related PRs
- Current CI status where relevant

**Stop conditions**:
- Repository mismatch
- Wrong branch
- Dirty worktree that may be overwritten (without authorization)
- Expected baseline mismatch → `STOPPED — BASELINE MISMATCH`
- Remote main has advanced unexpectedly → `STOPPED — BASELINE ADVANCED`
- Related PR state differs materially from the task contract
- Required remote evidence cannot be accessed

Do not automatically reset, discard, stash-and-forget, rebase, rewrite history, or delete branches unless the task explicitly authorizes it.

### Phase 3: Execution

Execute with explicit boundaries:

**Forbidden without authorization**:
- Push directly to `main`
- Merge PRs
- Start the next milestone slice
- Close a milestone
- Delete tests
- Reduce test coverage silently
- Change files outside the allowlist
- Rewrite `main` history
- Reuse stale CI evidence
- Change governance facts to desired-state claims
- Mark SA approval in repository records without an actual SA decision

### Phase 4: Evidence Collection

Collect evidence in the mandated order:

```
inspect local result
→ inspect remote result
→ run tests
→ inspect PR
→ inspect exact-head CI
→ evaluate acceptance criteria
→ validate evidence consistency
→ derive final status
```

Do not select a status first and then search for supporting evidence.

### Phase 5: Status Derivation

Use `derive_status.py`. The PM must not freely choose final status.

---

## 2. Governing Principles

### 2.1 Planning is not implementation

The following do NOT constitute implementation:
- A plan, generated text, code displayed in chat
- Code not written to the repository
- Local uncommitted changes
- A local-only commit
- An unpushed branch
- A PR description
- An intended action
- A similar implementation from an earlier task
- A prior CI run
- An assumed successful command
- A report generated without tool evidence

### 2.2 Implementation is not readiness

Readiness additionally requires:
- Remote commit existence
- Correct PR
- Correct base and head
- Exact-head CI
- Required tests and smoke checks
- Complete acceptance evidence
- No forbidden action
- No unresolved UNKNOWN evidence

### 2.3 Evidence precedes status

The PM must derive status from collected evidence, not select a status and then search for supporting evidence.

### 2.4 Remote state is authoritative

GitHub remote state is authoritative for:
- Branch existence, remote branch head, remote commit existence
- PR existence, state, base, head, merge state
- CI run ID, event, head SHA, conclusion

Local Git state is necessary but not sufficient proof of remote completion.

Local editor links (e.g., `vscode-file://...`) must never be used as final remote evidence.

### 2.5 Fail closed

Every acceptance item: `PASS` | `FAIL` | `UNKNOWN`

- `UNKNOWN` is not `PASS`
- Missing evidence is not `PASS`
- Tool failure is not `PASS`
- Empty output is not `PASS`
- Partial output is not `PASS` unless explicitly sufficient
- Any required `FAIL` or `UNKNOWN` prevents `READY` status

### 2.6 Exact-head invariant

```
remote feature branch HEAD = PR head SHA = CI head SHA = reported review SHA
```

After rebase, merge-from-main, amend, force-with-lease update, or new commit, all earlier CI and review evidence becomes stale.

### 2.7 Desired state ≠ actual state

For every governance or platform control, report separately: required policy, actual state, evidence, residual gap, compensating control, risk owner, revisit trigger.

Never report a policy requirement as a technically enforced platform capability.

### 2.8 Tool output is evidence, not intent

When a required tool fails, times out, returns no/partial data, is not installed, is unauthenticated, or cannot access the resource → evidence is `FAIL` or `UNKNOWN`. Do not continue as though the tool succeeded.

### 2.9 Deterministic tests are not live verification

Validator unit tests passing ≠ live validator run passing against the real PR.

### 2.10 PM cannot self-certify completion

The PM may report: `NOT READY`, `IMPLEMENTED — PR OPEN — READY FOR SA REVIEW`, `MERGED`, `BLOCKED`, `STOPPED`.

The PM must not report: `COMPLETE`, `CLOSED`, `SA APPROVED`, `AUTHORIZED TO MERGE`, `AUTHORIZED TO START NEXT SLICE` unless those decisions were explicitly issued by the SA.

---

## 3. Completion Semantics

### IMPLEMENTED LOCALLY
- Required local files and tests exist
- Local verification has run
- Changes may be uncommitted or unpushed
- **Cannot be used for SA review readiness**

### IMPLEMENTED
- Required changes exist
- Required tests exist
- Commit exists
- Commit is pushed
- Remote branch head equals reported commit SHA

### READY FOR SA REVIEW
- IMPLEMENTED is true
- PR exists, is open, is not draft
- PR base is correct
- PR head equals remote branch head
- CI succeeded on the exact PR head
- Required tests and smoke checks passed
- All acceptance items are PASS
- No tool failures for required evidence
- No unknown evidence
- No forbidden actions performed

### MERGED
- GitHub reports `merged=true`
- `merged_at` exists
- PR number exists
- Merged head matches authorized head (where authorization was required)
- Merge commit exists
- Target branch contains the result

### POST-MERGE VERIFIED
- MERGED is true
- New main SHA recorded
- Post-merge CI succeeded on exact new main SHA
- Regression suite passed
- Main contains the expected implementation
- No unexpected branch drift

### COMPLETE / CLOSED
Cannot be self-issued by PM. Require explicit SA decision.
