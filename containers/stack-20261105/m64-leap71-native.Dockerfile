# syntax=docker/dockerfile:1.7
FROM mcr.microsoft.com/dotnet/sdk:10.0@sha256:de4fe90a98845d75910b9769662465c84de1a934665c431279d1382b2bddc02b
ENV DEBIAN_FRONTEND=noninteractive DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-venv ninja-build g++ libboost-iostreams-dev libboost-system-dev \
    libtbb-dev libblosc-dev zlib1g-dev libimath-dev libopenexr-dev \
    libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev \
    libgl1-mesa-dev libwayland-dev libxkbcommon-dev \
    && rm -rf /var/lib/apt/lists/*
COPY containers/stack-20261105/cmake.requirements.txt /opt/locks/cmake.requirements.txt
RUN python3 -m venv /opt/build-tools \
    && /opt/build-tools/bin/pip install --no-cache-dir --require-hashes -r /opt/locks/cmake.requirements.txt
ENV PATH=/opt/build-tools/bin:${PATH}
WORKDIR /src
COPY containers/stack-20261105/sources.lock containers/stack-20261105/Smoke.csproj ./
COPY containers/m64-leap71/bootstrap.sh containers/m64-leap71/Program.cs ./
RUN sh bootstrap.sh /upstream \
    && git -C /upstream/PicoGKRuntime submodule update --init --depth 1 \
    && git -C /upstream/PicoGKRuntime submodule status --recursive > /opt/locks/native-submodules.txt
RUN --mount=type=cache,id=stack-picogk-native-net10,target=/native-build \
    cmake -S /upstream/PicoGKRuntime -B /native-build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DOPENVDB_BUILD_BINARIES=OFF -DOPENVDB_BUILD_UNITTESTS=OFF \
      -DOPENVDB_CORE_SHARED=OFF -DOPENVDB_CORE_STATIC=ON -DGLFW_BUILD_WAYLAND=OFF \
      -DOPENVDB_USE_DELAYED_LOADING=OFF -DUSE_IMATH_HALF=OFF -DUSE_EXR=OFF \
      -DGLFW_BUILD_EXAMPLES=OFF -DGLFW_BUILD_TESTS=OFF -DGLFW_BUILD_DOCS=OFF \
    && cmake --build /native-build --target picogk -j 1 \
    && install -Dm755 /native-build/lib/picogk.so /opt/native/picogk.26.2.so
RUN dotnet build Smoke.csproj -c Release -o /app -p:GeneratePackageOnBuild=false \
    && cp /opt/native/picogk.26.2.so /app/
COPY containers/stack-20261105/RuntimeWitness.csproj /opt/witness/
COPY containers/m64-leap71/RuntimeWitness.cs /opt/witness/
ENV LD_LIBRARY_PATH=/app
RUN dotnet build /opt/witness/RuntimeWitness.csproj -c Release -o /opt/witness/bin
RUN --network=none dotnet /opt/witness/bin/RuntimeWitness.dll /tmp/build-witness \
    && rm -rf /tmp/build-witness
ENTRYPOINT ["dotnet", "/opt/witness/bin/RuntimeWitness.dll"]
CMD ["/tmp/runtime-witness"]
