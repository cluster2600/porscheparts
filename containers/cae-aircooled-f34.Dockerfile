# syntax=docker/dockerfile:1.7

FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517

ARG AATE_COMMIT=c0f75f953d67cd325d28d1300672d14288f22934
ARG AATE_ARCHIVE_SHA256=28ee8d96b6943fab11b3d70ea3befe472d06d24741962cdb399b1d54e7ff7d3b

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        calculix-ccx \
        curl \
        git \
        gmsh \
        gnupg \
        python3 \
        python3-gmsh \
        python3-numpy \
    && curl -fsSL https://dl.openfoam.org/gpg.key | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends openfoam14 \
    && curl -fsSL "https://codeload.github.com/OpenFOAM/ICengines/tar.gz/${AATE_COMMIT}" -o /tmp/icengines.tar.gz \
    && echo "${AATE_ARCHIVE_SHA256}  /tmp/icengines.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/ICengines \
    && tar -xzf /tmp/icengines.tar.gz --strip-components=1 -C /opt/ICengines \
    && /bin/bash -lc 'source /opt/openfoam14/etc/bashrc && cd /opt/ICengines && ./Allwmake -j 2' \
    && rm -rf /var/lib/apt/lists/* /tmp/icengines.tar.gz

WORKDIR /workspace

LABEL org.opencontainers.image.title="3dprinting993-cae-aircooled-f34" \
      org.opencontainers.image.description="OpenFOAM 14 AATE, Gmsh and CalculiX for the F34 air-cooled four-valve head" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="GPL-3.0-or-later AND GPL-2.0-or-later"

ENTRYPOINT ["/bin/bash", "-lc"]
