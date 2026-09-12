# VF-vNEXT-G3 · Evidence 07 — Limitations + STOP assessment

## 1. STOP-condition assessment (Issue #48)

| Stop condition | Assessment |
|---|---|
| Existing accepted observation semantics materially conflict with ARCH-03 | NOT triggered — Observation stays immutable downstream fact; only an additive seam added |
| Alarm cannot be modeled as Event specialization without a breaking domain contract | NOT triggered — `AlarmEventFact(EventFact)` subtype + category ALARM; existing `AlarmManager` signal behavior preserved |
| Correct alignment requires capability/readiness implementation | NOT triggered — none added |
| Correct solution requires G4 coordinator/ports | NOT triggered — none used |
| Provenance alignment requires changing accepted G2 authority | NOT triggered — G2 `ProvenanceV2` reused read-only; no second model |
| Preserving ASSY/continuous behavior requires domain runtime rewrite | NOT triggered — ASSY 354, continuous 61, no runtime rewrite |
| External protocol/schema changes become necessary | NOT triggered — no protocol/export change |
| Scope expands into G4+ | NOT triggered |

## 2. Limitations (explicitly NOT implemented, per Issue #48)

- Capability registry/state/readiness: NOT implemented.
- G4 coordinator/typed ports / composition graph: NOT implemented.
- G5 ASSY federation, G6 UI/frontend, G7 run/scenario control, G8 baseline
  program, G9 PIM semantic binding/canonical resolver, G10 SH-WTP runtime: NOT
  implemented.
- Historian/database retention: NOT implemented (EventStore is in-memory
  append-only; no persistence).
- Alarm notification/escalation/workflow, real-plant acknowledgement/control
  authority: NOT implemented.
- `AssyLineRuntime` and existing `observation/envelope.py`, `service.py`,
  `point.py`, `policy.py`, `router.py`, `projection.py`, `identity.py`,
  `observation/__init__.py`, `telemetry/__init__.py`, `telemetry_frame.py`,
  `discrete/`, `maintenance/`, `core/`: NOT modified.

## 3. Scope-guard verification

- Changed files are all within the G3 allowlist (13 files); file validation
  PASS.
- No G4+ symbols/surfaces introduced; EventStore exposes no mutation/deletion;
  Observation and Event are downstream facts only.

## 4. Head state

- Working tree clean after commit; branch/head pushed; remote head verified.
- Production base `origin/main` = `f5261c8ca18cd4e01779c0274b55270ba028b4e5`
  (inspected; not merged). G4 NOT started.
