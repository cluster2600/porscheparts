# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU minimale F38 : solveur stationnaire standard-library et ses sept
# preuves parentes publiques. Aucun scan, maillage, poids, secret ou client API.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS gas-path-f38

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/gas-path-f38-cache

RUN test "${TARGETARCH}" = "amd64"

COPY containers/gas-path-f38-smoke.py /opt/gas-path-f38/smoke.py
COPY twins/reference-917-engine/source/run_gas_path_network_f38.py /opt/gas-path-f38/twins/reference-917-engine/source/run_gas_path_network_f38.py
COPY twins/reference-917-engine/gas-path-network-f38.json /opt/gas-path-f38/twins/reference-917-engine/gas-path-network-f38.json
COPY twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json /opt/gas-path-f38/twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json
COPY twins/reference-917-engine/doe-surrogate-f34.json /opt/gas-path-f38/twins/reference-917-engine/doe-surrogate-f34.json
COPY twins/reference-917-engine/air-oil-core-controls-f34a.json /opt/gas-path-f38/twins/reference-917-engine/air-oil-core-controls-f34a.json
COPY twins/reference-917-engine/integrated-bench-assembly-f37.json /opt/gas-path-f38/twins/reference-917-engine/integrated-bench-assembly-f37.json
COPY twins/reference-917-engine/evidence/f33/cycle-thermal-report.json /opt/gas-path-f38/twins/reference-917-engine/evidence/f33/cycle-thermal-report.json
COPY twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json /opt/gas-path-f38/twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json
COPY twins/reference-917-engine/evidence/f34/report.json /opt/gas-path-f38/twins/reference-917-engine/evidence/f34/report.json
COPY twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json /opt/gas-path-f38/twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json

ARG GAS_PATH_UID=9138
ARG GAS_PATH_GID=9138
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${GAS_PATH_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${GAS_PATH_GID}:" /etc/group \
    && printf 'gas-path-f38:x:%s:\n' "${GAS_PATH_GID}" >> /etc/group \
    && printf 'gas-path-f38:x:%s:%s:F38 stationary gas path:/tmp:/usr/sbin/nologin\n' \
      "${GAS_PATH_UID}" "${GAS_PATH_GID}" >> /etc/passwd \
    && find /opt/gas-path-f38 -type d -exec chmod 0555 {} + \
    && find /opt/gas-path-f38 -type f -exec chmod 0444 {} + \
    && chmod 0555 /opt/gas-path-f38/smoke.py \
      /opt/gas-path-f38/twins/reference-917-engine/source/run_gas_path_network_f38.py

USER ${GAS_PATH_UID}:${GAS_PATH_GID}
WORKDIR /tmp

# Rejoue le calcul et compare byte pour byte la preuve canonique, après USER et
# sans réseau. Toutes les gates de validation physique doivent rester fermées.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/gas-path-f38-build-smoke.json; \
      stderr=/tmp/gas-path-f38-build-smoke.stderr; \
      if ! python /opt/gas-path-f38/smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" "${XDG_CACHE_HOME}" /tmp/f38-smoke-output'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-gas-path-f38" \
      org.opencontainers.image.description="Minimal offline linux/amd64 CPU image for the fail-closed F38 steady station network" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.licenses="NOASSERTION"

CMD ["python", "/opt/gas-path-f38/smoke.py"]
