# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F28 : auteur CAO build123d/OCCT et round-trip STEP uniquement.
# Aucun scan, modele vehicule, solveur, poids de modele ou secret n'est inclus.

ARG PYTHON_BASE_IMAGE=python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
FROM ${PYTHON_BASE_IMAGE} AS system-libs

ARG TARGETARCH
RUN test "${TARGETARCH}" = "amd64"

# Extraire seulement les bibliotheques partagees liees par OCCT. Installer
# libgl1 par APT tirerait Mesa/LLVM (~216 Mio) alors qu'aucun rendu n'est fait.
RUN --mount=type=bind,source=debhouse/cad-author,target=/debs,readonly \
    --mount=type=bind,source=containers/stack-20261105/cad-author-system-packages.sha256,target=/tmp/packages.sha256,readonly \
    mkdir -p /runtime && cd /debs && sha256sum -c /tmp/packages.sha256 \
    && for package in ./*.deb; do dpkg-deb --extract "${package}" /runtime; done

FROM ${PYTHON_BASE_IMAGE} AS python-cad

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN --mount=type=bind,source=wheelhouse/cad-author,target=/wheels,readonly \
    --mount=type=bind,source=containers/stack-20261105/cad-author.requirements.txt,target=/tmp/cad-author-f28-requirements.txt,readonly \
    python -m pip install --no-index --find-links=/wheels \
      --only-binary=:all: \
      --require-hashes \
      --no-deps \
      --requirement /tmp/cad-author-f28-requirements.txt \
    && python -m pip check \
    && test "$(python -c 'from importlib.metadata import version; print(version("build123d"))')" = "0.13.0" \
    && test "$(python -c 'from importlib.metadata import version; print(version("cadquery-ocp-novtk"))')" = "8.0.1.1.0"

FROM ${PYTHON_BASE_IMAGE} AS cad-author-f28

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/cad-author-f28-cache

RUN test "${TARGETARCH}" = "amd64"

# cadquery-ocp-novtk lie encore libGL/libX11. Seuls les fichiers des onze
# paquets Debian fixes par version et SHA-256 sont copies depuis le stage court.
COPY --from=system-libs /runtime/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=system-libs /runtime/usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=system-libs /runtime/usr/share/X11/ /usr/share/X11/
COPY --from=system-libs /runtime/etc/fonts/ /etc/fonts/
COPY --from=system-libs /runtime/usr/share/fontconfig/ /usr/share/fontconfig/
COPY --from=system-libs /runtime/usr/share/doc/ /usr/share/doc/
COPY --from=python-cad /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

COPY containers/stack-20261105/cad-author.requirements.txt /opt/cad-author-f28/cad-author-f28-requirements.txt
COPY containers/stack-20261105/cad-author-f28-smoke.py /opt/cad-author-f28/cad-author-f28-smoke.py
COPY containers/stack-20261105/cad-author-system-packages.sha256 /opt/cad-author-f28/cad-author-f28-system-packages.sha256

ARG CAD_UID=9178
ARG CAD_GID=9178
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${CAD_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${CAD_GID}:" /etc/group \
    && printf 'cad-author:x:%s:\n' "${CAD_GID}" >> /etc/group \
    && printf 'cad-author:x:%s:%s:CAD author:/tmp:/usr/sbin/nologin\n' "${CAD_UID}" "${CAD_GID}" >> /etc/passwd \
    && chmod 0444 /opt/cad-author-f28/cad-author-f28-requirements.txt \
      /opt/cad-author-f28/cad-author-f28-system-packages.sha256 \
    && chmod 0555 /opt/cad-author-f28/cad-author-f28-smoke.py \
    && mkdir -p /workspace \
    && chown "${CAD_UID}:${CAD_GID}" /workspace

USER ${CAD_UID}:${CAD_GID}
WORKDIR /workspace

# Le vrai round-trip build123d -> STEP -> OCCT est exerce apres USER, sans reseau.
# Tout stderr (warning de cache/fontconfig inclus) est une erreur de recette.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/cad-author-f28-build-smoke.json; \
      stderr=/tmp/cad-author-f28-build-smoke.stderr; \
      if ! python /opt/cad-author-f28/cad-author-f28-smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" "${XDG_CACHE_HOME}"'

LABEL org.opencontainers.image.title="3dprinting993-cad-author-f28" \
      org.opencontainers.image.description="Minimal CPU CAD authoring image with build123d 0.13.0 and OCCT 7.9.3; synthetic STEP round-trip only, no vehicle geometry" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="NOASSERTION"

CMD ["python", "/opt/cad-author-f28/cad-author-f28-smoke.py"]
