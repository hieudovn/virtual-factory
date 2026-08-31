# VF-DEPLOY-01 — docker-build.md

## Build command (clean, no cache — §14)

```text
docker compose --project-directory d:\Project\Github\virtual-factory \
  -f d:\Project\Github\virtual-factory\docker-compose.assy.yml \
  build --no-cache
```

## Resulting image identity

| Item | Value |
|---|---|
| Image | `vf-assy:latest` |
| Image ID | `e0ded2accbf5` |
| Base image | `python:3.11-slim` |
| Python (in image) | 3.11.16 |
| OS / architecture | linux / amd64 |
| WORKDIR | `/app` |
| Default CMD | `virtual-factory run --steps 60 --quiet` (generic; ASSY override via compose) |
| Package | `virtual-factory` (editable install, `.[mqtt,api]` extras) built from repo HEAD `18d253d` |
| Build deps | copied from committed repo only: `pyproject.toml`, `README.md`, `src/`, `configs/`, `docs/` |

`docker inspect vf-assy:latest`:

```text
workdir=/app os=linux arch=amd64
cmd=["virtual-factory","run","--steps","60","--quiet"]
env=[...,"PYTHONDONTWRITEBYTECODE=1","PYTHONUNBUFFERED=1"]
```

## Dockerfile (unchanged generic VF image)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY docs ./docs
RUN pip install --no-cache-dir -e ".[mqtt,api]"
CMD ["virtual-factory", "run", "--steps", "60", "--quiet"]
```

The root `Dockerfile` was NOT modified in this gate. All ASSY-specific launch
behavior lives in `docker-compose.assy.yml` (Option A, §3 of the gate).

## Reproducibility

- The build depends only on committed repository content (`.dockerignore`
  excludes `.git`, caches, `out/`, `*.egg-info`).
- No uncommitted local files are required to build.
- No secrets are baked into the image.
