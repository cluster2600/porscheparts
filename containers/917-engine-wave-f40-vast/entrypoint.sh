#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "transport_entrypoint_requires_root" >&2
    exit 77
fi

/opt/917-engine-wave-f40-vast/prepare_layout.sh

if [ "$#" -eq 0 ]; then
    set -- python /opt/917-engine-wave-f40-vast/image_smoke.py
fi

exec "$@"
