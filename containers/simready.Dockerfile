# syntax=docker/dockerfile:1.7
#
# 3dprinting993 - NVIDIA CAD-to-SimReady runtime for a single Vast.ai container.
#
# Content Agents normally use Docker Compose. Vast.ai standard instances are
# already unprivileged containers and cannot run Docker-in-Docker, so this image
# installs OVRTX, Material Agent and Physics Agent in isolated virtual
# environments and supervises their native service entrypoints directly.

FROM ubuntu:24.04

ARG TARGETARCH=amd64
ARG CONTENT_AGENTS_COMMIT=36dbf3f274f8e256637230a05a085853f65cc175
ARG SIMREADY_FOUNDATION_COMMIT=0ed0dfbc539c9de99289771bd6848effe3ef5779
ARG USD_CONVERT_CAD_VERSION=0.2.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
    NVIDIA_VISIBLE_DEVICES=all \
    CONTENT_AGENTS_ROOT=/opt/content-agents \
    SIMREADY_FOUNDATION_ROOT=/opt/simready-foundation \
    WU_SO_PACKAGE_DIR=/opt/content-agents/.build-resources/scene_optimizer_core \
    WU_OVRTX_VENV_DIR=/opt/ovrtx-runtime \
    WU_OVPHYSX_VENV_DIR=/opt/ovphysx-runtime \
    CONTENT_AGENTS_MATERIAL_AGENT_BASE_URL=http://127.0.0.1:8100 \
    CONTENT_AGENTS_PHYSICS_AGENT_BASE_URL=http://127.0.0.1:8200 \
    RENDER_ENDPOINT=http://127.0.0.1:8001 \
    PATH=/opt/usd-convert-cad/bin:/opt/simready-validation/bin:/usr/local/bin:/usr/bin:/bin

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      curl \
      git \
      git-lfs \
      gnupg \
      jq \
      libgl1 \
      libglib2.0-0 \
      libgomp1 \
      libgpgme11t64 \
      libopengl0 \
      libvulkan1 \
      libx11-6 \
      libxt6 \
      openssh-server \
      passwd \
      python3.12 \
      python3.12-dev \
      python3.12-venv \
      rsync \
      supervisor \
      tini \
      unzip \
      xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.12 /usr/bin/python

RUN git clone --filter=blob:none https://github.com/nvidia-omniverse/content-agents.git /opt/content-agents \
    && git -C /opt/content-agents checkout --detach "${CONTENT_AGENTS_COMMIT}" \
    && git -C /opt/content-agents lfs pull \
    && git clone --filter=blob:none https://github.com/NVIDIA/simready-foundation.git /opt/simready-foundation \
    && git -C /opt/simready-foundation checkout --detach "${SIMREADY_FOUNDATION_COMMIT}" \
    && git -C /opt/simready-foundation lfs pull \
    && /opt/content-agents/scripts/fetch_build_resources.sh \
    && install -D -m 0644 \
       /opt/content-agents/apps/ovrtx_rendering_api/nvidia_icd.json \
       /etc/vulkan/icd.d/nvidia_icd.json \
    && chmod -R a+rX /opt/content-agents /opt/simready-foundation

# OVRTX application and its deliberately isolated native renderer runtime.
RUN python3.12 -m venv /opt/ovrtx-app \
    && /opt/ovrtx-app/bin/pip install --no-cache-dir --upgrade "pip>=26.1" uv \
    && cd /opt/content-agents \
    && SETUPTOOLS_SCM_PRETEND_VERSION=0.5.2 UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/ovrtx-app/bin/uv pip install --python /opt/ovrtx-app/bin/python \
       -e ".[telemetry]" --no-config --no-sources \
    && cd /opt/content-agents/apps/ovrtx_rendering_api \
    && /opt/ovrtx-app/bin/uv pip install --python /opt/ovrtx-app/bin/python \
       -e . --no-config --no-sources \
    && /opt/ovrtx-app/bin/uv venv /opt/ovrtx-runtime --python python3.12 \
    && /opt/ovrtx-app/bin/uv pip install --python /opt/ovrtx-runtime/bin/python \
       -r /opt/content-agents/world_understanding/functions/graphics/pylock.ovrtx-runtime.toml \
       --require-hashes --no-deps --no-config --no-sources \
    && PYTHONPATH=/opt/content-agents WU_OVRTX_AUTO_PROVISION=0 \
       WU_OVRTX_LOCK_DIR=/tmp/wu-ovrtx-locks \
       /opt/ovrtx-app/bin/python -m world_understanding.functions.graphics.render_ovrtx --provision-only \
    && rm -rf /tmp/wu-ovrtx-locks /root/.cache/uv

# Material Agent uses a separate environment to avoid OpenUSD provider drift.
RUN python3.12 -m venv /opt/material-agent \
    && /opt/material-agent/bin/pip install --no-cache-dir --upgrade "pip>=26.1" uv \
    && cd /opt/content-agents \
    && SETUPTOOLS_SCM_PRETEND_VERSION=0.5.2 UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/material-agent/bin/uv pip install --python /opt/material-agent/bin/python \
       -e ".[telemetry]" --no-config --no-sources \
    && cd /opt/content-agents/apps/material_agent \
    && UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/material-agent/bin/uv pip install --python /opt/material-agent/bin/python \
       -e . --no-config --no-sources \
    && cd /opt/content-agents/apps/material_agent_service \
    && UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/material-agent/bin/uv pip install --python /opt/material-agent/bin/python \
       -e . --no-config --no-sources \
    && rm -rf /root/.cache/uv

