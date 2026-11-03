# 05 — Negative, static and executed checks

## Executed read-only VF checks

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_assy_mes_bridge_v1.py \
  tests/test_assy_mes_03_evidence.py \
  tests/test_vf_contract_finality_01.py
# 55 passed, 1 warning
```

```text
PYTHONPATH=src TIPA_ASSY_CONFIG=configs/plants/tipa_assy_demo.yaml \
  ASSY_MES_DEMO_STEPS=24 python -m virtual_factory.assembly.assy_mes_bridge
# 666 messages, 9 types, 666 unique keys, 6 sub-lines
# duplicate_message_keys = 0
```

This proves the producer-side C4 contract, per-attempt quality, measurement
grouping, genealogy, release, LINE_OUT, OEE, and duplicate-poll idempotency.

## Static MES allowlist probe

Command (Python AST, read-only; no Odoo import):

```python
import ast, pathlib
p = pathlib.Path('/tmp/opencode/mes-audit/odoo/custom_addons/mes_core/services/mes_virtual_factory_adapter.py')
tree = ast.parse(p.read_text())
# extract MESSAGE_TYPE_ALLOWLIST, V11_ONLY_MESSAGE_TYPES, EXECUTION_EVENT_DISPATCH
```

Output:

```json
{
  "message_type_allowlist": [
    "mes.checklist_result",
    "mes.execution_event",
    "mes.genealogy_relationship",
    "mes.issue",
    "mes.measurement_result",
    "mes.oee_summary",
    "mes.quality_result",
    "mes.release",
    "mes.run_status"
  ],
  "v11_only": ["mes.checklist_result", "mes.measurement_result"],
  "execution_event_dispatch": [
    "DOWNTIME_END", "DOWNTIME_START", "LINE_OUT",
    "OPERATION_COMPLETED", "REWORK_TRIGGERED", "WIP_ENTERED"
  ],
  "c5_candidate_in_allowlist": false,
  "instrument_calibration_c4_type_in_allowlist": false,
  "record_only_hold": {
    "facade_model": "mes.quality.hold",
    "hold_default_status_open": true,
    "derive_quality_state_filters_source": false,
    "readiness_hold_query_filters_source": false
  }
}
```

## Negative matrix

| Negative case | Expected | Evidence | Result |
|---|---|---|---|
| Unknown C4 `message_type` | rejected machine-readably | MES `_validate_envelope` (`:162-179`) | Static PASS; MES runtime NOT RUN |
| Duplicate message | `duplicate`, same record | MES handlers + VF duplicate poll test | VF PASS; MES runtime NOT RUN |
| Missing/unknown `contract_version` | rejected | MES `_validate_contract_version` (`:199-220`) | Static PASS; MES runtime NOT RUN |
| v1.1-only type on v1 | rejected `message_type_requires_v1_1` | MES `:213-216` | Static PASS; MES runtime NOT RUN |
| Unknown `execution_event.event_type` | rejected, no fallback | MES `_process_execution_event` (`:439-454`) | Static PASS; MES runtime NOT RUN |
| `idempotency_key != message_key` | rejected | MES `_validate_payload_idempotency` (`:183-197`) | Static PASS; MES runtime NOT RUN |
| C5 `vf-qms-evidence-v1` through C4 | rejected | MES allowlist | Static PASS |
| `mes.instrument_calibration` through C4 | rejected | MES allowlist | Static PASS |
| Partial line mapping / absent actor / late Finished / missing quality source | MES-side negative tests exist but require Odoo | MES test files | **NOT RUN** |
| Record-only hold treated as operational | should not be; currently can be | Evidence 04 | **DISCREPANCY** |

## MES test-runtime status

```text
python3 -c "import odoo; print(odoo.__version__)"  -> AttributeError (repo folder, not framework)
python3 -c "import psycopg2"                       -> ModuleNotFoundError
```

MES Odoo adapter/ingress/characterization tests were **NOT RUN**. This is not a
PASS and does not authorize a compatibility claim that depends on live MES
behaviour. The static allowlist/dispatch checks above are the only MES evidence.

## Local full-suite environment note

A local full-suite run with a `gh` token that can see private
`hieudovn/PlantOS` makes the legacy probe
`tests/test_dday_b6_c01_contract_fidelity.py::test_c01_06_plantos_compatibility_records_exact_gap`
fail because it asserts PlantOS is absent. This audit did not modify that test,
the probe module, or PlantOS. Exact-head CI (no PlantOS visibility) passes; the
local gate neutralises `gh` auth so the visibility baseline matches CI.

## PlantOS checks

- PlantOS repository accessible and cloned read-only at
  `23126a470c0a5faff0046251bb979117b115a169`.
- Contract docs present; no PlantOS runtime was started; no broker/API write.
- VF synthetic namespace and provenance inspected in
  `src/virtual_factory/workspaces/plantos_export.py`.
- No claim of PlantOS ingestion/historian proof.
