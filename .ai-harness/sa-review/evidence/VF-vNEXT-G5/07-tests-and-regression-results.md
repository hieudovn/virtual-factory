# VF-vNEXT-G5 · Evidence 07 — Tests + regression results

## 1. New G5 tests

Command: `python -m pytest tests/test_federation_tipa_assy.py -q`

Result: **26 passed** (0 failures). Covers the Issue #50 test set:
1 exact TIPA → ASSY → six sub-line hierarchy; 2 ASSY container-only cannot
register; 3 six sub-lines executable-capable with canonical paths; 4 six
adapters wrap six existing runtimes without rewriting; 5 adapter time ==
wrapped runtime time; 6 representative standalone vs federated parity at
supported shared boundaries (release, AP04 join, real-config six-line replica);
7 runtime/config/feed/RNG isolation; 8 no direct cross-scope mutation; 9
identity drift/mismatch fails closed via existing G4 rules; (10 ASSY oracle
green — below); 11 no G6+ (evidence 06). Includes the G5-C01 decoupling tests
(`test_production_host_initializes_without_demo_composition`,
`test_federation_api_exposes_no_demo_policy_authority`).

## 2. Regression groups (Issue #50)

| Group | Result |
|---|---|
| New G5 tests | **26 passed** (incl. C01 decoupling) |
| G4 composition tests | **56 passed** |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm_manager) | **328 passed** |
| Core graph/port/runtime | **21 passed** |
| Discrete runtime/scheduler | **279 passed** |
| Complete ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1875 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 3. Flakes

None surfaced in the G5 runs (ASSY oracle and full suite both clean).

## 4. Lint / type / compile / harness

- No configured ruff/mypy/black (unchanged).
- `python -m compileall -q src/virtual_factory/federation` → exit 0.
- No modified file outside the G5 allowlist (verify_changed_files PASS).
- Task-contract preflight: baseline matches `origin/main`
  `f5261c8ca18cd4e01779c0274b55270ba028b4e5`; branch
  `feature/vf-vnext-g5` created from required base
  `ae0a86e4ad8add77c731fbd597534f24a2f7b575`; clean after commit.
