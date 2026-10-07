# DDAY-B2-C01 — 02. Harness gate repair (C01-B)

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`harness_repair`; patch [`implementation.patch`](./implementation.patch).

Two independent, task-independent defects prevented `run_task_gate.py` from
producing a machine-derived READY status. Both are now fixed **in the
allowlisted orchestrator**; no validation was weakened.

## Defect 1 — P21 report did not identify its head (fixed)

`P21` wrote `gate-report.provisional.md` containing only status/gate/steps.
`P22` then required the report to reference `implementation.commit_sha`:

```python
head = evidence.get("implementation", {}).get("commit_sha", "")[:12]
if head and head not in report:
    issues.append(f"Report does not reference head SHA {head}")
```

Because P1/P22 do not read the task contract, **every** task failed there:

| Gate run | Head | Result |
|---|---|---|
| DDAY-B2 (before) | `5e9d28d3b3ee` | `GATE_EXIT=5` — "Report does not reference head SHA 5e9d28d3b3ee" |
| DDAY-B2 (before) | `184136aa667a` | `GATE_EXIT=5` — "Report does not reference head SHA 184136aa667a" |

**Fix:** the report writer is extracted as `_write_gate_report(...)`, which always
emits `**Implementation SHA**: <commit_sha>`; P21 and P24 both use it. This fixes
*report generation*. `validate_report_consistency.py` is **untouched**, and a
report without the SHA still fails closed (negative control in the evidence:
`report_without_sha_fails_closed.passed == false`).

**After:**

```
P22: Validate provisional
Report is consistent with evidence.
```

| Check | Result |
|---|---|
| Generated provisional report contains the full implementation SHA | **true** |
| … and its 12-character prefix | **true** |
| `validate_report_consistency.py` on the generated report | **passed**, 0 issues |
| Report without the SHA (control) | still **fails** — validation not weakened |

## Defect 2 — PR state representation mismatch (fixed, disclosed)

With a token, `verify_remote_state.py` stores the PR state exactly as the GitHub
REST API reports it — `"open"` (lowercase) — while `derive_status.py` and the
harness evidence fixtures use the canonical uppercase form:

```python
if pr_state != "OPEN" and not pr.get("merged"):
    return "NOT READY — GOVERNANCE FAILURE"
```

Observed: the gate completed P01–P24 with **every step PASS and every acceptance
item PASS**, yet derived `NOT READY — GOVERNANCE FAILURE` purely from
representation, so exit 0 was unreachable with a token. (Without a token the gh
CLI path yields `OPEN`, but `_resolve_pr` returns `None` without a token, so the
PR is never attached and the run ends `PUSHED — PR MISSING`.)

**Fix:** `run_task_gate.py` normalizes the PR state to the harness' canonical
representation (`.upper()`) immediately after PR metadata is collected, before
status derivation and acceptance evaluation. This aligns a representation — it
does not relax anything: PR open / not-draft / base-main / head-equality checks
are untouched.

Representation-only proof (`machine-evidence.json` → `pr_state_normalization`):

| Input | After normalization | `derive_status` |
|---|---|---|
| `"open"` | `OPEN` | `IMPLEMENTED — PR OPEN — READY FOR SA REVIEW` |
| `"closed"` | `CLOSED` | `NOT READY — GOVERNANCE FAILURE` |
| `"OPEN"` | `OPEN` (idempotent) | — |

**Disclosure and residual:** the root cause lives in
`.ai-harness/scripts/verify_remote_state.py`, which is **outside the C01
allowlist**, so it was not modified. The normalization is a boundary alignment;
if the SA prefers the fix at the source, a one-line `.upper()` normalization in
`verify_remote_state.py` would make the shim removable. Reported, not expanded.

## Focused harness tests

`.ai-harness/tests/test_gate_report_provisional.py` (new, 5 tests):

| Test | Guards |
|---|---|
| `test_provisional_report_references_implementation_sha` | the P21 artefact satisfies P22 |
| `test_report_without_sha_fails_closed` | validation is still fail-closed |
| `test_final_report_references_sha_and_pipeline` | the P24 artefact identifies its head |
| `test_pr_state_is_normalized_to_harness_convention` | normalization is representation-only and idempotent |
| `test_closed_pr_still_fails_closed_after_normalization` | a closed PR still derives NOT READY |

Result: **9/9 PASS** (these 5 plus the 4 pre-existing
`test_validate_report_consistency.py` tests).
