# VF-vNEXT-G1 · Evidence 05 — Regression and test results

## 1. New G1 tests (this gate)

Command:

```
python -m pytest tests/test_workspace_foundation.py \
    tests/test_workspace_validation.py tests/test_workspace_config.py -q
```

Result: **32 passed** (0 failures).

(C01-1 added duplicate-local-id + ambiguity coverage; C02-1 added the
workspace-root-parent negative and the completeness test; C03-1 removed the
over-restrictive self-nesting negative and added the repeated-ancestor-local-id
positive — net 32.)

## 2. ASSY regression oracle (ARCH-05 incl. C01 functional semantics where automated)

Command:

```
python -m pytest tests/test_assy_line.py tests/test_assy_demo.py \
    tests/test_demo_composition.py tests/test_auto_equiv_01.py \
    tests/test_quality.py tests/test_quality_records_projection.py \
    tests/test_demo_assy_mes_v1.py tests/test_assy_mes_bridge_v1.py \
    tests/test_assy_mes_03_evidence.py tests/test_m6_int_01.py \
    tests/test_sub_line_identity.py tests/test_auto_timing.py \
    tests/test_auto_timing_runtime.py tests/test_vf_contract_finality_01.py -q
```

Result: **354 passed** on the deterministic re-run. Covers the ASSY route/quality/
genealogy/timing/LINE_OUT oracle and the ARCH-05 C01 semantic obligations that
are automated. No `AssyLineRuntime` file was modified.

Note (pre-existing test-isolation flake, NOT caused by G1): the ASSY test
`test_demo_composition.py::TestReset::test_reset_creates_fresh_configs` asserts
that old/new config object Python `id()`s are disjoint across a reset. Because
`id()` is a memory address, once the GC frees the old config objects the
allocator can reuse the same addresses for the freshly created configs, so the
`id()` sets overlap intermittently under GC/timing-dependent collection order.
The test passes in isolation and when its whole file runs alone (49/49), and it
is unrelated to the workspace package (`demo_composition` does not import it).
G1 cannot modify this ASSY-domain test (assembly/ is a G1-forbidden path); it is
recorded honestly as a pre-existing baseline anomaly per the Issue #46
requirement to distinguish baseline failures.

## 3. Continuous/compressor baseline (ARCH-06)

Command:

```
python -m pytest tests/test_compressor_train.py tests/test_compressor_states.py \
    tests/test_operating_states.py tests/test_minimal_process_dynamics.py \
    tests/test_minimal_closed_loop.py tests/test_demand_profile.py \
    tests/test_balance.py tests/test_pid_controller.py \
    tests/test_engine_boundary.py tests/test_controller_boundary.py -q
```

Result: **61 passed** (0 failures).
## 4. Full repository suite

Command:

```
python -m pytest tests -q
```

Result: **1679 passed** on the deterministic re-run. One run surfaced the
pre-existing `id()`-based ASSY flake described above (1 failed / 1678 passed);
the re-run was clean (1679 passed, 0 failures). No other baseline exceptions.

## 5. Lint / type checks

The repository has NO configured linter/type checker (no ruff/mypy/black/flake8
in `pyproject.toml`, no setup.cfg/.flake8/pre-commit). The only static check
available is Python compilation:

```
python -m compileall -q src/virtual_factory/workspace   # exit 0
```

Result: compile PASS. There are no configured repo lint/type gates to run beyond
pytest + compilation.
