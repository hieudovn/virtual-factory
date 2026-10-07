# DDAY-B4 — 06. Machine task-gate status

Canonical tool: `.ai-harness/scripts/run_task_gate.py`
Contract: [`.ai-harness/tasks/DDAY-B4.json`](../../../tasks/DDAY-B4.json)
Machine record: `.ai-harness/traces/DDAY-B4/evidence.json`
Machine report: `.ai-harness/traces/DDAY-B4/gate-report.md`

Invocation (Windows: `PYTHONIOENCODING` deliberately NOT set — forcing UTF-8
mangles the em dash in the derived status string and breaks the READY compare):

```
python .ai-harness/scripts/run_task_gate.py \
    --task .ai-harness/tasks/DDAY-B4.json --token <github-token>
```

## Result

```
GATE COMPLETE (47.3s)
Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW
Gate: ready_for_sa_review | Satisfied: True | Exit: 0
```

| Item | Value |
| --- | --- |
| Machine-derived status | `IMPLEMENTED — PR OPEN — READY FOR SA REVIEW` |
| Gate | `ready_for_sa_review` |
| `requested_gate_satisfied` | `true` |
| Exit code | `0` |
| Pipeline steps P01–P24 | **24/24 PASS** |
| Acceptance A01–A14 | **14/14 PASS** |
| Implementation SHA at gate time | `9d4f43275c34f62a8a55b410fd427e469f7004ee` |
| Exact-head CI | run `37133165235`, event `pull_request`, conclusion `success` |

## Invariants

```
remote_branch_equals_pr_head      : true
pr_head_equals_implementation_sha : true
ci_head_equals_pr_head            : true
evidence_validator_exit_zero      : true
report_consistency_exit_zero      : true
smoke_vf_effective_pass           : false   # CI-owned smoke, not required here
smoke_vf2_effective_pass          : false   # CI-owned smoke, not required here
```

## First gate attempt — pre-existing flake only

The first gate invocation exited `5` with `Preliminary: NOT READY — TEST
FAILURE`. The single failure was the disclosed pre-existing nondeterministic
test:

```
tests.test_demo_composition.TestReset::test_reset_creates_fresh_runtimes
assert old_runtime_ids.isdisjoint(new_runtime_ids)
```

`id()` is a memory address and CPython may reuse addresses after `reset()`
releases the previous objects, so the assertion is not guaranteed — it is
unrelated to B4 and is explicitly out of scope per Issue #105 §13. Root cause is
demonstrated deterministically in
[`flaky_reset_disclosure.py`](flaky_reset_disclosure.py). The recorded rerun of
the same gate invocation was green on every step.

## Local test records used by the gate

| Step | Result |
| --- | --- |
| P06 full suite (gate) | PASS — 1716/1716 |
| P07 smoke `SMOKE-BW-FACTORY` | PASS (10.2 s) |
| P07 smoke `SMOKE-BW-UI` | PASS (1.9 s) |
| P07 smoke `SMOKE-BW` | PASS (0.2 s) |

`machine-evidence.json` also records the offline captures: B4 slice 27/27 PASS,
regression subset 163/164 then 164/164 on rerun (same pre-existing flake), full
suite 1716/1716 PASS.

## Authorization

`may_open_pr: true`, `may_merge: false`, `may_start_next_task: false`.

No merge was performed and B5 has not been started. The PM does not self-certify
`COMPLETE`, `CLOSED` or `SA APPROVED`.
