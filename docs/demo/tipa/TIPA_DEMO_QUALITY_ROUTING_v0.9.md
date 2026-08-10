# TIPA Demo Quality & Routing Model — v0.9

> **Status**: M6-S01 freeze.
> **Purpose**: Quality station behavior for demo — PASS/FAIL/HOLD/RETEST.
> Provisional behavior is clearly marked.

---

## 1. AP03 — Manual QC / Checklist

| Field | Value | Status |
|-------|-------|--------|
| Type | Manual checklist inspection | CONFIRMED_FROM_TIPA_DOCUMENT |
| Checks | Configurable checklist items | PROVISIONAL_FOR_DEMO |
| Measurements | Selected dimensional/visual checks | PROVISIONAL_FOR_DEMO |
| PASS route | → AP04 | PROVISIONAL_FOR_DEMO |
| FAIL/HOLD route | WIP held at AP03; operator review | PROVISIONAL_FOR_DEMO |
| Retry | Manual resolution → retest or escalate | PROVISIONAL_FOR_DEMO |

**Demo behavior**: PASS by default; configurable FAIL probability for scenario B.

---

## 2. AP06 — Electrical / Functional Test

| Field | Value | Status |
|-------|-------|--------|
| Type | Electrical resistance + functional test | CONFIRMED_FROM_TIPA_DOCUMENT |
| Measurements | R_U-V, R_V-W, R_W-U (Ω), rotation direction, sound | PENDING_TIPA_CONFIRMATION |
| PASS route | → AP07 | CONFIRMED_FROM_TIPA_DOCUMENT |
| FAIL route | → HOLD → RETEST | PROVISIONAL_FOR_DEMO |
| RETEST limit | 2 retests max; then remain HOLD | PROVISIONAL_FOR_DEMO |
| Measurement spec | Configurable min/max per parameter | PROVISIONAL_FOR_DEMO |

### AP06 State Machine (Provisional for Demo)

```
TEST_START
    ↓
MEASURE (R_U-V, R_V-W, R_W-U, rotation, sound)
    ↓
EVALUATE (all within spec?)
    ├─ YES → PASS → AP07
    └─ NO  → FAIL → HOLD
                    ↓
                  RETEST (if < max_retests)
                    ├─ PASS → AP07
                    └─ FAIL → HOLD (permanent for demo)
```

**⚠️ PROVISIONAL_FOR_DEMO**: Actual TIPA FAIL routing is not confirmed.
This model is for demo purposes only.

---

## 3. AP08 — Visual Inspection

| Field | Value | Status |
|-------|-------|--------|
| Type | Visual / camera inspection | CONFIRMED_FROM_TIPA_DOCUMENT |
| PASS route | → AP09 | CONFIRMED_FROM_TIPA_DOCUMENT |
| NG route | → HOLD → REINSPECT | PROVISIONAL_FOR_DEMO |
| Defect classification | Configurable list (scratch, misalignment, ...) | PROVISIONAL_FOR_DEMO |
| REINSPECT limit | 1 reinspect max | PROVISIONAL_FOR_DEMO |

**⚠️ PROVISIONAL_FOR_DEMO**: Actual TIPA NG disposition is not confirmed.

---

## 4. AP11 — Final QC / Release

| Field | Value | Status |
|-------|-------|--------|
| Type | Final inspection + release | CONFIRMED_FROM_TIPA_DOCUMENT |
| Checks | Packaging integrity, label, documentation | PROVISIONAL_FOR_DEMO |
| PASS route | → RELEASED_FINISHED_GOOD | PROVISIONAL_FOR_DEMO |
| HOLD route | → Held for review | PROVISIONAL_FOR_DEMO |
| Sampling | 100% for demo (actual sampling TBD) | PENDING_TIPA_CONFIRMATION |

---

## 5. Quality Station Configuration

All thresholds must be configurable:

| Station | Configurable Items |
|---------|-------------------|
| AP03 | Checklist items, measurement limits |
| AP06 | Resistance min/max, rotation direction, sound threshold, max retests |
| AP08 | Defect types, max reinspects |
| AP11 | Release criteria |

---

## 6. Design Risks

| Risk | Mitigation |
|------|------------|
| Actual AP06 FAIL routing differs | Configurable routing; change target without code change |
| AP08 NG classification unknown | Configurable defect list |
| AP11 sampling unknown | 100% for demo; configurable later |
