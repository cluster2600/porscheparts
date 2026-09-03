#!/bin/sh
set -eu

runtime_dir=/run/sshd
lock=${runtime_dir}/simready-runtime-host-keys.lock
marker=${runtime_dir}/simready-runtime-host-keys.ready

test "$(id -u)" -eq 0
test -L /usr/sbin/sshd
test -x /usr/lib/openssh/sshd.real
test -x /usr/bin/flock
test -x /usr/bin/ssh-keygen
test -f /root/.no_auto_tmux
test ! -L /root/.no_auto_tmux
test "$(stat -c '%u:%g:%a' /root/.no_auto_tmux)" = "0:0:600"
test -z "$(find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key*' -print -quit)"

# Hold the exact wrapper lock and prove two concurrent sshd invocations wait.
exec 8>"${lock}"
/usr/bin/flock -x 8
/usr/sbin/sshd -T >/tmp/simready-sshd-smoke-1.out 2>/tmp/simready-sshd-smoke-1.err &
first=$!
/usr/sbin/sshd -T >/tmp/simready-sshd-smoke-2.out 2>/tmp/simready-sshd-smoke-2.err &
second=$!
sleep 1
kill -0 "${first}"
kill -0 "${second}"
/usr/bin/flock -u 8
exec 8>&-
wait "${first}"
wait "${second}"

test ! -s /tmp/simready-sshd-smoke-1.err
test ! -s /tmp/simready-sshd-smoke-2.err
test -f "${marker}"
test ! -L "${marker}"
test "$(stat -c '%u:%g:%a' "${marker}")" = "0:0:600"
test -n "$(find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key' -print -quit)"

printf '%s\n' '{"status":"simready_ephemeral_sshd_concurrency_smoke_passed"}'
