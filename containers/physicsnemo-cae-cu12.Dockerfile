# syntax=docker/dockerfile:1.7
#
# Image modulaire PhysicsNeMo CAE. Elle contient uniquement l'environnement
# de surrogate learning : aucun scan, dataset, poids, solveur classique ou
# composant Omniverse n'est copié dans l'image.

ARG CUDA_BASE_IMAGE=nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04@sha256:ac55d124da4882b497f732d8dfd9a702d5447a5f29d08d56da6f64f0a1eb34bc
FROM ${CUDA_BASE_IMAGE} AS physicsnemo-cae

ARG TARGETARCH
ARG PHYSICSNEMO_VERSION=2.2.1
ARG TORCH_VERSION=2.10.0
ARG TORCHVISION_VERSION=0.25.0
ARG TORCH_GEOMETRIC_VERSION=2.8.0.post1
ARG ANTLR4_RUNTIME_VERSION=4.9.3
ARG ANTLR4_RUNTIME_SDIST_SHA256=f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b
ARG PIP_VERSION=26.2.1
ARG SETUPTOOLS_VERSION=84.0.0
ARG WHEEL_VERSION=0.48.0

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/physicsnemo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    VIRTUAL_ENV=/opt/physicsnemo \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    PHYSICSNEMO_REQUIRE_GPU=0

# Les roues PyG de la combinaison torch 2.10 / cu128 / Python 3.12 sont
# publiées pour linux/amd64. L'échec est volontaire sur une autre architecture.
RUN test "${TARGETARCH}" = "amd64"

# Le digest de l'image finale est la frontière de reproductibilité. Les paquets
# Ubuntu suivent les correctifs de sécurité du dépôt noble au jour du build.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        passwd \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY containers/physicsnemo-cae-cu12-constraints.txt /opt/build/constraints.txt

RUN python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version' \
    && python3 -m venv /opt/physicsnemo \
    && /opt/physicsnemo/bin/python -m pip install --only-binary=:all: \
        "pip==${PIP_VERSION}" \
        "setuptools==${SETUPTOOLS_VERSION}" \
        "wheel==${WHEEL_VERSION}" \
    && /opt/physicsnemo/bin/python -m pip download --no-deps --no-binary=:all: \
        --dest /opt/build \
        "antlr4-python3-runtime==${ANTLR4_RUNTIME_VERSION}" \
    && printf '%s  %s\n' \
        "${ANTLR4_RUNTIME_SDIST_SHA256}" \
        "/opt/build/antlr4-python3-runtime-${ANTLR4_RUNTIME_VERSION}.tar.gz" \
        | sha256sum -c - \
    && /opt/physicsnemo/bin/python -m pip wheel --no-build-isolation --no-deps \
        --no-index \
        --wheel-dir /opt/build/wheels \
        "/opt/build/antlr4-python3-runtime-${ANTLR4_RUNTIME_VERSION}.tar.gz" \
    && /opt/physicsnemo/bin/python -m pip install --only-binary=:all: \
        --no-index \
        --find-links /opt/build/wheels \
        "antlr4-python3-runtime==${ANTLR4_RUNTIME_VERSION}" \
    && /opt/physicsnemo/bin/python -m pip install --only-binary=:all: \
        --index-url https://download.pytorch.org/whl/cu128 \
        --constraint /opt/build/constraints.txt \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
    && /opt/physicsnemo/bin/python -m pip install --only-binary=:all: \
        --find-links https://data.pyg.org/whl/torch-2.10.0+cu128.html \
        --constraint /opt/build/constraints.txt \
        "torch-geometric==${TORCH_GEOMETRIC_VERSION}" \
        "torch-scatter==2.1.2+pt210cu128" \
        "torch-sparse==0.6.18+pt210cu128" \
        "torch-cluster==1.6.3+pt210cu128" \
    && /opt/physicsnemo/bin/python -m pip install --only-binary=:all: \
        --extra-index-url https://pypi.nvidia.com \
        --constraint /opt/build/constraints.txt \
        "nvidia-physicsnemo[mesh-extras]==${PHYSICSNEMO_VERSION}" \
    && /opt/physicsnemo/bin/python -m pip check \
    && /opt/physicsnemo/bin/python -m pip freeze --all \
        > /opt/physicsnemo/environment.freeze.txt

COPY containers/physicsnemo-cae-cu12-smoke.py /usr/local/bin/physicsnemo-cae-smoke
RUN chmod 0555 /usr/local/bin/physicsnemo-cae-smoke \
    && /opt/physicsnemo/bin/python /usr/local/bin/physicsnemo-cae-smoke

RUN groupadd --gid 1000 physicsnemo \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash physicsnemo \
    && mkdir -p /workspace/input /workspace/output /workspace/jobs \
    && chown -R physicsnemo:physicsnemo /workspace

USER 1000:1000
WORKDIR /workspace

LABEL org.opencontainers.image.title="3dprinting993-physicsnemo-cae-cu12" \
      org.opencontainers.image.description="PhysicsNeMo 2.2.1 CUDA 12 CAE surrogate environment; no scans, datasets or model weights" \
      org.opencontainers.image.version="2.2.1" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Apache-2.0 AND BSD-3-Clause AND MIT AND LicenseRef-NVIDIA-CUDA"

CMD ["physicsnemo-cae-smoke"]
