# VF-vNEXT-G4 · Evidence 08 — Limitations + STOP assessment

## 1. STOP-condition assessment (Issue #49)

| Stop condition | Assessment |
|---|---|
| Safe solution requires a single universal engine/timestep/scheduler | NOT triggered — mechanism-neutral participant; different cadences proven |
| Existing G1/G2/G3 authority contracts must be broken | NOT triggered — G1 identity reused, G2 identity referenced, G3 untouched |
| Correct cyclic composition requires a domain-specific numerical solver | NOT triggered — cycles safe via staged detached exchange; no solver implemented |
| Typed port semantics cannot be separated from PIM canonical ownership | NOT triggered — ports are VF structural identity; no PIM canonical |
| Safe integration requires rewriting AssyLineRuntime | NOT triggered — assembly/ untouched |
| Compatibility requires breaking PlantGraph/current core ports | NOT triggered — distinct additive seam; core untouched |
| Failure semantics require transactional rollback/checkpoint support | NOT triggered — no rollback claimed; honest fail-closed semantics |
| Scope expands into G5+ | NOT triggered |

## 2. Explicitly NOT implemented (deferred)

G5 ASSY federation; G6 UI; G7 run-control/UI/API, replay, restart policy; G8
regression program; G9 semantic binding/PIM resolver; G10 SH-WTP; final
material/energy schemas; numerical coupling solver/algebraic-loop iteration;
historian/database; real-plant control; frontend changes; AssyLineRuntime
rewrite; legacy WTP mini-engine migration/deletion.

## 3. Scope-guard verification

- Changed files all within the G4 allowlist (15 files); file validation PASS.
- `workspace/`, `provenance/`, `observation/`, `telemetry/`, `discrete/`,
  `assembly/`, `core/`, `ui/`, `integration/`, `protocols/` untouched.

## 4. Head state

Working tree clean after commit; branch/head pushed; remote head verified.
Production base `origin/main` = `f5261c8ca18cd4e01779c0274b55270ba028b4e5`
(inspected; not merged). G5 NOT started.
