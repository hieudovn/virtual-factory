# Task Prompt Template

> **This task is governed by**: `.ai-harness/PM-EXECUTION-CONTRACT.md`
>
> **Task contract**: `.ai-harness/tasks/<TASK-ID>.json`
>
> Before modifying files: run task-contract validation and preflight.
>
> Before final reporting: run the full task gate.
>
> Use only the machine-derived status.
>
> Do not merge or start the next slice unless explicitly authorized for the exact current head SHA.
>
> The contract is mandatory.
>
> Planning is not implementation. Implementation is not readiness.
> Local state is not remote completion. UNKNOWN is not PASS.
> Tool failure is not PASS. Stale CI is not valid CI.
> Desired policy is not actual platform state.
> Deterministic tests are not live verification.
> The PM may not self-certify COMPLETE or CLOSED.

---

## Task Metadata

| Field | Value |
|-------|-------|
| Task ID | `VF-DM-XXX-YYY` |
| Repository | `hieudovn/virtual-factory` |
| Current milestone | `M2-XXX` |

---

## Objective

<!-- Clear, unambiguous task objective -->

---

## Explicit Non-Objectives

<!-- What this task explicitly does NOT do -->

---

## Execution Parameters

| Field | Value |
|-------|-------|
| Required branch | `feature/xxx` |
| Expected baseline SHA | `0000000000000000000000000000000000000000` |

---

## Path Control

**Allowed paths**:

**Forbidden paths**:

---

## Required Deliverables

---

## Required Tests

---

## Required Smoke Checks

---

## Required Remote Evidence

---

## Forbidden Actions

- Do not push directly to `main`
- Do not merge PRs without SA authorization
- Do not start the next milestone slice
- Do not self-certify COMPLETE or CLOSED

---

## Stop Conditions

---

## Acceptance Criteria

---

## Authorization Boundary

| Permission | Granted |
|------------|---------|
| May open PR | Yes |
| May merge | No (SA authorization required) |
| May start next task | No (SA authorization required) |

---

## Required Final Evidence

<!-- Structured evidence report fields -->

---

## Allowed Final Statuses

- `NOT READY — <reason>`
- `IMPLEMENTED — PR OPEN — READY FOR SA REVIEW`
