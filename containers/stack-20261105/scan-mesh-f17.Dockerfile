# Upgrade candidate 2026-11-05. Original recipe retained.
# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F17 : préparation, frontières et segmentation de maillages seulement.

ARG PYTHON_BASE_IMAGE=python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
FROM ${PYTHON_BASE_IMAGE} AS scan-mesh-f17

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN test "${TARGETARCH}" = "amd64"

# PyMeshLab embarque Qt/MeshLab mais attend les dispatchers GL/OpenGL du système.
# Les versions sont celles du dépôt Debian bookworm de la base épinglée.
RUN --mount=type=bind,source=debhouse/common,target=/debs,readonly dpkg -i /debs/*.deb

RUN --mount=type=bind,source=containers/stack-20261105/scan-mesh.requirements.txt,target=/tmp/requirements.txt,readonly \
    --mount=type=bind,source=wheelhouse/scan,target=/wheels,readonly \
    python -m pip install --no-index --find-links=/wheels \
        --no-deps \
        --only-binary=:all: \
        --require-hashes \
        --requirement /tmp/requirements.txt \
    && python -m pip check

COPY twins/reference-917-engine/source/prepare_scan.py /opt/3dprinting993/twins/reference-917-engine/source/prepare_scan.py
COPY twins/reference-917-engine/source/analyze_boundaries.py /opt/3dprinting993/twins/reference-917-engine/source/analyze_boundaries.py
COPY twins/reference-917-engine/source/segment_engine.py /opt/3dprinting993/twins/reference-917-engine/source/segment_engine.py
COPY containers/stack-20261105/scan-mesh-f17-smoke.py /usr/local/bin/scan-mesh-f17-smoke

ARG MESH_UID=9177
ARG MESH_GID=9177
RUN chmod 0555 \
        /opt/3dprinting993/twins/reference-917-engine/source/prepare_scan.py \
        /opt/3dprinting993/twins/reference-917-engine/source/analyze_boundaries.py \
        /opt/3dprinting993/twins/reference-917-engine/source/segment_engine.py \
        /usr/local/bin/scan-mesh-f17-smoke \
    && mkdir -p /workspace/input /workspace/interfaces /workspace/output \
    && chown -R "${MESH_UID}:${MESH_GID}" /workspace

USER ${MESH_UID}:${MESH_GID}
WORKDIR /workspace

RUN --network=none /usr/local/bin/scan-mesh-f17-smoke

LABEL org.opencontainers.image.title="3dprinting993-scan-mesh-f17" \
      org.opencontainers.image.description="CPU-only scan mesh preparation, boundary screening and spatial segmentation; no scans or interfaces" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Python-2.0 AND BSD-3-Clause AND MIT AND GPL-3.0-only"

CMD ["/usr/local/bin/scan-mesh-f17-smoke"]
