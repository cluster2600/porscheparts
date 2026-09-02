# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F34b : preflight air/huile et fixture Cantera generique non moteur.
# Les contrats, seeds et le manifeste planifie sont embarques; aucun scan,
# poids IA, secret, acces distant, resultat DOE ou cas canonique execute.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS python-dependencies

ARG TARGETARCH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN test "${TARGETARCH}" = "amd64"

RUN --mount=type=bind,source=containers/air-oil-cycle-f34b.requirements.txt,target=/tmp/air-oil-cycle-f34b.requirements.txt,readonly \
    PIP_NO_INDEX=0 python -m pip install \
      --only-binary=:all: \
      --require-hashes \
      --no-deps \
      --requirement /tmp/air-oil-cycle-f34b.requirements.txt \
    && python -m pip check \
    && test "$(python -c 'from importlib.metadata import version; print(version("cantera"))')" = "3.2.0" \
    && test "$(python -c 'from importlib.metadata import version; print(version("numpy"))')" = "2.5.2"

FROM ${PYTHON_BASE_IMAGE} AS air-oil-cycle-f34b

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/air-oil-cycle-f34b-cache

RUN test "${TARGETARCH}" = "amd64"

COPY --from=python-dependencies /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

COPY containers/air-oil-cycle-f34b.requirements.txt /opt/air-oil-cycle-f34b/requirements.txt
COPY containers/air-oil-cycle-f34b-smoke.py /opt/air-oil-cycle-f34b/smoke.py
COPY scripts/run_917_air_oil_cycle_f34b.py /opt/air-oil-cycle-f34b/scripts/run_917_air_oil_cycle_f34b.py
COPY twins/reference-917-engine/air-oil-core-controls-f34a.json /opt/air-oil-cycle-f34b/twins/reference-917-engine/air-oil-core-controls-f34a.json
COPY twins/reference-917-engine/doe-surrogate-f34.json /opt/air-oil-cycle-f34b/twins/reference-917-engine/doe-surrogate-f34.json
COPY twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json /opt/air-oil-cycle-f34b/twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json
COPY twins/reference-917-engine/evidence/f34/doe-case-manifest.json /opt/air-oil-cycle-f34b/twins/reference-917-engine/evidence/f34/doe-case-manifest.json

ARG AIR_OIL_CYCLE_UID=9133
ARG AIR_OIL_CYCLE_GID=9133
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${AIR_OIL_CYCLE_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${AIR_OIL_CYCLE_GID}:" /etc/group \
    && printf 'air-oil-cycle:x:%s:\n' "${AIR_OIL_CYCLE_GID}" >> /etc/group \
    && printf 'air-oil-cycle:x:%s:%s:F34b air-oil cycle solver:/tmp:/usr/sbin/nologin\n' \
      "${AIR_OIL_CYCLE_UID}" "${AIR_OIL_CYCLE_GID}" >> /etc/passwd \
    && find /opt/air-oil-cycle-f34b -type d -exec chmod 0555 {} + \
    && find /opt/air-oil-cycle-f34b -type f -exec chmod 0444 {} + \
    && chmod 0555 /opt/air-oil-cycle-f34b/smoke.py \
      /opt/air-oil-cycle-f34b/scripts/run_917_air_oil_cycle_f34b.py \
    && mkdir -p /workspace \
    && chown "${AIR_OIL_CYCLE_UID}:${AIR_OIL_CYCLE_GID}" /workspace

USER ${AIR_OIL_CYCLE_UID}:${AIR_OIL_CYCLE_GID}
WORKDIR /workspace

# Le build execute seulement le preflight et une fixture thermochimique
# generique non moteur, apres USER et sans reseau. Aucun des 2 570 cas DOE
# canoniques n'est lance et le solveur forward moteur n'est jamais appele.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/air-oil-cycle-f34b-build-smoke.json; \
      stderr=/tmp/air-oil-cycle-f34b-build-smoke.stderr; \
      if ! python /opt/air-oil-cycle-f34b/smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" "${XDG_CACHE_HOME}"'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-air-oil-cycle-f34b" \
      org.opencontainers.image.description="Minimal linux/amd64 CPU image embedding fail-closed F34 air/oil contracts, a zero-execution DOE manifest and a generic non-engine Cantera smoke" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.licenses="NOASSERTION"

CMD ["python", "/opt/air-oil-cycle-f34b/smoke.py"]
