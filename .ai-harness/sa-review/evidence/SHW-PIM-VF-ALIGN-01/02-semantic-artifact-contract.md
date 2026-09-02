# 02 — PIM-Owned Semantic Artifact Contract (conceptual export)

This defines **what PIM owns and may export** as the immutable semantic handoff
input. All fields are conceptual — no export tooling is implemented in
ALIGN-01, and VF must not invent site-verified facts PIM has not established.

## 2.1 Canonical object/asset artifact

```text
artifact_id            # name of the exported artifact
version                # semver
content_sha            # content hash of the exact artifact

objects[]:
  canonical_object_id  # PIM-owned; stable identity within the applicable semantic contract/namespace (no identifier scheme chosen here)
  classification       # asset/area/system/equipment type taxonomy (PIM-owned)
  name / label
  relationships[]      # parent/child, part-of, feeds/feeds-by (structural truth)

signals[]:
  canonical_signal_id  # PIM-owned; stable identity within the applicable semantic contract/namespace (no identifier scheme chosen here)
  object_ref           # canonical_object_id this signal reports on
  classification       # signal type taxonomy (PIM-owned)
  unit                 # engineering unit (where established)
  observability        # NON-NORMATIVE example only (e.g. measurable | inferred | configurable)
                       #   — not a PIM enum unless proven by an authoritative PIM artifact

signal_state_map[]:    # where defined
  canonical_signal_id
  state_dimension      # e.g. operating_state, quality_state, availability
  allowed_values[]     # vocabulary for that dimension (PIM-owned)
```

## 2.2 State-dimension vocabulary artifact (PIM-owned)

```text
state_dimensions[]:
  dimension_id         # NON-NORMATIVE example (e.g. operating_state)
  vocabulary[]         # enum of values (PIM-owned); SH WTP MUST NOT flatten into one giant enum
  semantics            # textual meaning of each value (PIM-owned, when established)
  origin               # NON-NORMATIVE example — PIM-owned evidence/maturity concept;
                       #   SourceMapped ≠ SiteVerified ≠ site truth
```

## 2.3 Evidence maturity / source status (PIM-owned, never mutated by VF)

The values below are **NON-NORMATIVE examples only** — ALIGN-01 freezes the
ownership and structural fields, NOT a new PIM vocabulary. The exact enum is
established by an authoritative PIM artifact.

```text
evidence_maturity:    # per object/signal/dimension; NON-NORMATIVE example:
  - SourceMapped      # mapping/provenance to an identified source — does NOT imply
                      #   the mapped fact has been site-verified or is plant ground truth
  - SiteVerified      # verified at site — DISTINCT from SourceMapped
  - Proposed          # not yet verified
  - Unknown           # not established

parameter_status:     # per parameter required by a model; NON-NORMATIVE example:
  - known             # value + source available
  - missing           # required but not available → fail-closed / review_required
  - unknown           # not established
  - review_required   # present but not yet compatibility-reviewed
```

**Clarification (frozen):** `SourceMapped` proves mapping/provenance to an
identified source system; it does NOT imply site verification or plant ground
truth. `SourceMapped` and `SiteVerified` remain distinct evidence concepts.

## 2.4 Artifact pinning (consumed read-only)

Every consumed artifact is referenced by:

```text
artifact name
version
commit SHA / content hash
```

VF stores the reference, not an editable copy. A changed SHA flips the
compatibility status to `review_required` until re-reviewed (see §04/§05).
