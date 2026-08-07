# Tool Failure Policy

When a required command or API call fails, the evidence is classified as FAIL or UNKNOWN — never as PASS.

---

## Failure Categories

### Hard Failure (→ FAIL)
- Non-zero exit code
- HTTP 4xx/5xx response
- Authentication failure
- Resource not found (confirmed)
- Malformed output that cannot be parsed

### Soft Failure (→ UNKNOWN)
- Timeout without result
- Empty output where data was expected
- Tool not installed
- Cannot access resource (transient)
- Partial data that is insufficient for the required evidence

---

## Recording Requirements

For every tool failure, record:

| Field | Description |
|-------|-------------|
| `tool` | Tool or command name |
| `command` | Exact command or API request |
| `timestamp` | ISO 8601 timestamp |
| `exit_code` | Exit code or HTTP status |
| `stdout` | Captured stdout (truncated if large) |
| `stderr` | Captured stderr (truncated if large) |
| `affected_evidence` | Evidence field names impacted |
| `classification` | `FAIL` or `UNKNOWN` |
| `execution_stopped` | Whether the tool failure halted execution |

---

## Forbidden Substitutions

When evidence is missing due to tool failure, do NOT replace it with:

- Manual assumption ("it should have worked")
- A prior successful report
- Model confidence ("I'm sure it passed")
- Similar earlier output from a different commit
- Editor-local link (`vscode-file://...`)
- Narrative explanation ("based on the workflow...")
- An assumed successful command ("the command would have returned...")

---

## Fallback Tools

Fallback tools are allowed ONLY when:

1. They provide **equivalent** evidence (same data fields)
2. The fallback is **documented** in the evidence record
3. The evidence clearly states which tool produced it

Example: If `gh` CLI is not installed, using the GitHub REST API directly is an acceptable fallback because both provide the same PR metadata.

---

## Impact on Status

| Failure Count | Impact |
|---------------|--------|
| 0 failures | No impact |
| Any FAIL on required evidence | Cannot reach READY |
| Any UNKNOWN on required evidence | Cannot reach READY |
| FAIL on optional evidence | May proceed with documented gap |
| Multiple FAIL/UNKNOWN | → `NOT READY — INSUFFICIENT EVIDENCE` |

---

## Execution Stop Rules

| Condition | Action |
|-----------|--------|
| Authentication failure | STOP — cannot access remote evidence |
| Repository not found | STOP — BASELINE MISMATCH |
| Branch not found remotely | STOP — verify branch was pushed |
| Required CI not found | UNKNOWN — may proceed with gap documented |
| All CI API attempts fail | UNKNOWN — cannot verify CI |
