#!/bin/sh
set -eu
test "$#" -eq 2 && test "$1" = --deadline-epoch || {
    echo 'Usage: picogk-vast-onstart --deadline-epoch UNIX_SECONDS' >&2
    exit 2
}
case "$2" in ''|*[!0-9]*) echo 'Invalid deadline' >&2; exit 2 ;; esac
now=$(date +%s)
remaining=$(( $2 - now ))
test "$remaining" -gt 0 && test "$remaining" -le 10800 || {
    echo 'Deadline must be in the next three hours' >&2
    exit 2
}
mkdir -p /workspace/picogk-smoke
# Vast ssh_direct starts SSH before onstart and may replace ENTRYPOINT.
# Reuse the original runtime-key helper in configuration-only mode, never
# start a second listener. It also handles an upstream-overwritten sshd shim.
/usr/local/bin/picogk-sshd-runtime-wrapper -T >/dev/null
test -s /root/.ssh/authorized_keys || {
    echo 'Vast runtime authorized_keys missing' >&2
    exit 2
}
test -f /root/.no_auto_tmux
timeout 120 dotnet /opt/picogk-witness/bin/RuntimeWitness.dll /workspace/picogk-smoke
printf '%s\n' "$2" > /workspace/PICOGK_DEADLINE_EPOCH
printf '%s\n' PICOGK_M64_READY > /workspace/PICOGK_READY
echo PICOGK_M64_READY
# The deadline is an auditable contract for the external Vast destroy guard.
# This preflight neither terminates provider billing nor starts another sshd;
# each submitted calculation must additionally have its own bounded timeout.
