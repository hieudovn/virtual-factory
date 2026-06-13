FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY docs ./docs

RUN pip install --no-cache-dir -e ".[mqtt]"

CMD ["virtual-factory", "run", "--steps", "60", "--quiet"]
