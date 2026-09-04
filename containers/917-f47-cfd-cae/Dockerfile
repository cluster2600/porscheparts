# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image F47 linux/amd64 : solveurs F46 et transport Vast borne.
# Aucun scan, domaine moteur, carte materiau ou secret n'est inclus.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
ARG UBUNTU_BASE_IMAGE=ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517
FROM ${PYTHON_BASE_IMAGE} AS python-dependencies

ARG TARGETARCH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore
RUN test "${TARGETARCH}" = "amd64"
RUN --mount=type=bind,source=containers/engine-cycle-f33.requirements.txt,target=/tmp/requirements.txt,readonly \
    PIP_NO_INDEX=0 python -m pip install --only-binary=:all: --require-hashes \
      --no-deps --requirement /tmp/requirements.txt \
    && python -m pip check \
    && test "$(python -c 'import cantera; print(cantera.__version__)')" = "3.2.0"

FROM ${UBUNTU_BASE_IMAGE} AS openfoam-base

ARG TARGETARCH
ARG OPENFOAM_PACKAGE_VERSION=20260724
ENV DEBIAN_FRONTEND=noninteractive
RUN test "${TARGETARCH}" = "amd64" \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl gnupg \
    && curl -fsSL https://dl.openfoam.org/gpg.key \
       | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" \
       > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       "openfoam14=${OPENFOAM_PACKAGE_VERSION}" \
       openmpi-bin=4.1.6-7ubuntu2 \
       python3=3.12.3-0ubuntu2.1 \
    && rm -rf /var/lib/apt/lists/*

FROM openfoam-base AS aate-builder

ARG AATE_COMMIT=c0f75f953d67cd325d28d1300672d14288f22934
ARG AATE_ARCHIVE_SHA256=28ee8d96b6943fab11b3d70ea3befe472d06d24741962cdb399b1d54e7ff7d3b
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && curl -fsSL "https://codeload.github.com/OpenFOAM/ICengines/tar.gz/${AATE_COMMIT}" \
       -o /tmp/icengines.tar.gz \
    && echo "${AATE_ARCHIVE_SHA256}  /tmp/icengines.tar.gz" | sha256sum -c - \
    && mkdir -p /tmp/ICengines /opt/aate/bin /opt/aate/lib /opt/aate/share \
    && tar -xzf /tmp/icengines.tar.gz --strip-components=1 -C /tmp/ICengines \
    && /bin/bash -eo pipefail -c ' \
         source /opt/openfoam14/etc/bashrc; \
         set -u; \
         export FOAM_USER_APPBIN=/opt/aate/bin; \
         export FOAM_USER_LIBBIN=/opt/aate/lib; \
         cd /tmp/ICengines; \
         ./Allwmake -j "$(nproc)"; \
         for executable in engineMeshConfig moveSurfaces predictRemeshInstants reorderPatchesAndFaces; do \
           test -x "/opt/aate/bin/${executable}"; \
         done; \
         test -f /opt/aate/lib/libpreProcessing.so; \
         test -f /opt/aate/lib/libsearchableSurfaces_w.so' \
    && cp /tmp/ICengines/README.md /opt/aate/share/ICengines-README.md \
    && printf '%s\n' "${AATE_COMMIT}" > /opt/aate/share/revision.txt \
    && find /opt/aate/bin -xtype l -delete

FROM openfoam-base AS f47-runtime

ARG TARGETARCH
ARG OPENFOAM_PACKAGE_VERSION=20260724
ARG AATE_COMMIT=c0f75f953d67cd325d28d1300672d14288f22934
ARG F47_UID=9147
ARG F47_GID=9147
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PYTHONNOUSERSITE=1 \
    PYTHONPATH=/opt/f47-python/lib/python3.12/site-packages \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/f47-cache \
    PATH=/opt/aate/bin:/opt/openfoam14/platforms/linux64GccDPInt32Opt/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LD_LIBRARY_PATH=/opt/aate/lib:/opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/openmpi-system:/opt/openfoam14/platforms/linux64GccDPInt32Opt/lib:/usr/lib/x86_64-linux-gnu/openmpi/lib \
    OMPI_MCA_rmaps_base_oversubscribe=1

