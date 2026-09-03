#!/usr/bin/env bash
# Initialisation minimale d'une instance Vast.ai utilisant l'image SimReady.
# Aucun secret n'est lu ici : les identifiants NVIDIA sont injectes ensuite
# par le wrapper OpenBao dedie.
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
READY="${WORKSPACE}/READY"
READY_TMP=""

if [ "$(id -u)" -ne 0 ]; then
    echo "simready onstart requires root" >&2
    exit 77
fi

umask 077
if [ -e "${WORKSPACE}" ]; then
    test -d "${WORKSPACE}" && test ! -L "${WORKSPACE}" || {
        echo "simready workspace rejected" >&2
        exit 84
    }
else
    install -d -o root -g root -m 0755 "${WORKSPACE}"
fi
mkdir -p "${WORKSPACE}/logs" "${WORKSPACE}/simready"
rm -f -- "${READY}"
cleanup_ready_tmp() {
    test -z "${READY_TMP:-}" || rm -f -- "${READY_TMP}"
}
trap cleanup_ready_tmp EXIT HUP INT TERM

# Vast's ssh_direct launcher may opt into an interactive tmux wrapper. Disable
# it in the image and verify the marker again here so BatchMode probes execute
# the requested command directly.
NO_AUTO_TMUX=/root/.no_auto_tmux
test -f "${NO_AUTO_TMUX}" && test ! -L "${NO_AUTO_TMUX}" || {
    echo "simready no-auto-tmux marker rejected" >&2
    exit 78
}
test "$(stat -c '%u:%g:%a' "${NO_AUTO_TMUX}")" = "0:0:600" || {
    echo "simready no-auto-tmux marker metadata rejected" >&2
    exit 79
}

HOST_KEY_MARKER=/run/sshd/simready-runtime-host-keys.ready
if [ ! -e "${HOST_KEY_MARKER}" ] && [ ! -L "${HOST_KEY_MARKER}" ]; then
    /usr/sbin/sshd -T >/dev/null
fi
test -f "${HOST_KEY_MARKER}" && test ! -L "${HOST_KEY_MARKER}" || {
    echo "simready runtime host-key marker rejected" >&2
    exit 80
}
test "$(stat -c '%u:%g:%a' "${HOST_KEY_MARKER}")" = "0:0:600" || {
    echo "simready runtime host-key marker metadata rejected" >&2
    exit 81
}

# Vast.ai injecte authorized_keys comme root, mais certains hotes le laissent
# avec un proprietaire ou des droits refuses par sshd. Corriger exactement ce
# repertoire evite l'echec d'authentification observe sur les premiers essais.
test -d /root/.ssh && test ! -L /root/.ssh || {
    echo "simready root SSH directory rejected" >&2
    exit 85
}
chown root:root /root/.ssh
chmod 0700 /root/.ssh
if [ -f /root/.ssh/authorized_keys ]; then
    test ! -L /root/.ssh/authorized_keys || {
        echo "simready authorized_keys symlink rejected" >&2
        exit 82
    }
    chown root:root /root/.ssh/authorized_keys
    chmod 0600 /root/.ssh/authorized_keys
fi
test -s /root/.ssh/authorized_keys || {
    echo "simready authorized_keys missing" >&2
    exit 83
}

nvidia-smi >"${WORKSPACE}/logs/nvidia-smi.log" 2>&1
smoke-test.sh simready-local-ai >"${WORKSPACE}/logs/simready-smoke.log" 2>&1
"${PHYSICSNEMO_PYTHON:-/opt/venv/bin/python}" \
    /usr/local/bin/physicsnemo-gpu-smoke \
    >"${WORKSPACE}/logs/physicsnemo-gpu-smoke.json" 2>&1
simready-services start >"${WORKSPACE}/logs/simready-services-start.log" 2>&1
simready-services status >"${WORKSPACE}/logs/simready-services-status.log" 2>&1
READY_TMP="$(/usr/bin/mktemp "${WORKSPACE}/.READY.XXXXXX")"
cat >"${READY_TMP}" <<'EOF'
{
  "schema_version": "1.0.0",
  "status": "simready_local_ai_services_ready",
  "ephemeral_ssh_host_keys": true,
  "batch_ssh_auto_tmux_disabled": true,
  "physicsnemo_gpu_smoke_passed": true,
  "local_vlm_ready": true,
  "ovrtx_ready": true,
  "material_agent_ready": true,
  "physics_agent_ready": true,
  "simulation_validated": false,
  "manufacturing_authorized": false,
  "target_1600_ch_validated": false
}
EOF
chmod 0644 "${READY_TMP}"
mv -f -- "${READY_TMP}" "${READY}"
READY_TMP=""
trap - EXIT HUP INT TERM
