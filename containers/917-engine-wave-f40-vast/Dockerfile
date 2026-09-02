# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image F40 Vast : couche SSH minimale au-dessus du solveur F39 immuable.
# Vast remplace cet ENTRYPOINT en mode ssh_direct ; vast-onstart.sh reste le prevol.

ARG F39_BASE_IMAGE=ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3
FROM ${F39_BASE_IMAGE} AS engine-wave-f40-vast

ARG TARGETARCH
USER 0:0

ENV HOME=/root \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore \
    NUMBA_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN test "${TARGETARCH}" = "amd64"

# Fermer la resolution APT sur les treize paquets de la fermeture minimale
# OpenSSH. Les clefs hote generees par postinst sont supprimees : Vast doit
# produire l'identite ephemere de chaque instance, jamais la partager via OCI.
RUN --mount=type=bind,source=containers/917-engine-wave-f40-vast/system-packages.sha256,target=/tmp/system-packages.sha256,readonly \
    apt-get update \
    && install -d -o _apt -g root -m 0755 /tmp/debs \
    && cd /tmp/debs \
    && apt-get download \
      libbsd0=0.11.7-2 \
      libcbor0.8=0.8.0-2+b1 \
      libedit2=3.1-20221030-2 \
      libfido2-1=1.12.0-2+b1 \
      libproc2-0=2:4.0.2-3 \
      libwrap0=7.6.q-32 \
      openssh-client=1:9.2p1-2+deb12u10 \
      openssh-server=1:9.2p1-2+deb12u10 \
      openssh-sftp-server=1:9.2p1-2+deb12u10 \
      procps=2:4.0.2-3 \
      runit-helper=2.15.2 \
      sensible-utils=0.0.17+nmu1 \
      ucf=3.0043+nmu1+deb12u1 \
    && sha256sum --check /tmp/system-packages.sha256 \
    && DEBIAN_FRONTEND=noninteractive dpkg -i /tmp/debs/*.deb \
    && test "$(dpkg-query -W -f='${Version}' openssh-server)" = "1:9.2p1-2+deb12u10" \
    && test "$(dpkg-query -W -f='${Version}' openssh-sftp-server)" = "1:9.2p1-2+deb12u10" \
    && test -x /usr/sbin/sshd \
    && rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub \
    && rm -rf /tmp/debs /var/lib/apt/lists/*

COPY containers/917-engine-wave-f40-vast/lock.json /opt/917-engine-wave-f40-vast/lock.json
COPY containers/917-engine-wave-f40-vast/system-packages.sha256 /opt/917-engine-wave-f40-vast/system-packages.sha256
COPY containers/917-engine-wave-f40-vast/stage_job.py /opt/917-engine-wave-f40-vast/stage_job.py
COPY containers/917-engine-wave-f40-vast/run_job.sh /opt/917-engine-wave-f40-vast/run_job.sh
COPY containers/917-engine-wave-f40-vast/prepare_layout.sh /opt/917-engine-wave-f40-vast/prepare_layout.sh
COPY containers/917-engine-wave-f40-vast/image_smoke.py /opt/917-engine-wave-f40-vast/image_smoke.py
COPY containers/917-engine-wave-f40-vast/vast_onstart.sh /opt/917-engine-wave-f40-vast/vast_onstart.sh
COPY containers/917-engine-wave-f40-vast/entrypoint.sh /opt/917-engine-wave-f40-vast/entrypoint.sh

RUN find /opt/917-engine-wave-f40-vast -type d -exec chmod 0555 {} + \
    && find /opt/917-engine-wave-f40-vast -type f -exec chmod 0444 {} + \
    && chmod 0555 \
      /opt/917-engine-wave-f40-vast/stage_job.py \
      /opt/917-engine-wave-f40-vast/run_job.sh \
      /opt/917-engine-wave-f40-vast/prepare_layout.sh \
      /opt/917-engine-wave-f40-vast/image_smoke.py \
      /opt/917-engine-wave-f40-vast/vast_onstart.sh \
      /opt/917-engine-wave-f40-vast/entrypoint.sh \
    && ln -s /opt/917-engine-wave-f40-vast/stage_job.py /usr/local/bin/917-wave-stage-job \
    && ln -s /opt/917-engine-wave-f40-vast/run_job.sh /usr/local/bin/917-wave-run-job \
    && ln -s /opt/917-engine-wave-f40-vast/vast_onstart.sh /usr/local/bin/917-wave-vast-onstart \
    && install -d -o root -g root -m 0755 /run/sshd /workspace \
    && install -d -o root -g root -m 0700 /root/.ssh \
    && /opt/917-engine-wave-f40-vast/prepare_layout.sh \
    && test ! -e /root/.ssh/authorized_keys \
    && test -z "$(find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key*' -print -quit)"

WORKDIR /workspace

# Le build exerce SSH empaquete, staging d'archive et chute de privileges.
# Aucun demon reseau n'est demarre et aucun modele 917 n'est execute ici.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/917-engine-wave-f40-vast-build-smoke.json; \
      stderr=/tmp/917-engine-wave-f40-vast-build-smoke.stderr; \
      if ! python /opt/917-engine-wave-f40-vast/image_smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" /workspace/inbox/* /workspace/jobs/* /workspace/results/*'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-917-engine-wave-f40-vast" \
      org.opencontainers.image.description="Minimal linux/amd64 Vast ssh_direct transport layer over immutable Aeolus1D 0.3.3 F39; engine claims remain blocked" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.base.name="ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3" \
      org.opencontainers.image.licenses="NOASSERTION"

# Root est requis uniquement pour l'entrypoint SSH injecte par Vast et le
# transfert SCP. 917-wave-run-job impose UID/GID 9139:9139 aux solveurs.
USER 0:0
ENTRYPOINT ["/opt/917-engine-wave-f40-vast/entrypoint.sh"]
CMD []
