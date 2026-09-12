# VF-vNEXT-G2-C01 · Evidence 08 — C01 corrections

SA review of exact head `571d7378b94c8c228d269d567ca865c2327770cb` required two
fail-closed invariant corrections. Both are applied; no frozen-contract conflict
was revealed, so no G3+/G9 scope expansion was needed.

## C01-1 — Workspace/scope consistency

`scope_path` (a G1 `StructuralPath`) is rooted in exactly one workspace. When
present it must agree with `workspace_id`.

Applied:

- `RunContextV2.__post_init__`: `scope_path.workspace_id != workspace_id` raises
  `RunContextV2Error`.
- `ProvenanceV2.__post_init__`: same check raises `ProvenanceError`.
- `from_discrete_run_context(...)`: constructs the generic context through the
  single validated constructor, so a mismatched `scope_path` cannot produce an
  inconsistent generic context (fail closed via the same invariant).

Tests added:

- `test_provenance_context.py::test_mismatched_scope_workspace_identity_fails_closed`
- `test_provenance_envelope.py::test_mismatched_scope_workspace_identity_fails_closed`
- `test_run_context_adapter.py::test_adapter_cannot_create_mismatched_scope_context`

## C01-2 — Per-signal runtime identity

`runtime_signal_id` is a per-signal execution identity; one frame-level value
cannot truthfully identify every signal in a multi-signal frame.

Applied (smallest correct design — no protocol redesign):

- Removed the frame-level `runtime_signal_id` field from `ProvenanceV2`
  (run/frame provenance only; `to_provenance_v2` parameter removed too).
- `ProvenancedFrame` now derives a deterministic per-signal `runtime_signal_id`
  at record construction: `<scope_path>/<signal.name>` (or `<workspace_id>/<signal.name>`
  when no scope), so distinct signals never share a runtime identity, while the
  common run/frame provenance is shared by every record.
- No PIM `canonical_signal_id` field exists or is fabricated (unchanged).

Tests added / reworked:

- `test_provenance_envelope.py::test_envelope_has_no_frame_level_runtime_signal_id`
- `test_telemetry_provenance_threading.py::test_no_fabricated_canonical_signal_id_and_per_signal_runtime_id`
- `test_telemetry_provenance_threading.py::test_distinct_signals_do_not_share_fabricated_runtime_identity`
  (multi-signal proof: a frame with many signals yields all-distinct runtime ids).

## Preserved (unchanged)

- legacy `build_publishable_frame`; discrete compatibility; `origin_kind=simulation`
  fail-closed; frozen fidelity/data-status vocabularies; deterministic output
  namespace seam; ASSY behavior; no G3+/G9.
