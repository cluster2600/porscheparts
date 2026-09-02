# syntax=docker/dockerfile:1.7

FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517

ARG FLUIDX3D_COMMIT=aba941305a2cc67b0953ba1d2ba177b590dcccc3
ARG FLUIDX3D_ARCHIVE_SHA256=38ec0137aaa453c4dbd7e4d8b5858e6c8c888235ec4ea43415444b5507cdb6f7

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        g++ \
        make \
        ocl-icd-opencl-dev \
        pocl-opencl-icd \
    && curl -fsSL "https://codeload.github.com/ProjectPhysX/FluidX3D/tar.gz/${FLUIDX3D_COMMIT}" -o /tmp/fluidx3d.tar.gz \
    && echo "${FLUIDX3D_ARCHIVE_SHA256}  /tmp/fluidx3d.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/FluidX3D \
    && tar -xzf /tmp/fluidx3d.tar.gz --strip-components=1 -C /opt/FluidX3D \
    && rm /opt/FluidX3D/src/OpenCL/lib/libOpenCL.so \
    && rm /tmp/fluidx3d.tar.gz \
    && rm -rf /var/lib/apt/lists/*

COPY twins/reference-917-engine/fluidx3d/defines.hpp /opt/FluidX3D/src/defines.hpp
COPY twins/reference-917-engine/fluidx3d/setup.cpp /opt/FluidX3D/src/setup.cpp

RUN cd /opt/FluidX3D && make Linux -j2

WORKDIR /opt/FluidX3D
ENTRYPOINT ["/opt/FluidX3D/bin/FluidX3D"]

LABEL org.opencontainers.image.title="3dprinting993-fluidx3d-aircooled-f34" \
      org.opencontainers.image.description="Independent LBM cross-check for F34 air-cooled four-valve head" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="FluidX3D free for non-commercial use"
