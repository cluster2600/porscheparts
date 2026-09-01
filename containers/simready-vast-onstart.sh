#!/usr/bin/env bash
# Initialisation minimale d'une instance Vast.ai utilisant l'image SimReady.
# Aucun secret n'est lu ici : les identifiants NVIDIA sont injectes ensuite
# par le wrapper OpenBao dedie.
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"

# Vast.ai injecte authorized_keys comme root, mais certains hotes le laissent
# avec un proprietaire ou des droits refuses par sshd. Corriger exactement ce
# repertoire evite l'echec d'authentification observe sur les premiers essais.
if [ -d /root/.ssh ]; then
    chown root:root /root/.ssh
    chmod 0700 /root/.ssh
fi
if [ -f /root/.ssh/authorized_keys ]; then
    chown root:root /root/.ssh/authorized_keys
    chmod 0600 /root/.ssh/authorized_keys
fi

mkdir -p "${WORKSPACE}/logs" "${WORKSPACE}/simready"
nvidia-smi >"${WORKSPACE}/logs/nvidia-smi.log" 2>&1
smoke-test.sh simready-local-ai >"${WORKSPACE}/logs/simready-smoke.log" 2>&1
simready-services start >"${WORKSPACE}/logs/simready-services-start.log" 2>&1
simready-services status >"${WORKSPACE}/logs/simready-services-status.log" 2>&1
touch "${WORKSPACE}/READY"
