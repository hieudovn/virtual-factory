# 17 — C03 Governance Consistency Corrections

**Logical review baseline:** PH00 C02 evidence state @ `81c90d496b5192caf9cfcfc883e2f6e26a7adcac`.
**Authoritative production baseline:** `main` @ `25a02a520f8371345242879954d7822553e9d004`.
**Gate type:** narrow documentation/evidence correction only (`.ai-harness/` only).

## SA finding 1 — §07 contradicted frozen B8

`07-workspace-isolation-test-plan.md` previously said namespace/provenance
threading is a "PH01 + small additive telemetry/provenance change". Corrected:

- §7.1 now states the `outputs.namespace` threading across shared
  runtime-output infrastructure (runtime assembly, telemetry, observation, file
  outputs, MQTT, OPC UA, Sparkplug where applicable, tests) **requires a
  dedicated CORE gate (B8)** and **MUST NOT be folded into PH01**.
- §7.2 now removes the "small additive" wording; any PH01 slice that depends on
  the threaded namespace must wait for the dedicated CORE gate.
- The term "small" is removed from governance language (also in `08` and `14`).

## SA finding 2 — Deterministic workspace-resolution invariant

Added as test **item #11** in §07 and reflected in the enforcement/invariant
section:

> same workspace manifest/version + semantic contract SHA + `scenario_id` +
> model/dependency versions ⇒ same resolved workspace composition, absent
> explicitly changed dependencies.

The test verifies the same pinned inputs resolve the same: plant/config
references; model type bindings; scenario selection; semantic artifact
references; output namespace binding; runtime engine/fidelity selection.

## Files corrected

| File | Change |
|---|---|
| `07-workspace-isolation-test-plan.md` | §7.1/§7.2 aligned to B8 (dedicated CORE gate, NOT folded into PH01); item #11 (deterministic resolution) added; "10 items" → "11 items" |
| `08-core-change-governance.md` | provenance-threading row: "dedicated CORE gate (B8, frozen in C02) — NOT 'small', NOT folded into PH01" |
| `14-risks-and-open-questions.md` | R3 mitigation: "requires a dedicated CORE gate (B8) — NOT folded into PH01" |
| `reports/SHW-VF-PH00.md` | §3 isolation wording → 11-item plan + dedicated CORE gate; §5 wording aligned |
| `CURRENT.md` | updated to C03 READY |

## Full-set search

Searched the complete PH00 report/evidence set for wording implying workspace
provenance threading can be silently implemented inside PH01. No contradictory
wording remains (verified: only corrected "NOT folded into PH01"/dedicated CORE
gate statements remain).

## Compliance

- Production code changed = **NO** (only `.ai-harness/`).
- Workspace loader / provenance threading implemented = **NO**.
- Dedicated CORE gate started = **NO**.
- PH01 started = **NO**.
- B1–B10 reopened = **NO** (only contradictory wording removed).
- No new architecture decision introduced (only governance consistency).
