# VF-DM-DEMO-ASSY-MES-03 — Docker exact-head smoke

Image: `vf-assy:latest` rebuilt on exact source SHA
(`SOURCE_SHA=05d0154d8b02942b2c14dc41015dfb192218b8fd`, the implementation head).
All production code (`src/`, `configs/`, `docs/`) was committed at or before
this head; later commits in this branch are documentation/evidence-only and do
not affect the image's runtime code (the Dockerfile copies `src`, `configs`,
`docs`, `pyproject.toml`, `README.md` only). Compose: `docker-compose.assy.yml`.

## Endpoints (all from the container at 127.0.0.1:8000)

| Check | Result |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /assy-demo` | HTTP 200 |
| `GET /assy-demo/version` | `source_sha=05d0154d8b02942b2c14dc41015dfb192218b8fd` (== final HEAD), `contract_version=tipa-assy-demo-v1.1`, `runtime=assy-demo` |
| `GET /assy-demo/sub-lines` | 6 sub-lines |
| `POST /assy-demo/reset {scenario:FAILED_FINAL}` → `jam` → `recover` → `run-to-terminal` | completed |
| `GET /assy-demo/mes-messages` | 702 messages, 702 unique keys, 0 duplicates |

## Message-type counts (container, FAILED_FINAL control sequence)

- `mes.execution_event`: 417
- `mes.run_status`: 27
- `mes.checklist_result`: 49
- `mes.measurement_result`: 96
- `mes.quality_result`: 57 (25 with `observations[]`)
- `mes.genealogy_relationship`: 43
- `mes.release`: 5
- `mes.issue`: 2
- `mes.oee_summary`: 6

`contract_version=tipa-assy-demo-v1.1` on every message.

The container's step-driven control sequence emits a few extra run_status /
execution_event messages relative to the bounded 666-message native smoke
(`python -m virtual_factory.assembly.assy_mes_bridge`), which remains the
authoritative bounded evidence (666 messages, 0 duplicates). The evidence
surface (checklist_result / measurement_result / observations) is identical.
