# VF-ARCH-06 · Evidence 10 — Decision J: Risks, STOP assessment, architecture closure, non-decisions

## 1. Risk assessment

| Risk (Issue #45) | Resolution |
|---|---|
| Treating old WTP mini-engine as target architecture | frozen: reference/legacy only (evidence 07) |
| Carrying duplicate mini-engines indefinitely without disposition | frozen disposition + future deprecation after G10 proof (evidence 07) |
| One SH-WTP Workspace = one engine assumption | rejected: archetype ≠ engine; engine at scope level (evidence 02/03) |
| Inventing site topology or SourceMapped/SiteVerified evidence | forbidden: representative/illustrative scopes only; `logical_only` (evidence 02/04) |
| Mixing PIM semantic identity with VF structural/runtime identity | B2 three distinct identities preserved (evidence 04) |
| Implementing semantic binding before identity/provenance foundation | G9 placed after G1+G2+G8 (evidence 08) |
| Resuming SH WTP too early | G10 placed last, after regression baseline (evidence 08) |
| Shared-core changes breaking ASSY | ASSY oracle + cont-baseline on every gate (evidence 09) |
| Roadmap gates overlapping so governance becomes meaningless | one-gate-at-a-time; dependency order frozen (evidence 08) |
| Leaving an unresolved platform architecture gap while claiming complete | addressed below (§3) |

## 2. STOP-condition assessment

| STOP condition | Assessment |
|---|---|
| SH WTP cannot map to ARCH-01..05 without a new platform decision | **Not triggered** — Workspace/Scope/Object + continuous archetype + observation/event/capability + Continuous UI + migration rules cover SH WTP; only domain model + frozen implementation gates remain |
| Accepted PIM/VF contracts conflict materially with target mapping | **Not triggered** — B1–B10 + ALIGN/COMPAT/EXPORT contracts reconciled as-is |
| Current WTP paths require an Owner/SA choice between incompatible architectures | **Not triggered** — both mini-engines are LEGACY/REFERENCE (B7); no competing target |
| Roadmap dependency order cannot avoid premature SH WTP/domain implementation | **Not triggered** — G10 is last, after foundation/binding/regression baseline |
| Closing architecture would hide an unresolved platform-level gap | **Not triggered** — see §3 |
| Safe mapping requires inventing plant/site truth | **Not triggered** — illustrative mapping only, `logical_only` ceiling |

## 3. Architecture closure assessment

**No unresolved platform-level architecture gap remains after ARCH-01..06.**

- ARCH-01..05 already froze: hierarchy/identity, runtime composition/command
  levels, observation/event/capability/readiness, product/UI interaction, and
  TIPA/ASSY migration + regression invariants.
- This gate (ARCH-06) proves SH WTP maps onto all of the above **without any new
  platform concept** — the only remaining work is a finite, ordered set of
  **implementation gates** (G1–G10), each with acceptance evidence and ASSY
  regression protection.
- Therefore: **umbrella #39 may close after SA accepts ARCH-06**, and the
  implementation program (G1..G10) becomes the next phase.

If any future gate discovers a genuine platform-level gap, that gate STOPs for
SA (the per-gate `no-dup-path`/`regression` evidence is the tripwire).

## 4. Frozen decisions (summary)

1. SH WTP = Workspace; process areas/units = hierarchical Scopes; equipment/
   instruments = Objects; site topology evidence-dependent (illustrative only).
2. Continuous/Batch/Discrete = archetypes; no one-engine-per-workspace;
   `runtime.engine: continuous_process` (B3).
3. Shared core owns execution/composition framework; SH-WTP physics is a future
   domain model, not platform architecture.
4. PIM = semantic authority; version/hash-pinned, fail-closed, read-only;
   fidelity ceiling `logical_only` (B1–B10 + ALIGN/COMPAT/EXPORT).
5. Legacy mini-engines = reference/legacy → future deprecation; not the target
   runtime (B7).
6. Observation/Event/Capability/Readiness + Continuous UI map to ARCH-03/ARCH-04
   without fabricated truth.
7. Ordered roadmap G1–G10; one-gate-at-a-time; per-gate acceptance evidence;
   ASSY oracle + cont-baseline on every gate.
8. No platform-level architecture gap remains; umbrella #39 may close after SA
   accepts ARCH-06.

## 5. Explicit non-decisions (deferred to implementation)

1. Implement Workspace/Scope classes.
2. Implement coordinator/ports.
3. Implement provenance-v2.
4. Implement semantic loader/binding.
5. Migrate ASSY.
6. Implement SH WTP runtime/domain models.
7. Delete/refactor legacy WTP mini-engines.
8. Change frontend components.
9. Invent SH WTP site topology/parameters/control logic.
10. Raise fidelity beyond accepted evidence.
11. Change PIM semantic contracts.
12. Begin any implementation gate.

**Decision J is explicit; STOP assessment clean; architecture closes without a
remaining platform-level gap.**
