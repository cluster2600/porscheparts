# Kit runtime builder only. The station composes its AI runtime separately.
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852 AS kit-build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 ca-certificates git curl unzip build-essential pkg-config \
    libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev \
    libsdl2-2.0-0 libgomp1 libxkbcommon0 libxt6 libglu1-mesa libegl1 \
    libgl1 libvulkan1 libnss3 libasound2t64 \
    && rm -rf /var/lib/apt/lists/*
COPY containers/picogk-station-kit/station.editor_streaming.kit containers/picogk-station-kit/launch.py containers/picogk-station-kit/open_scene.py /opt/station-kit-recipe/
COPY containers/stack-20261105/kit-install.sh /opt/station-kit-recipe/install.sh
ARG NVIDIA_EULA_ACCEPTED=no
RUN NVIDIA_EULA_ACCEPTED=$NVIDIA_EULA_ACCEPTED bash /opt/station-kit-recipe/install.sh

FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 ca-certificates libx11-6 libxrandr2 libxinerama1 libxcursor1 \
    libxi6 libsdl2-2.0-0 libgomp1 libxkbcommon0 libxt6 libglu1-mesa \
    libegl1 libgl1 libvulkan1 libnss3 libasound2t64 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=kit-build /opt/station-kit-runtime /opt/station-kit-runtime
COPY --from=kit-build /usr/local/bin/station-kit /usr/local/bin/station-kit
COPY containers/stack-20261105/nvidia-headless-icd.json /etc/vulkan/icd.d/nvidia-headless.json
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,video,display \
    VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia-headless.json
# File/package verification is separate from the GPU editor/streaming test.
CMD ["bash", "-ec", "test -x /opt/station-kit-runtime/kit/kit; test -s /opt/station-kit-runtime/apps/station.editor_streaming.kit; test -s /opt/station-kit-runtime/LICENSE; grep -qx b8e9f2e4f2930d19e87e3702d4eeaf00d9846676 /opt/station-kit-runtime/kit-app-template-revision.txt; echo KIT_PACKAGED_GPU_RUNTIME_UNTESTED"]
