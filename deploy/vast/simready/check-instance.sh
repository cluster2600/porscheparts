#!/usr/bin/env bash
# Vérifie le contrat, l'authentification SSH et la readiness réelle du conteneur.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"

INSTANCE_ID=""
EXPECTED_IMAGE=""
REPORT=""
MAX_DPH="${MAX_ACTUAL_DPH}"
WRAPPER="${OPENBAO_VASTAI_BIN:-}"
KNOWN_HOSTS=""
READY_TIMEOUT_SECONDS=1200
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --wrapper) WRAPPER="$2"; shift 2 ;;
        --report) REPORT="$2"; shift 2 ;;
        --known-hosts) KNOWN_HOSTS="$2"; shift 2 ;;
        --ready-timeout-seconds) READY_TIMEOUT_SECONDS="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${REPORT}" ] && [ -n "${KNOWN_HOSTS}" ] \
    || { echo "usage: $0 --instance-id ID --expected-image REPO@sha256:DIGEST --report PATH --known-hosts PATH [--max-actual-dph 2.50]" >&2; exit 2; }
[[ "${READY_TIMEOUT_SECONDS}" =~ ^[1-9][0-9]{0,3}$ ]] \
    && [ "${READY_TIMEOUT_SECONDS}" -le 3600 ] \
    || controller_die "ready-timeout-seconds doit être compris entre 1 et 3600"
OPENBAO_VASTAI_BIN="${WRAPPER}"
require_vast_wrapper

write_readiness_result() {
    python3 - "${REPORT}" "$1" <<'PY'
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

path = Path(sys.argv[1])
passed = sys.argv[2] == "1"
payload = json.loads(path.read_text(encoding="utf-8"))
payload["ssh_authenticated"] = passed
payload["remote_ready"] = passed
payload["remote_ready_marker"] = "/workspace/READY"
payload["ready_checked_at"] = datetime.now(timezone.utc).isoformat()
if not passed:
    payload["status"] = "blocked"
    payload["passed"] = False
    payload.setdefault("errors", []).append(
        "authentification SSH ou marqueur /workspace/READY indisponible avant expiration"
    )
temporary = path.with_name(path.name + ".partial")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(temporary, path)
PY
}

ready=0
deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
# Le wrapper de lancement a déjà validé le contrat. Le relire sans exiger SSH
# permet d'échouer immédiatement sur une divergence permanente.
python3 "${INSTANCE_GUARD}" \
    --wrapper "${OPENBAO_VASTAI_BIN}" \
    --instance-id "${INSTANCE_ID}" \
    --expected-image "${EXPECTED_IMAGE}" \
    --expected-label "${EXPECTED_LABEL}" \
    --expected-gpu-name "${EXPECTED_GPU_NAME}" \
    --min-gpu-ram-mb "${MIN_GPU_RAM_MB}" \
    --min-cpu-cores "${MIN_CPU_CORES}" \
    --min-cpu-ram-mb "${MIN_CPU_RAM_MB}" \
    --min-disk-space-gb "${MIN_DISK_SPACE_GB}" \
    --max-actual-dph "${MAX_DPH}" \
    --allowed-status created \
    --allowed-status loading \
    --allowed-status running \
    --report "${REPORT}" >/dev/null \
    || controller_die "contrat Vast différent des limites avant attente SSH"

# Attendre seulement les deux champs SSH transitoires. Toute autre divergence
# interrompt immédiatement le contrôle afin de limiter la dépense.
metadata_ready=0
while [ "${SECONDS}" -lt "${deadline}" ]; do
    if python3 "${INSTANCE_GUARD}" \
        --wrapper "${OPENBAO_VASTAI_BIN}" \
        --instance-id "${INSTANCE_ID}" \
        --expected-image "${EXPECTED_IMAGE}" \
        --expected-label "${EXPECTED_LABEL}" \
        --expected-gpu-name "${EXPECTED_GPU_NAME}" \
        --min-gpu-ram-mb "${MIN_GPU_RAM_MB}" \
        --min-cpu-cores "${MIN_CPU_CORES}" \
        --min-cpu-ram-mb "${MIN_CPU_RAM_MB}" \
        --min-disk-space-gb "${MIN_DISK_SPACE_GB}" \
        --max-actual-dph "${MAX_DPH}" \
        --require-ssh \
        --allowed-status created \
        --allowed-status loading \
        --allowed-status running \
        --report "${REPORT}" >/dev/null 2>&1; then
        metadata_ready=1
        break
    fi
    python3 - "${REPORT}" <<'PY' || controller_die "contrat Vast divergent pendant l'attente SSH"
import json
from pathlib import Path
import sys

errors = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("errors", [])
transient = {"hôte SSH invalide", "port SSH invalide"}
raise SystemExit(0 if errors and set(errors) <= transient else 1)
PY
    sleep 10
done
[ "${metadata_ready}" = "1" ] || {
    write_readiness_result 0
    controller_die "métadonnées contractuelles ou SSH indisponibles avant expiration"
}

guard_and_prepare_ssh \
    "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" "${REPORT}" "${KNOWN_HOSTS}" \
    created loading running
while [ "${SECONDS}" -lt "${deadline}" ]; do
    if controller_ssh "test -f /workspace/READY" >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 10
done

[ "${ready}" = "1" ] || {
    write_readiness_result 0
    controller_die "instance non joignable ou non prête avant expiration"
}
# Le marqueur READY ne remplace pas le contrôle final de l'état contractuel.
guard_and_prepare_ssh \
    "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" "${REPORT}" "${KNOWN_HOSTS}" running
write_readiness_result 1
printf '%s\n' "${REPORT}"
