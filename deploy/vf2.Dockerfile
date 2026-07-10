# VF-2 PIM-native Simulation Runtime — Local Dev Docker Image
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install minimal dependencies
RUN pip install --no-cache-dir pyyaml fastapi uvicorn pydantic

# Copy VF-2 module
COPY simulators/vf2/ ./simulators/vf2/
COPY simulators/__init__.py ./simulators/__init__.py

# Create output directory
RUN mkdir -p /app/out

# Default: API server mode with golden fixture
EXPOSE 8102

CMD ["python", "-m", "simulators.vf2.main", \
     "--package", "simulators/vf2/examples/sample_pim_package.json", \
     "--config", "simulators/vf2/config.yaml", \
     "--api-server"]
