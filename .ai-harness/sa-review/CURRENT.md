# SA REVIEW INBOX

Task: VF-vNEXT-R3-C01
Status: READY FOR SA REVIEW (authoritative canonical reset generation as the output projection epoch)
Parent: VF-vNEXT-R3 (Issue #81) — SA review finding on comment 5643455951
Prerequisite: R3 head 311109c3c6a8f3b6550dfef8659348e0bd70e28e (SA: architecture accepted, C01 required before PASS)

Gate type:
CORRECTION gate. Narrow additive lifecycle seam only — no architecture redesign,
no G22 run identity change, no second lifecycle authority, no R4/R5/SH-WTP/gateway.

Previous head: 311109c3c6a8f3b6550dfef8659348e0bd70e28e
Branch: feature/vf-vnext-r3-c01
New head: b6f04fc860e01fd62e256e3ba9ee8a020d2de9a8
Harness preflight: PASSED

Fixed:
- RuntimeSession owns monotonic reset_generation (alias reset_epoch): incremented
  ONLY when reset() succeeds (a failed reset never advances it), same run_id,
  restarted at 1 by new_attempt()/replay(). It is read-only lifecycle metadata,
  never a run/lifecycle identity.
- CanonicalAssyOutput reads the projection epoch from that seam
  (epoch_source = canonical_session_reset_generation); the poll-to-poll
  regression inference was deleted and a session without the seam fails closed.
- Binding order fixed: federation -> epoch sync -> bridges, with the binding
  recomputed after a fresh-run epoch change (no stale prior-run epoch bound into
  a new-attempt/replay bridge). Output remains read-only (mutation guard intact).
- NEW tests/test_vnext_r3_c01_reset_generation.py (15); migrated the single
  epoch-sensitive assertion in the R3 test module to be epoch-relative.
- Evidence VF-vNEXT-R3-C01/01..05 (all PASS) + regenerated VF-vNEXT-R3 evidence
  under the corrected semantics + report + manifest gate context and the new
  r3c01_reset_generation baseline group.

Focused proof:
- reset_generation 1 -> 2 -> 3; failed reset leaves it unchanged; new_attempt and
  replay restart at 1 (envelope + emitted keys + payload metadata say epoch 1).
- Required regression: poll at S (t=480s) -> reset -> NO poll -> re-step to the
  byte-identical S -> poll: epoch 2 -> 3, 60 new facts emitted, delivered == new
  keys, no collision with pre-reset keys; repeated poll delivers 0.
- In-context reset does NOT rebuild the federation (1 -> 1); a fresh attempt adds
  exactly its own run federation; exactly 1 RuntimeSession; 0 legacy controllers;
  polls leave state and generation unchanged; mutation guard raises.

Regression: C01 15 passed; R3 27; R1 40; R2 27; G22 session/replay 15;
observation/MES contracts 77; full suite 2583 -> 2598 passed; canonical baseline
(41 groups) 41/41 groups PASS at b6f04fc (`BASELINE PASSED: all required groups green`,
`failed_groups: []`), including `checks_preflight` PASSED and
`checks_changed_files` PASSED (21 files) and the new `r3c01_reset_generation`
group (41 groups total; the R3 head had 40).

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED /
NOT_IMPLEMENTED.
