# syntax=docker/dockerfile:1.7
# Image CPU F15: Python standard library, contrat, pipeline et smoke uniquement.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS obj-metrology-f15

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0

RUN test "${TARGETARCH}" = "amd64"

COPY twins/reference-917-engine/source/build_scan_segmentation_f15.py /opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py
COPY twins/reference-917-engine/scan-segmentation-f15.json /opt/3dprinting993/twins/reference-917-engine/scan-segmentation-f15.json
COPY containers/obj-metrology-f15-smoke.py /usr/local/bin/obj-metrology-f15-smoke

ARG METROLOGY_UID=9175
ARG METROLOGY_GID=9175
RUN chmod 0555 \
        /opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py \
        /usr/local/bin/obj-metrology-f15-smoke \
    && mkdir -p /workspace/input /workspace/output \
    && chown -R "${METROLOGY_UID}:${METROLOGY_GID}" /workspace

USER ${METROLOGY_UID}:${METROLOGY_GID}
WORKDIR /workspace

# Le vrai pipeline est exécuté après USER sur une fixture éphémère dans /tmp.
RUN /usr/local/bin/obj-metrology-f15-smoke

LABEL org.opencontainers.image.title="3dprinting993-obj-metrology-f15" \
      org.opencontainers.image.description="Standard-library-only CPU OBJ inventory and topology segmentation; no scans or datasets" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Python-2.0 AND MIT"

CMD ["/usr/local/bin/obj-metrology-f15-smoke"]
