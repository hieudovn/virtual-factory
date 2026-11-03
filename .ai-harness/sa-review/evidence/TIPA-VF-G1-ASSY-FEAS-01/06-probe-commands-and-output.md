# 06 — Offline probe commands and raw output

All probes were executed read-only against `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe`.
No repository file was modified by a probe.

## Environment

```text
Python 3.12.3 (venv at /tmp/opencode/venv)
PYTHONPATH=src
Dependencies installed from pyproject [dev]: pydantic, PyYAML, pytest, fastapi, uvicorn, httpx, jsonschema
```

## Probe script

```python
import json, inspect
from virtual_factory.assembly.line_runtime import AssyLineRuntime, load_assy_config_from_yaml, AssyLineError
from virtual_factory.assembly.demo_composition import AssyDemoComposition, DemoScenario
from virtual_factory.assembly.assy_mes_bridge import build_assy_mes_pipeline

CFG = "configs/plants/tipa_assy_demo.yaml"
out = {}

# 1. Zero external RSO2 input: no replenish, no produce_rso2_wip.
rt = AssyLineRuntime(config=load_assy_config_from_yaml(CFG))
sso2 = rt.produce_sso2_wip()
rt.introduce_to_assy(sso2, "PAL-001")
try:
    for _ in range(8):
        rt.execute_dwell()
        if rt.conveyor.state.value == "ready_to_index":
            rt.index_line()
    out["zero_external_rso2"] = {"crashed": False, "sim_time_s": rt.simulation_time_s,
        "rso2_buffer_size": rt.rso2_buffer_size, "trace_tail": [str(e) for e in rt.trace[-4:]]}
except AssyLineError as e:
    out["zero_external_rso2"] = {"crashed": True, "exception": type(e).__name__, "message": str(e),
        "sim_time_s": rt.simulation_time_s, "rso2_buffer_size": rt.rso2_buffer_size,
        "trace_tail": [str(x) for x in rt.trace[-4:]]}

# 2. Absence of external injection API.
rt2 = AssyLineRuntime(config=load_assy_config_from_yaml(CFG))
sig = {}
for name in ("produce_sso2_wip", "produce_rso2_wip", "introduce_to_assy", "advance_cycle",
             "execute_dwell", "index_line", "reset"):
    sig[name] = str(inspect.signature(getattr(rt2, name)))
try:
    rt2.introduce_to_assy("EXT-SSO2-0001", "PAL-EXT")
    ext = {"accepted": True}
except Exception as e:
    ext = {"accepted": False, "exception": type(e).__name__, "message": str(e)}
out["external_injection"] = {"signatures": sig, "introduce_unregistered_external_wip": ext,
    "has_advance_to": hasattr(rt2, "advance_to"),
    "has_next_event_time": hasattr(rt2, "next_event_time"),
    "has_time_advance_api": [n for n in dir(rt2) if any(k in n.lower() for k in ("advance", "horizon", "next_event"))]}

# 3. Competing sub-lines: independent per-context RSO2 buffers.
comp = AssyDemoComposition(config_path=CFG, scenario=DemoScenario.HAPPY_PATH)
comp.initialize()
sl = {}
for sid, ctx in comp.contexts.items():
    sl[sid] = {
        "rso2_buffer_size": ctx.runtime.rso2_buffer_size,
        "rso2_buffer_object_id": id(ctx.runtime._rso2_wips),
        "rso2_ids_sample": sorted(ctx.runtime._rso2_wips)[:3],
        "sso2_queue_len": len(ctx.sso2_ids),
        "simulation_time_s": ctx.runtime.simulation_time_s,
    }
out["competing_sub_lines"] = {"contexts": sl, "shared_rso2_objects": len({v["rso2_buffer_object_id"] for v in sl.values()}),
    "note": "each context owns a distinct RSO2 dict; bare RSO2-0001 IDs repeat per sub-line"}

# 4. Reset/replay: composition fingerprint + bridge generation.
comp2 = AssyDemoComposition(config_path=CFG, scenario=DemoScenario.HAPPY_PATH, selected_sub_line_id="ASSY-SL01")
comp2.initialize()
pipe = build_assy_mes_pipeline(); bridge = pipe.bridge
bridge.poll(comp2)
for _ in range(6):
    comp2.step_all(); bridge.poll(comp2)
def fp(c):
    return {sid: [(e.event_type, round(e.simulation_time_s,3), e.position, e.wip_id, e.detail)
                 for e in ctx.runtime.trace] for sid, ctx in c.contexts.items()}
run1 = sorted({m.payload.get("run_id") for m in bridge.projected_messages})
keys1 = {m.key for m in bridge.projected_messages}
fp1 = fp(comp2)
comp2.reset()
bridge.poll(comp2)
for _ in range(6):
    comp2.step_all(); bridge.poll(comp2)
run2 = sorted({m.payload.get("run_id") for m in bridge.projected_messages})
keys2 = {m.key for m in bridge.projected_messages}
fp2 = fp(comp2)
before = len(keys2); bridge.poll(comp2); after = len({m.key for m in bridge.projected_messages})
out["reset_replay"] = {"run_ids_after_first": run1, "run_ids_after_reset": run2,
    "trace_fingerprint_equal_after_reset": fp1 == fp2,
    "keys_before_dup_poll": before, "keys_after_dup_poll": after,
    "message_types_first_run": sorted({m.message_type for m in bridge.projected_messages})}

print(json.dumps(out, indent=2, default=str))
```

## Raw output

