# syntax=docker/dockerfile:1.7
# Add the installed NVIDIA skill's exact validation pins without downgrading
# the already tested Content Agents / OVRTX / PhysicsNeMo service runtimes.
FROM ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699

COPY tests/manual/m64_simready_pinned_runtime_smoke.sh /usr/local/libexec/m64-simready-pinned-runtime-smoke.sh
RUN /usr/bin/env -i \
      PATH=/opt/simready-validation/bin:/usr/local/bin:/usr/bin:/bin \
      PIP_CONFIG_FILE=/dev/null UV_NO_CONFIG=1 \
      /usr/bin/timeout --kill-after=15s 600s \
      /bin/sh /usr/local/libexec/m64-simready-pinned-runtime-smoke.sh \
      > /opt/m64-pinned-runtime-cpu-smoke.log 2>&1 \
      || { m64_build_status=$?; tail -150 /opt/m64-pinned-runtime-cpu-smoke.log; exit "$m64_build_status"; }
RUN test -s /opt/m64-pinned-runtime-cpu-smoke.log \
    && chmod 0444 /opt/m64-pinned-runtime-cpu-smoke.log \
    && chmod 0555 /usr/local/libexec/m64-simready-pinned-runtime-smoke.sh

# The corrected fallback invokes the original helper directly even if Vast
# replaces /usr/sbin/sshd. It neither regenerates existing keys nor starts an
# additional listener. The wrapper also explicitly runs that helper before onstart.
COPY containers/simready-vast-onstart.sh /usr/local/bin/simready-vast-onstart
COPY containers/simready-sshd-runtime-wrapper.sh /usr/local/bin/simready-sshd-runtime-wrapper
COPY containers/smoke-test.sh /usr/local/bin/smoke-test.sh
RUN chmod 0555 /usr/local/bin/simready-vast-onstart /usr/local/bin/simready-sshd-runtime-wrapper /usr/local/bin/smoke-test.sh

# Intentionally do not change PATH or SIMREADY_FOUNDATION_ROOT globally: M64
# atomic phases select /opt/m64-simready-validate and /opt/m64-simready-foundation.
LABEL org.opencontainers.image.title="3dprinting993-simready-m64-runtime" \
      org.opencontainers.image.description="Isolated NVIDIA skill-pinned M64 validation runtime; manufacturing not authorized"
