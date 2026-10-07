# DDAY-B2 — 11. Machine task-gate status

**Mandated gate:** `python .ai-harness/scripts/run_task_gate.py --task .ai-harness/tasks/DDAY-B2.json --token <token>`

**Outcome: `GATE_EXIT=5` — reproduces identically at every head at which it was run.**

| Gate run | Head at run time | P01–P21 | P22 | Exit |
|---|---|---|---|---|
| 1 | `5e9d28d3b3ee` | all PASS | `Report does not reference head SHA 5e9d28d3b3ee` | 5 |
| 2 | `184136aa667a` | all PASS | `Report does not reference head SHA 184136aa667a` | 5 |

The failure is head-independent, which is expected: P21/P22 do not read the task
contract at all. Because the evidence and report for this slice are themselves
committed on the reviewed branch, the reviewed head advances with every evidence
commit; the P22 defect therefore cannot be out-run by adding commits. The head
reported to the SA is verified live at review time and recorded in the machine
trace (`.ai-harness/traces/DDAY-B2/evidence.json`).

Raw records: `.ai-harness/traces/DDAY-B2/evidence.json`,
`.ai-harness/traces/DDAY-B2/preliminary-evidence.json`,
`.ai-harness/traces/DDAY-B2/regression.xml`.

## Pipeline steps that executed — all PASS

| Step | Name | Result | Detail |
|---|---|---|---|
| P01 | Load contract | PASS | |
| P02 | Validate contract | PASS | |
| P03 | Preflight | PASS | clean tree, baseline match |
| P04 | Changed files | PASS | `FILE VALIDATION PASSED (31 file(s))` |
| P05 | Local evidence | PASS | |
| P06 | Tests | PASS | full suite 1664 collected / 1664 passed / 0 failed |
| P07 | Smoke checks | PASS | `SMOKE-BW` → effective PASS |
| P08 | Remote state | PASS | commit verified on remote, branch head matches reported SHA |
| P09 | PR metadata | PASS | PR #101 open, base `main`, head equals the reported SHA |
| P10 | Exact-head CI | PASS | CI run `37095984681`, event `pull_request`, conclusion `success` |
| P11 | Merge CI smoke | PASS | no `SMOKE-VF`/`SMOKE-VF2` entries in this contract |
| P12 | Invariants | PASS | `remote_branch_equals_pr_head`, `pr_head_equals_implementation_sha`, `ci_head_equals_pr_head` all `true` |
| P13 | Pre-status acceptance | PASS | `7 PASS, 0 FAIL, 0 UNKNOWN` (A01–A07) |
| P14 | Tool failures | PASS | none |
| P15 | Contradictions | PASS | none |
| P16 | Preliminary status | (mid-run artifact) | see note below |
| P17–P19 | Persist / validate / reload | PASS | `Evidence is consistent.` |
| P20–P21 | Provisional status + report | PASS | |
| **P22** | **Validate provisional** | **FAIL** | `Report does not reference head SHA <head>` |

P23/P24 were not reached because P22 returned a blocking failure and the gate
exits 5 (`harness internal / stabilization failure`).

## Root cause of the P22 failure

`run_task_gate.py` P21 writes its own provisional report at
`.ai-harness/traces/DDAY-B2/gate-report.provisional.md` containing only:

```
# Gate Report (Provisional) — DDAY-B2
**Status**: <derived status>
**Gate**: <gate> | **Satisfied**: <bool> | **Exit**: <code>
- [PASS] P01 Load contract
...
```

`validate_report_consistency.py` (`P22`) then requires the report to contain the
implementation head SHA:

```python
head = evidence.get("implementation", {}).get("commit_sha", "")[:12]
if head and head not in report:
    issues.append(f"Report does not reference head SHA {head}")
```

The gate-generated provisional report never contains a commit SHA, so this check
can never be satisfied by the artifact the gate itself produces. Exact
reproduction:

```
$ python .ai-harness/scripts/validate_report_consistency.py \
    .ai-harness/traces/DDAY-B2/preliminary-evidence.json \
    .ai-harness/traces/DDAY-B2/gate-report.provisional.md
REPORT INCONSISTENCIES (1):
  - Report does not reference head SHA <head>
exit_code=1
```

The requirement itself is intentional — the harness's own unit tests assert that
a report must reference the head SHA
(`.ai-harness/tests/test_validate_report_consistency.py::test_clean_report_passes`).
The defect is that **P21 does not put the SHA into the report it generates**.

This is a **pre-existing defect in `run_task_gate.py`**, unrelated to the B2
change set, and it is not task-specific: the same failure occurs for any task in
this repository state, because P21/P22 do not depend on the task contract.

## Independent verification of the same checks

Because P22 aborts the pipeline before P23/P24, the remaining canonical checks
were executed directly against the same evidence record:

| Component | Command | Result |
|---|---|---|
| Changed files vs harness baseline | `verify_changed_files.py --task .ai-harness/tasks/DDAY-B2.json` | `PASSED (33 file(s))`, exit 0 |
| Changed files vs SA B2 baseline (`cb908c6`) | `verify_changed_files.py --task …/scope-contract-b2-baseline.json` | `PASSED (27 file(s))`, exit 0 |
| Evidence validation | `validate_evidence.py .ai-harness/traces/DDAY-B2/evidence.json` | `Evidence is consistent.`, exit 0 |
| Final acceptance (A08–A12) | `evaluate_acceptance.py … --phase final` | `12 PASS, 0 FAIL, 0 UNKNOWN`, exit 0 |

Counts grow with the number of evidence artifacts committed; each run is a strict
subset check, and the B2-scope check (27 files) covers exactly the deliverables
plus the frozen B1 artifacts.

Combined machine acceptance: **A01–A12 all PASS, 0 FAIL, 0 UNKNOWN**.

## Classification

| Aspect | Status |
|---|---|
| B2 deliverable vs Issue #102 acceptance criteria | **PASS** (A01–A12 all PASS) |
| Exact-head invariant (branch = PR = CI = reported SHA) | **PASS** |
| Required gate machine derivation to `IMPLEMENTED — PR OPEN — READY FOR SA REVIEW` | **NOT ACHIEVED** — blocked by the P22/P21 harness defect |
| Can B2 fix it? | **No** — `.ai-harness/scripts/` is outside the B2 allowlist; the stop condition `ALLOWLIST EXPANSION REQUIRED` applies and no unauthorized change was made |

The PM therefore does **not** self-certify the gate as satisfied. This is reported
as a required-tool failure in line with `PM-EXECUTION-CONTRACT.md` §2.5 and §2.8,
with the deliverable evidence submitted for SA review at the same time so the SA
can decide between:

1. authorizing a bounded harness correction to `run_task_gate.py` P21 (add the
   head SHA to the generated provisional report), after which the gate can be
   re-run for this exact head; or
2. accepting the substantive machine evidence above (which is the same evidence
   the gate would consume) as the B2 gate, and treating the P22 step as a known
   harness defect.