```json
{
  "zero_external_rso2": {
    "crashed": true,
    "exception": "AssyLineError",
    "message": "AP04 JOIN: no RSO2 WIP available",
    "sim_time_s": 480.0,
    "rso2_buffer_size": 0,
    "trace_tail": [
      "[t=360.0s] dwell=4 AP03 STATION_COMPLETE SSO2-0001 (checklist complete items=3)",
      "[t=480.0s] dwell=4 DWELL_META (DWELL_READY actual=120s)",
      "[t=480.0s] dwell=4 DWELL_META (INDEX)",
      "[t=480.0s] dwell=4 AP04 WIP_MOVED SSO2-0001 (\u2192 AP04)"
    ]
  },
  "external_injection": {
    "signatures": {
      "produce_sso2_wip": "() -> 'str'",
      "produce_rso2_wip": "() -> 'str'",
      "introduce_to_assy": "(wip_id: 'str', carrier_id: 'str') -> 'None'",
      "advance_cycle": "() -> 'list[LineEvent]'",
      "execute_dwell": "() -> 'list[LineEvent]'",
      "index_line": "() -> 'list[LineEvent]'",
      "reset": "() -> 'None'"
    },
    "introduce_unregistered_external_wip": {
      "accepted": false,
      "exception": "AssyLineError",
      "message": "Unknown WIP: EXT-SSO2-0001"
    },
    "has_advance_to": false,
    "has_next_event_time": false,
    "has_time_advance_api": ["_advance_operation", "advance_cycle"]
  },
  "competing_sub_lines": {
    "contexts": {
      "ASSY-SL01": {
        "rso2_buffer_size": 7,
        "rso2_buffer_object_id": 126971837661824,
        "rso2_ids_sample": ["RSO2-0001", "RSO2-0002", "RSO2-0003"],
        "sso2_queue_len": 7,
        "simulation_time_s": 0.0
      },
      "ASSY-SL02": {
        "rso2_buffer_size": 7,
        "rso2_buffer_object_id": 126971837675776,
        "rso2_ids_sample": ["RSO2-0001", "RSO2-0002", "RSO2-0003"],
        "sso2_queue_len": 7,
        "simulation_time_s": 0.0
      },
      "ASSY-SL03": {
        "rso2_buffer_size": 7,
        "rso2_buffer_object_id": 126971837449216,
        "rso2_ids_sample": ["RSO2-0001", "RSO2-0002", "RSO2-0003"],
        "sso2_queue_len": 7,
        "simulation_time_s": 0.0
      },
      "ASSY-SL04": {
        "rso2_buffer_size": 7,
        "rso2_buffer_object_id": 126971837456192,
        "rso2_ids_sample": ["RSO2-0001", "RSO2-0002", "RSO2-0003"],
        "sso2_queue_len": 7,
        "simulation_time_s": 0.0
      },
      "ASSY-SL05": {
        "rso2_buffer_size": 7,
        "rso2_buffer_object_id": 126971837725696,
        "rso2_ids_sample": ["RSO2-0001", "RSO2-0002", "RSO2-0003"],
        "sso2_queue_len": 7,
        "simulation_time_s": 0.0
      },
      "ASSY-SL06": {
        "rso2_buffer_size": 7,
        "rso2_buffer_object_id": 126971837766656,
        "rso2_ids_sample": ["RSO2-0001", "RSO2-0002", "RSO2-0003"],
        "sso2_queue_len": 7,
        "simulation_time_s": 0.0
      }
    },
    "shared_rso2_objects": 6,
    "note": "each context owns a distinct RSO2 dict; bare RSO2-0001 IDs repeat per sub-line"
  },
  "reset_replay": {
    "run_ids_after_first": [
      "ASSY-SL01:R1", "ASSY-SL02:R1", "ASSY-SL03:R1",
      "ASSY-SL04:R1", "ASSY-SL05:R1", "ASSY-SL06:R1"
    ],
    "run_ids_after_reset": [
      "ASSY-SL01:R1", "ASSY-SL01:R2", "ASSY-SL02:R1", "ASSY-SL02:R2",
      "ASSY-SL03:R1", "ASSY-SL03:R2", "ASSY-SL04:R1", "ASSY-SL04:R2",
      "ASSY-SL05:R1", "ASSY-SL05:R2", "ASSY-SL06:R1", "ASSY-SL06:R2"
    ],
    "trace_fingerprint_equal_after_reset": true,
    "keys_before_dup_poll": 384,
    "keys_after_dup_poll": 384,
    "message_types_first_run": [
      "mes.checklist_result",
      "mes.execution_event",
      "mes.genealogy_relationship",
      "mes.run_status"
    ]
  }
}
```

## C4 six-sub-line smoke output

```text
PYTHONPATH=src TIPA_ASSY_CONFIG=configs/plants/tipa_assy_demo.yaml \
  ASSY_MES_DEMO_STEPS=24 python -m virtual_factory.assembly.assy_mes_bridge
```

```json
{
  "run_ids": ["ASSY-SL01:R1", "ASSY-SL02:R1", "ASSY-SL03:R1",
              "ASSY-SL04:R1", "ASSY-SL05:R1", "ASSY-SL06:R1"],
  "message_counts": {
    "mes.run_status": 9,
    "mes.execution_event": 399,
    "mes.checklist_result": 49,
    "mes.genealogy_relationship": 43,
    "mes.issue": 2,
    "mes.quality_result": 57,
    "mes.measurement_result": 96,
    "mes.release": 5,
    "mes.oee_summary": 6
  },
  "total": 666,
  "unique_message_keys": 666,
  "duplicate_message_keys": 0,
  "sub_lines": 6
}
```
