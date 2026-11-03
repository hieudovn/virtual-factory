# 01 — ASSY seed / replenish / on-demand production callgraph

Read-only inspection at `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe`.
No source, config or test file was modified.

## Complete inventory of SSO2 / RSO2 creation paths

| # | Entry point | Source / effect | Called by | Integrated-mode risk | Evidence |
|---|---|---|---|---|---|
| 1 | `AssyDemoComposition.initialize` | Seeds 7 SSO2 WIPs into `ctx.sso2_ids` and 7 RSO2 WIPs into the private runtime buffer for every one of six contexts | `initialize()`, `reset()` | Mandatory local production; cannot be suppressed by `continuous_feed_enabled` | `src/virtual_factory/assembly/demo_composition.py:255-259`, `:377-379` |
| 2 | `ContinuousFeedPolicy.replenish` | Tops SSO2 when remaining `< sso2_low_watermark`; tops RSO2 to `rso2_target` | `AssyDemoComposition.step_all` when `continuous_feed_enabled` | Local regeneration; suppressible only through the feed flag | `demo_composition.py:94-115`, `:322-338` |
| 3 | `AssyDemoContext.step_context` on-demand RSO2 | If a WIP is at AP04 and `rso2_buffer_size == 0`, calls `runtime.produce_rso2_wip()` | `step_all` per context | **Not gated by `continuous_feed_enabled`**: disabling the feed policy does not disable this path | `demo_composition.py:151-165` |
| 4 | `AssyLineRuntime.produce_sso2_wip()` | Calls `UpstreamProducer.produce_sso2(sim_time)` and registers a WIP | Composition seed/replenish, tests | Public local producer; no external-ID argument | `src/virtual_factory/assembly/line_runtime.py:610-615` |
| 5 | `AssyLineRuntime.produce_rso2_wip()` | Calls `UpstreamProducer.produce_rso2(sim_time)` and inserts into `_rso2_wips` | Composition seed/replenish, on-demand path, tests | Public local producer; no external-ID argument | `line_runtime.py:617-623` |
| 6 | `UpstreamProducer.produce_sso2/produce_rso2` | Sequential local IDs and simulated-time stamps | Only through `AssyLineRuntime` | Produces local identity; cannot preserve an external parent ID | `src/virtual_factory/assembly/upstream.py:54-66` |
| 7 | `UpstreamProducer.can_produce_sso2/can_produce_rso2` | Time-interval predicates (120 s) | Not called by the six-sub-line composition | Latent time-driven producer, not wired into the demo loop | `upstream.py:68-78` |
| 8 | `AssyDemoContext.introduce_next_sso2` | Introduces the next **already-registered** SSO2 ID into PRE-ASSY | `step_context` after index | Cannot introduce an unregistered external WIP | `demo_composition.py:139-149` |
| 9 | `AssyLineRuntime._execute_ap04_join` | Pops the first RSO2 from `_rso2_wips` and creates a Motor child | AP04 dispatch | No reservation, eligibility or external selection | `line_runtime.py:1709-1740` |
| 10 | `AssyLineRuntime.reset` | Clears WIP/RSO2 buffers and reinitialises timing | Direct or via composition reset | Clears all local state; composition reset re-seeds immediately | `line_runtime.py:1824-1846` |
| 11 | `AssyDemoComposition.reset` | Calls `initialize()` again | Control surface/tests | Re-seeds 7 + 7 per context; bridge detects time regression and bumps generation | `demo_composition.py:377-379` |

## Legacy single-line scenario (not the six-sub-line runtime)

`src/virtual_factory/assembly/demo_assy_mes/scenario.py` is a deterministic
fact script (`DemoRunner`). It does not seed runtime WIPs and is not a source
of six-sub-line external feed. It is retained as the C4 fixture/oracle path.

## Conclusion

There are **four active local production/seed paths** in the six-sub-line demo:

1. `initialize` seed of 7 SSO2 and 7 RSO2 per context;
2. `ContinuousFeedPolicy.replenish` SSO2 top-up;
3. `ContinuousFeedPolicy.replenish` RSO2 top-up;
4. `AssyDemoContext.step_context` on-demand RSO2.

Path 4 is independent of `continuous_feed_enabled`, so the currently exposed
flag is **not sufficient** for integrated mode. All four must be disabled and
replaced by an explicit external-input port before an integrated run can claim
"zero local phantom feed".