# Physics Agent keeps OvPhysX in its own runtime for the same OpenUSD reason.
RUN python3.12 -m venv /opt/physics-agent \
    && /opt/physics-agent/bin/pip install --no-cache-dir --upgrade "pip>=26.1" uv \
    && cd /opt/content-agents \
    && SETUPTOOLS_SCM_PRETEND_VERSION=0.5.2 UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/physics-agent/bin/uv pip install --python /opt/physics-agent/bin/python \
       -e ".[telemetry]" --no-config --no-sources \
    && cd /opt/content-agents/apps/physics_agent \
    && UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/physics-agent/bin/uv pip install --python /opt/physics-agent/bin/python \
       -e . --no-deps --no-config --no-sources \
    && case "${TARGETARCH}" in \
         amd64) tuning_lock=pylock.physics-tuning-runtime.toml; ovphysx_lock=pylock.ovphysx-runtime.toml ;; \
         arm64) tuning_lock=pylock.physics-tuning-runtime.aarch64.toml; ovphysx_lock=pylock.ovphysx-runtime.aarch64.toml ;; \
         *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && /opt/physics-agent/bin/uv pip install --python /opt/physics-agent/bin/python \
       -r "/opt/content-agents/apps/physics_agent/runtime/${tuning_lock}" \
       --no-config --no-sources \
    && /opt/physics-agent/bin/uv venv /opt/ovphysx-runtime --python python3.12 \
    && /opt/physics-agent/bin/uv pip install --python /opt/ovphysx-runtime/bin/python \
       -r "/opt/content-agents/apps/physics_agent/runtime/${ovphysx_lock}" \
       --require-hashes --no-deps --no-config --no-sources \
    && env -u PYTHONPATH /opt/ovphysx-runtime/bin/python -c \
       "from ovphysx import PhysX; physics = PhysX(device='cpu'); physics.release()" \
    && touch /opt/ovphysx-runtime/.wu-ovphysx-runtime-ready \
    && cd /opt/content-agents/apps/physics_agent_service \
    && UV_DYNAMIC_VERSIONING_BYPASS=0.5.2 \
       /opt/physics-agent/bin/uv pip install --python /opt/physics-agent/bin/python \
       -e . --no-config --no-sources \
    && rm -rf /root/.cache/uv

# Validation and CAD conversion stay isolated because both ship OpenUSD APIs.
RUN python3.12 -m venv /opt/simready-validation \
    && /opt/simready-validation/bin/pip install --no-cache-dir --upgrade "pip>=26.1" uv \
    && /opt/simready-validation/bin/uv pip install --python /opt/simready-validation/bin/python \
       -r /opt/simready-foundation/requirements.txt "numpy>=1.24,<3" \
    && python3.12 -m venv /opt/usd-convert-cad \
    && /opt/usd-convert-cad/bin/pip install --no-cache-dir --upgrade "pip>=26.1" \
    && /opt/usd-convert-cad/bin/pip install --no-cache-dir \
       --extra-index-url https://pypi.nvidia.com "usd-convert-cad==${USD_CONVERT_CAD_VERSION}"

COPY containers/simready-supervisord.conf /etc/simready-supervisord.conf
COPY containers/simready-services.sh /usr/local/bin/simready-services
COPY containers/simready-smoke.sh /usr/local/bin/simready-smoke
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
COPY containers/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod 0555 \
      /usr/local/bin/entrypoint.sh \
      /usr/local/bin/simready-services \
      /usr/local/bin/simready-smoke \
      /usr/local/bin/smoke-test.sh \
      /opt/content-agents/apps/ovrtx_rendering_api/docker-entrypoint.sh \
    && install -d -m 0755 /workspace /workspace/logs \
       /var/material-agent/sessions /var/physics-agent/sessions \
    && groupadd --gid 10001 renderer \
    && useradd --uid 10001 --gid renderer --create-home --home-dir /home/renderer renderer \
    && useradd --uid 10000 --create-home --home-dir /home/agents agents \
    && chown -R renderer:renderer /home/renderer \
    && chown -R agents:agents /var/material-agent /var/physics-agent \
    && install -d -o renderer -g renderer -m 0700 /home/renderer/.cache/ovrtx-nv-shadercache \
    && install -d -o renderer -g renderer -m 0700 /tmp/.X11-unix \
    && OVRTX_BIN=/opt/ovrtx-runtime/lib/python3.12/site-packages/ovrtx/bin \
    && mkdir -p "${OVRTX_BIN}/cache" \
    && rm -rf "${OVRTX_BIN}/cache/nv_shadercache" \
    && chown -R renderer:renderer "${OVRTX_BIN}/cache" \
    && ln -s /home/renderer/.cache/ovrtx-nv-shadercache "${OVRTX_BIN}/cache/nv_shadercache"

WORKDIR /workspace
EXPOSE 8001 8100 8200 22

LABEL org.opencontainers.image.title="3dprinting993-simready" \
      org.opencontainers.image.description="Single-container NVIDIA OVRTX, Material Agent, Physics Agent, USD conversion and SimReady validation runtime" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="Apache-2.0 AND LicenseRef-NVIDIA-Omniverse"

ENTRYPOINT ["tini", "-g", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
