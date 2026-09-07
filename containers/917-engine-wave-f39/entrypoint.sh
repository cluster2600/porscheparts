#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
    set -- python /opt/917-engine-wave-f39/smoke.py
fi

exec "$@"
