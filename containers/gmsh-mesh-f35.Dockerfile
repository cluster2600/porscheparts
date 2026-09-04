# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F35 : Gmsh 4.15.2 et bibliotheques ELF minimales pour maillage
# OCC synthetique. Aucun scan, STEP projet, solveur CFD, secret ou resultat CAE.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS system-libs

ARG TARGETARCH
RUN test "${TARGETARCH}" = "amd64"

RUN --mount=type=bind,source=containers/gmsh-mesh-f35-system-packages.sha256,target=/tmp/gmsh-mesh-f35-system-packages.sha256,readonly \
    set -eu; \
    mkdir -p /downloads /runtime; \
    cd /downloads; \
    apt-get update; \
    apt-get download \
      fontconfig-config=2.14.1-4 \
      libbrotli1=1.0.9-2+b6 \
      libbsd0=0.11.7-2 \
      libexpat1=2.5.0-1+deb12u3 \
      libfontconfig1=2.14.1-4 \
      libfreetype6=2.12.1+dfsg-5+deb12u4 \
      libgl1=1.6.0-1 \
      libglu1-mesa=9.0.2-1.1 \
      libglvnd0=1.6.0-1 \
      libglx0=1.6.0-1 \
      libgomp1=12.2.0-14+deb12u1 \
      libopengl0=1.6.0-1 \
      libpng16-16=1.6.39-2+deb12u5 \
      libx11-6=2:1.8.4-2+deb12u2 \
      libx11-data=2:1.8.4-2+deb12u2 \
      libxau6=1:1.0.9-1 \
      libxcb1=1.15-1 \
      libxcursor1=1:1.2.1-1 \
      libxdmcp6=1:1.1.2-3 \
      libxext6=2:1.3.4-1+b1 \
      libxfixes3=1:6.0.0-2 \
      libxft2=2.3.6-1 \
      libxinerama1=2:1.1.4-3 \
      libxrender1=1:0.9.10-1.1; \
    sha256sum -c /tmp/gmsh-mesh-f35-system-packages.sha256; \
    for package in ./*.deb; do dpkg-deb -x "${package}" /runtime; done; \
    rm -rf /var/lib/apt/lists/* /downloads

FROM ${PYTHON_BASE_IMAGE} AS python-gmsh

ARG TARGETARCH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN test "${TARGETARCH}" = "amd64"

RUN --mount=type=bind,source=containers/gmsh-mesh-f35.requirements.txt,target=/tmp/gmsh-mesh-f35.requirements.txt,readonly \
    PIP_NO_INDEX=0 python -m pip install \
      --only-binary=:all: \
      --require-hashes \
      --no-deps \
      --requirement /tmp/gmsh-mesh-f35.requirements.txt \
    && python -m pip check \
    && test "$(python -c 'from importlib.metadata import version; print(version("gmsh"))')" = "4.15.2"

FROM ${PYTHON_BASE_IMAGE} AS gmsh-mesh-f35

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/gmsh-mesh-f35-cache

RUN test "${TARGETARCH}" = "amd64"

COPY --from=system-libs /runtime/lib/x86_64-linux-gnu/ /lib/x86_64-linux-gnu/
COPY --from=system-libs /runtime/usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=system-libs /runtime/etc/fonts/ /etc/fonts/
COPY --from=system-libs /runtime/usr/share/fontconfig/ /usr/share/fontconfig/
COPY --from=system-libs /runtime/usr/share/X11/ /usr/share/X11/
COPY --from=system-libs /runtime/usr/share/doc/ /usr/share/doc/
COPY --from=python-gmsh /usr/local/bin/gmsh /usr/local/bin/gmsh
COPY --from=python-gmsh /usr/local/lib/libgmsh.so.4.15 /usr/local/lib/libgmsh.so.4.15
COPY --from=python-gmsh /usr/local/lib/python3.12/site-packages/gmsh.py /usr/local/lib/python3.12/site-packages/gmsh.py
COPY --from=python-gmsh /usr/local/lib/python3.12/site-packages/gmsh-4.15.2.dist-info/ /usr/local/lib/python3.12/site-packages/gmsh-4.15.2.dist-info/
COPY --from=python-gmsh /usr/local/share/doc/gmsh/LICENSE.txt /usr/local/share/doc/gmsh/LICENSE.txt
COPY --from=python-gmsh /usr/local/share/doc/gmsh/CREDITS.txt /usr/local/share/doc/gmsh/CREDITS.txt
COPY --from=python-gmsh /usr/local/share/doc/gmsh/CHANGELOG.txt /usr/local/share/doc/gmsh/CHANGELOG.txt
COPY --from=python-gmsh /usr/local/share/doc/gmsh/README.txt /usr/local/share/doc/gmsh/README.txt

COPY containers/gmsh-mesh-f35.requirements.txt /opt/gmsh-mesh-f35/requirements.txt
COPY containers/gmsh-mesh-f35-system-packages.sha256 /opt/gmsh-mesh-f35/system-packages.sha256
COPY containers/gmsh-mesh-f35-smoke.py /opt/gmsh-mesh-f35/smoke.py

ARG GMSH_MESH_UID=9135
ARG GMSH_MESH_GID=9135
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${GMSH_MESH_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${GMSH_MESH_GID}:" /etc/group \
    && printf 'gmsh-mesh:x:%s:\n' "${GMSH_MESH_GID}" >> /etc/group \
    && printf 'gmsh-mesh:x:%s:%s:F35 Gmsh mesh worker:/tmp:/usr/sbin/nologin\n' \
      "${GMSH_MESH_UID}" "${GMSH_MESH_GID}" >> /etc/passwd \
    && find /opt/gmsh-mesh-f35 -type d -exec chmod 0555 {} + \
    && find /opt/gmsh-mesh-f35 -type f -exec chmod 0444 {} + \
    && chmod 0555 /opt/gmsh-mesh-f35/smoke.py \
    && mkdir -p /workspace \
    && chown "${GMSH_MESH_UID}:${GMSH_MESH_GID}" /workspace

USER ${GMSH_MESH_UID}:${GMSH_MESH_GID}
WORKDIR /workspace

# Le build prouve uniquement que la recette hermetique maille un volume OCC
# synthetique et detecte tout Jacobien non positif; aucune geometrie Porsche.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/gmsh-mesh-f35-build-smoke.json; \
      stderr=/tmp/gmsh-mesh-f35-build-smoke.stderr; \
      if ! python /opt/gmsh-mesh-f35/smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" "${XDG_CACHE_HOME}"'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-gmsh-mesh-f35" \
      org.opencontainers.image.description="Minimal linux/amd64 Gmsh 4.15.2 image for a fail-closed synthetic OCC volume mesh smoke" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.licenses="GPL-2.0-or-later"

CMD ["python", "/opt/gmsh-mesh-f35/smoke.py"]
