# syntax=docker/dockerfile:1.7
#
# 3dprinting993 - reconstruction image (GPU / CUDA)
#
# Purpose: turn photographs of a 993 part into a scaled mesh, without any GUI.
# Every tool in this image is driven by a command line or a Python API so a
# script or an agent can run the whole pipeline unattended.
#
# Build:  docker build -f containers/recon.Dockerfile -t 3dprinting993-recon:dev .
# Run:    docker run --rm --gpus all -v "$PWD/work:/workspace" 3dprinting993-recon:dev bash

ARG CUDA_VERSION=13.4.3
ARG UBUNTU_VERSION=24.04

# ---------------------------------------------------------------------------
# Stage 1 - build COLMAP and GLOMAP with CUDA enabled.
# Distribution packages ship COLMAP without CUDA, so dense reconstruction is
# only available from a source build.
# ---------------------------------------------------------------------------
FROM nvidia/cuda:13.4.3-devel-ubuntu24.04@sha256:5626a7d0ecafe3e7c115a452f6b05f20f214f8509346196a7835b205dc5b7fd9 AS builder

ARG COLMAP_VERSION=4.2.1
ARG GLOMAP_VERSION=1.2.0
# CUDA 13 excludes pre-Turing GPUs. Explicit targets cover retained Turing,
# Ampere, Ada, Hopper and Blackwell hardware; GPU execution remains untested.
ARG CUDA_ARCHITECTURES="75;80;86;89;90;100;120"

ENV DEBIAN_FRONTEND=noninteractive CMAKE_BUILD_PARALLEL_LEVEL=2

# Dependency list follows COLMAP 4.x upstream, minus Qt (no GUI) and minus
# Intel MKL (OpenBLAS gives the same linear algebra for a few gigabytes less).
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      python3-venv \
      git \
      libboost-graph-dev \
      libboost-program-options-dev \
      libboost-system-dev \
      libceres-dev \
      libcgal-dev \
      libcurl4-openssl-dev \
      libeigen3-dev \
      libflann-dev \
      libfreeimage-dev \
      libglew-dev \
      libgmock-dev \
      libgoogle-glog-dev \
      libgtest-dev \
      liblapack-dev \
      libmetis-dev \
      libopenblas-dev \
      libopenimageio-dev \
      libsqlite3-dev \
      libssl-dev \
      libsuitesparse-dev \
      ninja-build \
      openimageio-tools \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /usr/include/opencv4

COPY containers/stack-20261105/cmake.requirements.txt /tmp/cmake.requirements.txt
RUN python3 -m venv /opt/build-tools \
    && /opt/build-tools/bin/pip install --no-cache-dir --require-hashes -r /tmp/cmake.requirements.txt
ENV PATH=/opt/build-tools/bin:${PATH}

RUN git clone --depth 1 --branch "${COLMAP_VERSION}" https://github.com/colmap/colmap.git /src/colmap \
    && test "$(git -C /src/colmap rev-parse HEAD)" = bd1fcf654d2dd8fefa1466999c190a246f83f4b9
RUN --mount=type=cache,id=stack-colmap-421-cuda1343,target=/src/colmap/build \
    cmake -S /src/colmap -B /src/colmap/build -GNinja \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_INSTALL_PREFIX=/opt/colmap \
        -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
        -DCUDA_ENABLED=ON \
        -DGUI_ENABLED=OFF \
        -DTESTS_ENABLED=OFF \
    && cmake --build /src/colmap/build --target install

# GLOMAP reuses the COLMAP database and solves the pose graph globally; on large
# image sets it replaces hours of incremental mapping with minutes.
#
# It is built against the COLMAP commit it pins upstream, not against the COLMAP
# installed above: GLOMAP 1.2.0 does not compile against COLMAP 4.2.1, whose
# Rigid3d API changed. Both live under separate prefixes, and /opt/colmap comes
# first on PATH, so the colmap CLI stays the current one.
RUN git clone --depth 1 --branch "${GLOMAP_VERSION}" https://github.com/colmap/glomap.git /src/glomap \
    && test "$(git -C /src/glomap rev-parse HEAD)" = 0edb1b8435e0f9a594318908b81a31f078a51bf7
RUN --mount=type=cache,id=stack-glomap-120-cuda1343,target=/src/glomap/build \
    cmake -S /src/glomap -B /src/glomap/build -GNinja \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_INSTALL_PREFIX=/opt/glomap \
        -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
        -DCMAKE_INSTALL_RPATH=/opt/glomap/lib \
        -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        -DFETCH_COLMAP=ON \
    && cmake --build /src/glomap/build --target install

# ---------------------------------------------------------------------------
# Stage 2 - runtime image.
# ---------------------------------------------------------------------------
FROM nvidia/cuda:13.4.3-runtime-ubuntu24.04@sha256:f58bd7a0701fae3a2160f22e1d451b77b349bd9ef83dad76f5529aa413c149a8 AS recon

ARG BLENDER_SERIES=5.2
ARG BLENDER_VERSION=5.2.3

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:/opt/colmap/bin:/opt/glomap/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv

# The -dev packages are kept in the runtime image on purpose: they carry the
# shared libraries COLMAP links against, under names that stay stable across
# Ubuntu point releases.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      ffmpeg \
      git \
      jq \
      libboost-graph-dev \
      libboost-program-options-dev \
      libboost-system-dev \
      libceres-dev \
      libfreeimage3 \
      libgl1 \
      libglew-dev \
      libgomp1 \
      libgoogle-glog-dev \
      libimage-exiftool-perl \
      libmetis-dev \
      libopenblas-dev \
      libopenimageio-dev \
      libsm6 \
      libsqlite3-0 \
      libx11-6 \
      libxfixes3 \
      libxi6 \
      libxrender1 \
      libxxf86vm1 \
      openssh-server \
      python3 \
      python3-venv \
      rsync \
      tmux \
      unzip \
      xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/colmap /opt/colmap
COPY --from=builder /opt/glomap /opt/glomap

# Blender runs headless here (--background --python) for remeshing, booleans and
# documentation renders next to the scan data.
RUN --mount=type=bind,source=downloads/blender-5.2.3-linux-x64.tar.xz,target=/tmp/blender.tar.xz,readonly \
    true \
    && echo "78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec  /tmp/blender.tar.xz" | sha256sum -c - \
    && tar -xJf /tmp/blender.tar.xz -C /opt \
    && ln -s "/opt/blender-${BLENDER_VERSION}-linux-x64/blender" /usr/local/bin/blender

# Python side of the pipeline: point clouds, meshes, image handling.
COPY containers/stack-20261105/recon.requirements.txt /opt/locks/recon.requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir pip==26.3 \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r /opt/locks/recon.requirements.txt \
    && /opt/venv/bin/pip check \
    && dpkg-query -W > /opt/locks/system-packages.txt

COPY containers/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/smoke-test.sh

COPY scripts /opt/3dprinting993/scripts
COPY catalog/templates /opt/3dprinting993/catalog/templates
ENV PYTHONPATH=/opt/3dprinting993

WORKDIR /workspace
EXPOSE 22

LABEL org.opencontainers.image.title="3dprinting993-recon" \
      org.opencontainers.image.description="Headless photogrammetry and mesh toolchain (COLMAP, GLOMAP, Blender, Open3D) for Porsche 993 part reconstruction" \
      org.opencontainers.image.source="https://github.com/cluster2600/porscheparts" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]

