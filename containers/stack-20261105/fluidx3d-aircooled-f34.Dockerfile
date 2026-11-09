FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive POCL_MAX_PTHREAD_COUNT=2
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl g++ make ocl-icd-opencl-dev pocl-opencl-icd \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://codeload.github.com/ProjectPhysX/FluidX3D/tar.gz/b85d64ee39a72687d163d42806c9a0ccdaed6d3c -o /tmp/source.tar.gz \
    && echo '69c049bf3e85350247d0cd6fe6a96c7a4c0272acb5d9cd15c75f797410b97230  /tmp/source.tar.gz' | sha256sum -c - \
    && mkdir -p /opt/FluidX3D \
    && tar -xzf /tmp/source.tar.gz --strip-components=1 -C /opt/FluidX3D \
    && rm /opt/FluidX3D/src/OpenCL/lib/libOpenCL.so /tmp/source.tar.gz
WORKDIR /opt/FluidX3D
COPY twins/reference-917-engine/fluidx3d/defines.hpp twins/reference-917-engine/fluidx3d/setup.cpp ./src/
RUN make Linux -j1 && cp bin/FluidX3D /usr/local/bin/fluidx3d-f34
COPY containers/stack-20261105/fluidx3d-smoke.cpp ./src/setup.cpp
RUN rm -f temp/setup.o bin/FluidX3D \
    && make Linux -j1 && cp bin/FluidX3D /usr/local/bin/fluidx3d-smoke \
    && dpkg-query -W > /opt/system-packages.txt
RUN --network=none fluidx3d-smoke
# Keep the historical executable and source available, but default to the
# bounded synthetic witness so starting the image never runs a head model.
COPY twins/reference-917-engine/fluidx3d/setup.cpp ./src/setup.cpp
ENTRYPOINT ["/usr/local/bin/fluidx3d-smoke"]
