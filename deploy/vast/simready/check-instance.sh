#!/usr/bin/env bash
# Vérification seule : aucune connexion SSH et aucune mutation Vast.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE_ID=""
EXPECTED_IMAGE=""
REPORT=""
MAX_DPH="${MAX_ACTUAL_DPH:-2.50}"
WRAPPER="${OPENBAO_VASTAI_BIN:-}"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --wrapper) WRAPPER="$2"; shift 2 ;;
        --report) REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${REPORT}" ] \
    || { echo "usage: $0 --instance-id ID --expected-image REPO@sha256:DIGEST --report PATH [--max-actual-dph 2.50]" >&2; exit 2; }
[ -n "${WRAPPER}" ] && [[ "${WRAPPER}" = /* ]] && [ -x "${WRAPPER}" ] \
    || { echo "OPENBAO_VASTAI_BIN ou --wrapper absolu et exécutable requis" >&2; exit 2; }
exec python3 "${SCRIPT_DIR}/_instance_guard.py" \
    --wrapper "${WRAPPER}" \
    --instance-id "${INSTANCE_ID}" \
    --expected-image "${EXPECTED_IMAGE}" \
    --max-actual-dph "${MAX_DPH}" \
    --require-ssh \
    --report "${REPORT}"
