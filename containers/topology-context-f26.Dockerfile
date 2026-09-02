# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F26 : OBJ + topologie NumPy + SVG stdlib. Aucun scan n'est inclus.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS topology-context-f26

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1

RUN test "${TARGETARCH}" = "amd64"

COPY containers/topology-context-f26-requirements.txt /tmp/topology-context-f26-requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_INDEX=0 python -m pip install \
      --only-binary=:all: \
      --require-hashes \
      --no-deps \
      --requirement /tmp/topology-context-f26-requirements.txt \
    && python -m pip check \
    && test "$(python -c 'import numpy; print(numpy.__version__)')" = "2.2.6"

COPY twins/reference-917-engine/topology-context-contract-f26.json /opt/3dprinting993/twins/reference-917-engine/topology-context-contract-f26.json
COPY twins/reference-917-engine/source/review_boundary_components_f18.py /opt/3dprinting993/twins/reference-917-engine/source/review_boundary_components_f18.py
COPY twins/reference-917-engine/source/build_topology_context_f26.py /opt/3dprinting993/twins/reference-917-engine/source/build_topology_context_f26.py
COPY containers/topology-context-f26-smoke.py /usr/local/bin/topology-context-f26-smoke

ARG CONTEXT_UID=9174
ARG CONTEXT_GID=9174
RUN chmod 0444 \
      /opt/3dprinting993/twins/reference-917-engine/topology-context-contract-f26.json \
    && chmod 0555 \
      /opt/3dprinting993/twins/reference-917-engine/source/review_boundary_components_f18.py \
      /opt/3dprinting993/twins/reference-917-engine/source/build_topology_context_f26.py \
      /usr/local/bin/topology-context-f26-smoke \
    && mkdir -p /workspace/input /workspace/output \
    && chown -R "${CONTEXT_UID}:${CONTEXT_GID}" /workspace

USER ${CONTEXT_UID}:${CONTEXT_GID}
WORKDIR /workspace

# Le vrai générateur est exercé avec une fixture OBJ éphémère, après USER et sans réseau.
RUN --network=none /usr/local/bin/topology-context-f26-smoke

LABEL org.opencontainers.image.title="3dprinting993-topology-context-f26" \
      org.opencontainers.image.description="Deterministic CPU topology-context generator: incident faces, two face rings, four orthographic views and global locators; no scans, datasets or model weights" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Python-2.0 AND BSD-3-Clause AND MIT"

CMD ["/usr/local/bin/topology-context-f26-smoke"]
