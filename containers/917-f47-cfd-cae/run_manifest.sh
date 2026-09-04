#!/bin/sh
set -eu
if [ "$(id -u)" -eq 0 ]; then
    exec setpriv --reuid=9147 --regid=9147 --clear-groups --no-new-privs \
        /opt/917-f47-cfd-cae/run_manifest.py "$@"
fi
test "$(id -u):$(id -g)" = "9147:9147" || { echo "runner_identity_rejected" >&2; exit 77; }
exec /opt/917-f47-cfd-cae/run_manifest.py "$@"
