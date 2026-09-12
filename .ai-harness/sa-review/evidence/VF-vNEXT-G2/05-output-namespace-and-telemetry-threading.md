# VF-vNEXT-G2 · Evidence 05 — Output namespace + telemetry provenance threading

## 1. Output namespace (PH00 B2/B8)

`derive_output_namespace(workspace_id, *, output_namespace=None,
output_namespace_suffix=None)`:

- deterministic: same inputs → same namespace;
- an explicit `output_namespace` wins and is sanitized as-is;
- otherwise derived from `workspace_id` (plus optional suffix) — still a DISTINCT
  output-routing concept, never the workspace identity, never a PIM canonical id;
- path-safe sanitization (non-alphanumeric → `-`), no global registry, no
  workspace-name special cases;
- empty `workspace_id` fails closed.

## 2. Telemetry provenance threading (additive)

`telemetry/telemetry_frame.py`:

- `build_publishable_frame(...)` — **legacy seam unchanged**; returns plain
  `list[SignalValue]` with NO provenance (no fabricated provenance for legacy
  callers).
- `build_provenanced_frame(..., provenance)` — additive G2 seam; returns an
  immutable `ProvenancedFrame(signals, provenance)` using the EXACT same policy
  filtering + signal coercion.
- `ProvenancedFrame.to_records()` — flattens signal fields verbatim and attaches
  the provenance envelope as a separate per-record `provenance` section (never
  overwrites signal fields, never fabricates a canonical id).
- `ProvenancedFrame.to_dict()` — deterministic serialization.

Domain `SignalValue` truth semantics are unchanged; provenance lives BESIDE the
signals, never merged into them.

## 3. Output-policy preservation

`build_provenanced_frame` reuses `build_publishable_frame`, so
`OutputPolicy.can_publish` behavior (industrial categories; `internal_truth`
excluded) is identical. Tests assert `internal_truth` never leaks through the G2
seam.

## 4. Protocol/export propagation decision

`mqtt_gateway`/`opcua_gateway` consume `list[SignalValue]` via `publish_frame`
and are NOT modified (their SignalValue seam is unchanged). Provenance is
threaded at the common `telemetry_frame` boundary; attaching it to protocol
publishers is deferred (no breaking external schema required in G2).