RUN test "${TARGETARCH}" = "amd64" \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       calculix-ccx=2.21-1 \
       gmsh=4.12.1+ds1-1.1build2 \
       openssh-server=1:9.6p1-3ubuntu13.19 \
       procps=2:4.0.4-4ubuntu3.3 \
       tini=0.19.0-1 \
       util-linux=2.39.3-9ubuntu6.6 \
    && test "$(dpkg-query -W -f='${Version}' calculix-ccx)" = "2.21-1" \
    && test "$(dpkg-query -W -f='${Version}' gmsh)" = "4.12.1+ds1-1.1build2" \
    && test "$(dpkg-query -W -f='${Version}' openssh-server)" = "1:9.6p1-3ubuntu13.19" \
    && mv /usr/sbin/sshd /usr/lib/openssh/sshd.real \
    && rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub \
    && rm -rf /var/lib/apt/lists/*

COPY --from=aate-builder /opt/aate /opt/aate
COPY --from=python-dependencies /usr/local/lib/python3.12/site-packages /opt/f47-python/lib/python3.12/site-packages
COPY benchmarks/openfoam-poiseuille-f25 /opt/917-f47-cfd-cae/benchmark
COPY containers/engine-cycle-f33.requirements.txt /opt/917-f47-cfd-cae/requirements.txt
COPY containers/917-f47-cfd-cae/ /opt/917-f47-cfd-cae/

RUN test -x /usr/sbin/nologin \
    && cp -a /opt/openfoam14/tutorials/multiRegion/CHT/heatedDuct /opt/917-f47-cfd-cae/cht-fixture \
    && ! grep -Eq "(^|:)${F47_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${F47_GID}:" /etc/group \
    && printf 'f47-solver:x:%s:\n' "${F47_GID}" >> /etc/group \
    && printf 'f47-solver:x:%s:%s:F47 bounded solver:/tmp:/usr/sbin/nologin\n' \
       "${F47_UID}" "${F47_GID}" >> /etc/passwd \
    && install -d -o root -g root -m 0755 /run/sshd /workspace \
    && install -d -o root -g root -m 0700 /root/.ssh \
    && install -o root -g root -m 0600 /dev/null /root/.no_auto_tmux \
    && printf '%s\n' \
       'PasswordAuthentication no' \
       'KbdInteractiveAuthentication no' \
       'PermitRootLogin prohibit-password' \
       'X11Forwarding no' \
       'AllowAgentForwarding no' \
       'PermitTunnel no' \
       > /etc/ssh/sshd_config.d/99-f47.conf \
    && chmod 0555 /opt/917-f47-cfd-cae/*.sh /opt/917-f47-cfd-cae/*.py \
    && chmod 0444 /opt/917-f47-cfd-cae/*.json /opt/917-f47-cfd-cae/requirements.txt \
    && cc -O2 -Wall -Wextra -Werror /opt/917-f47-cfd-cae/cuda_driver_smoke.c \
       -ldl -o /usr/local/bin/f47-cuda-smoke \
    && chmod 0555 /usr/local/bin/f47-cuda-smoke \
    && ln -s /opt/917-f47-cfd-cae/image_smoke.py /usr/local/bin/f47-image-smoke \
    && ln -s /opt/917-f47-cfd-cae/run_manifest.sh /usr/local/bin/f46-run-manifest \
    && ln -s /opt/917-f47-cfd-cae/vast_onstart.sh /usr/local/bin/f46-vast-onstart \
    && ln -s /opt/917-f47-cfd-cae/sshd_runtime_wrapper.sh /usr/sbin/sshd \
    && /opt/917-f47-cfd-cae/prepare_layout.sh \
    && test ! -e /root/.ssh/authorized_keys \
    && test -z "$(find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key*' -print -quit)" \
    && test ! -e /usr/local/bin/ICEEngineFoam \
    && test ! -e /usr/local/bin/iceEngineFoam

WORKDIR /workspace

# Smokes CPU reels, hors ligne et apres chute explicite vers l'utilisateur 9147.
# Le smoke CUDA reste volontairement un gate runtime car le build n'a pas de GPU.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/f47-build-smoke.json; stderr=/tmp/f47-build-smoke.stderr; \
      if ! setpriv --reuid=9147 --regid=9147 --clear-groups --no-new-privs \
        /usr/local/bin/f47-image-smoke >"${stdout}" 2>"${stderr}"; then \
        cat "${stdout}"; cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; test ! -s "${stderr}"; rm -f -- "${stdout}" "${stderr}"'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-cfd-cae-f46" \
      org.opencontainers.image.description="F47 linux/amd64 runtime recipe for bounded F46 OpenFOAM, AATE/ICengines, Cantera, Gmsh and CalculiX jobs" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.licenses="GPL-3.0-or-later AND GPL-2.0-or-later" \
      org.opencontainers.image.version.openfoam="${OPENFOAM_PACKAGE_VERSION}" \
      org.opencontainers.image.revision.aate="${AATE_COMMIT}" \
      org.opencontainers.image.runtime-user="9147:9147"

# Root est reserve au transport ssh_direct et a l'armement du watchdog. Le
# runner et tous les smokes/solveurs passent obligatoirement sous 9147:9147.
USER 0:0
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/917-f47-cfd-cae/entrypoint.sh"]
CMD []
