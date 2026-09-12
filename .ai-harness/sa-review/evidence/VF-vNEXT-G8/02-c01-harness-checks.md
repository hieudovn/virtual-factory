# VF-vNEXT-G8-C01 · Evidence 02 — Harness checks as first-class baseline groups

SA review `5557658309` of exact head `6914149df7f2cf04953a0d9e4ad6845ac43a80eb`
found the manifest/entrypoint did not include the required compile/static/
preflight/changed-file harness checks. This C01 correction stays strictly in
G8/harness scope. No `src` change; no G1-G7 semantics change; no G9/G10.

## What changed
- `vnext_baseline_manifest.json` → version 1.1.0. Groups are now typed and
  first-class: every group carries `type: "pytest"` (files/directory) or
  `type: "command"` (explicit repo-native command run from the repo root).
  Four non-pytest command groups were added: `checks_compile`,
  `checks_static_lint_type`, `checks_changed_files`, `checks_preflight`.
  Stale/brittle per-group `expected` metadata was removed (no hard-coded counts
  that contradict the current baseline). A truthful `static_checks` note states
  the repo configures no ruff/mypy/black/pyright/flake8 and none is invented.
- `run_vnext_baseline.py` — generalized minimally: manifest groups execute as
  pytest groups OR explicit command groups. Bounded substitutions in command
  `cmd`: `{python}` → running interpreter; `{changed_files_file}` →
  materialized `git diff --name-only <changed_files_base> HEAD` artifact for
  `kind: "changed_files"` commands. Every command group runs from the repo
  root, reports its group id + PASS/FAIL, contributes non-zero to overall
  failure, and appears in the optional JSON output alongside pytest groups.
- `check_repo_static_config.py` (new) — truthful static/lint/type check:
  reports "no ruff/mypy/black/pyright/flake8 configured" (passes), and FAILS if
  a configured static tool is detected that the baseline does not execute.
- `tests/test_vnext_g8_entrypoint.py` (new, 3 tests) — bounded smoke proof of
  the COMMAND-group code path: a failing command group makes the canonical
  baseline exit non-zero and names the group; a passing command group exits 0;
  `{python}` substitution works. (These are added to the `g8_cross_gate_invariants`
  baseline pytest group so the default baseline exercises them.)

## Command groups in the manifest (required checks)
| Group | Command (repo-native) | Purpose |
|---|---|---|
| checks_compile | `python -m compileall -q src tests .ai-harness/regression .ai-harness/scripts` | compile check used by the repo |
| checks_static_lint_type | `python .ai-harness/regression/check_repo_static_config.py` | truthful static/lint/type check (none configured; none invented) |
| checks_changed_files | `python .ai-harness/scripts/verify_changed_files.py --task VF-vNEXT-G8.json --changed-files <diff base..HEAD>` | changed-file validation used by the repo |
| checks_preflight | `python .ai-harness/scripts/preflight.py --task VF-vNEXT-G8.json` | harness preflight used by the repo (runs last; clean committed tree required) |

Default canonical invocation `python .ai-harness/regression/run_vnext_baseline.py`
runs the COMPLETE required baseline (12 pytest groups + 4 command checks).

## Results (post-commit canonical baseline run)
See `01-regression-baseline-and-invariants.md` + report for the authoritative
group-by-group table. Command checks: compile PASS, static PASS (truthful no-tool),
changed_files PASS, preflight PASS. Full suite PASS (1968 passed: 1956 + 9 G8
invariants + 3 entrypoint smokes). Overall baseline PASS.

## Flake observation (recorded honestly)
The first full canonical run reported `assy_oracle` FAIL once on the pre-existing
accepted test `tests/test_demo_composition.py::TestReset::test_reset_creates_fresh_configs`
(an object-identity assertion; `id()` reuse after GC). This is a known
nondeterministic pattern in that ACCEPTED test and is NOT caused by C01 (no
src/gate test change; the same module passes in the full suite, alone, and on
the authoritative re-run below). The authoritative complete canonical baseline
re-run is green (assy_oracle 354 PASS, full_suite 1968 PASS).

## Confirmation
- No `src/` change; no architecture/runtime semantics change; no new framework.
- G9/G10 NOT started.
