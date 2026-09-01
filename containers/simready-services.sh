#!/usr/bin/env bash
set -euo pipefail

CONFIG=/etc/simready-supervisord.conf
SECRET_FILE=/workspace/secrets/nvidia.env

load_credentials() {
    if [ ! -f "${SECRET_FILE}" ]; then
        echo "simready: missing ${SECRET_FILE}; install it through the approved OpenBao wrapper" >&2
        return 1
    fi
    if [ "$(stat -c '%a' "${SECRET_FILE}")" != "600" ]; then
        echo "simready: ${SECRET_FILE} must have mode 0600" >&2
        return 1
    fi
    set -a
    # shellcheck disable=SC1090
    . "${SECRET_FILE}"
    set +a
    if [ -z "${NVIDIA_API_KEY:-}" ]; then
        echo "simready: NVIDIA_API_KEY is not configured" >&2
        return 1
    fi
    export NGC_API_KEY="${NGC_API_KEY:-${NVIDIA_API_KEY}}"
}

wait_for_health() {
    local name="$1" url="$2" attempts="$3"
    local attempt=1
    while [ "${attempt}" -le "${attempts}" ]; do
        if curl --fail --silent --show-error --max-time 10 "${url}" >/dev/null; then
            echo "simready: ${name} ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 5
    done
    echo "simready: ${name} did not become ready" >&2
    return 1
}

wait_for_ovrtx() {
    local attempt=1
    while [ "${attempt}" -le 180 ]; do
        if curl --fail --silent --show-error --max-time 10 \
            http://127.0.0.1:8001/health \
            | jq -e '.status == "healthy" and .gpu_initialized == true' >/dev/null; then
            echo "simready: ovrtx ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 5
    done
    echo "simready: ovrtx did not initialize its GPU renderer" >&2
    return 1
}

case "${1:-}" in
    start)
        load_credentials
        simready-nvidia-auth-check
        mkdir -p /workspace/logs
        if [ -s /tmp/simready-supervisord.pid ] \
            && kill -0 "$(cat /tmp/simready-supervisord.pid)" 2>/dev/null; then
            echo "simready: services already running"
        else
            supervisord -c "${CONFIG}"
        fi
        wait_for_health material-agent http://127.0.0.1:8100/health 60
        wait_for_health physics-agent http://127.0.0.1:8200/health 60
        wait_for_ovrtx
        ;;
    stop)
        if [ -S /tmp/simready-supervisor.sock ]; then
            supervisorctl -c "${CONFIG}" shutdown
        fi
        ;;
    status)
        supervisorctl -c "${CONFIG}" status
        ;;
    foreground)
        load_credentials
        simready-nvidia-auth-check
        exec supervisord -n -c "${CONFIG}"
        ;;
    *)
        echo "usage: simready-services start|stop|status|foreground" >&2
        exit 2
        ;;
esac
