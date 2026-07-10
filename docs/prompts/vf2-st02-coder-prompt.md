# Prompt for Coder — VF-2 ST02: Package Validator

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST02 — Package Validator  
> **Prerequisite:** VF2-ST01 completed (models.py + package_loader.py working)  
> **Previous:** `docs/prompts/vf2-st01-coder-prompt.md`

---

## Context

ST01 built the package loader that reads a PIM-generated JSON package and creates validated Pydantic models. ST02 adds **cross-reference validation** — checking that objects, signals, topology edges, and scenarios are internally consistent.

---

## What You're Building

### `package_validator.py` — Structural & semantic validation

```python
from simulators.vf2.models import VF2Package
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

def validate_package(pkg: VF2Package, strict: bool = False) -> ValidationResult:
    """
    Validate a loaded VF-2 package for internal consistency.
    
    Checks:
    1. package_id is present and non-empty
    2. source_model is present with system="PIM"
    3. Every object has simulation_object_id and canonical_id
    4. Every signal references a valid object (canonical_asset_id exists)
    5. Every topology edge references valid objects (from/to exist)
    6. Boundary endpoints (objects not in objects[]) → warning (compatibility mode)
    7. Every scenario trigger_simulation_object_id references a valid object
    8. Every scenario affected_simulation_signal_ids references valid signals
    9. No orphan signals (signals without a matching object)
    10. No orphan topology edges
    11. Duplicate object IDs, signal IDs, scenario IDs
    
    Args:
        pkg: Loaded VF2Package
        strict: If True, boundary endpoints are errors. If False, warnings only.
    
    Returns:
        ValidationResult with errors and warnings
    """
    ...
```

### Validation Rules (in priority order)

| # | Check | Severity | Detail |
|---|-------|----------|--------|
| V1 | `package_id` non-empty | Error | Must not be null/empty |
| V2 | `source_model.system == "PIM"` | Error | Provenance check |
| V3 | Duplicate `simulation_object_id` | Error | No two objects with same ID |
| V4 | Duplicate `simulation_signal_id` | Error | No two signals with same ID |
| V5 | Duplicate `scenario_id` | Error | No two scenarios with same ID |
| V6 | Every object has `simulation_object_id` + `canonical_id` | Error | Required identity fields |
| V7 | Every signal has `canonical_asset_id` in objects | Warning | Signal-parent object reference |
| V8 | Every signal has `simulation_signal_id` with VF2. prefix | Error | Signal ID convention |
| V9 | Topology edge `from` exists in objects | Warning (compat) / Error (strict) | Boundary endpoint |
| V10 | Topology edge `to` exists in objects | Warning (compat) / Error (strict) | Boundary endpoint |
| V11 | Scenario `trigger_simulation_object_id` exists | Error | Trigger must reference real object |
| V12 | Scenario `affected_simulation_signal_ids` reference signals | Warning | Missing signal reference |
| V13 | Orphan signal (no object-owning-asset found) | Warning | Signal without home |
| V14 | `schema_version == "1.0"` | Error | Already checked in loader, re-check here |
| V15 | `validation_rules` have rule_id, rule_name, severity | Warning | Malformed rule |
| V16 | Scenario `expected_effects[].signal_id` references valid signal (when non-empty) | Warning | Effect target clarity |

### Boundary Endpoint Policy (per SA C3)

```python
def validate_package(pkg, strict=False):
    # ...
    # For each topology edge:
    if edge.from_simulation_object_id not in object_ids:
        if strict:
            errors.append(f"Topology edge from='{edge.from_simulation_object_id}' not in objects")
        else:
            warnings.append(f"Boundary endpoint (from): {edge.from_simulation_object_id} not in objects[] — treated as external")
    # Same for edge.to_simulation_object_id
```

---

## Files to Create/Modify

### 1. `simulators/vf2/package_validator.py` (NEW)

All validation logic. Export `validate_package()` and `ValidationResult`.

### 2. `simulators/vf2/tests/test_package_validator.py` (NEW)

Tests covering:
- Valid package passes with zero errors
- Missing package_id → error
- Missing source_model → error  
- Duplicate object ID → error
- Topology edge with unknown `from` → warning (compat mode), error (strict mode)
- Scenario trigger references nonexistent object → error
- Scenario affected signal references nonexistent signal → warning
- Orphan signal → warning
- Empty objects[] → error
- Strict mode boundary check → error instead of warning

```python
import pytest
from pathlib import Path
from simulators.vf2.package_loader import load_package
from simulators.vf2.package_validator import validate_package, ValidationResult

GOLDEN = Path(__file__).resolve().parent.parent / "examples" / "sample_pim_package.json"

class TestPackageValidator:
    
    def test_golden_fixture_passes(self):
        pkg = load_package(GOLDEN)
        result = validate_package(pkg)
        assert result.valid
        assert len(result.errors) == 0
    
    def test_missing_package_id(self):
        pkg = load_package(GOLDEN)
        pkg.package_id = ""
        result = validate_package(pkg)
        assert not result.valid
    
    def test_boundary_endpoint_warning_compat_mode(self):
        pkg = load_package(GOLDEN)
        # Add a topology edge to nonexistent object
        from simulators.vf2.models import VF2ProcessEdge
        from copy import deepcopy
        pkg = deepcopy(pkg)
        bogus_edge = VF2ProcessEdge(
            from_simulation_object_id="VF2-REF-PMP-101A",
            to_simulation_object_id="VF2-NONEXISTENT",
            relation_type="FLOWS_TO"
        )
        pkg.topology.process_edges = list(pkg.topology.process_edges) + [bogus_edge]
        result = validate_package(pkg, strict=False)
        assert result.valid  # compat mode: still valid
        assert any("Boundary endpoint" in w for w in result.warnings)
    
    def test_boundary_endpoint_error_strict_mode(self):
        # Same setup, strict=True → error
        ...
    
    def test_duplicate_object_id(self):
        ...
    
    # ... (12+ tests total)
```

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | Golden fixture passes validation (0 errors) | `validate_package(golden).valid == True` |
| AC-2 | Missing package_id → not valid | Error reported |
| AC-3 | Duplicate object IDs → error | Error reported |
| AC-4 | Duplicate signal IDs → error | Error reported |
| AC-5 | Topology edge to boundary (compat mode) → warning, still valid | Warning logged |
| AC-6 | Topology edge to boundary (strict mode) → error, not valid | Error reported |
| AC-7 | Scenario trigger to nonexistent object → error | Error reported |
| AC-8 | Orphan signal → warning | Warning logged |
| AC-9 | All ST02 tests pass | `python -m pytest simulators/vf2/tests/test_package_validator.py -v` |
| AC-10 | VF-1 regression OK | `python -m pytest simulators/wtp/tests/` — 13/13 |
