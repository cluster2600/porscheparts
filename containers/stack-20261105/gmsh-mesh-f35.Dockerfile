# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F35 : Gmsh 4.15.2 et bibliotheques ELF minimales pour maillage
# OCC synthetique. Aucun scan, STEP projet, solveur CFD, secret ou resultat CAE.

ARG PYTHON_BASE_IMAGE=python:3.15.2-slim-bookworm@sha256:4e03260adeeebafccd084f3584e6b84823aba5651cfb53ef8a078ed441ddf9cd
FROM ${PYTHON_BASE_IMAGE} AS system-libs

ARG TARGETARCH
RUN test "${TARGETARCH}" = "amd64"

RUN --mount=type=bind,source=debhouse/gmsh,target=/debs,readonly \
    --mount=type=bind,source=containers/stack-20261105/gmsh-system-packages.sha256,target=/tmp/packages.sha256,readonly \
    mkdir -p /runtime && cd /debs && sha256sum -c /tmp/packages.sha256 \
    && for package in ./*.deb; do dpkg-deb --extract "${package}" /runtime; done

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
COPY --from=python-gmsh /usr/local/lib/python3.15/site-packages/gmsh.py /usr/local/lib/python3.15/site-packages/gmsh.py
COPY --from=python-gmsh /usr/local/lib/python3.15/site-packages/gmsh-4.15.2.dist-info/ /usr/local/lib/python3.15/site-packages/gmsh-4.15.2.dist-info/
COPY --from=python-gmsh /usr/local/share/doc/gmsh/LICENSE.txt /usr/local/share/doc/gmsh/LICENSE.txt
COPY --from=python-gmsh /usr/local/share/doc/gmsh/CREDITS.txt /usr/local/share/doc/gmsh/CREDITS.txt
COPY --from=python-gmsh /usr/local/share/doc/gmsh/CHANGELOG.txt /usr/local/share/doc/gmsh/CHANGELOG.txt
COPY --from=python-gmsh /usr/local/share/doc/gmsh/README.txt /usr/local/share/doc/gmsh/README.txt

COPY containers/gmsh-mesh-f35.requirements.txt /opt/gmsh-mesh-f35/requirements.txt
COPY containers/stack-20261105/gmsh-system-packages.sha256 /opt/gmsh-mesh-f35/system-packages.sha256
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
