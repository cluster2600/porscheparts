# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F23 : générateur stdlib du workpack de revue humaine seulement.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS boundary-review-f23

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN test "${TARGETARCH}" = "amd64"

COPY twins/reference-917-engine/source/build_boundary_review_workpack_f23.py /opt/3dprinting993/twins/reference-917-engine/source/build_boundary_review_workpack_f23.py
COPY containers/boundary-review-f23-smoke.py /usr/local/bin/boundary-review-f23-smoke

ARG REVIEW_UID=9173
ARG REVIEW_GID=9173
RUN chmod 0555 \
        /opt/3dprinting993/twins/reference-917-engine/source/build_boundary_review_workpack_f23.py \
        /usr/local/bin/boundary-review-f23-smoke \
    && mkdir -p /workspace/input /workspace/output \
    && chown -R "${REVIEW_UID}:${REVIEW_GID}" /workspace

USER ${REVIEW_UID}:${REVIEW_GID}
WORKDIR /workspace

# Le vrai générateur est exercé sur une fixture éphémère après USER et sans réseau.
RUN --network=none /usr/local/bin/boundary-review-f23-smoke

LABEL org.opencontainers.image.title="3dprinting993-boundary-review-f23" \
      org.opencontainers.image.description="Standard-library-only CPU generator for a local SVG/JSON/CSV human-review workpack; no scans, geometry, datasets or model weights" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Python-2.0 AND MIT"

CMD ["/usr/local/bin/boundary-review-f23-smoke"]
