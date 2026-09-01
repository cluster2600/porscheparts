# syntax=docker/dockerfile:1.7
#
# 3dprinting993 - GPU-accelerated CAD, FEA and physics-ML image
#
# This image is intended for Vast.ai instances with an NVIDIA GPU. It keeps
# the editable CAD/mesh tools close to the differentiable solvers, so one
# mounted project can move from STEP to mesh to a physics-informed surrogate.
#
# Build:
#   docker build -f containers/physicsml.Dockerfile -t 3dprinting993-physicsml:dev .
# Run:
#   docker run --rm --gpus all --ipc=host -v "$PWD:/workspace/project" \
#     3dprinting993-physicsml:dev bash
#
# The optional PhysicsNeMo GNN extra is deliberately opt-in. It brings
# torch-geometric extension packages whose wheels are architecture-specific:
# add --build-arg PHYSICSNEMO_EXTRAS=cu12,sym,mesh-extras,model-extras,gnns
# when that feature is needed.

ARG CUDA_VERSION=12.8.1
ARG UBUNTU_VERSION=24.04
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS physicsml

ARG OPENFOAM_VERSION=13
ARG JAX_VERSION=0.11.1
ARG JAX_FEM_VERSION=0.0.12
ARG PHYSICSNEMO_VERSION=2.2.0
ARG PHYSICSNEMO_EXTRAS=cu12,sym,mesh-extras,model-extras
ARG DEEPXDE_VERSION=1.15.0

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 \
    DDE_BACKEND=pytorch \
    XLA_PYTHON_CLIENT_PREALLOCATE=false \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Keep the same command-line CAD/meshing/simulation surface as cadsim. The
# CUDA developer image adds the compiler and runtime needed by GPU packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
      admesh \
      build-essential \
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
      python3-dev \
      python3-venv \
      rsync \
      time \
      tmux \
      unzip \
      xvfb \
    && rm -rf /var/lib/apt/lists/*

# OpenFOAM from the OpenFOAM Foundation repository (GPL, Ubuntu 24.04
# "noble"), matching the CPU cadsim image.
RUN curl -fsSL https://dl.openfoam.org/gpg.key | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" \
        > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "openfoam${OPENFOAM_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

ENV FOAM_VERSION=${OPENFOAM_VERSION}
RUN printf '. /opt/openfoam%s/etc/bashrc\n' "${OPENFOAM_VERSION}" >> /etc/bash.bashrc

# The top-level versions are pinned so a rebuilt image is reviewable. JAX's
# CUDA 12 wheel is used alongside the CUDA 12.8 base image; PhysicsNeMo's cu12
# extra supplies its CUDA/PyTorch-side optional dependencies.
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
        typer \
        matplotlib \
        "jax[cuda12]==${JAX_VERSION}" \
        "jax-fem==${JAX_FEM_VERSION}" \
        "nvidia-physicsnemo[${PHYSICSNEMO_EXTRAS}]==${PHYSICSNEMO_VERSION}" \
        "deepxde==${DEEPXDE_VERSION}"

COPY containers/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/smoke-test.sh

# Mount the repository at runtime for the source-of-truth catalogue. The
# scripts/templates are also copied into the image so a minimal job can run
# without a second checkout.
COPY scripts /opt/3dprinting993/scripts
COPY templates /opt/3dprinting993/templates
COPY containers/examples /opt/3dprinting993/containers/examples
ENV PYTHONPATH=/opt/3dprinting993

WORKDIR /workspace
EXPOSE 22

LABEL org.opencontainers.image.title="3dprinting993-physicsml" \
      org.opencontainers.image.description="GPU CAD, meshing, FEA and physics-ML toolchain (JAX-FEM, PhysicsNeMo, DeepXDE) for Porsche 993 digital-twin research" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
