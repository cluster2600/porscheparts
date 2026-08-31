# syntax=docker/dockerfile:1.7
#
# 3dprinting993 - scan-to-CAD and CFD preparation image (CPU / high memory).
#
# The purchased scans are mounted at runtime. They are never copied into the
# image or Docker build context.

FROM ubuntu:24.04

ARG OPENFOAM_VERSION=13

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    FOAM_VERSION=${OPENFOAM_VERSION} \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      admesh \
      blender \
      ca-certificates \
      curl \
      gmsh \
      gnupg \
      jq \
      libgl1 \
      libglu1-mesa \
      libxft2 \
      libxcursor1 \
      libxinerama1 \
      libxrandr2 \
      openssh-server \
      python3 \
      python3-gmsh \
      python3-venv \
      rsync \
      time \
      tmux \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://dl.openfoam.org/gpg.key \
      | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" \
      > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "openfoam${OPENFOAM_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && printf '. /opt/openfoam%s/etc/bashrc\n' "${OPENFOAM_VERSION}" >> /etc/bash.bashrc

RUN python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir \
      build123d==0.11.1 \
      manifold3d==3.5.2 \
      matplotlib==3.11.1 \
      meshio==5.3.5 \
      numpy==2.5.2 \
      pillow==12.3.0 \
      pymeshlab==2025.7.post1 \
      rich==15.0.0 \
      scipy==1.18.1 \
      scikit-image==0.26.0 \
      shapely==2.1.2 \
      tqdm==4.70.0 \
      trimesh==5.1.0 \
      typer==0.21.0

COPY containers/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/smoke-test.sh

COPY scripts /opt/3dprinting993/scripts
COPY templates /opt/3dprinting993/templates
ENV PYTHONPATH=/opt/3dprinting993

WORKDIR /workspace
EXPOSE 22

LABEL org.opencontainers.image.title="3dprinting993-mesh-cfd" \
      org.opencontainers.image.description="Headless OBJ cleanup, STEP proxy generation and OpenFOAM CFD preparation" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
