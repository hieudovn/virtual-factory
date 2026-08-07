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
# Run the full task gate for a contract
python .ai-harness/scripts/run_task_gate.py --task tasks/VF-DM-M2-S05-BASELINE.json --report-only

# Validate evidence
python .ai-harness/scripts/validate_evidence.py examples/valid-ready-evidence.json

# Derive status from evidence
python .ai-harness/scripts/derive_status.py examples/valid-ready-evidence.json

# Preflight check
python .ai-harness/scripts/preflight.py --task tasks/VF-DM-M2-S05-BASELINE.json
```

## Dependencies

Python 3.11+ standard library. No external frameworks.
