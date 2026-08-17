# VF-CONTRACT-FINALITY-01 — changed-files.md

Production code (additive only):

| File | Change |
|---|---|
| `src/virtual_factory/assembly/quality_records.py` | `QualityRecord` gains `terminal: bool = False` (frozen dataclass, defaulted → backward compatible) and `terminal` in `to_dict()` |
| `src/virtual_factory/assembly/line_runtime.py` | `_execute_quality_disposition` stamps `terminal = disposition in ("FAIL","NG") and attempt >= qcfg.max_attempts` on the record — the SAME condition as the existing FAILED_FINAL transition (no logic change) |
| `src/virtual_factory/assembly/observation_bridge.py` | `_quality_fact` emits `is_terminal` + `terminal_state`; `assy.quality_result` FieldPolicy allow-list extended with both fields; imports `QualityStatus` |

Tests:

| File | Change |
|---|---|
| `tests/test_vf_contract_finality_01.py` | NEW — 16 tests covering gate §12 requirements 1–16 |

No change to:
- `src/virtual_factory/observation/projections/mes.py` (MESProjection already passes envelope payload fields through generically)
- runtime transition logic, retry policy, release conditions, routing, timing,
  AUTO/MANUAL equivalence
- any other message type or observation point
- MES repo (untouched)
- Docker deployment files (unchanged — image picks up new `src` on rebuild)

No MES/Odoo IDs, no AP06/TIPA-specific field names, no consumer-specific
concepts in generic core.
