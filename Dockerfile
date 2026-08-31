FROM python:3.11-slim

WORKDIR /app

# VF-DM-DEMO-ASSY-MES-02: bake the exact source SHA into the image so the
# runtime can expose it (default "unknown" keeps the generic image portable).
ARG SOURCE_SHA=unknown
ENV VF_SOURCE_SHA=$SOURCE_SHA

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY docs ./docs

RUN pip install --no-cache-dir -e ".[mqtt,api]"

CMD ["virtual-factory", "run", "--steps", "60", "--quiet"]
