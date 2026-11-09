FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/jax-fem/bin:$PATH \
    PETSC_CONFIGURE_OPTIONS="--with-mpi=0 --with-fc=0 --with-debugging=0 --with-shared-libraries=1 --with-make-np=2" \
    MAKEFLAGS=-j2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev python3-venv build-essential libopenblas-dev liblapack-dev \
    libgl1 libglu1-mesa libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY containers/stack-20261105/jax-fem.requirements.txt /opt/locks/jax-fem.requirements.txt
RUN python3 -m venv /opt/jax-fem \
    && pip install --no-cache-dir --require-hashes -r /opt/locks/jax-fem.requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends patchelf \
    && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:a4dc46c1b4403545ac2274741ce10801366c4a9a7b2683b678d18f6663b93496 https://files.pythonhosted.org/packages/df/0f/0a3ae83f60fba9357e8de2acef74fc0871078c9991ae8aac4d04df118030/petsc-3.26.1.tar.gz /tmp/petsc.tar.gz
RUN pip install --no-cache-dir --no-build-isolation --no-deps /tmp/petsc.tar.gz \
    && rm /tmp/petsc.tar.gz
ADD --checksum=sha256:66a5c31de33293faefa72d6edc5abad5586f438c28842804de0044d8763087a2 https://files.pythonhosted.org/packages/af/26/59e1517a9bfd24e34c83c3d61143dbcdf5b6f9653baf5c0493745dd42dba/petsc4py-3.26.1.tar.gz /tmp/petsc4py.tar.gz
RUN pip install --no-cache-dir --no-build-isolation --no-deps /tmp/petsc4py.tar.gz \
    && rm /tmp/petsc4py.tar.gz && pip check \
    && pip freeze --all > /opt/locks/environment.freeze.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxcursor1 libxfixes3 libxft2 libfontconfig1 libxinerama1 \
    && rm -rf /var/lib/apt/lists/*
COPY containers/stack-20261105/jax-fem-smoke.py /opt/stack/jax-fem-smoke.py
RUN --network=none JAX_PLATFORMS=cpu python /opt/stack/jax-fem-smoke.py
ENTRYPOINT ["/opt/jax-fem/bin/python"]
CMD ["/opt/stack/jax-fem-smoke.py"]
