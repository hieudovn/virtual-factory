# VF-vNEXT-G2 · Evidence 06 — Tests + regression results

## 1. New G2 tests

Command:

```
python -m pytest tests/test_provenance_context.py tests/test_provenance_envelope.py \
    tests/test_provenance_namespace.py tests/test_run_context_adapter.py \
    tests/test_telemetry_provenance_threading.py -q
```

Result: **32 passed** (0 failures).

Covers (Issue #47 "Required tests / proofs"):
- generic context immutable + deterministic serialization;
- identity concepts not collapsed (workspace/scope/run/scenario/namespace/
  runtime signal vs absent canonical);
- continuous + discrete + batch + hybrid share the same generic contract without
  engine-cardinality assumptions;
- missing/invalid required identity fails closed;
- origin_kind cannot become plant truth; only allowed data-status/fidelity
  accepted;
- semantic pins immutable/serialized, no PIM validation;
- runtime_signal_id distinct from canonical; no fabricated canonical id;
- telemetry provenance deterministic + additive; legacy seam unchanged;
- output-policy behavior unchanged.

## 2. Targeted regression (G1 + discrete + telemetry/observation)

Command: `python -m pytest tests/test_workspace_*.py tests/test_discrete_*.py
tests/test_run_service.py tests/test_control_commands.py
tests/test_runtime_snapshot_diagnostics.py tests/test_auto_timing_snapshot.py
tests/test_telemetry_frame.py tests/test_output_policy.py
tests/test_telemetry_export.py tests/test_mqtt_gateway.py
tests/test_sparkplug_gateway.py tests/test_signal_value.py
tests/test_ring_buffer.py tests/test_alarm_manager.py -q`

Result: **415 passed** (0 failures). The discrete `RunContext` consumers,
telemetry frame, output policy, export, MQTT/Sparkplug gateway and signal/ring/
alarm seams are all unaffected.

## 3. ASSY regression oracle

Result: **354 passed** (0 failures). `AssyLineRuntime` and ASSY run ids/
idempotency untouched.

## 4. Continuous/compressor baseline

Result: **61 passed** (0 failures).

## 5. Full repository suite

`python -m pytest tests -q`

Result: **1711 passed in 19.09s (0 failures)**. No baseline anomalies in this
run (1679 pre-G2 + 32 new G2 tests).

## 6. Lint / type / compile

No ruff/mypy/black configured in the repo (unchanged). Compile check:
`python -m compileall -q src/virtual_factory/provenance` → exit 0.
