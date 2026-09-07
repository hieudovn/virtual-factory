# VF-vNEXT-G12C-C01 — Authority consistency fix — Evidence

Correction: SA comment `5566580805` (base `73aab0322613251293de0c719b9fc1691fcc3a4a`).

## Blocker addressed

The G12C admission artifact simultaneously asserted
`synthetic_reference_execution = PENDING_LATER_PIM_REVIEW` while also granting
`SYNTHETIC_REFERENCE_ALLOWED` for T106/T108 and authorizing T108 as the first G13
slice. The global pending state contradicted the already-completed candidate-scoped
review.

## Fix (smallest planning/test-only correction)

Replaced the ambiguous global `synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`
with explicit, deterministic, candidate-scoped authorization semantics in
`shwtp_synthetic_runtime_admission.json`:

- `review_status = COMPLETE`
- `authorization_mode = CANDIDATE_SCOPED`
- `authorized_candidates = [UNIT-SHW-L1-T106, UNIT-SHW-L1-T108]`
- `first_authorized_slice = [UNIT-SHW-L1-T108]`
- `blocked_candidates = [UNIT-SHW-WASH-T110]`

`g13_authorization_plan` aligned to the same field names
(`first_authorized_slice` / `authorized_candidates` / `blocked_candidates`).

Unchanged: `vf_runtime_authorization = NOT_AUTHORIZED`,
`site_authorized_execution = NOT_AUTHORIZED`, all PIM pins, fidelity ceilings, and the
three candidate decisions (T106 ALLOWED, T108 ALLOWED, T110 BLOCKED_PENDING_EVIDENCE).

## Semantics made explicit

- NO blanket SH-WTP runtime authorization (mode = CANDIDATE_SCOPED).
- T108 is the first authorized G13 slice; T106 allowed only later/optional.
- T110 remains blocked; site-faithful execution remains NOT_AUTHORIZED.

## Strengthened regression (`tests/test_vnext_g12c_admission_review.py`)

Added:
- `test_scoped_authorization_semantics`
- `test_no_pending_review_with_authorized_candidates` — fails if any authorized
  candidate/slice exists while the artifact still has a pending-review state
  (asserts `review_status == COMPLETE`, `synthetic_reference_execution` absent,
  and `PENDING_LATER_PIM_REVIEW` absent).
- `test_no_blanket_shwtp_authorization`

G12C tests now 16 (was 13). Full suite 2093 passed.

## Unchanged

No production runtime code, no G4 projection, no PIM change, no G13 implementation.
