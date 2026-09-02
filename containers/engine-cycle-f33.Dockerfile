# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F33 : thermochimie Cantera et solveurs reseau Python uniquement.
# Aucun scan, modele moteur, donnees d'essai, poids IA ou secret n'est inclus.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS python-dependencies

ARG TARGETARCH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN test "${TARGETARCH}" = "amd64"

RUN --mount=type=bind,source=containers/engine-cycle-f33.requirements.txt,target=/tmp/engine-cycle-f33.requirements.txt,readonly \
    PIP_NO_INDEX=0 python -m pip install \
      --only-binary=:all: \
      --require-hashes \
      --no-deps \
      --requirement /tmp/engine-cycle-f33.requirements.txt \
    && python -m pip check \
    && test "$(python -c 'from importlib.metadata import version; print(version("cantera"))')" = "3.2.0" \
    && test "$(python -c 'from importlib.metadata import version; print(version("numpy"))')" = "2.5.2"

FROM ${PYTHON_BASE_IMAGE} AS engine-cycle-f33

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/engine-cycle-f33-cache

RUN test "${TARGETARCH}" = "amd64"

COPY --from=python-dependencies /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

COPY containers/engine-cycle-f33.requirements.txt /opt/engine-cycle-f33/requirements.txt
COPY scripts/smoke_engine_cycle_f33.py /opt/engine-cycle-f33/smoke.py

ARG ENGINE_CYCLE_UID=9133
ARG ENGINE_CYCLE_GID=9133
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${ENGINE_CYCLE_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${ENGINE_CYCLE_GID}:" /etc/group \
    && printf 'engine-cycle:x:%s:\n' "${ENGINE_CYCLE_GID}" >> /etc/group \
    && printf 'engine-cycle:x:%s:%s:F33 engine-cycle solver:/tmp:/usr/sbin/nologin\n' \
      "${ENGINE_CYCLE_UID}" "${ENGINE_CYCLE_GID}" >> /etc/passwd \
    && chmod 0444 /opt/engine-cycle-f33/requirements.txt \
    && chmod 0555 /opt/engine-cycle-f33/smoke.py \
    && mkdir -p /workspace \
    && chown "${ENGINE_CYCLE_UID}:${ENGINE_CYCLE_GID}" /workspace

USER ${ENGINE_CYCLE_UID}:${ENGINE_CYCLE_GID}
WORKDIR /workspace

# Le build exerce une fixture thermochimique generique apres USER et sans reseau.
# Elle ne constitue ni un modele moteur, ni une preuve de puissance.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/engine-cycle-f33-build-smoke.json; \
      stderr=/tmp/engine-cycle-f33-build-smoke.stderr; \
      if ! python /opt/engine-cycle-f33/smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" "${XDG_CACHE_HOME}"'

LABEL org.opencontainers.image.title="3dprinting993-engine-cycle-f33" \
      org.opencontainers.image.description="Minimal linux/amd64 CPU image with Cantera 3.2.0 for non-correlated engine-cycle and thermal-network reference studies" \
      org.opencontainers.image.source="https://github.com/cluster2600/3dprinting993" \
      org.opencontainers.image.licenses="NOASSERTION"

CMD ["python", "/opt/engine-cycle-f33/smoke.py"]
