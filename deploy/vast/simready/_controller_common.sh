#!/usr/bin/env bash
# Fonctions locales pour les opérations atomiques sur une instance déjà créée.

CONTROLLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Utilisé par les scripts qui sourcent cette bibliothèque.
# shellcheck disable=SC2034
REPOSITORY_ROOT="$(cd "${CONTROLLER_DIR}/../../.." && pwd)"
INSTANCE_GUARD="${CONTROLLER_DIR}/_instance_guard.py"
OPENBAO_VASTAI_BIN="${OPENBAO_VASTAI_BIN:-}"
MAX_ACTUAL_DPH="${MAX_ACTUAL_DPH:-2.50}"
EXPECTED_LABEL="${EXPECTED_LABEL:-3dprinting993-simready-local-ai}"
SSH_HOST=""
SSH_PORT=""
SSH_TARGET=""
SSH_OPTIONS=()

controller_die() {
    printf 'vast-simready: %s\n' "$*" >&2
    return 1
}

validate_controller_id() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || controller_die "identifiant de job invalide"
}

validate_pinned_image() {
    [[ "$1" =~ ^[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$ ]] \
        || controller_die "image attendue non épinglée par digest"
}

require_vast_wrapper() {
    [ -n "${OPENBAO_VASTAI_BIN}" ] || controller_die "OPENBAO_VASTAI_BIN doit désigner explicitement le wrapper approuvé"
    [[ "${OPENBAO_VASTAI_BIN}" = /* ]] || controller_die "OPENBAO_VASTAI_BIN doit être absolu"
    [ -x "${OPENBAO_VASTAI_BIN}" ] || controller_die "wrapper OpenBao Vast.ai absent ou non exécutable"
}

guard_and_prepare_ssh() {
    local instance_id="$1" expected_image="$2" max_dph="$3" guard_report="$4" known_hosts="$5"
    shift 5
    local status_args=()
    local guard_mode_args=()
    local status
    require_vast_wrapper
    for status in "$@"; do status_args+=(--allowed-status "${status}"); done
    if [ "${GUARD_SKIP_COST_CAP:-0}" = "1" ]; then
        guard_mode_args+=(--skip-cost-cap)
    fi
    python3 "${INSTANCE_GUARD}" \
        --wrapper "${OPENBAO_VASTAI_BIN}" \
        --instance-id "${instance_id}" \
        --expected-image "${expected_image}" \
        --expected-label "${EXPECTED_LABEL}" \
        --max-actual-dph "${max_dph}" \
        --require-ssh \
        "${guard_mode_args[@]}" \
        --report "${guard_report}" \
        "${status_args[@]}" >/dev/null
    read -r SSH_HOST SSH_PORT < <(python3 - "${guard_report}" <<'PY'
import json
from pathlib import Path
import sys
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
instance = report["instance"]
print(instance["ssh_host"], instance["ssh_port"])
PY
)
    mkdir -p "$(dirname "${known_hosts}")"
    touch "${known_hosts}"
    chmod 0600 "${known_hosts}"
    SSH_TARGET="root@${SSH_HOST}"
    SSH_OPTIONS=(
        -p "${SSH_PORT}"
        -o BatchMode=yes
        -o ConnectTimeout=20
        -o ServerAliveInterval=15
        -o ServerAliveCountMax=4
        -o StrictHostKeyChecking=accept-new
        -o "UserKnownHostsFile=${known_hosts}"
    )
}

controller_ssh() {
    # Les seules chaînes distantes fournies par les appelants utilisent des
    # identifiants validés par validate_controller_id.
    # shellcheck disable=SC2029
    ssh "${SSH_OPTIONS[@]}" "${SSH_TARGET}" "$@"
}
