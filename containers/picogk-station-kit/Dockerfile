FROM ghcr.io/cluster2600/qwen38-flash-next-vast@sha256:6b3b1790dd3140c27a5b5f85181dccef06c8d96c02f3003bb3c9b267b8758e34

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl unzip build-essential pkg-config libx11-dev libxrandr-dev \
    libxinerama-dev libxcursor-dev libxi-dev libsdl2-2.0-0 libgomp1 \
    libxkbcommon0 libxt6 libglu1-mesa libegl1 libgl1 libvulkan1 \
    && rm -rf /var/lib/apt/lists/*
COPY containers/picogk-station-kit /opt/station-kit-recipe
ARG NVIDIA_EULA_ACCEPTED=no
RUN NVIDIA_EULA_ACCEPTED=$NVIDIA_EULA_ACCEPTED bash /opt/station-kit-recipe/install.sh
