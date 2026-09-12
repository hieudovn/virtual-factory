# VF-vNEXT-G6 · Evidence 05 — Inspector / Monitoring separation + capability baseline (Issue #51 F/G)

## F — Inspector (object-centric) vs Monitoring (scope-centric)
Frozen in code + tests (`structural_context` semantics):
- Inspector selection is object-centric ONLY when an object is actually
  selected and resolvable in the selected scope (`kind == "object"`).
- Monitoring context is scope-centric (`kind == "scope"`) — no object is
  fabricated when only a scope is selected.
- Changing hierarchy scope never fabricates an object selection; an object
  requested on a scope that does not own it fails closed (never silently
  changes structural ownership).
- Container-only scopes may be selected for monitoring/context but
  `executable_capable == False` and `executable_controls_implied == False`.

Tests: `TestInspectorMonitoringSeparation` (object context only when selected;
object-not-in-scope fails closed; container context implies no executable
controls) and `TestContainer...` in selection tests.

## G — Capability-driven visibility baseline
- Capability comes from G1 `ScopeMode` booleans (`container_only` /
  `executable_capable`) in the projection; never inferred from scope
  name/archetype (navigator renders the badge from these booleans).
- Container-only never presents itself as executable; unavailable/unknown
  features are absent/disabled (mounts are `hidden` until a script renders
  real content) rather than fabricated.
- No full G7 run-control capability policy is implemented.

## No-G7 / no-G8+ checks
- The only new endpoints are read-only GET projections; a route-scan test
  asserts no non-GET `/api/ui` route exists (no run-control/replay/
  orchestration API).
- `hierarchy.py` exposes no run/step/reset function; no G8+/G9/G10 scope
  appears (no new packages outside `ui/`; changed-file allowlist enforced).
