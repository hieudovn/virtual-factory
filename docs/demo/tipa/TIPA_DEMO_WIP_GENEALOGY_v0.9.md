# TIPA Demo WIP & Genealogy Model — v0.9

> **Status**: M6-S01 freeze.
> **Purpose**: WIP identity lifecycle and AP04 parent-child genealogy for demo.
> Simulation semantic names — NOT claimed as actual TIPA terminology.

---

## 1. Demo WIP State Progression

```
SSO2_SEMI_FINISHED         (from SSO2 upstream)
    ↓
ASSY_STATOR_SIDE_WIP       (after PRE-ASSY, AP01, AP02)
    ↓  (checked at AP03)
ASSY_STATOR_SIDE_WIP       (after AP03 QC)
    ↓  + RSO2_SEMI_FINISHED + components
MOTOR_CORE_ASSEMBLY_WIP    (after AP04 JOIN)
    ↓
MECHANICALLY_ASSEMBLED_MOTOR (after AP05)
    ↓
ELECTRICALLY_TESTED_MOTOR  (after AP06)
    ↓  (after AP07, AP08)
VISUALLY_ACCEPTED_MOTOR    (after AP08)
    ↓
BOXED_MOTOR                (after AP09)
    ↓
PALLETIZED_PRODUCT         (after AP10)
    ↓
RELEASED_FINISHED_GOOD     (after AP11)
```

---

## 2. WIP Identity Rules

| Rule | Value |
|------|-------|
| WIP ID prefix (SSO2) | `SSO2-{seq:04d}` |
| WIP ID prefix (RSO2) | `RSO2-{seq:04d}` |
| WIP ID prefix (MOTOR) | `MTR-{seq:04d}` (after AP04) |
| Pallet/Carrier ID | `PAL-{seq:03d}` |
| ID immutability | WIP ID never changes after creation |
| ID uniqueness | Sequential, per-run scope |

---

## 3. AP04 JOIN — Genealogy

### Conceptual Model

```
Parent A: SSO2-derived ASSY WIP (e.g., SSO2-0001)
Parent B: RSO2 semi-finished WIP (e.g., RSO2-0001)
Components: [bearing_set, rotor_core, ...]

        ↓ JOIN at AP04

Child: MOTOR_CORE_ASSEMBLY_WIP (e.g., MTR-0001)
```

### Genealogy Representation

| Field | Value |
|-------|-------|
| Child WIP ID | `MTR-{seq:04d}` |
| Parent A (SSO2) | `SSO2-{seq:04d}` |
| Parent B (RSO2) | `RSO2-{seq:04d}` |
| Components | List of component IDs (configurable) |
| Join timestamp | `simulation_time_s` |
| Join station | `AP04` |
| Relationship type | `assembly_join` |

### Genealogy Preservation

- Parent identities preserved in child's genealogy context
- MES observation of AP04 includes genealogy relationship
- Component list is configuration-driven (`ap04_component_list`)

---

## 4. Pallet / Carrier Identity Separation

| Concept | Identity | Relationship to WIP |
|---------|----------|---------------------|
| WIP | `MTR-0001` | The motor being produced |
| Carrier | `PAL-027` | The pallet carrying the WIP |

**Rule**: WIP identity ≠ carrier identity. Both are tracked independently.
Carrier may be reused after product release.

---

## 5. Identity at Observation Boundary

| Observation | Subject (WIP) | Context (Carrier) |
|-------------|---------------|-------------------|
| AP01 completion | `SSO2-0001` | `PAL-001` |
| AP04 join | `MTR-0001` (new) | `PAL-004` |
| AP06 test | `MTR-0001` | `PAL-006` |
| AP11 release | `MTR-0001` | `PAL-011` |

---

## 6. Design Risks

| Risk | Mitigation |
|------|------------|
| Actual TIPA WIP naming differs | Simulation names are internal; map to TIPA terms at observation boundary |
| Component list incomplete | Configurable list; add items without code change |
| Genealogy depth > 2 levels | Current model supports direct parent-child; extend if needed post-demo |
