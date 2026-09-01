#!/usr/bin/env bash
# Verifie l'acces au modele utilise par Material Agent sans afficher le secret
# ni le corps de la reponse NVIDIA.
set -euo pipefail

SECRET_FILE="${SIMREADY_SECRET_FILE:-/workspace/secrets/nvidia.env}"
API_URL="${NVIDIA_CHAT_API_URL:-https://integrate.api.nvidia.com/v1/chat/completions}"
MODEL="${MA_VLM_MODEL:-google/gemma-4-31b-it}"

if [ -z "${NVIDIA_API_KEY:-}" ]; then
    if [ ! -f "${SECRET_FILE}" ]; then
        echo "simready: missing ${SECRET_FILE}; install it through the approved OpenBao wrapper" >&2
        exit 1
    fi
    if [ "$(stat -c '%a' "${SECRET_FILE}")" != "600" ]; then
        echo "simready: ${SECRET_FILE} must have mode 0600" >&2
        exit 1
    fi
    set -a
    # shellcheck disable=SC1090
    . "${SECRET_FILE}"
    set +a
fi

if [ -z "${NVIDIA_API_KEY:-}" ]; then
    echo "simready: NVIDIA_API_KEY is not configured" >&2
    exit 1
fi

request_file="$(mktemp)"
trap 'rm -f "${request_file}"' EXIT
printf '{"model":"%s","messages":[{"role":"user","content":"Reply OK"}],"max_tokens":1,"temperature":0}' \
    "${MODEL}" >"${request_file}"

http_code="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 15 --max-time 45 \
    --header "Authorization: Bearer ${NVIDIA_API_KEY}" \
    --header 'Content-Type: application/json' \
    --data-binary "@${request_file}" \
    "${API_URL}")"

if [ "${http_code}" != "200" ]; then
    echo "simready: NVIDIA inference authorization failed (HTTP ${http_code})" >&2
    exit 1
fi

echo "simready: NVIDIA inference authorization OK"
