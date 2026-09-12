# VF-ARCH-06 · Evidence 05 — Decision E: Observation / Event / Capability / Readiness mapping

## 1. Decision statement

**SH WTP continuous observations, process/equipment state, alarms/events,
water-quality/process capabilities and readiness map to ARCH-03 WITHOUT
fabricating measured/site truth. Runtime truth stays synthetic; projections
cache/index but never mutate; readiness is deterministic aggregation.**

## 2. Mapping

| SH WTP concern | ARCH-03 contract | Mapping rule |
|---|---|---|
| Process/equipment state (tank level, flow, pump status) | Runtime State (only mutable truth) | shared-core runtime owns state; observation is downstream |
| Continuous observations (transmitters, KPI) | Observation (immutable, downstream) | `observation/*` seam; `origin_kind=simulation`, `data_status=synthetic` (B6) |
| Alarms (threshold, state) | Alarm ⊂ Event; Alarm List = projection | `telemetry/alarm_manager.py` projection; alarm lifecycle never mutates the event fact |
| Process/water-quality capabilities | Capability namespaces (platform/execution-domain/workspace-feature) | SH WTP capabilities declared by provider; never workspace-name hard-coded |
| Scope/workspace readiness | Readiness = deterministic aggregation | aggregate capability + binding + runtime + child-scope states; never a hidden evaluator, no arbitrary score |
| Evidence maturity | Provenance ≠ Evidence (VF synthetic ≠ PIM SiteVerified) | VF never upgrades evidence; `DEMO_SYNTHETIC`/`synthetic` never relabeled measured/site truth |

## 3. Fidelity/provenance binding (no fabricated truth)

- `data_status` ∈ {`synthetic`, `simulated_ground_truth`} only (B6); plain
  `measured`/`ground_truth` NOT used for VF-generated data.
- Fidelity field: `logical_only | synthetic_reference | first_order`; SH WTP
  stays `logical_only` unless a later SA gate raises it.
- Live Series is bounded current-run; not a Historian (ARCH-03/ARCH-04).

## 4. What SH WTP must NOT claim

- No `SourceMapped`/`SiteVerified` operational-truth claims at S1.
- No water-quality/process capability states invented without a declared provider.
- No promotion of a measured/site status from synthetic data.

## 5. Conclusion

SH WTP maps to ARCH-03 without new concepts; the only new surface is the
future SH-WTP domain capability declarations (provider-declared), which are
implementation, not architecture.

**Decision E is explicit and evidence-safe.**
