# syntax=docker/dockerfile:1.7
#
# 3dprinting993 - CAD and simulation image (CPU, no GPU needed)
#
# Purpose: build parametric geometry from code, mesh it, run FEA and CFD, and
# slice a prototype - all from scripts. Rented machines are used here for core
# count and memory, not for CUDA.
#
# Build:  docker build -f containers/cadsim.Dockerfile -t 3dprinting993-cadsim:dev .
# Run:    docker run --rm -v "$PWD/work:/workspace" 3dprinting993-cadsim:dev bash

FROM ubuntu:24.04 AS cadsim

ARG OPENFOAM_VERSION=13

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      admesh \
      ca-certificates \
      calculix-ccx \
      curl \
      git \
      gnupg \
      gphoto2 \
      jq \
      libgl1 \
      libglu1-mesa \
      libimage-exiftool-perl \
      libxcursor1 \
      libxinerama1 \
      libxrandr2 \
      openscad \
      openssh-server \
      prusa-slicer \
      python3 \
      python3-venv \
      rsync \
      time \
      tmux \
      unzip \
      xvfb \
    && rm -rf /var/lib/apt/lists/*

# OpenFOAM from the OpenFOAM Foundation repository (GPL, Ubuntu 24.04 "noble").
RUN curl -fsSL https://dl.openfoam.org/gpg.key | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" \
        > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "openfoam${OPENFOAM_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

ENV FOAM_VERSION=${OPENFOAM_VERSION}
RUN printf '. /opt/openfoam%s/etc/bashrc\n' "${OPENFOAM_VERSION}" >> /etc/bash.bashrc

# Code-first CAD and simulation driving. build123d and CadQuery expose the same
# OCCT kernel FreeCAD uses, but as a Python API, so geometry stays reviewable
# text and STEP export is one call.
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir \
        build123d \
        cadquery \
        gmsh \
        meshio \
        pyvista \
        trimesh \
        manifold3d \
        numpy \
        scipy \
        foamlib \
        ccx2paraview \
        pyserial \
        pillow \
        tqdm \
        rich \
        typer

COPY containers/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/smoke-test.sh

# Repository tooling: capture at the bench and validation of what it produces.
COPY scripts /opt/3dprinting993/scripts
COPY templates /opt/3dprinting993/templates
ENV PYTHONPATH=/opt/3dprinting993

WORKDIR /workspace
EXPOSE 22

LABEL org.opencontainers.image.title="3dprinting993-cadsim" \
      org.opencontainers.image.description="Scriptable CAD and simulation toolchain (build123d, CadQuery, Gmsh, CalculiX, OpenFOAM, PrusaSlicer) for Porsche 993 parts" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
