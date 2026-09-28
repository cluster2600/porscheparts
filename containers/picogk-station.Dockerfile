# syntax=docker/dockerfile:1.7
# One standard Vast container: no Docker socket or nested Docker required.
ARG PICOGK_IMAGE=ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:7c7048431256c455d1396c2e71e38be15b6d0d5d035f41fdde03de47a9025ccd
ARG QWEN_IMAGE=ghcr.io/cluster2600/qwen38-flash-next-vast@sha256:6b3b1790dd3140c27a5b5f85181dccef06c8d96c02f3003bb3c9b267b8758e34
ARG KIT_IMAGE=kit-build
FROM ${QWEN_IMAGE} AS kit-build
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl unzip build-essential pkg-config libx11-dev libxrandr-dev \
    libxinerama-dev libxcursor-dev libxi-dev libsdl2-2.0-0 libgomp1 \
    libxkbcommon0 libxt6 libglu1-mesa libegl1 libgl1 libvulkan1 \
    && rm -rf /var/lib/apt/lists/*
COPY containers/picogk-station-kit /opt/station-kit-recipe
ARG NVIDIA_EULA_ACCEPTED=no
RUN NVIDIA_EULA_ACCEPTED=$NVIDIA_EULA_ACCEPTED bash /opt/station-kit-recipe/install.sh

FROM node:22.19.0-bookworm-slim@sha256:4a4884e8a44826194dff92ba316264f392056cbe243dcc9fd3551e71cea02b90 AS client-build
WORKDIR /build/client
COPY deploy/vast/station-client/ ./
RUN npm ci --ignore-scripts --no-audit --no-fund && npm test && npm run build

FROM ${PICOGK_IMAGE} AS picogk
# Preserve Debian ABI dependencies privately; never replace Ubuntu's libc.
RUN mkdir -p /native-libs && ldd /app/picogk.26.2.so \
    | awk '/=> \/.*lib(boost|tbb|blosc|lz4|snappy|zstd|z\.so)/ {print $3}' \
    | xargs -r cp -L -t /native-libs

FROM ${QWEN_IMAGE} AS station-core
ENV DEBIAN_FRONTEND=noninteractive \
    DOTNET_ROOT=/usr/share/dotnet DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 \
    MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306 \
    MAX_MODEL_LEN=262144 MAX_NUM_SEQS=4 MAX_NUM_BATCHED_TOKENS=4096 \
    GPU_MEMORY_UTILIZATION=0.90 TENSOR_PARALLEL_SIZE=2 DATA_PARALLEL_SIZE=1 \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,video,display \
    NVIDIA_VISIBLE_DEVICES=all PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server rsync supervisor tini python3.12-venv python3-numpy \
    calculix-ccx gmsh libicu74 libgl1 libegl1 libglu1-mesa libopengl0 \
    libvulkan1 vulkan-tools libx11-6 libxrandr2 libxinerama1 libxcursor1 libxi6 \
    libsdl2-2.0-0 libgomp1 libxkbcommon0 libxt6 libnss3 libasound2t64 \
    xvfb xauth unzip pkg-config build-essential curl git ca-certificates \
    && find /etc/ssh -maxdepth 1 -name 'ssh_host_*' -type f -delete \
    && mv /usr/sbin/sshd /usr/lib/openssh/sshd.real \
    && mkdir -p /run/sshd /opt/provenance /workspace/logs /root/.ssh \
    && chmod 0700 /root/.ssh \
    && install -m 0600 /dev/null /root/.no_auto_tmux \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN curl -fL --retry 3 -o /tmp/freecad.AppImage \
    https://github.com/FreeCAD/FreeCAD/releases/download/1.0.2/FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage \
    && echo 'e00be00ad9fdb12b05c5002bfd1aa2ea8126f2c1d4e2fb603eb7423b72904f61  /tmp/freecad.AppImage' | sha256sum -c - \
    && chmod 0755 /tmp/freecad.AppImage && cd /opt \
    && /tmp/freecad.AppImage --appimage-extract >/dev/null \
    && mv squashfs-root freecad && rm /tmp/freecad.AppImage
COPY --from=picogk /usr/share/dotnet/ /usr/share/dotnet/
COPY --from=picogk /native-libs/ /opt/picogk-native/lib/
COPY --from=picogk /app/ /app/
COPY --from=picogk /upstream/PicoGK/ /upstream/PicoGK/
COPY --from=picogk /opt/picogk-witness/ /opt/picogk-witness/
COPY --from=picogk /opt/m64/ /opt/m64/
COPY --from=picogk /opt/m64-source/ /opt/m64-source/
COPY --from=picogk /opt/provenance/sources.lock /opt/provenance/native-library.sha256 /opt/provenance/dotnet-info.txt /opt/provenance/
RUN ln -s /usr/share/dotnet/dotnet /usr/local/bin/dotnet \
    && test "$(dotnet --version)" = 9.0.317
COPY containers/cad-author-f28-requirements.txt /opt/provenance/cad-requirements.txt
COPY containers/m64-leap71/geometry-qa-requirements.txt /opt/provenance/geometry-requirements.txt
RUN python3.12 -m venv /opt/cad \
    && /opt/cad/bin/pip install --no-cache-dir --no-deps --require-hashes -r /opt/provenance/cad-requirements.txt \
    && /opt/cad/bin/pip check \
    && python3.12 -m venv /opt/geometry-qa \
    && /opt/geometry-qa/bin/pip install --no-cache-dir -r /opt/provenance/geometry-requirements.txt \
    && /opt/geometry-qa/bin/pip freeze > /opt/provenance/geometry-resolved.txt
COPY containers/picogk-station/ovrtx-requirements.txt /opt/provenance/ovrtx-requirements.txt
RUN python3.12 -m venv /opt/ovrtx-runtime \
    && /opt/ovrtx-runtime/bin/pip install --no-cache-dir --no-deps --require-hashes -r /opt/provenance/ovrtx-requirements.txt
COPY containers/simready-sshd-runtime-wrapper.sh /usr/local/bin/station-sshd
COPY containers/m64-leap71/sshd-policy.conf /etc/ssh/sshd_config.d/00-station.conf
COPY containers/picogk-station/*.sh containers/picogk-station/cad-smoke.py containers/picogk-station/render.py containers/picogk-station/supervisord.conf /opt/station/
COPY containers/picogk-station/nvidia_icd.json /etc/vulkan/icd.d/nvidia_icd.json
RUN ln -s /usr/local/bin/station-sshd /usr/sbin/sshd \
    && chmod 0755 /usr/local/bin/station-sshd /opt/station/*.sh \
    && ln -s /opt/station/picogk.sh /usr/local/bin/station-picogk \
    && ln -s /opt/station/qwen.sh /usr/local/bin/station-qwen \
    && ln -s /opt/station/onstart.sh /usr/local/bin/station-onstart \
    && ln -s /opt/station/render.sh /usr/local/bin/station-render \
    && ln -s /opt/freecad/AppRun /usr/local/bin/station-freecad \
    && ln -s /opt/ovrtx-runtime/lib/python3.12/site-packages/ovrtx/bin/library /opt/ovrtx-runtime/lib/python3.12/site-packages/library \
    && sed -i '/--served-model-name/i\  --revision "$MODEL_REVISION" \\' /opt/qwen/start.sh \
    && dpkg-query -W > /opt/provenance/ubuntu-packages.tsv \
    && /opt/station/cpu-smoke.sh
WORKDIR /workspace
EXPOSE 22
ENTRYPOINT ["tini", "-g", "--", "/opt/station/entrypoint.sh"]
CMD ["sshd"]
LABEL org.opencontainers.image.title="PicoGK CAD Qwen Omniverse station" \
    org.opencontainers.image.source="https://github.com/cluster2600/porscheparts" \
    org.opencontainers.image.description="Software geometry qualification only; no manufacturing validation"

FROM station-core AS station-demo
RUN /opt/geometry-qa/bin/pip install --no-cache-dir 'usd-core==25.11' 'shapely==2.1.2' \
    && /opt/geometry-qa/bin/pip check \
    && /opt/geometry-qa/bin/pip freeze > /opt/provenance/geometry-resolved.txt \
    && useradd --uid 10002 --create-home --shell /bin/bash station-worker \
    && OVRTX_BIN=/opt/ovrtx-runtime/lib/python3.12/site-packages/ovrtx/bin \
    && mkdir -p "${OVRTX_BIN}/cache" "${OVRTX_BIN}/mdl/omniverse_exts" \
    && chown -R station-worker:station-worker "${OVRTX_BIN}/cache" "${OVRTX_BIN}/mdl/omniverse_exts" \
    && runuser -u station-worker -- test -w "${OVRTX_BIN}/cache" \
    && runuser -u station-worker -- test -w "${OVRTX_BIN}/mdl/omniverse_exts" \
    && install -d -o station-worker -g station-worker /workspace/jobs
COPY twins/picogk-station-demo/StationDemo.csproj twins/picogk-station-demo/Program.cs /opt/station-repo/twins/picogk-station-demo/
COPY scripts/run_picogk_station_demo.py scripts/run_metal_am_geometry_screen.py scripts/build_process_route_card.py /opt/station-repo/scripts/
COPY twins/reference-917-engine/source/run_f50_lpbf_geometry_audit.py /opt/station-repo/twins/reference-917-engine/source/
COPY catalog/manufacturing/machines/eos-m290.json /opt/station-repo/catalog/manufacturing/machines/
COPY catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json /opt/station-repo/catalog/manufacturing/processes/
RUN dotnet build /opt/station-repo/twins/picogk-station-demo/StationDemo.csproj \
    -c Release -o /opt/station-demo/bin -p:GeneratePackageOnBuild=false \
    && ln -s /opt/station/demo.sh /usr/local/bin/station-demo \
    && timeout 600 /usr/local/bin/station-demo /opt/provenance/station-demo-cpu

FROM ${KIT_IMAGE} AS kit-ready
FROM station-demo AS station
COPY --from=kit-ready /opt/station-kit-runtime/ /opt/station-kit-runtime/
COPY --from=kit-ready /usr/local/bin/station-kit /usr/local/bin/station-kit
COPY --from=client-build /build/client/dist/ /opt/station-client/
COPY --chmod=0755 deploy/vast/station/media-relay.py /usr/local/bin/station-media-relay
COPY containers/picogk-station/cad-coupon.py /opt/station/cad-coupon.py
RUN printf '%s\n' 'This software contains source code provided by NVIDIA Corporation.' \
    'https://docs.omniverse.nvidia.com/avp/latest/common/NVIDIA_Omniverse_License_Agreement.html' \
    'https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/' \
    > /opt/provenance/NVIDIA-NOTICE.txt \
    && QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH=/opt/freecad/usr/lib \
    /opt/freecad/usr/bin/python /opt/station/cad-coupon.py /opt/provenance/cad-coupon
LABEL org.opencontainers.image.licenses="NOASSERTION"
