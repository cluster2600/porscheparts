# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image CPU F39 : Aeolus1D et ses dependances numeriques verrouillees.
# Le smoke Sod est generique; il ne prouve ni moteur flat-12, ni turbo, ni puissance.

ARG PYTHON_BASE_IMAGE=python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef
FROM ${PYTHON_BASE_IMAGE} AS python-dependencies

ARG TARGETARCH
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN test "${TARGETARCH}" = "amd64"

RUN --mount=type=bind,source=containers/917-engine-wave-f39/requirements.txt,target=/tmp/requirements.txt,readonly \
    PIP_NO_INDEX=0 python -m pip install \
      --only-binary=:all: \
      --require-hashes \
      --no-deps \
      --requirement /tmp/requirements.txt \
    && python -m pip check \
    && test "$(python -c 'from importlib.metadata import version; print(version("aeolus1d"))')" = "0.3.3" \
    && test "$(python -c 'from importlib.metadata import version; print(version("h5py"))')" = "3.14.0" \
    && test "$(python -c 'from importlib.metadata import version; print(version("llvmlite"))')" = "0.49.0" \
    && test "$(python -c 'from importlib.metadata import version; print(version("numba"))')" = "0.67.0" \
    && test "$(python -c 'from importlib.metadata import version; print(version("numpy"))')" = "2.2.6" \
    && test "$(python -c 'from importlib.metadata import version; print(version("scipy"))')" = "1.16.3"

FROM ${PYTHON_BASE_IMAGE} AS engine-wave-f39

ARG TARGETARCH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/917-engine-wave-f39-cache \
    NUMBA_CACHE_DIR=/tmp/917-engine-wave-f39-numba \
    NUMBA_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN test "${TARGETARCH}" = "amd64"

COPY --from=python-dependencies /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=python-dependencies /usr/local/bin/aeolus1d /usr/local/bin/aeolus1d

COPY containers/917-engine-wave-f39/requirements.txt /opt/917-engine-wave-f39/requirements.txt
COPY containers/917-engine-wave-f39/smoke.py /opt/917-engine-wave-f39/smoke.py
COPY containers/917-engine-wave-f39/entrypoint.sh /opt/917-engine-wave-f39/entrypoint.sh

ARG ENGINE_WAVE_UID=9139
ARG ENGINE_WAVE_GID=9139
RUN test -x /usr/sbin/nologin \
    && ! grep -Eq "(^|:)${ENGINE_WAVE_UID}:" /etc/passwd \
    && ! grep -Eq "(^|:)${ENGINE_WAVE_GID}:" /etc/group \
    && printf 'engine-wave-f39:x:%s:\n' "${ENGINE_WAVE_GID}" >> /etc/group \
    && printf 'engine-wave-f39:x:%s:%s:F39 engine wave solver:/tmp:/usr/sbin/nologin\n' \
      "${ENGINE_WAVE_UID}" "${ENGINE_WAVE_GID}" >> /etc/passwd \
    && find /opt/917-engine-wave-f39 -type d -exec chmod 0555 {} + \
    && find /opt/917-engine-wave-f39 -type f -exec chmod 0444 {} + \
    && chmod 0555 /opt/917-engine-wave-f39/smoke.py \
      /opt/917-engine-wave-f39/entrypoint.sh \
      /usr/local/bin/aeolus1d \
    && mkdir -p /workspace \
    && chown "${ENGINE_WAVE_UID}:${ENGINE_WAVE_GID}" /workspace

USER ${ENGINE_WAVE_UID}:${ENGINE_WAVE_GID}
WORKDIR /workspace

# Le build exerce la pile native et un tube a choc apres USER et sans reseau.
# Il n'execute aucun modele 917 et maintient toutes les gates moteur fermees.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/917-engine-wave-f39-build-smoke.json; \
      stderr=/tmp/917-engine-wave-f39-build-smoke.stderr; \
      if ! python /opt/917-engine-wave-f39/smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" "${XDG_CACHE_HOME}" "${NUMBA_CACHE_DIR}"'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-917-engine-wave-f39" \
      org.opencontainers.image.description="Minimal offline linux/amd64 CPU image with Aeolus1D 0.3.3 for generic non-correlated 1D gas-dynamics studies" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.licenses="NOASSERTION"

ENTRYPOINT ["/opt/917-engine-wave-f39/entrypoint.sh"]
CMD []
