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
- **Required mappings:** every runtime signal that publishes to a consumer must
  resolve to exactly one canonical signal id (or be explicitly marked
  `unmapped`).
- **Optional mappings:** auxiliary/internal signals may remain VF-local with no
  canonical counterpart, tagged as simulation-only.

```text
mapping:
  runtime_signal_id: SHW.T102.LEVEL
  canonical_signal_id: <PIM-owned id>      # read-only
  kind: required | optional
  status: mapped | unmapped | review_required
```

## 4.3 Fail-closed rules (SH WTP, mode: required)

The workspace is **invalid to load/run** when ANY of:

```text
1. required semantic artifact reference is missing;
2. artifact version is missing;
3. content SHA / hash is missing;
4. content SHA / hash does not match the pinned reference;
5. compatibility.status is not "compatible";
6. a required canonical mapping is missing or "review_required".
```

On failure: the workspace does not start the simulation; the run is rejected with
a diagnostic that identifies the missing/mismatched/review-required artifact or
mapping. No fallback to fabricated canonical semantics is permitted.

## 4.4 Out of scope here (no implementation)

- No semantic-binding validation code.
- No workspace loader.
- No PIM export tooling.
These are reserved for later, separately-authorized gates.
