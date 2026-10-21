# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Synthetic geometry verification only. No scans, CAD, models or credentials.
FROM python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef

ARG TARGETARCH
RUN test "${TARGETARCH}" = amd64

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp \
    WARP_CACHE_PATH=/tmp/warp-cache

COPY containers/warp-geometry.requirements.txt /opt/warp-geometry/requirements.txt
RUN python -m pip install --only-binary=:all: --require-hashes --no-deps \
      --requirement /opt/warp-geometry/requirements.txt \
    && python -m pip check \
    && python -c 'from importlib.metadata import version; assert version("warp-lang") == "1.18.0"; assert version("numpy") == "2.2.6"'

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
