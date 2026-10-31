# AI Execution Harness — Virtual Factory

Prevents AI PM, coding agents and automation from:
- Misunderstanding task commands
- Silently changing task scope
- Confusing planning with implementation
- Reporting work that does not exist (local-only → remote)
- Using stale CI or evidence from another commit
- Describing desired governance policy as actual platform enforcement
- Merging or starting subsequent work without authorization
- Self-certifying a milestone as complete

## Structure

```
.ai-harness/
├── README.md                          ← this file
├── PM-EXECUTION-CONTRACT.md           ← mandatory lifecycle rules
├── STATUS-DEFINITIONS.md              ← machine-derived statuses
├── TOOL-FAILURE-POLICY.md             ← failure ≠ success
├── EVIDENCE-SCHEMA.json               ← evidence structure
├── TASK-PROMPT-TEMPLATE.md            ← future task template
├── REPORT-TEMPLATE.md                 ← status report template
├── schemas/                           ← JSON schemas
├── scripts/                           ← validators & verifiers
├── tests/                             ← deterministic harness tests
├── examples/                          ← valid & invalid evidence fixtures
├── tasks/                             ← baseline task contracts
└── traces/                            ← runtime artifacts (gitignored)
```

## Usage

```bash
# Run the full task gate (normal mode)
python .ai-harness/scripts/run_task_gate.py \
  --task .ai-harness/tasks/VF-DM-M2-S05-BASELINE.json

# Run report-only (no modifications, no write)
python .ai-harness/scripts/run_task_gate.py \
  --task .ai-harness/tasks/VF-DM-M2-S05-BASELINE.json \
  --report-only

# Validate evidence
python .ai-harness/scripts/validate_evidence.py \
  .ai-harness/examples/valid-ready-evidence.json

# Derive status from evidence
python .ai-harness/scripts/derive_status.py \
  .ai-harness/examples/valid-ready-evidence.json

# Preflight check
python .ai-harness/scripts/preflight.py \
  --task .ai-harness/tasks/VF-DM-M2-S05-BASELINE.json
```

### Command Reference

| Command | Access | Credentials |
|---------|--------|-------------|
| `preflight.py` | Read-only (local git) | None |
| `verify_changed_files.py` | Read-only (local git) | None |
| `verify_remote_state.py` | GitHub API | `GITHUB_TOKEN` env or `--token` |
| `verify_exact_head_ci.py` | GitHub API | `GITHUB_TOKEN` env or `--token` |
| `validate_evidence.py` | Read-only (file) | None |
| `derive_status.py` | Read-only (file) | None |
| `evaluate_acceptance.py` | Read-only (file) | None |
| `run_task_gate.py` | Orchestration (+ API for remote) | `GITHUB_TOKEN` env or `--token` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Requested gate satisfied, all required steps PASS |
| 1 | Validly evaluated but NOT ready |
| 2 | Contract, schema or invocation error |
| 3 | Required tool or remote evidence unavailable |
| 4 | Baseline or repository mismatch |
| 5 | Harness internal error |

### Generated Artifacts

- `.ai-harness/traces/<task-id>/evidence.json` — complete evidence record
- `.ai-harness/traces/<task-id>/gate-report.md` — human-readable gate report

## Dependencies

Python 3.11+ standard library. No external frameworks.


---

## SA Remote Design Workflow (separate from PM execution)

For SA-owned docs, architecture, planning, contract specifications and governance changes, see [SA-DESIGN-WORKFLOW.md](SA-DESIGN-WORKFLOW.md).

- Design work: branch sa/design/*, explicit approved/draft authority issue, atomic SA contract and document commit, GitHub-API remote preflight, exact-head PR diff + SA Design Gate CI.
- Harness/CI governance: branch sa/governance/* only with explicit PO authorization and controlled paths.
- The SA gate is [scripts/sa_design_gate.py](scripts/sa_design_gate.py), triggered by [.github/workflows/sa-design-gate.yml](../.github/workflows/sa-design-gate.yml).
- This does not apply to PM source edits, test execution or deployment: those remain under PM-EXECUTION-CONTRACT.md and run_task_gate.py. A passing SA gate means documentation scope and baseline validated, **not** implementation approved, runtime tested or merged.
- Missing GitHub API or exact-head CI evidence blocks READY and must be reported UNKNOWN. No direct main write or automatic merge.
