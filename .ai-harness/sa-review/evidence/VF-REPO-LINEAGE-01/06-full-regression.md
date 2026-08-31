# 06 — Full Regression Result (reconciled head `4336521`)

Command:
```
pytest tests -q -p no:cacheprovider --tb=short
```

Result:
```
1647 passed in 29.91s
```

## Baseline comparison

| Head | Tests |
|---|---|
| `main` (MES-01 only, from MES-01 evidence) | 1099 passed |
| accepted ASSY lineage `240d8db` (MES-03 report) | 1611 passed |
| **reconciled head `4336521` (this gate)** | **1647 passed, 0 failed** |

The reconciled head passes the union of both suites with **zero failures** —
no accepted test regressed, and no unrelated production change was required.

## Accepted-behavior preservation proof (Issue #25)

| Required behavior | Evidence |
|---|---|
| six-sub-line ASSY runtime | `test_assy_*`, `test_ops0*`, `test_m6_int_01` all green |
| AP04 genealogy semantics | green (targeted set) |
| AP06 FAIL→retest→PASS | `test_assy_mes_03_evidence.py::TestAp06Measurement` green |
| AP08 NG→reinspect→PASS | `test_assy_mes_03_evidence.py::TestObservations` green |
| terminal `failed_final` semantics | `test_assy_mes_bridge_v1.py` + `test_vf_contract_finality_01.py` green |
| LINE_OUT GOOD/REJECT | `test_assy_mes_bridge_v1.py` green |
| MES v1.1 checklist/measurement/detailed quality evidence | `test_assy_mes_03_evidence.py` (16 tests) green |
| deterministic idempotency / timestamps | `TestContractProvenance`, `TestContractAndIdempotency` green |
| existing continuous/compressor functionality | `test_cli_*`, `test_compressor_*`, `test_benchmark`, `test_fault_engine`, `test_runtime_*` all green |
| single-sub-line MES-01 customer demo (preserved) | `test_demo_assy_mes_v1.py` green |

**Verdict: no accepted ASSY/MES behavior is lost.**
