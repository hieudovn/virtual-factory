# VF-DEPLOY-01 — network-plan.md

## Current network topology

`vf-assy` runs on its own default Compose network:

```text
docker compose -f docker-compose.assy.yml config
networks:
  default:
    name: vf-assy_default
```

Only port `8000` is published (`8000:8000`). No MQTT/OPC UA ports are exposed.

## Future MES E2E shared network (§11) — documented, NOT connected yet

Preferred concept: external shared Docker network `manufacturing-demo`.

```text
VF compose stack ─┐
                  ├─ external Docker network "manufacturing-demo"
MES compose stack ┘
```

The MES stack is NOT required to live inside the VF compose file.

### Exact one-line change needed for E2E (documented in `docker-compose.assy.yml` and `docs/deployment/assy-docker.md`)

```bash
# 1. create the shared external network once
docker network create manufacturing-demo
```

```yaml
# 2. uncomment in docker-compose.assy.yml:
networks:
  default:
    name: manufacturing-demo
    external: true
```

```bash
# 3. re-create the stack
docker compose -f docker-compose.assy.yml down
docker compose -f docker-compose.assy.yml up -d
```

Then the MES compose stack joins the same external network and reaches the VF
ASSY service as `vf-assy:8000` by service name.

### Out of scope (explicitly not done)

- No MES URL / MES credentials / Odoo IDs configured.
- No MES REST transport/gateway added.
- No MES→VF context.
- `MES-INT-E2E-01` is HOLD pending SA review of this gate.
