# 09 — Fidelity Governance

Three initial fidelity levels for SH WTP. No physics is implemented in PH00.

## 9.1 Levels

| Level | Meaning | Allowed content | Gate |
|---|---|---|---|
| **LogicalOnly** | Categorical/state transitions; discrete states and their ordering; no engineering numbers | unit states (RUN/STOP/FAULT), stage presence, routing logic, alarm states | default ceiling for SH WTP |
| **SyntheticReference** | Configured illustrative numeric values, **explicitly synthetic** | reference flows, levels, pressures chosen to be representative but tagged `data_status=synthetic` | requires an `output_policy.mode=synthetic_reference` marker |
| **FirstOrder** | Simplified documented physical dynamics, only when parameters are sufficient | mass balance, first-order settling, hydraulic head, disinfection CT | requires documented parameter source + unit consistency + DOMAIN-MODEL gate |

## 9.2 Rules (frozen)

1. No unjustified engineering numbers at `LogicalOnly`.
2. `SyntheticReference` numbers MUST be tagged synthetic (never presented as
   measured plant data) — enforced via the output provenance contract (§10
   `data_status` field).
3. `FirstOrder` is allowed only for model types whose parameters are explicitly
   sourced (PIM/state templates or documented assumptions); no unverifiable
   constants.
4. Fidelity ceiling is declared per workspace in
   `runtime.fidelity_ceiling` (§06); a workspace may not exceed its ceiling.

## 9.3 SH WTP initial mapping (proposal only)

| WTP stage | Suggested initial fidelity |
|---|---|
| Intake / raw-water pump | LogicalOnly + SyntheticReference (pump head) |
| Chemical dosing | LogicalOnly |
| Clarification | FirstOrder mass balance (settling) only if parameters available; else SyntheticReference |
| Filtration | LogicalOnly (RUN/BACKWASH/IDLE) + SyntheticReference |
| Disinfection | FirstOrder CT only if dose/residual parameters available; else LogicalOnly |
| Clear-water / distribution | LogicalOnly + SyntheticReference |

## 9.4 Non-goal

PH00 does not choose formulas, coefficients, or signal values. It freezes the
level taxonomy and the tagging rule so PH01 cannot silently invent numbers.
