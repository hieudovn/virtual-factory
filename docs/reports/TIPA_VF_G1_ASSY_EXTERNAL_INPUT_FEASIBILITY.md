# TIPA-VF-G1-ASSY-FEAS-01 — ASSY external-feed / factory-clock feasibility

**Issue:** [#126](https://github.com/hieudovn/virtual-factory/issues/126)  
**Task contract:** `.ai-harness/tasks/TIPA-VF-G1-ASSY-FEAS-01.json`  
**Governance:** `.ai-harness/PM-EXECUTION-CONTRACT.md`  
**Design input (unmerged):** PR [#132](https://github.com/hieudovn/virtual-factory/pull/132), head `ff485d5bb50e55e91b90008465e4cc87ab7a9f22`  
**Baseline:** `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe`  
**Mode:** read-only inspection, offline tests and probes only. **No production code, config, test or contract was changed.**

## 1. Status

```text
PM EXECUTION COMPLETE — REPORT-ONLY PR OPEN — READY FOR SA REVIEW
```

The machine-derived status and exact-head evidence are recorded by the task gate
and in the PR/issue comment. The PM does **not** self-certify COMPLETE, CLOSED,
SA APPROVED or NEXT SLICE AUTHORIZED.

## 2. Task interpretation

| Field | Value |
|---|---|
| Task ID | `TIPA-VF-G1-ASSY-FEAS-01` (Issue #126) |
| Objective | Prove, with code/test evidence, whether the six-sub-line ASSY runtime can accept an additive external SSO2/RSO2 feed and a factory-clock seam without rewriting core |
| Deliverables | This report, task JSON, SA-review summary, six evidence files |
| Explicit non-deliverables | No adapter, no G2/G3-A implementation, no C4 change, no production edit, no merge/deploy |
| Required branch | `reports/tipa-vf-g1-assy-feasibility` |
| Expected baseline | `04fb9413bd5af3c4f0457047267a60b3ea4e94fe` |
| Allowed paths | Task JSON, this report, SA-review report, evidence directory |
| Forbidden | `src/`, `configs/`, `tests/`, `simulators/`, `deploy/`, `examples/`, packaging/deployment files |
| Stop conditions | Baseline drift; design-head drift; untestable required evidence; feasibility decision requiring production change; unidentifiable local feed |
| Authorization | May open report-only PR; may not merge, deploy or start next slice |

## 3. Repository state at preflight

| Field | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Current branch | `reports/tipa-vf-g1-assy-feasibility` |
| Working tree | Clean before first write |
| Local HEAD | `04fb9413bd5af3c4f0457047267a60b3ea4e94fe` |
| `origin/main` | `04fb9413bd5af3c4f0457047267a60b3ea4e94fe` |
| Expected baseline | `04fb9413bd5af3c4f0457047267a60b3ea4e94fe` |
| Baseline match | PASS |
| PR #132 design head | `ff485d5bb50e55e91b90008465e4cc87ab7a9f22` (remote match, unmerged design input) |

## 4. Decision

**Additive external input is possible only with a bounded local extension; the
current runtime does not already support it. A shared factory clock / exact
event-boundary advance is NOT SUPPORTED by the current ASSY runtime.**

| Question | Decision |
|---|---|
| Can all local SSO2/RSO2 production be suppressed additively? | **Yes**, via an immutable run mode that gates all four local paths (`SAFE_ADDITIVE`) |
| Can external SSO2 be injected at PRE-ASSY with original parent ID? | **Not as-is**; requires an additive registration/port (`NEEDS_LOCAL_EXTENSION`) |
| Can external RSO2 be injected at AP04 with original parent ID? | **Not as-is**; requires registration + reservation (`NEEDS_LOCAL_EXTENSION`) |
| Is there an exact factory-clock/advance API? | **NO SUPPORT** — no `advance_to`, `next_event_time`, propose/commit or global scheduler wiring |
| Can six lines be locked to one event boundary? | **NO SUPPORT**; requires a coordinator/adapter (`BLOCKED_REDESIGN` for the same-time claim) |
| Is AP04 reservation/all-or-nothing supported? | **No**; AP04 pops the first Rotor, no ledger, no rollback (`NEEDS_LOCAL_EXTENSION`) |
| Are snapshot/reset/run generation/C4 stable? | **Yes**; additive adapter is safe (`SAFE_ADDITIVE`) |
| Is legacy ASSY / Bottled Water preserved? | **Yes**; all selected legacy tests passed, no test/config/source edit |

No core rewrite is justified by this audit. G3-A must be a separate,
SA-authorized bounded slice.

## 5. Question 1 — every SSO2/RSO2 seed, top-up and on-demand path

| Path | Effect | Code |
|---|---|---|
| `AssyDemoComposition.initialize` | Seeds 7 SSO2 + 7 RSO2 per context (6 × 14 WIPs) | `src/virtual_factory/assembly/demo_composition.py:255-259` |
| `ContinuousFeedPolicy.replenish` | SSO2 low-watermark top-up and RSO2 target top-up | `demo_composition.py:94-115` |
| `AssyDemoContext.step_context` | On-demand RSO2 when a WIP is at AP04 and buffer is empty | `demo_composition.py:151-165` |
| `AssyLineRuntime.produce_sso2_wip` / `produce_rso2_wip` | Public local producer methods; no external-ID argument | `src/virtual_factory/assembly/line_runtime.py:610-623` |
| `UpstreamProducer.produce_sso2` / `produce_rso2` | Sequential local IDs + simulated timestamp | `src/virtual_factory/assembly/upstream.py:54-66` |
| `UpstreamProducer.can_produce_*` | 120 s interval predicates; not wired to the composition | `upstream.py:68-78` |
| `AssyDemoContext.introduce_next_sso2` | Introduces only already-registered SSO2 IDs at PRE-ASSY | `demo_composition.py:139-149` |
| `_execute_ap04_join` | Pops the first RSO2; creates Motor child and genealogy | `line_runtime.py:1709-1740` |
| `AssyLineRuntime.reset` / `AssyDemoComposition.reset` | Clears state; composition reset immediately re-seeds | `line_runtime.py:1824-1846`; `demo_composition.py:377-379` |

**Critical finding:** `continuous_feed_enabled=False` disables only
`ContinuousFeedPolicy.replenish`. It does **not** disable the on-demand RSO2 path
in `step_context`, and it does **not** stop `initialize` from seeding 7 + 7.
Integrated mode must gate **all four** paths, not just the existing flag.

Evidence: `01-feed-replenish-callgraph.md`.

## 6. Question 2 — minimal injection seam and clock coupling

### 6.1 Injection seam

- SSO2/pre-ASSY: `introduce_to_assy(wip_id, carrier_id)` preserves the supplied
  ID (`line_runtime.py:626-641`), but the ID must already exist in `_wips`.
  An unregistered external ID is rejected: `Unknown WIP: EXT-SSO2-0001`
  (probe 06).
- AP04/RSO2: `_rso2_wips` is private and populated only by
  `produce_rso2_wip()`; AP04 consumes `next(iter(...))` with no external
  selection (`line_runtime.py:1712-1719`).
- Minimal additive seam: an external input port that registers original IDs and
  provenance, with no local production when mode is `INTEGRATED`.
- The existing genealogy path uses the supplied parent IDs verbatim, so
  original parent identity can be preserved **if** registration is added.

### 6.2 Six contexts and lockstep

`step_all` explicitly says each context advances independently and makes no
assertion about equal simulation time (`demo_composition.py:322-338`). A
regression asserts simulation times are not forced equal
(`tests/test_demo_composition.py:352-364`). There is no common event boundary,
tie order or atomic cross-line commit.

### 6.3 Exact-time API

`AssyLineRuntime` advances time only in `execute_dwell` and `index_line`
(`line_runtime.py:992`, `:1771`), using a station-load-dependent `actual_dwell`
(`line_runtime.py:940-955`). It has no `advance_to`, `next_event_time`,
`propose`/`commit`, or scheduler. `DiscreteClock.advance_to` and
`FutureEventScheduler` exist but are not wired to ASSY
(`src/virtual_factory/discrete/clock.py:46`; `scheduler.py:161,206`).

**Exact-time verdict: NO SUPPORT.** Per the G1A design rule, integration must
stop rather than fabricate a common timestamp.

## 7. Question 3 — reservation, AP04 consumption, join, buffers

- No reservation entity or ledger exists. `ap04_required_parent_sources` is
  loaded (`line_runtime.py:161,272`) but never enforced.
- AP04 pops the first Rotor, with no qualification, quantity, owner, version,
  expiration or all-or-nothing reservation (`line_runtime.py:1712-1719`).
- Genealogy, child and parent lifecycle are mutated in memory with no
  transaction/rollback (`line_runtime.py:1718-1740`).
- Buffers are unbounded: `sso2_ids` list and `_rso2_wips` dict
  (`demo_composition.py:127`; `line_runtime.py:500`).
- Failure modes: missing Rotor raises `AssyLineError` instead of
  `WAITING_FOR_MATERIAL`; missing SSO2 simply never reaches AP04; a failure after
  `pop()` loses the Rotor.
- Two sub-lines cannot compete for one Rotor today because each context owns a
  separate `_rso2_wips` dict (six distinct objects in probe 06).

Evidence: `03-reservation-join-and-buffers.md`.

## 8. Question 4 — snapshot/reset/backward compatibility/C4

- Snapshot is detached and read-only (`demo_composition.py:360-375`; bridge poll
  is read-only, `assy_mes_bridge.py:337-358`).
- Reset rebuilds all contexts and re-seeds; the bridge detects time regression
  and increments `ASSY-SLxx:R<n>` (`assy_mes_bridge.py:281-291,376-387`).
- Probe: reset produced `R2` with identical trace fingerprint; duplicate poll
  added zero keys (384 → 384).
- C4 remains `tipa-assy-demo-v1.1` (`assy_mes_bridge.py:81`), 9 message types,
  666 messages, 666 unique keys in the smoke run.
- A provisional adapter is **SAFE_ADDITIVE** if it does not change the C4
  message types/keys, legacy defaults, or quality/genealogy semantics.
- C4 `run_id` is sub-line scoped (`ASSY-SLxx:R<n>`); a future
  `factory_run_id` must be additive, not substituted into C4 identity.

Evidence: `04-snapshot-reset-compatibility.md`.

## 9. Question 5 — exact regression oracles

| ID | Scenario | Expected oracle | Current result |
|---|---|---|---|
| OR-01 | Zero external input in integrated mode | Zero local `SSO2_PRODUCED`/`RSO2_PRODUCED`; deterministic `WAITING_FOR_MATERIAL`; no motor created; no escaping exception | **FAIL** — seeds locally; missing Rotor raises `AssyLineError` |
| OR-02 | Two sub-lines compete for one Rotor | Exactly one reservation/consumption; one child; loser waits; no double consumption | **NO MECHANISM** — independent per-context buffers |
| OR-03 | External WIP arrives late | Original external ID accepted; wait then join; no phantom WIP | **NO SUPPORT** — unregistered external WIP rejected |
| OR-04 | Replay/reset | Identical trace fingerprint; new `R<n+1>`; no key reuse; duplicate poll adds zero keys | **PASS** — probe and existing tests |
| OR-05 | AP06 FAIL → PASS | Both attempts retained; distinct record IDs/keys; FAIL not overwritten or terminal | **PASS** — existing tests (109 + 110 passed) |

Commands and raw output are in `06-probe-commands-and-output.md` and
`05-regression-oracle-and-seams.md`.

## 10. Question 6 — seam classification and bounded G3-A proposal

| Seam | Classification |
|---|---|
| Suppress all local SSO2/RSO2 seed/replenish | `SAFE_ADDITIVE` |
| Register external SSO2 at PRE-ASSY | `NEEDS_LOCAL_EXTENSION` |
| Register external RSO2 at AP04 | `NEEDS_LOCAL_EXTENSION` |
| Exact factory-clock / event-boundary advance | `BLOCKED_REDESIGN` (same-time six-line claim); adapter boundary still needs local extension |
| Reservation / all-or-nothing join | `NEEDS_LOCAL_EXTENSION` |
| Snapshot/reset/run_id/C4 | `SAFE_ADDITIVE` |
| Late external WIP / wait state | `NEEDS_LOCAL_EXTENSION` |
| Buffer capacity / FIFO / qualification | `BLOCKED_REDESIGN` outside ASSY; must come from G2 ledger |

### Proposed smallest G3-A allowlist (not authorized by this issue)

- `src/virtual_factory/assembly/integrated_input.py` (new port/adapter)
- `src/virtual_factory/assembly/line_runtime.py` (additive registration and AP04 reservation hook only)
- `src/virtual_factory/assembly/demo_composition.py` (additive mode gating of the four local paths)
- `src/virtual_factory/assembly/assy_mes_bridge.py` (additive factory-run correlation only; C4 unchanged)
- `tests/test_tipa_g3a_external_input.py` (new OR-01…OR-05)

Forbidden in G3-A: AP04 join math rewrite, quality/attempt semantics, genealogy
shape, C4 wire change, `discrete/`, legacy ASSY defaults, Bottled Water.

### G3-A stop criteria

1. No accepted exact event-boundary seam → STOP.
2. OR-01/02/03 still produce local WIP, double consumption, phantom child or an
   uncaught exception → STOP.
3. Legacy ASSY / Bottled Water regression fails → STOP.
4. Change required to C4 or production quality/genealogy semantics → STOP.
5. Change required outside the allowlist → STOP.

## 11. Tests and smoke evidence

| Check | Result |
|---|---|
| `tests/test_sim_val_01_feed.py`, `test_demo_composition.py`, `test_assy_mes_bridge_v1.py`, `test_assy_mes_03_evidence.py`, `test_vf_contract_finality_01.py` | **109 passed, 1 warning** |
| `tests/test_dday_b2_bottled_water_line.py`, `test_assy_line.py`, `test_demo_assy_mes_v1.py`, `test_m6_int_01.py` | **110 passed, 1 warning** |
| C4 six-sub-line smoke | 666 messages, 9 types, 666 unique keys, 6 sub-lines |
| `virtual-factory validate --config configs/plants/compressor_train_benchmark_01.yaml` | PASS |
| VF2 package `--validate-only` | PASS (warnings only) |
| Zero-external-Rotor probe | Fails with `AP04 JOIN: no RSO2 WIP available` (current behaviour, oracle fail) |
| External-injection probe | `Unknown WIP: EXT-SSO2-0001`; no `advance_to`/`next_event_time` |
| Competing-sub-line probe | Six distinct RSO2 dicts; same bare IDs per context |
| Reset/replay probe | Trace fingerprint equal; `R1 → R2`; duplicate poll adds 0 keys |

No test was skipped or deleted. No production code was changed.

## 12. Acceptance matrix

| Criterion | Result | Evidence |
|---|---|---|
| A01 Evidence-backed feed/replenish callgraph | PASS | Evidence 01 |
| A02 Injection seam and original parent identity assessed | PASS (extension required) | Evidence 02/03 |
| A03 Six contexts and line lockstep assessed | PASS (no lockstep) | Evidence 02 |
| A04 Exact-time API assessed with explicit NO SUPPORT | PASS | Evidence 02 |
| A05 Reservation/consumption/join/buffer/failure assessed | PASS | Evidence 03 |
| A06 Snapshot/reset/run_id/C4 stability assessed | PASS | Evidence 04 |
| A07 Five regression oracles captured | PASS (OR-01…03 fail/no mechanism; OR-04/05 pass) | Evidence 05/06 |
| A08 Seam classification and bounded G3-A allowlist | PASS | Evidence 05 |
| A09 Legacy ASSY and Bottled Water not modified; tests run | PASS | Tests above; file diff |
| A10 No production code/config/test changed | PASS | Git diff / gate |
| A11 Exact-head PR/CI evidence | PENDING at report authoring; recorded at PR/issue comment | Task gate |

## 13. Issues / residual risk

| Type | Detail |
|---|---|
| Current-runtime gap | Zero external feed is not supported: four local paths, including on-demand RSO2, must be gated. |
| Current-runtime gap | No exact event-boundary API; no global lockstep. |
| Current-runtime gap | AP04 has no reservation/rollback and raises instead of waiting. |
| Governance | G3-A implementation is **not authorized** by this report. A separate SA Design Lock/Issue is required. |
| Design input | PR #132 is unmerged design input, not main; it is referenced, not treated as implementation truth. |

## 14. Final status

```text
Derived status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW
```

Only the exact-head task gate and PR/issue evidence may confirm this status. The
PM does not self-certify COMPLETE/CLOSED, does not merge, and does not start G2,
G3-A or any next slice.
