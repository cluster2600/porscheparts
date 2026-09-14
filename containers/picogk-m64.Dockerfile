# Official managed/native sources are pinned in sources.lock; the SDK manifest
# digest fixes .NET SDK 9.0.317 on Debian 12. No scans or private CAD are copied.
ARG NATIVE_IMAGE=native
FROM mcr.microsoft.com/dotnet/sdk:9.0@sha256:f190d2dd9eef2899c91ac323caa0bd2b39334a5400ba93013e5199da39dad940 AS native
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake ninja-build g++ libboost-iostreams-dev libboost-system-dev \
    libtbb-dev libblosc-dev zlib1g-dev libimath-dev libopenexr-dev \
    libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev \
    libgl1-mesa-dev libwayland-dev libxkbcommon-dev \
    && apt-get clean
WORKDIR /src
COPY containers/m64-leap71/sources.lock containers/m64-leap71/bootstrap.sh containers/m64-leap71/Smoke.csproj containers/m64-leap71/Program.cs ./
RUN sh bootstrap.sh /upstream
RUN git -C /upstream/PicoGKRuntime submodule update --init --depth 1
RUN cmake -S /upstream/PicoGKRuntime -B /native-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DOPENVDB_BUILD_BINARIES=OFF \
    -DOPENVDB_BUILD_UNITTESTS=OFF -DOPENVDB_CORE_SHARED=OFF \
    -DOPENVDB_CORE_STATIC=ON -DGLFW_BUILD_WAYLAND=OFF \
    -DOPENVDB_USE_DELAYED_LOADING=OFF -DUSE_IMATH_HALF=OFF -DUSE_EXR=OFF \
    -DGLFW_BUILD_EXAMPLES=OFF -DGLFW_BUILD_TESTS=OFF -DGLFW_BUILD_DOCS=OFF
RUN cmake --build /native-build --target picogk -j 4
RUN dotnet build Smoke.csproj -c Release -o /app -p:GeneratePackageOnBuild=false
RUN cp /native-build/lib/picogk.so /app/picogk.26.2.so

# An explicitly inspected local native-preflight image may be substituted for
# native to reuse its already-passing x86 C++ build. CI uses the stage above.
FROM ${NATIVE_IMAGE} AS workstation
LABEL org.opencontainers.image.title="M64 PicoGK headless workstation" \
      org.opencontainers.image.description="Geometry research only; no manufacturing or engine validation" \
      org.opencontainers.image.source="https://github.com/cluster2600/porscheparts"
RUN test "$(dotnet --version)" = 9.0.317 \
    && apt-get update && apt-get install -y --no-install-recommends openssh-server ca-certificates python3-venv time libgl1 \
    && apt-get clean \
    && find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*' -delete \
    && mv /usr/sbin/sshd /usr/lib/openssh/sshd.real \
    && mkdir -p /run/sshd /opt/picogk-witness /opt/provenance /workspace \
    && install -m 0600 /dev/null /root/.no_auto_tmux
ENV LD_LIBRARY_PATH=/app \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    PATH=/opt/geometry-qa/bin:$PATH \
    MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1
COPY containers/m64-leap71/geometry-qa-requirements.txt /opt/provenance/geometry-qa-requirements.txt
RUN python3 -m venv /opt/geometry-qa \
    && /opt/geometry-qa/bin/pip install --no-cache-dir -r /opt/provenance/geometry-qa-requirements.txt \
    && /opt/geometry-qa/bin/pip freeze > /opt/provenance/geometry-qa-resolved.txt
COPY containers/m64-leap71/geometry-python-smoke.py /opt/picogk-witness/geometry-python-smoke.py
COPY containers/m64-leap71/RuntimeWitness.csproj containers/m64-leap71/RuntimeWitness.cs /opt/picogk-witness/
COPY containers/m64-leap71/vast-entrypoint.sh /usr/local/bin/picogk-entrypoint
COPY containers/m64-leap71/vast-onstart.sh /usr/local/bin/picogk-vast-onstart
COPY containers/m64-leap71/picogk-smoke.sh /usr/local/bin/smoke-test.sh
COPY containers/simready-sshd-runtime-wrapper.sh /usr/local/bin/picogk-sshd-runtime-wrapper
COPY containers/m64-leap71/sshd-policy.conf /etc/ssh/sshd_config.d/00-picogk.conf
COPY containers/m64-leap71/sources.lock containers/m64-leap71/native-submodules.lock /opt/provenance/
COPY twins/m64-cylinder-head/source/picogk/HeadVoxels.csproj twins/m64-cylinder-head/source/picogk/Program.cs /opt/m64-source/
RUN dotnet build /opt/picogk-witness/RuntimeWitness.csproj -c Release -o /opt/picogk-witness/bin \
    && dotnet build /opt/m64-source/HeadVoxels.csproj -c Release -o /opt/m64 -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false \
    && chmod 0755 /usr/local/bin/picogk-entrypoint /usr/local/bin/picogk-vast-onstart /usr/local/bin/smoke-test.sh /usr/local/bin/picogk-sshd-runtime-wrapper \
    && ln -s /usr/local/bin/picogk-sshd-runtime-wrapper /usr/sbin/sshd \
    && dpkg-query -W > /opt/provenance/debian-packages.tsv \
    && dotnet --info > /opt/provenance/dotnet-info.txt \
    && sha256sum /app/picogk.26.2.so > /opt/provenance/native-library.sha256 \
    && dotnet /opt/picogk-witness/bin/RuntimeWitness.dll /opt/provenance/runtime-witness \
    && /usr/local/bin/smoke-test.sh picogk-m64
# SSH host keys were removed in the same layer as installation. Runtime keys
# are container-specific; deleting them only in a later layer would leak keys.
EXPOSE 22
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/picogk-entrypoint"]
CMD ["sshd"]
