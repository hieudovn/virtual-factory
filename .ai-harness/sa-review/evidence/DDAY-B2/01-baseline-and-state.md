# DDAY-B2 — 01. Baseline, branch, PR and clean-state evidence

**Task:** `DDAY-B2` — Bottled Water Hero Line Runtime Reuse
**SA authorization:** `hieudovn/virtual-factory#102` (B2 ONLY)
**PR:** `#101` — base `main`, head `sa/dday-track-b-20261003`
**Contract:** [`.ai-harness/tasks/DDAY-B2.json`](../../../tasks/DDAY-B2.json)
**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `git`

## Repository truth captured at evidence generation

| Field | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `sa/dday-track-b-20261003` |
| Implementation head (`135113d`) | `135113d` — "DDAY-B2: Bottled Water hero line reuse on the existing discrete runtime" |
| Contract commit | `211c3ef` — "DDAY-B2: task contract authored from SA Issue #102" |
| SA-issued B2 baseline (Issue #102) | `cb908c66ab1de03e1798d9609fdf46d0fc42e675` (frozen B1 head) |
| `origin/main` | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Branch head before the first B2 write | `cb908c66ab1de03e1798d9609fdf46d0fc42e675` |
| Baseline match at B2 start | **yes** — verified by preflight (see below) |

`origin/main` had not advanced: it is still the merge base of this branch.

## Harness preflight (run before any B2 implementation write)

```
$ python .ai-harness/scripts/preflight.py --task .ai-harness/tasks/DDAY-B2.json
PRECHECK PASSED
exit_code=0
```

Run with a clean working tree at the contract commit `211c3ef`. The authoritative
machine record for the final reviewed head is pipeline step **P03** of the task
gate ([`.ai-harness/traces/DDAY-B2/gate-report.md`](../../../traces/DDAY-B2/gate-report.md)).

### Why the contract records two baseline SHAs

`preflight.py` and `verify_changed_files.py` define `expected_base_sha` as the
*repository* baseline: they compare it with `origin/main` and diff it against
`HEAD`. The SA-issued B2 baseline is the *branch* baseline (the frozen B1 head).
Both were true at B2 start, so both are recorded explicitly:

- `expected_base_sha` = `f5261c8…` — harness semantics (`origin/main`)
- `sa_expected_baseline_sha` = `cb908c6…` — SA-issued B2 baseline
- `baseline_semantics_note` — explains the distinction inside the contract

No governance fact was altered; both facts are reported side by side.

## Change set relative to the B1 baseline

```
A  .ai-harness/tasks/DDAY-B2.json
A  configs/workspaces/bottled-water-dday/line.yaml
M  src/virtual_factory/assembly/demo_controller.py
M  src/virtual_factory/assembly/line_runtime.py
A  tests/test_dday_b2_bottled_water_line.py
5 files changed, 1356 insertions(+), 17 deletions(-)
```

Both the full B2 patch and the implementation-only patch are stored verbatim:
[`implementation.patch`](./implementation.patch),
[`implementation-only.patch`](./implementation-only.patch).

## Working tree

The only untracked path at capture time was the evidence directory itself
(`?? .ai-harness/sa-review/evidence/DDAY-B2/`), which is the artifact being
generated. Implementation files were committed before capture.
