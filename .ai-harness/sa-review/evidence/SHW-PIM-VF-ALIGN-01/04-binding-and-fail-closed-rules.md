# 04 — Binding, Mapping & Fail-Closed Rules

## 4.1 Binding model

SH WTP uses `semantic_binding.mode: required`. The workspace manifest pins the
semantic sources (artifact + version + content SHA) and carries a separate
`compatibility` record (see §05). VF never binds by name alone.

## 4.2 Mapping rules (local → canonical, without identity capture)

- VF maps its **runtime-local keys** (`runtime_signal_id`, `model_signal_key`)
  to PIM **canonical ids** via an explicit mapping artifact.
- The local key is **never renamed** to `canonical_signal_id`; the mapping is a
  separate relationship (local_key → canonical_signal_id).
- **Required mappings:** every runtime signal that publishes to a consumer MUST
  resolve to exactly **one valid PIM-owned canonical target** with
  `status: mapped`. For SH WTP the ONLY acceptable required state is
  `mapped` with exactly one valid target. Any of the following MUST fail
  closed: `unmapped`, `review_required`, missing target, ambiguous or
  multiple target.
- **Optional mappings:** auxiliary/internal simulation-only signals may remain
  VF-local with no canonical counterpart, provided they are explicitly tagged
  non-published / non-canonical (simulation-only). They do not participate in
  the fail-closed check.

```text
mapping:
  runtime_signal_id: SHW.T102.LEVEL
  canonical_signal_id: <PIM-owned id>      # read-only; required mappings MUST have exactly one
  kind: required | optional
  status: mapped | unmapped | review_required
```

**Freeze (SH WTP):** for `kind: required`, `status: mapped` with exactly one
valid PIM-owned canonical target is the ONLY acceptable state. `unmapped`,
`review_required`, `missing target`, and `ambiguous/multiple target` MUST fail
closed. Optional simulation-only mappings may stay local/unmapped only when
explicitly non-published and non-canonical.

## 4.3 Fail-closed rules (SH WTP, mode: required)

The workspace is **invalid to load/run** when ANY of:

```text
1. required semantic artifact reference is missing;
2. artifact version is missing;
3. content SHA / hash is missing;
4. content SHA / hash does not match the pinned reference;
5. compatibility.status is not "compatible";
6. a required canonical mapping is not `mapped`, or does not have exactly one
   valid PIM-owned canonical target — i.e. it is `unmapped`,
   `review_required`, missing its target, or has an ambiguous/multiple target;
7. an optional mapping is claimed as published/canonical without a resolved
   canonical target (simulation-only mappings must stay explicitly local and
   non-canonical).
```

On failure: the workspace does not start the simulation; the run is rejected with
a diagnostic that identifies the missing/mismatched/review-required artifact or
mapping. No fallback to fabricated canonical semantics is permitted.

## 4.4 Out of scope here (no implementation)

- No semantic-binding validation code.
- No workspace loader.
- No PIM export tooling.
These are reserved for later, separately-authorized gates.
