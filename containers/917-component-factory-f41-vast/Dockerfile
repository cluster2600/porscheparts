# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
# Image F41 Vast : transport SSH minimal au-dessus de l'auteur CAO F28 immuable.
# Vast remplace cet ENTRYPOINT en ssh_direct ; le onstart reste le prevol.

ARG F28_BASE_IMAGE=ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57
FROM ${F28_BASE_IMAGE} AS component-factory-f41-vast

ARG TARGETARCH
USER 0:0

ENV HOME=/root \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PYTHONNOUSERSITE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_NO_INDEX=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN test "${TARGETARCH}" = "amd64"

# Fermer la resolution APT sur la fermeture minimale OpenSSH. Les clefs hote
# creees par postinst sont retirees : chaque instance Vast doit produire sa
# propre identite ephemere et injecter seulement la clef publique autorisee.
RUN --mount=type=bind,source=containers/917-component-factory-f41-vast/system-packages.sha256,target=/tmp/system-packages.sha256,readonly \
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
    && test -x /usr/bin/setpriv \
    && rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub \
    && rm -rf /tmp/debs /var/lib/apt/lists/*

COPY containers/917-component-factory-f41-vast/lock.json /opt/917-component-factory-f41-vast/lock.json
COPY containers/917-component-factory-f41-vast/system-packages.sha256 /opt/917-component-factory-f41-vast/system-packages.sha256
COPY containers/917-component-factory-f41-vast/stage_job.py /opt/917-component-factory-f41-vast/stage_job.py
COPY containers/917-component-factory-f41-vast/run_job.sh /opt/917-component-factory-f41-vast/run_job.sh
COPY containers/917-component-factory-f41-vast/prepare_layout.sh /opt/917-component-factory-f41-vast/prepare_layout.sh
COPY containers/917-component-factory-f41-vast/image_smoke.py /opt/917-component-factory-f41-vast/image_smoke.py
COPY containers/917-component-factory-f41-vast/vast_onstart.sh /opt/917-component-factory-f41-vast/vast_onstart.sh
COPY containers/917-component-factory-f41-vast/entrypoint.sh /opt/917-component-factory-f41-vast/entrypoint.sh

RUN find /opt/917-component-factory-f41-vast -type d -exec chmod 0555 {} + \
    && find /opt/917-component-factory-f41-vast -type f -exec chmod 0444 {} + \
    && chmod 0555 \
      /opt/917-component-factory-f41-vast/stage_job.py \
      /opt/917-component-factory-f41-vast/run_job.sh \
      /opt/917-component-factory-f41-vast/prepare_layout.sh \
      /opt/917-component-factory-f41-vast/image_smoke.py \
      /opt/917-component-factory-f41-vast/vast_onstart.sh \
      /opt/917-component-factory-f41-vast/entrypoint.sh \
    && ln -s /opt/917-component-factory-f41-vast/stage_job.py /usr/local/bin/917-cad-stage-job \
    && ln -s /opt/917-component-factory-f41-vast/run_job.sh /usr/local/bin/917-cad-run-job \
    && ln -s /opt/917-component-factory-f41-vast/vast_onstart.sh /usr/local/bin/917-cad-vast-onstart \
    && install -d -o root -g root -m 0755 /run/sshd /workspace \
    && install -d -o root -g root -m 0700 /root/.ssh \
    && /opt/917-component-factory-f41-vast/prepare_layout.sh \
    && test ! -e /root/.ssh/authorized_keys \
    && test -z "$(find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key*' -print -quit)"

WORKDIR /workspace

# Smoke reel build123d -> STEP -> OCCT apres staging et chute vers 9178:9178.
# Aucun demon reseau, modele moteur, scan ou resultat F41 n'est embarque.
RUN --network=none /bin/bash -euo pipefail -c '\
      stdout=/tmp/917-component-factory-f41-vast-build-smoke.json; \
      stderr=/tmp/917-component-factory-f41-vast-build-smoke.stderr; \
      if ! python /opt/917-component-factory-f41-vast/image_smoke.py >"${stdout}" 2>"${stderr}"; then \
        cat "${stderr}" >&2; exit 1; \
      fi; \
      cat "${stdout}"; \
      if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi; \
      rm -rf -- "${stdout}" "${stderr}" /workspace/inbox/* /workspace/jobs/* /workspace/results/*'

ARG OCI_SOURCE=https://github.com/cluster2600/3dprinting993
LABEL org.opencontainers.image.title="3dprinting993-917-component-factory-f41-vast" \
      org.opencontainers.image.description="Minimal linux/amd64 Vast ssh_direct transport layer over immutable build123d/OCCT F28; CAD and manufacturing claims remain blocked" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.base.name="ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57" \
      org.opencontainers.image.licenses="NOASSERTION"

# Root sert uniquement au transport SSH/SCP et au staging. 917-cad-run-job
# impose ensuite l'utilisateur CAO existant 9178:9178 sans capability.
USER 0:0
ENTRYPOINT ["/opt/917-component-factory-f41-vast/entrypoint.sh"]
CMD []
