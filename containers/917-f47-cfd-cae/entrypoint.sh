#!/bin/sh
set -eu
test "$(id -u)" -eq 0 || { echo "transport_entrypoint_requires_root" >&2; exit 77; }
/opt/917-f47-cfd-cae/prepare_layout.sh
if [ "$#" -eq 0 ]; then
    exec setpriv --reuid=9147 --regid=9147 --clear-groups --no-new-privs \
        /usr/local/bin/f47-image-smoke
fi
exec "$@"
