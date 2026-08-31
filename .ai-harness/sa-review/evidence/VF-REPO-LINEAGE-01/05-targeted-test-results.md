# 05 — Targeted Test Results (reconciled head `4336521`)

Targeted tests covering BOTH lineages' accepted behavior, run on the
reconciliation merge head `43365214144cbf623252158cbbb7ff0dc3ef59ae`.

Command:
```
pytest tests/test_demo_assy_mes_v1.py tests/test_assy_mes_bridge_v1.py \
       tests/test_assy_mes_03_evidence.py tests/test_assy_demo.py \
       -q -p no:cacheprovider --tb=short
```

Result:
```
96 passed in 13.42s
```

## Coverage mapping to Issue #25 required behavior

| Required behavior (Issue #25) | Covered by | Result |
|---|---|---|
| six-sub-line ASSY runtime | `test_assy_demo.py`, `test_assy_mes_bridge_v1.py` | PASS |
| AP04 genealogy semantics | `test_assy_mes_bridge_v1.py` (genealogy facts) | PASS |
| AP06 FAIL→retest→PASS | `test_assy_mes_03_evidence.py::TestAp06Measurement` | PASS |
| AP08 NG→reinspect→PASS | `test_assy_mes_03_evidence.py::TestObservations` | PASS |
| terminal `failed_final` semantics | `test_assy_mes_bridge_v1.py` (LINE_OUT/terminal), `test_assy_mes_03_evidence.py` | PASS |
| LINE_OUT GOOD/REJECT | `test_assy_mes_bridge_v1.py` | PASS |
| MES v1.1 checklist / measurement / detailed quality evidence | `test_assy_mes_03_evidence.py` (16 tests) | PASS |
| deterministic idempotency / timestamps | `test_assy_mes_bridge_v1.py::TestContractProvenance`, `test_assy_mes_03_evidence.py::TestContractAndIdempotency` | PASS |
| single-sub-line MES-01 customer demo (preserved) | `test_demo_assy_mes_v1.py` | PASS |
| existing continuous/compressor functionality | not in this targeted set; covered by full regression (§06) | — |

**96/96 PASS — both lineages' focused tests pass together on the reconciled head.**
