# syntax=docker/dockerfile:1.7
#
# 3dprinting993 - scan-to-CAD and CFD preparation image (CPU / high memory).
#
# The purchased scans are mounted at runtime. They are never copied into the
# image or Docker build context.

FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852

ARG OPENFOAM_VERSION=14

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    FOAM_VERSION=${OPENFOAM_VERSION} \
    OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      admesh \
      ca-certificates \
      curl \
      gnupg \
      jq \
      libgl1 \
      libgomp1 \
      libsm6 \
      libxrender1 \
      libxxf86vm1 \
      xz-utils \
      libglu1-mesa \
      libxft2 \
      libxcursor1 \
      libxinerama1 \
      libxrandr2 \
      openssh-server \
      python3 \
      python3-venv \
      rsync \
      time \
      tmux \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://dl.openfoam.org/gpg.key \
      | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" \
      > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "openfoam${OPENFOAM_VERSION}" \
    && rm -rf /var/lib/apt/lists/* \
    && printf '. /opt/openfoam%s/etc/bashrc\n' "${OPENFOAM_VERSION}" >> /etc/bash.bashrc

ARG BLENDER_VERSION=5.2.3
RUN --mount=type=bind,source=downloads/blender-5.2.3-linux-x64.tar.xz,target=/tmp/blender.tar.xz,readonly \
    echo "78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec  /tmp/blender.tar.xz" | sha256sum -c - \
    && tar -xJf /tmp/blender.tar.xz -C /opt \
    && ln -s /opt/blender-5.2.3-linux-x64/blender /usr/local/bin/blender
COPY containers/stack-20261105/mesh-cfd.requirements.txt /opt/locks/mesh-cfd.requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir pip==26.3 \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes -r /opt/locks/mesh-cfd.requirements.txt \
    && /opt/venv/bin/pip check \
    && dpkg-query -W > /opt/locks/system-packages.txt
COPY containers/stack-20261105/mesh-cfd-smoke.py /opt/stack/mesh-cfd-smoke.py

COPY containers/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/smoke-test.sh

COPY scripts /opt/3dprinting993/scripts
COPY catalog/templates /opt/3dprinting993/catalog/templates
ENV PYTHONPATH=/opt/3dprinting993

WORKDIR /workspace
EXPOSE 22

LABEL org.opencontainers.image.title="3dprinting993-mesh-cfd" \
      org.opencontainers.image.description="Headless OBJ cleanup, STEP proxy generation and OpenFOAM CFD preparation" \
      org.opencontainers.image.source="https://github.com/cluster2600/porscheparts" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
