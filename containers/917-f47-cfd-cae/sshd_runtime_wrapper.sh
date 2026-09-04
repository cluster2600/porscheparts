#!/bin/sh
set -eu
real_sshd=/usr/lib/openssh/sshd.real
runtime_dir=/run/sshd
marker=${runtime_dir}/f47-runtime-host-keys.ready
lock=${runtime_dir}/f47-runtime-host-keys.lock
test "$(id -u)" -eq 0 || { echo "sshd_runtime_wrapper_requires_root" >&2; exit 77; }
test -x "${real_sshd}" || { echo "sshd_runtime_real_binary_missing" >&2; exit 78; }
install -d -o root -g root -m 0755 "${runtime_dir}"
for argument in "$@"; do
    [ "${argument}" != "-R" ] || exec "${real_sshd}" "$@"
done
umask 077
exec 9>"${lock}"
flock -x 9
ssh-keygen -A
count=0
for key in /etc/ssh/ssh_host_*_key; do
    [ -e "${key}" ] || continue
    test -f "${key}" && test ! -L "${key}" || { echo "host_key_rejected" >&2; exit 79; }
    test "$(stat -c '%u:%g:%a' "${key}")" = "0:0:600" || { echo "host_key_mode_rejected" >&2; exit 80; }
    count=$((count + 1))
done
test "${count}" -gt 0 || { echo "host_keys_missing" >&2; exit 81; }
temporary=$(mktemp "${runtime_dir}/.f47-host-keys.XXXXXX")
chown root:root "${temporary}"
chmod 0600 "${temporary}"
mv -f -- "${temporary}" "${marker}"
flock -u 9
exec 9>&-
exec "${real_sshd}" "$@"
