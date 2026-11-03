# VF OpenCode / DeepSeek on VPS — additive SA issue authoring policy v1

**Authority:** VF PO directive 2026-11-03; [VF #139](https://github.com/hieudovn/virtual-factory/issues/139). **Reference pinned:** [Capacity OS SA Issue Authoring Contract at cf44bbf](https://github.com/hieudovn/Personal-Capacity-OS/blob/cf44bbf2ade39fb3c6f40776b09b58f0c676fd91/docs/operations/sa-issue-authoring-contract.md). **Scope:** `hieudovn/virtual-factory` only.

## 0. Governance precedence and current state

- **Authoritative today:** VF `AGENTS.md`, `.ai-harness/PM-EXECUTION-CONTRACT.md`, `.ai-harness/scripts/preflight.py`, `run_task_gate.py` (P01–P24), `derive_status.py`, exact-head CI and existing evidence schema. This document **does not change their behavior**.
- Reference Capacity OS provides recommended issue metadata and one-task operating discipline. It **does not override VF's machine gate**, branch/PR checks or human review.
- Until PM [#138](https://github.com/hieudovn/virtual-factory/issues/138) is implemented and accepted, the reference's `work_branch`, `resume_policy`, `environment`, `budget`, `touch` fields are **authoring discipline, NOT automated enforcement**. VF canonical machine task field remains `required_branch`.
- **Known deliberate conflict:** Capacity OS recommends draft PR; VF currently returns `NOT READY — GOVERNANCE FAILURE` when `pull_request.draft=true` and only recognizes non-draft OPEN PR at `READY FOR SA REVIEW`. **Do not weaken this gate or mislabel draft as READY.** PM may open draft PR as progress (not READY), and change the **same** PR to ready-for-review before running final exact-head task gate once explicitly supported by tooling. Until then prefer current VF-tested non-draft PR only when ready to satisfy VF gate. #138 will test/lock the transition; no scope implied here.
- VF CI includes a harness self-test step using `|| true`; that step alone cannot prove harness regression passed. Explicit required tests must exit zero in the PM report. Remove swallowing only under a separately authorized executable change, not by this docs PR.

## 1. Single Issue / session / branch / PR

**One issue = one verifiable deliverable = one unique branch = one PR = one OpenCode session**. A dependency chain is a sequential batch, **not** multiple issues in one prompt. One issue's evidence/report is part of its deliverable, not an extra feature. Dispatch capacity 1: stop on first blocker, do not skip ahead or open the next slice. Every issue must have a real unique ID. Work on another repo is forbidden unless separately PO authorized outside this VF flow.

## 2. Issue structure — mandatory authoring data

**Issue body:** Title + one JSON fenced task-contract + Objective + executable Acceptance + Report Format + STOP conditions. The JSON is the full dispatch specification. On task execution, PM must also commit the VF-native task JSON under `.ai-harness/tasks/<task_id>.json` (name/path pinned per issue); no bare issue text substitutes for the existing VF task artifact and gate.

| Metadata | SA rule | VF harness compatibility (current) |
|---|---|---|
| `task_id`, `repository`, `objective` | required exact | existing fields |
| `requested_gate` | `ready_for_sa_review` for final review | existing gate |
| `base_branch` | `main`; no inference from arbitrary checkout | preflight checks `origin/main` |
| `expected_base_sha` | 40-char SHA from remote after dependencies land; **repin** before dispatch | existing required field and drift STOP |
| `work_branch` | unique Issue branch; must match `required_branch` | `required_branch` is canonical now |
| `resume_policy` | `continue_if_branch_exists`; inspect exact branch/PR ownership and commit history; do not rewrite under review | manual until #138 |
| `environment.setup`, `environment.run_tests` | complete project-local Python/venv commands; record first-run feasibility | issue instructions until #138 |
| `allowed_paths`, `forbidden_paths` | explicit minimal paths/prefixes, never any other repository | existing changed-files verifier |
| `required_deliverables`, `required_tests`, `explicit_non_objectives` | exact paths/commands and exclusions | existing fields |
| `budget.max_bash_commands` | bounded realistic command budget | not VPS enforced today |
| `depends_on`, `touch` | list prerequisites and file-family conflicts | authoring only; task dispatch sequential |
| `acceptance_criteria` | preserve VF P01–P24 machine criteria **plus** task-specific observable outcomes | VF schema and gate |

Every task explicitly says: **Do not merge. Do not install OS packages.** No direct main, no deploy or next slice. Don't silently modify baseline or shared worktree, auto-rebase, force push or create a duplicate PR.

## 3. Pre-publish SA checklist

1. Verify remote repo, main head and all prerequisite PRs/issues. If a predecessor is unmerged, mark **BLOCKED** and do NOT dispatch with stale main SHA; record provisional SHA only as `PLANNING` and replace once dependencies merge.
2. Confirm `work_branch` is absent, or named as a deliberate resume of exactly this task and remote PR. Distinct task IDs may never claim the same branch or edit one another's frozen PR.
3. Make one deliverable explicit, list exact output files and required test commands. Include positive + negative acceptance tests; unsupported integration behavior remains `NOT RUN` / `UNKNOWN`.
4. Use `python3` and project `.venv` for VF; `python -m pip install -e '.[dev]'` is **project dependency setup**, not permission to install OS packages. Reuse provisioned environment where possible. Confirm command availability on VPS before dispatch; unavailable preflight becomes blocker.
5. No assumptions about arbitrary OpenCode subagent capabilities. OpenCode PM can choose its internal tools within budget; SA pins interfaces, design decisions and invariants. Don't require remote other-repo reads for VF factory-engine tasks unless explicitly justified.
6. Preserve VF original status rules. A non-draft PR with exact-head CI and all tests still requires SA review; CI success alone is not approval.
7. Short dispatch prompt: only Issue URL and request to honor task contract. Chat outcome: issue, gate, branch, HEAD 40-digit SHA, PR, CI, report URL and blockers if any. Detailed evidence stays `docs/reports/` and `.ai-harness/sa-review/` if required.

## 4. Resume and VPS scope

- No assumption that OpenCode has a clean worktree. First inspect VPS checkout path, branch, dirty state, `origin/main`, assigned Issue, existing PR, task manifest and CI. STOP on mismatch; do not delete/stash/overwrite unknown work.
- Resume `continue_if_branch_exists`: continue a matching task only if branch/PR is its own and base hasn't drifted; append new commits, never rewrite branch under active review.
- No root/host package installation, daemon/timer/service changes, credentials output, production broker/API or other-repo mutations. An Issue must name an explicit authorized exception to alter these; ordinary VF simulation tasks have none.
- If shell/agent budget exhausted: publish a **partial truthful report and blockers** only when safe; do not invent commit or CI; same Issue resumes later.
- Report actual control enforcement vs requested discipline separately. OpenCode scheduler capacity/session behavior is not independently attested by this VF document.

## 5. G1/G2 migration order (not authorizations)

1. [#131](https://github.com/hieudovn/virtual-factory/pull/131) SA workflow governance and this documentation PR independently reviewed/merged; validate exact main SHA.
2. [#138](https://github.com/hieudovn/virtual-factory/issues/138) PM implements the **small** compatibility changes/tests in the existing harness with no bypass and exact-head review.
3. [#132](https://github.com/hieudovn/virtual-factory/pull/132) G1A architecture and schemas enters main through normal SA review/CI.
4. [#133](https://github.com/hieudovn/virtual-factory/issues/133) G1A contract QA: one task, complete JSON, negative fixtures and schema tests, no factory engine code. Authorizing gate only after #132 merged + #138 accepted and baseline re-pinned.
5. [#127](https://github.com/hieudovn/virtual-factory/issues/127) generic Factory Coordinator, then [#128](https://github.com/hieudovn/virtual-factory/issues/128) material ledger: release separately after SA Design Lock. [#136](https://github.com/hieudovn/virtual-factory/issues/136) remains SA design before ASSY integration.
6. Do not broaden to MES/QMS/PlantOS source changes; VF integration assumptions stay at adapters' boundaries.

## 6. Report requirements

Per Issue: paths changed; branch; full remote HEAD; PR URL; exact-head CI run URL/conclusion; required commands & results; semantic PASS/FAIL/NOT RUN; blockers; remaining work. In chat: compact one-line summary and report link. Do not report `COMPLETE`, `CLOSED`, `SA APPROVED` or `NEXT SLICE AUTHORIZED` on behalf of SA.

**Status of this document:** proposed SA policy on PR branch until accepted/merged. It is NOT an executable harness upgrade, and all currently enforced VF gates remain unchanged.
