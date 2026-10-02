#!/bin/sh
set -eu
if [ "${1:-}" = sshd ]; then
    exec /usr/sbin/sshd -D -e
fi
exec "$@"
