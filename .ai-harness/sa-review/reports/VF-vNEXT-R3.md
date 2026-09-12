# VF-vNEXT-R3 — Canonical Same-Session Observation / MES Output Reintegration

Gate type: **IMPLEMENTATION** (the only authorized implementation gate).
Issue: https://github.com/hieudovn/virtual-factory/issues/81

- Repository: `hieudovn/virtual-factory`
- Branch: `feature/vf-vnext-r3`
- Base (technical branch point / accepted R2 head): `4fc81e72780fe14ba5532407fdc8113b44385617`
- Expected base sha (origin/main): `f5261c8ca18cd4e01779c0274b55270ba028b4e5`
- Contract commit: `.ai-harness/tasks/VF-vNEXT-R3.json`
- Head: (final commit on this branch)
- Harness preflight: **PASSED** (branch + clean tree + expected_base_sha == origin/main)
- Authority refs: R0 (Issue #78, CLOSED/frozen), R2 (Issue #80, accepted), R2V (Issue #82, PASS `ASSY_RICH_SIMULATION_VALIDATED`)

## 1. Objective delivered

ASSY outbound Observation/MES/data projection is restored **on top of the SAME
canonical TIPA `RuntimeSession`** accepted in R1/R2:

```
WorkspaceMonitor
  -> ONE TIPA RuntimeSession
  -> AssyExecutionBridge
  -> TipaAssyFederation
  -> exactly 6 AssyLineRuntime truths
  -> READ-ONLY observation/output projection
       -> ObservationService / ObservationRouter
       -> MESProjection / ProjectedMessage
       -> in-memory/demo gateway evidence
```

`/assy-demo/observations`, `/assy-demo/mes-messages` and `/assy-demo/mes-trace` are
re-enabled as canonical, non-deferred endpoints (they no longer return the R2 503).
No output path constructs, owns, advances, resets or forks simulation truth.

## 2. Changed files

- `src/virtual_factory/ui/assy_output.py` (**NEW**) — `CanonicalAssyOutput`: read-only
  same-session output adapter (canonical binding, composition shim over
  `federation.sub_lines`, projection namespace/epoch, hard read-only mutation guard,
  `observations()/mes_messages()/mes_trace()/identity()`).
- `src/virtual_factory/ui/assy_experience.py` — public `require_federation()` seam;
  `DEFERRED_FEATURES` no longer defers R3 output (jam/recover/run-to-terminal/
  scenario_change stay R4).
- `src/virtual_factory/ui/api.py` — the three R3 endpoints now serve the canonical
  projection; memoized `_get_assy_output()`; error mapper extended with
  `output_unavailable` / `output_mutation_blocked` fail-closed responses.
- `src/virtual_factory/assembly/observation_bridge.py` — **additive** canonical seam
  (`canonical=` binding: canonical run id supersedes the legacy sub-line-local run
  generation; canonical identity in reality context; `source_run_key` +
  `projection_epoch` + scope in fact identity; `projection_epoch_for()`). Default
  (unbound) behaviour is unchanged.
- `src/virtual_factory/assembly/assy_mes_bridge.py` — the same additive seam.
- `tests/test_vnext_r3_canonical_observation_mes.py` (**NEW**, 27 tests).
- `tests/test_vnext_r2_same_session_rich_assy.py` — migrated the obsolete R2
  ownership assertion (the R3 endpoints are no longer 503-deferred); all other R2
  assertions unchanged.
- `.ai-harness/**` — task contract, evidence, report, CURRENT.md, manifest gate
  context + new `r3_canonical_observation_mes` baseline group.

Not modified: `AssyLineRuntime`, R1 production driver/profile, generic G4 coordinator,
`federation/`, `runcontrol/`, SH-WTP, PIM/MES repo, gateway protocols, `configs/`,
`docs/`, `deploy/`, `examples/`.

## 3. Canonical run / provenance identity contract

- Canonical parent-session identity bound into every emitted fact: `workspace_id`
  (`TIPA`), **canonical `run_id` from the `RuntimeSession`**, pinned `scenario_id`,
  pinned profile id, `provenance = simulation_synthetic`, `site_truth = false`,
  `authority = canonical_tipa_runtime_session`.
- Per-fact identity shape: **`canonical_run_id` + source scope (`sub_line_id` /
  `scope_path`) + projection epoch + `source_event_id`**, so the six lines never
  collide on the shared canonical run id. The legacy `ASSY-SLxx:R<n>` key is retained
  only as a subordinate `source_run_key` (never a second lifecycle authority).
- Observation envelopes carry the canonical identity in `context`; MES
  `ProjectedMessage.key`/`payload.run_id`/`payload.idempotency_key` all carry the
  canonical run id (verified in `03-mes-messages.json`).
- Projection epoch: **projection metadata only** (explicitly not a run/lifecycle
  identity). G22 reset/new-attempt/replay run identity semantics are unchanged.

## 4. Evidence (machine-derived: `evidence/VF-vNEXT-R3/`)

| Artefact | Proof | Result |
|---|---|---|
| `01-same-session-output-identity.json` | shell/rich/output share `TIPA-0001`; same six runtime objects; **1 federation + 1 session + 0 legacy controllers** constructed on the API path | PASS |
| `02-observation-facts.json` | 780 canonical facts over 20 steps: 546 operation completions, **72 AP04 genealogy** (child `MTR-0001`), 138 quality, 30 AP11 final-QC, **24 releases**, 130 per sub-line × 6; every fact carries the canonical run id + epoch/scope identity | PASS |
| `03-mes-messages.json` | 1159 accepted-contract MES messages across 7 families (`execution_event`, `quality_result`, `genealogy_relationship`, `release`, `run_status`, `checklist_result`, `measurement_result`) covering all six sub-lines; every key/payload carries the canonical run id; `contract_version=tipa-assy-demo-v1.1` | PASS |
| `04-idempotency.json` | repeated poll without stepping: 0 newly delivered (count unchanged 60 → 60 obs / 97 → 97 MES); step → poll delivers exactly the newly available facts (30) | PASS |
| `05-lifecycle-projection-safety.json` | reset keeps run id `TIPA-0001`, epoch 1 → 2, 60 post-reset facts all in the new epoch with no pre-reset collision; NEW ATTEMPT → `TIPA-0002` fresh namespace (epoch 1, no carry-over); REPLAY → `TIPA-0003` fresh namespace with the same deterministic family multiset | PASS |
| `06-held-one-five-continue-output.json` | hold `ASSY-SL03`: **0** new facts on the held line while the other five advance (6 → 21 facts each); Frame A shows the held line frozen; release resumes (+ facts) | PASS |
| `07-no-simulation-mutation.json` | three full endpoint polls: step count 4 → 4, simulation time 480 → 480 s, run id stable, positions/genealogy/production/quality unchanged for all six lines; injected-mutation guard raises `OutputMutationError` | PASS |
| `08-api-endpoints.json` | `/observations` 200 (60), `/mes-messages` 200 (97), `/mes-trace` 200 (97) — canonical run id, `legacy_runtime_authority: false`; jam/recover/run-to-terminal still 409 `deferred_to: R4` | PASS |

## 5. Regression

| Suite | Result |
|---|---|
| NEW R3 focused (`tests/test_vnext_r3_canonical_observation_mes.py`) | **27 passed** |
| R2 (`test_vnext_r2_same_session_rich_assy.py`, R3-deferred assertion migrated) | passed |
| R1 production semantics (`test_vnext_r1_production_semantics.py`) | 40 passed |
| Observation/MES contract regressions (`test_m6_int_01.py`, `test_assy_mes_bridge_v1.py`, `test_assy_mes_03_evidence.py`, `test_vf_contract_finality_01.py`) | passed **unchanged** (no migration needed — the additive seam is default-off) |
| Full suite (`python -m pytest -q -p no:cacheprovider tests`) | **2583 passed** (2556 → 2583, +27 R3) |
| Canonical baseline at the pushed head (40 groups incl. the new R3 group + `checks_preflight` + `checks_changed_files`) | see the SA submission message (machine-derived at the pushed head) |

## 6. Bounded / explicitly NOT done

- No production transport/gateway work (no MQTT/Kafka/OPC/REST routing, no
  store-forward/retry topology, no multi-gateway deployment, no external MES
  connectivity). R3 proves message generation/projection + demo/in-memory delivery.
- AP05 jam/recover/run-to-terminal/OEE and scenario mutation remain **deferred to R4**
  (409, `legacy_runtime_authority: false`).
- **No R4 parity work started, no R5 consolidation, no SH-WTP expansion, no PIM/MES
  repo change, no rebase onto main, no merge.**
- Output checkpoints/projection epochs are projection state only; they never alter
  runtime state (proved by the mutation guard + the before/after evidence).

## 7. Statements

- One product-path TIPA run authority; exactly six canonical ASSY sub-line runtimes;
  no legacy `DemoController`/`AssyDemoComposition` authority anywhere on the output
  path; zero legacy controllers instantiated.
- Authority unchanged: `vf_runtime_authorization = NOT_AUTHORIZED`;
  `site_authorized_execution = NOT_AUTHORIZED`;
  `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## 8. Verdict

`VF-vNEXT-R3 — READY FOR SA REVIEW`.
