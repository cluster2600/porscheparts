#!/usr/bin/env bash
# Container entrypoint shared by both images.
#
# Marketplace launch modes (SSH, Jupyter) replace this entrypoint with their own
# init, so anything essential here is also done by containers/provision-vastai.sh.
set -euo pipefail

# Make the container environment visible to injected SSH and tmux sessions.
if [ -w /etc/environment ]; then
    {
        printf 'PATH=%s\n' "${PATH}"
        [ -n "${VIRTUAL_ENV:-}" ] && printf 'VIRTUAL_ENV=%s\n' "${VIRTUAL_ENV}"
        [ -n "${FOAM_VERSION:-}" ] && printf 'FOAM_VERSION=%s\n' "${FOAM_VERSION}"
    } > /etc/environment
fi

mkdir -p /workspace

# A provisioning script may be handed over by the host platform.
if [ -n "${PROVISIONING_SCRIPT:-}" ] && [ ! -f /workspace/.provisioned ]; then
    echo "entrypoint: running provisioning script ${PROVISIONING_SCRIPT}"
    curl -fsSL "${PROVISIONING_SCRIPT}" -o /tmp/provision.sh
    bash /tmp/provision.sh && touch /workspace/.provisioned
fi

exec "$@"
