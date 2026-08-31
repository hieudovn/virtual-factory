# 08 — Core-Change Governance

Frozen promotion ladder for any workspace need. A workspace must NOT silently
change shared layers.

```text
Workspace need
  → implement workspace-local (config / mapping / scenario / workspace-local model)
  → prove the abstraction reusable across ≥2 workspaces
  → separate SA review
  → dedicated CORE / DOMAIN-MODEL gate
  → regression across affected workspaces
  → promote to shared layer (core/ or equipment/ etc.)
```

## 8.1 Classification of likely SH WTP needs

| Likely need | Classification | Route |
|---|---|---|
| New plant config (`shw_wtp.yaml`) | workspace-local | config only — no gate |
| New scenarios (e.g. filter backwash, pump trip) | workspace-local | scenario files — no gate |
| New model types (`clarifier_v1`, `rapid_filter_v1`, `ozone_contactor_v1`, `chemical_doser_v1`, `clearwell_v1`) | **reusable water-treatment domain model** | implement in `equipment/` + `configs/model_types/*.yaml`; dedicated DOMAIN-MODEL gate before promotion |
| Reuse of existing `tank_v1`, `centrifugal_pump_v1`, `control_valve_v1`, `pipe_v1`, transmitters | existing generic core/domain | no change |
| `engine_factory` dispatch extension (`discrete_assembly`, `discrete_generic`) | **shared-core change** | dedicated CORE gate; NOT part of PH00/PH01 |
| Threading `workspace_id` through telemetry/observation provenance | **shared-core/telemetry change** | dedicated CORE gate (B8, frozen in C02) — NOT “small”, NOT folded into PH01 |
| New solver physics (coagulation kinetics, disinfection CT) | **domain model** (FirstOrder at most) | DOMAIN-MODEL gate; requires documented parameters (§09) |

## 8.2 Promotion criteria (frozen)

A component is promoted to shared only when ALL hold:

1. Used by ≥2 workspaces with non-trivial behavior.
2. Fully parameterized by `configs/model_types/*.yaml` (no hard-coded plant).
3. Covered by a `tests/test_*` that runs against ≥2 plant configs.
4. No import of any workspace package (`assembly/`, `simulators/`).
5. SA-authorized via a dedicated CORE/DOMAIN-MODEL gate (never folded into a
   workspace gate).

## 8.3 Anti-promotion (frozen)

- Do NOT promote `simulators/wtp` stage engines or `simulators/vf2` engines
  into `src/virtual_factory` without a dedicated gate.
- Do NOT promote ASSY's hard-coded `tipa.py` topology into the shared core.
- Do NOT add a workspace-specific engine kind for SH WTP.

## 8.4 Stop rule

If a workspace need **cannot** be satisfied without modifying shared
core/domain first → **STOP FOR SA** and request a dedicated CORE/DOMAIN-MODEL
gate before continuing the workspace slice.
