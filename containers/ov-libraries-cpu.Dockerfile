# syntax=docker/dockerfile:1.7

# Minimal CPU runtime for the current standalone Omniverse library architecture.
# OVRTX is deliberately excluded: rendering requires an RTX-capable worker and
# stays in containers/simready.Dockerfile.
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ARG OVPHYSX_VERSION=0.5.11
ARG OVSTAGE_VERSION=0.1.1.355824
ARG NUMPY_VERSION=2.5.2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/ovphysx/lib:/usr/local/lib/python3.12/site-packages/ovstage/bin:/usr/local/lib/python3.12/site-packages/ovstage/bin/plugins

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libgl1 libgomp1 libopengl0 libx11-6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN python -m pip install --no-cache-dir \
      "numpy==${NUMPY_VERSION}" \
      "ovphysx==${OVPHYSX_VERSION}" \
      "ovstage==${OVSTAGE_VERSION}" \
    && python -c "import ovphysx, ovstage; assert ovphysx.__version__ == '${OVPHYSX_VERSION}'; assert ovstage"

RUN python -c "from ovphysx import PhysX; physics = PhysX(); physics.release()"

WORKDIR /workspace
ENTRYPOINT ["python"]
