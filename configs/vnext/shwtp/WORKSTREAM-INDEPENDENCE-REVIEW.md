# VF-vNEXT-G17A — Post-G16 Platform Workstream Independence Review

Gate: `VF-vNEXT-G17A` · Planning/review only. No runtime implementation.

Base (required): `732decd68a02af6f0ee1de1e830631747a99d060` (G16 accepted head).
External PIM evidence: `d10049801a1eb022a7fa2e83badabefb92fb7412`
Verdict: `T108-DIST-EVIDENCE — STILL_INSUFFICIENT` → `UNIT-SHW-L1-T108 -> UNIT-SHW-DIST-P108` stays BLOCKED.

## Purpose

Separate VF work that genuinely depends on unresolved plant semantic authority
from platform capability work that can proceed independently. Establish the
post-G16 principle:

> Plant-specific runtime expansion = evidence-gated.
> Platform capability evolution = may continue independently where semantics do
> not depend on unresolved plant truth.

## Classification

- `CAN_PROCEED_INDEPENDENTLY` — platform capability, no plant truth required.
- `BLOCKED_BY_PIM_EVIDENCE` — requires unresolved PIM semantic authority.
- `SHOULD_WAIT_FOR_RUNTIME_EXPANSION` — platform, but only meaningful after the
  runtime expands.

### CAN_PROCEED_INDEPENDENTLY (16)

| Workstream | Priority | Model |
|---|---|---|
| WS-01 multi-participant federation generalization (>2) | HIGH | Pro |
| WS-02 generic coordinator/runtime lifecycle hardening | MEDIUM | Pro |
| WS-03 deterministic replay across federated participants | HIGH | Pro |
| WS-04 federation diagnostics generalization | MEDIUM | Pro |
| WS-05 evaluation trace abstraction/generalization | MEDIUM | Pro |
| WS-06 scenario input handling | MEDIUM | Pro |
| WS-07 orchestration-policy abstraction (seam only) | HIGH | Pro |
| WS-08 runtime inspection/introspection | MEDIUM | Flash |
| WS-09 composition/topology visualization | MEDIUM | Flash |
| WS-10 run status / health state | LOW | Flash |
| WS-13 online charts for current values | LOW | Flash |
| WS-14 generic boundary/port monitoring | MEDIUM | Flash |
| WS-15 failure propagation semantics across participants | HIGH | Pro |
| WS-16 participant attempt isolation / lifecycle invariants | HIGH | Pro |
| WS-17 heterogeneous executable scope archetypes | MEDIUM | Pro |
| WS-18 future coupling-policy extension seam | HIGH | Pro |

### SHOULD_WAIT_FOR_RUNTIME_EXPANSION (2)

- WS-11 multi-scope runtime UI shell (premature; TIPA+continuous already have
  G6 hierarchy UI; no wider federated runtime to shell over yet).
- WS-12 alarms/events for simulation runtime (G3 fact mechanism already exists;
  runtime-facing alarm surface + domain rules wait for runtime + domain truth).

### BLOCKED_BY_PIM_EVIDENCE (5)

- WS-19 whole-plant SH-WTP execution
- WS-20 DIST-P108 runtime / projection / federation
- WS-21 T110 runtime
- WS-22 Line 2 runtime
- WS-23 chemical/electrical/automation runtime

## Topology distinction (per SA clarification)

- `PIM_AUTHORITATIVE_TOPOLOGY` — still BLOCKED for T108->DIST-P108; never
  fabricated, never inferred from names/descriptions/aggregates.
- `VF_SCENARIO_ASSUMED_TOPOLOGY` — may be considered for a future bounded
  synthetic-reference gate; explicit/versioned/provenanced/reversible; never
  promoted to site truth; never back-propagated into PIM/KG authority.

## Recommended next gate (exactly one)

`VF-vNEXT-G18 — Generic scenario-topology overlay (VF_SCENARIO_ASSUMED_TOPOLOGY)`
capability, model **Pro**. First illustrative use-case: carry T108 -> DIST-P108
as an explicit synthetic scenario assumption (NOT PIM-derived truth).

This satisfies all seven selection criteria — most importantly it is independent
of unresolved T108->DIST-P108 semantic authority, reduces whole-plant federation
risk by enforcing assumed-vs-authoritative topology separation, and does not
broaden SH-WTP runtime authorization. It must preserve:

- PIM relation != VF scenario assumption
- assumption explicit / versioned / provenanced / reversible
- CompositionGraph != semantic authority
- no broad whole-plant runtime authorization
- no silent promotion of assumption to site truth

G18 is NOT started in G17A.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

No runtime, UI, graph, PIM, projection, or federation implementation was
performed. No DIST-P108/T110/Line2/chemical/electrical/automation runtime.
No Gauss-Seidel/iterative/multirate policy. No G4 redesign.

See machine-readable artifact:
`configs/vnext/shwtp/shwtp_workstream_independence_review.json`
