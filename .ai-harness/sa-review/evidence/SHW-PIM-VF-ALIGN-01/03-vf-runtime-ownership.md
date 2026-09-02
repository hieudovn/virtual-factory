# 03 — VF-Owned Runtime Contract

VF is the **simulation runtime**. It owns runtime-only identity and provenance
and must NEVER overwrite PIM semantic/evidence truth.

## 3.1 VF MAY own (runtime-only)

```text
workspace_id                # stable logical VF workspace identity
runtime instance ids        # per-run workspace/runtime instance identity
run_id / scenario_id        # execution identity
step / simulation_time_s    # execution clock
runtime-local keys          # runtime_signal_id / model_signal_key — DISTINCT
                            #   from canonical_signal_id (never renamed to it)
simulation state instances  # concrete instances of PIM-defined state dimensions
transitions / scenario execution
fidelity                    # declared; bounded by runtime.fidelity_ceiling
synthetic output provenance # origin_kind: simulation
simulation-only status      # data_status: synthetic | simulated_ground_truth
outputs.namespace           # protocol/path-safe, bound to workspace_id
```

## 3.2 VF MUST NOT

```text
- invent or rewrite canonical object/signal ids;
- rename a VF-local key to canonical_signal_id;
- mutate PIM evidence maturity / source status (SourceMapped, SiteVerified, Proposed);
- upgrade/downgrade observability or state semantics silently;
- fabricate canonical semantics for a missing/unknown parameter to keep the
  simulation running;
- present simulation output as real plant/site truth (data_status is synthetic /
  simulated_ground_truth only);
- overwrite PIM site truth with runtime values.
```

## 3.3 The split in one line

**PIM owns "what the plant is" (semantic truth). VF owns "what this run did"
(runtime truth).** The two never mix: canonical identity and evidence maturity
flow PIM → VF read-only; runtime identity and synthetic provenance stay VF-local.
