# syntax=docker/dockerfile:1.7
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852 AS ccx-build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gfortran libspooles-dev libarpack2-dev liblapack-dev \
    ca-certificates curl bzip2 perl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://dhondt.de/ccx_2.23.src.tar.bz2 -o /tmp/ccx.tar.bz2 \
    && echo '9c88385c10fb04f5dc6c4e98027a51bebdd8aee3920e05190d6c1dd08357d6e7  /tmp/ccx.tar.bz2' | sha256sum -c - \
    && tar -xjf /tmp/ccx.tar.bz2 -C /tmp \
    && cd /tmp/CalculiX/ccx_2.23/src \
    && sed -i 's/ccx_2.23.a  $(LIBS)/ccx_2.23.a/' Makefile \
    && make -j2 CFLAGS='-O2 -I/usr/include/spooles -DARCH="Linux" -DSPOOLES -DARPACK -DMATRIXSTORAGE -DNETWORKOUT' \
      FFLAGS='-O2 -cpp -fallow-argument-mismatch' \
      LIBS='/usr/lib/x86_64-linux-gnu/libspooles.a -larpack -llapack -lblas -lpthread -lm -lc' \
    && install -Dm755 ccx_2.23 /opt/ccx/ccx

FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv ca-certificates libarpack2t64 libgfortran5 libgomp1 \
    libglu1-mesa libxcursor1 libxinerama1 libxft2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ccx-build /opt/ccx/ccx /usr/local/bin/ccx
COPY containers/stack-20261105/cae-reference.requirements.txt /opt/locks/requirements.txt
RUN python3 -m venv /opt/venv \
    && pip install --no-cache-dir --require-hashes -r /opt/locks/requirements.txt \
    && pip check && dpkg-query -W > /opt/locks/system-packages.txt
COPY scripts/cad_recode/ccx_smoke.py /opt/stack/ccx-smoke.py
RUN --network=none python /opt/stack/ccx-smoke.py /tmp/build-smoke \
    && cat /tmp/build-smoke/checks.json && rm -rf /tmp/build-smoke
WORKDIR /workspace
ENTRYPOINT ["python"]
CMD ["/opt/stack/ccx-smoke.py", "/tmp/runtime-smoke"]
