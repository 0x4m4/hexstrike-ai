# Samson SBM — On-Premise Enterprise runtime image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-samson.txt /workspace/requirements-samson.txt
RUN pip install --upgrade pip \
    && pip install -r /workspace/requirements-samson.txt \
    && apt-get purge -y --auto-remove gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY samson /workspace/samson
COPY config /workspace/config
COPY target-arena /workspace/target-arena
COPY examples /workspace/examples
COPY docker-compose.yml /workspace/docker-compose.yml

RUN mkdir -p \
      /workspace/samson/rag/docs/emulation \
      /workspace/samson/rag/reports \
      /workspace/samson/redteam/guardrail/configs \
      /workspace/samson/redteam/emulation/artifacts \
    && python3 -c "import samson, samson.orchestrator, samson.redteam.shodan_collector; print('samson_import_ok', samson.__version__)"

ENTRYPOINT ["python3", "/workspace/samson/orchestrator.py"]
CMD ["health"]
