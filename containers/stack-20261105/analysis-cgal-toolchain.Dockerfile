# syntax=docker/dockerfile:1.7
# New analysis-only toolchain; does not replace the frozen CFD replay image.
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ make libboost-dev libgmp-dev libmpfr-dev ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN curl --connect-timeout 30 --max-time 600 -fsSL \
      https://github.com/CGAL/cgal/releases/download/v6.2.1/CGAL-6.2.1-library.tar.xz -o /tmp/cgal.tar.xz \
    && echo '8e7ce1e30e8ffcb3e69d153c3a561bb1f38bbb4becd8e6544cbaa0fb2889af62  /tmp/cgal.tar.xz' | sha256sum -c - \
    && mkdir -p /opt/CGAL /opt/stack \
    && tar -xJf /tmp/cgal.tar.xz --strip-components=1 -C /opt/CGAL \
    && rm /tmp/cgal.tar.xz
COPY containers/stack-20261105/cgal-toolchain-smoke.cpp /opt/stack/cgal-toolchain-smoke.cpp
RUN g++ -std=c++17 -O2 -I/opt/CGAL/include /opt/stack/cgal-toolchain-smoke.cpp \
    -lgmp -lmpfr -o /opt/stack/cgal-toolchain-smoke
CMD ["/opt/stack/cgal-toolchain-smoke"]
