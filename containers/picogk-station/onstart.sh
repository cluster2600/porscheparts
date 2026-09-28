#!/bin/sh
set -eu
# Billing termination is enforced by the external Vast guard, not this process.
mkdir -p /workspace/logs
/usr/local/bin/station-sshd -T >/dev/null
test -s /root/.ssh/authorized_keys
if ! supervisorctl -c /opt/station/supervisord.conf pid >/dev/null 2>&1; then
    supervisord -c /opt/station/supervisord.conf
fi
# STOPPED is intentional before the guarded Qwen/Kit start, and makes status
# return nonzero even when the daemon itself is healthy.
supervisorctl -c /opt/station/supervisord.conf status || true
supervisorctl -c /opt/station/supervisord.conf pid
