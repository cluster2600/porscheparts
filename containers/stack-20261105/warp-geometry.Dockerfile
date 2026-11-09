# Upgrade candidate 2026-11-05. Original recipe and evidence remain immutable.
# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Synthetic geometry verification only. No scans, CAD, models or credentials.
ARG PYTHON_BASE_IMAGE=python:3.15.2-slim-bookworm@sha256:4e03260adeeebafccd084f3584e6b84823aba5651cfb53ef8a078ed441ddf9cd
FROM ${PYTHON_BASE_IMAGE}

ARG TARGETARCH
RUN test "${TARGETARCH}" = amd64

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp \
    WARP_CACHE_PATH=/tmp/warp-cache

COPY containers/stack-20261105/warp.requirements.txt /opt/warp-geometry/requirements.txt
RUN --mount=type=bind,source=wheelhouse/warp,target=/wheels,readonly python -m pip install --no-index --find-links=/wheels --only-binary=:all: --require-hashes --no-deps \
      --requirement /opt/warp-geometry/requirements.txt \
    && python -m pip check \
    && python -c 'from importlib.metadata import version; assert version("warp-lang") == "1.19.0"; assert version("numpy") == "2.5.4"'

COPY benchmarks/warp-geometry/pilot.py benchmarks/warp-geometry/kernels.py /opt/warp-geometry/

RUN groupadd --gid 9179 warp-pilot \
    && useradd --uid 9179 --gid 9179 --home-dir /tmp --no-create-home \
      --shell /usr/sbin/nologin warp-pilot \
    && mkdir -p /output /workspace \
    && chown 9179:9179 /output /workspace \
    && chmod 0555 /opt/warp-geometry/pilot.py /opt/warp-geometry/kernels.py \
    && chmod 0444 /opt/warp-geometry/requirements.txt

USER 9179:9179
WORKDIR /workspace

LABEL org.opencontainers.image.title="porscheparts-warp-geometry" \
      org.opencontainers.image.description="Synthetic point-to-mesh distance checks against an analytic box oracle; CUDA validation requires a separate GPU run" \
      org.opencontainers.image.source="https://github.com/cluster2600/porscheparts" \
      org.opencontainers.image.licenses="NOASSERTION"

ENTRYPOINT ["python", "/opt/warp-geometry/pilot.py"]
CMD ["--device", "cuda:0", "--output", "/output/report.json", "--samples", "4096", "--repeats", "5"]
