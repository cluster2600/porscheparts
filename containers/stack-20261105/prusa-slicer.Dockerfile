# syntax=docker/dockerfile:1.7
# Auxiliary upstream CLI build used to replace Ubuntu's older slicer.
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852 AS build
ENV DEBIAN_FRONTEND=noninteractive CMAKE_BUILD_PARALLEL_LEVEL=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates build-essential autoconf cmake libglu1-mesa-dev \
    libgtk-3-dev libdbus-1-dev libwebkit2gtk-4.1-dev texinfo curl \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch version_2.9.7 https://github.com/prusa3d/PrusaSlicer.git /src \
    && test "$(git -C /src rev-parse version_2.9.7)" = 4b8477da3eee0254e4ecf57212a9aa89f68e0c10 \
    && test "$(git -C /src rev-parse HEAD)" = 450d70dd81c9b8990bc6bc8e690e31f82ddceb11
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends automake libtool \
    && rm -rf /var/lib/apt/lists/*
# Preserve upstream GMP bytes while avoiding the repeatedly truncated primary download.
ADD --checksum=sha256:eae9326beb4158c386e39a356818031bd28f3124cf915f8c5b1dc4c7a36b4d7c https://mirrors.kernel.org/gnu/gmp/gmp-6.2.1.tar.bz2 /src/deps/build/downloads/GMP/gmp-6.2.1.tar.bz2
RUN cmake -S /src/deps -B /src/deps/build -DDEP_WX_GTK3=ON -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /src/deps/build --parallel 1
RUN cmake -S /src -B /src/build -DCMAKE_BUILD_TYPE=Release \
    -DSLIC3R_STATIC=ON -DSLIC3R_GUI=OFF -DSLIC3R_PCH=OFF \
    -DSLIC3R_BUILD_TESTS=OFF -DSLIC3R_FHS=ON -DCMAKE_INSTALL_PREFIX=/opt/prusa \
    -DCMAKE_PREFIX_PATH=/src/deps/build/destdir/usr/local \
    && cmake --build /src/build --parallel 1 \
    && cmake --install /src/build
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/prusa/bin:/usr/local/bin:/usr/bin:/bin
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libgl1 libglu1-mesa libdbus-1-3 libgomp1 python3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/prusa /opt/prusa
COPY containers/stack-20261105/prusa-smoke.py /opt/stack/prusa-smoke.py
CMD ["python3", "/opt/stack/prusa-smoke.py"]
