# syntax=docker/dockerfile:1.7

FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        calculix-ccx \
        ca-certificates \
        gmsh \
        python3 \
        python3-gmsh \
        python3-numpy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

LABEL org.opencontainers.image.title="3dprinting993-cae-reference-f31" \
      org.opencontainers.image.description="Gmsh and CalculiX reference screening for the Porsche 917 F29 cylinder-head concepts" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["python3"]
