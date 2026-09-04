# VF-vNEXT-G1 · Evidence 06 — Known limitations (deferred to G2+) + STOP assessment

## 1. Known limitations explicitly deferred (NOT part of G1)

| Deferred item | Gate |
|---|---|
| Execution/runtime boundary behind executable-capable Scopes (G1 models capability only) | G2+ / G4 |
| Runtime Context + Provenance v2 (workspace identity/provenance threading) | G2 |
| Observation / Event / Alarm production alignment | G3 |
| Composition Graph / Coordinator / Typed Ports | G4 |
| TIPA/ASSY federation migration (hosting `AssyLineRuntime` behind scopes) | G5 |
| Shared hierarchical UI primitives | G6 |
| Hierarchical Scenario / Run Control | G7 |
| vNext Platform Regression Baseline gate | G8 |
| Semantic Binding vNext / PIM loader (`semantic_binding.mode: required`) | G9 |
| SH WTP runtime / domain models | G10 |
| Adapters wiring existing runtime objects into the structural model | later |
| Workspace uniqueness across multiple manifests in one context | later (no global registry by design) |

## 2. STOP-condition assessment (Issue #46)

| STOP condition | Assessment |
|---|---|
| Correct implementation requires changing an ARCH-01..06 frozen decision | **Not triggered** — implementation follows ARCH-01..06 as-is (execution boundary, not engine cardinality; container vs executable; identity separation) |
| Generic model cannot represent both TIPA/ASSY and generic continuous without workspace/domain hard-coding | **Not triggered** — builder/loader are fully generic; TIPA/ASSY and generic-continuous are expressed as data fixtures (evidence 03) |
| G1 requires runtime coordinator/composition to function safely | **Not triggered** — G1 is pure structure; no runtime is needed to build/validate the tree |
| Structural identity cannot separate from PIM canonical identity | **Not triggered** — identity module defines only VF structural ids; B2 separation preserved (evidence 03 §5) |
| Preserving ASSY behavior requires rewriting `AssyLineRuntime` | **Not triggered** — `AssyLineRuntime` untouched; ASSY regression 354 passed |
| PH00 workspace config requirements conflict with current production schema | **Not triggered** — config seam is additive under `configs/workspaces/`; no existing schema changed |
| Implementation requires inventing SH-WTP site truth | **Not triggered** — fixtures are generic; no site/evidence claims (evidence 03 §3) |
| Scope expands into G2+ | **Not triggered** — only structural foundation implemented; G2+ items listed above are explicitly absent |

**Conclusion: no STOP condition triggered.**

## 3. Architecture-gap note (G1 is the first implementation gate)

G1 does not alter the ARCH-06 closure conclusion. It adds the production
structural foundation that the later implementation gates (G2..G10) consume.
No platform-level architecture gap is introduced or reopened.
