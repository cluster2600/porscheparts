# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F35 : OpenFOAM Foundation 14 + utilitaires AATE/ICengines.
# Aucun scan, modèle Porsche, mécanisme chimique, poids IA ou secret n'est inclus.

ARG UBUNTU_BASE_IMAGE=ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
FROM ${UBUNTU_BASE_IMAGE} AS openfoam-base

ARG TARGETARCH
ARG OPENFOAM_PACKAGE_VERSION=20261008
ENV DEBIAN_FRONTEND=noninteractive

RUN test "${TARGETARCH}" = "amd64" \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://dl.openfoam.org/gpg.key \
       | gpg --dearmor -o /usr/share/keyrings/openfoam.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/openfoam.gpg] http://dl.openfoam.org/ubuntu noble main" \
       > /etc/apt/sources.list.d/openfoam.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       "openfoam14=${OPENFOAM_PACKAGE_VERSION}" \
       openmpi-bin \
       python3 \
    && rm -rf /var/lib/apt/lists/*

FROM openfoam-base AS aate-builder

ARG AATE_COMMIT=8bba57f7e004c57d3a36b6df0f972bcc7c4c82a1
ARG AATE_ARCHIVE_SHA256=2afdb5bdfa6626becfb345887f73102807d98f58bf7ac80cd9037e2b985c2617

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
         ./Allwmake -j 2; \
         for executable in engineMeshConfig moveSurfaces predictRemeshInstants reorderPatchesAndFaces; do \
           test -x "/opt/aate/bin/${executable}"; \
         done; \
         test -f /opt/aate/lib/libpreProcessing.so; \
         test -f /opt/aate/lib/libsearchableSurfaces_w.so; \
         find /opt/aate/bin -xtype l -delete' \
    && cp /tmp/ICengines/README.md /opt/aate/share/ICengines-README.md \
    && printf '%s\n' \
       "https://github.com/OpenFOAM/ICengines/tree/${AATE_COMMIT}" \
       > /opt/aate/share/ICengines-source.txt

FROM openfoam-base AS openfoam-engine-f35

ARG TARGETARCH
ARG OPENFOAM_PACKAGE_VERSION=20261008
ARG AATE_COMMIT=8bba57f7e004c57d3a36b6df0f972bcc7c4c82a1
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    PATH=/opt/aate/bin:/opt/openfoam14/platforms/linux64GccDPInt32Opt/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LD_LIBRARY_PATH=/opt/aate/lib:/opt/openfoam14/platforms/linux64GccDPInt32Opt/lib/openmpi-system:/opt/openfoam14/platforms/linux64GccDPInt32Opt/lib:/usr/lib/x86_64-linux-gnu/openmpi/lib \
    OMPI_MCA_rmaps_base_oversubscribe=1

RUN test "${TARGETARCH}" = "amd64"

COPY --from=aate-builder /opt/aate /opt/aate
COPY outils/benchmarks/openfoam-poiseuille-f25 /opt/openfoam-engine-f35/benchmark
COPY containers/stack-20261105/openfoam-engine-f35-smoke.sh /usr/local/bin/openfoam-engine-f35-smoke

ARG OPENFOAM_ENGINE_UID=9135
ARG OPENFOAM_ENGINE_GID=9135
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${OPENFOAM_ENGINE_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${OPENFOAM_ENGINE_GID}:" /etc/group \
    && printf 'openfoam-engine:x:%s:\n' "${OPENFOAM_ENGINE_GID}" >> /etc/group \
    && printf 'openfoam-engine:x:%s:%s:F35 OpenFOAM engine solver:/tmp:/usr/sbin/nologin\n' \
       "${OPENFOAM_ENGINE_UID}" "${OPENFOAM_ENGINE_GID}" >> /etc/passwd \
    && chmod 0555 /usr/local/bin/openfoam-engine-f35-smoke \
       /opt/aate/bin/engineMeshConfig \
       /opt/aate/bin/moveSurfaces \
       /opt/aate/bin/predictRemeshInstants \
       /opt/aate/bin/reorderPatchesAndFaces \
       /opt/aate/lib/libpreProcessing.so \
       /opt/aate/lib/libsearchableSurfaces_w.so \
    && find /opt/openfoam-engine-f35 /opt/aate/share -type d -exec chmod 0555 {} + \
    && find /opt/openfoam-engine-f35 /opt/aate/share -type f -exec chmod 0444 {} + \
    && mkdir -p /workspace \
    && chown "${OPENFOAM_ENGINE_UID}:${OPENFOAM_ENGINE_GID}" /workspace

USER ${OPENFOAM_ENGINE_UID}:${OPENFOAM_ENGINE_GID}
WORKDIR /workspace

# Deux vrais calculs synthétiques, série puis MPI 2 rangs, sont exécutés après
# USER et sans réseau. Ils vérifient le solveur; ils ne prouvent aucun moteur.
RUN --network=none openfoam-engine-f35-smoke

LABEL org.opencontainers.image.title="3dprinting993-openfoam-engine-f35" \
      org.opencontainers.image.description="Dedicated linux/amd64 CPU image with OpenFOAM Foundation 14 and pinned AATE/ICengines utilities" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.version.openfoam="${OPENFOAM_PACKAGE_VERSION}" \
      org.opencontainers.image.revision.aate="${AATE_COMMIT}"

CMD ["openfoam-engine-f35-smoke"]
