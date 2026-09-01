#!/usr/bin/env bash
# Container entrypoint shared by all images.
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
        [ -n "${DDE_BACKEND:-}" ] && printf 'DDE_BACKEND=%s\n' "${DDE_BACKEND}"
        [ -n "${XLA_PYTHON_CLIENT_PREALLOCATE:-}" ] && printf 'XLA_PYTHON_CLIENT_PREALLOCATE=%s\n' "${XLA_PYTHON_CLIENT_PREALLOCATE}"
        [ -n "${PYTORCH_CUDA_ALLOC_CONF:-}" ] && printf 'PYTORCH_CUDA_ALLOC_CONF=%s\n' "${PYTORCH_CUDA_ALLOC_CONF}"
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
