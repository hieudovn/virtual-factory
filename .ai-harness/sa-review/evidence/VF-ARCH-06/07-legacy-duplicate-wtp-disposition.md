# VF-ARCH-06 · Evidence 07 — Decision G: Legacy / duplicate WTP mini-engine disposition

## 1. Decision statement

**The two standalone WTP runtime paths are frozen with an explicit disposition;
nothing is deleted or refactored in this gate.**

## 2. Disposition matrix

| Path | Frozen disposition | Rationale |
|---|---|---|
| `simulators/wtp` | **reference only** → **future deprecation** after regression proof | PH00 B7 LEGACY/REFERENCE; hard-coded 92 signals; own OPC UA/ingest/dashboard; not the target runtime |
| `simulators/vf2` | **reference only** (PIM-package binding pattern) → **candidate for extraction/adaptation** of the package-driven binding ideas | PH00 B7; evidences the dual-ID / PIM-package pattern that semantic-binding vNext will formalize |
| `src/virtual_factory` shared continuous core | **reusable shared-core** (keep, evolve) | plant-agnostic; proven by continuous/compressor tests |

## 3. Rules (frozen)

- Do **not** delete or refactor `simulators/wtp` / `simulators/vf2` now.
- Do **not** import either mini-engine as an SH WTP runtime dependency.
- Do **not** carry duplicate mini-engines indefinitely: the roadmap (evidence
  08) ends with SH WTP runtime vNext; after its regression proof, the legacy
  paths are deprecated (a future SA-reviewed gate performs the removal).
- `simulators/vf2` may contribute the **package/binding pattern** (dual IDs,
  package validation, fail-closed checks) as reference material for Semantic
  Binding vNext — extraction happens in that future gate, not here.

## 4. Duplicate-path risk

The duplicate-path risk is **bounded**: the two mini-engines are self-contained
under `simulators/`, never linked into `src/virtual_factory` runtime (only UI nav
links). No third runtime path exists. The roadmap's "no duplicate runtime path"
acceptance evidence (evidence 09) applies to the NEW shared path, which must not
fork.

**Decision G is explicit.**
