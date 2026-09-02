#!/bin/sh
set -eu

real_sshd=/usr/lib/openssh/sshd.real
runtime_dir=/run/sshd
host_key_marker=${runtime_dir}/f41-runtime-host-keys.ready

if [ "$(id -u)" -ne 0 ]; then
    echo "sshd_runtime_wrapper_requires_root" >&2
    exit 77
fi

test -x "${real_sshd}" || {
    echo "sshd_runtime_real_binary_missing" >&2
    exit 78
}

if [ -e "${runtime_dir}" ]; then
    test -d "${runtime_dir}" && test ! -L "${runtime_dir}" || {
        echo "sshd_runtime_directory_rejected" >&2
        exit 83
    }
    test "$(stat -c '%u:%g' "${runtime_dir}")" = "0:0" || {
        echo "sshd_runtime_directory_owner_rejected" >&2
        exit 84
    }
else
    install -d -o root -g root -m 0755 "${runtime_dir}"
fi

# An OpenSSH child re-exec (-R) inherits the already opened host-key file
# descriptors. Do not touch the filesystem again in that internal mode.
for argument in "$@"; do
    if [ "${argument}" = "-R" ]; then
        exec "${real_sshd}" "$@"
    fi
done

# The image deliberately contains no host private key. Vast's ssh_direct
# entrypoint invokes /usr/sbin/sshd before onstart, so create the instance
# identity just in time in the writable container layer. ssh-keygen -A only
# creates missing default host keys and never replaces an existing identity.
umask 077
rm -f -- "${host_key_marker}"
/usr/bin/ssh-keygen -A

host_key_count=0
for host_key in /etc/ssh/ssh_host_*_key; do
    [ -e "${host_key}" ] || continue
    test -f "${host_key}" || {
        echo "sshd_runtime_host_key_not_regular" >&2
        exit 85
    }
    test ! -L "${host_key}" || {
        echo "sshd_runtime_host_key_symlink_rejected" >&2
        exit 86
    }
    test "$(stat -c '%u:%g:%a' "${host_key}")" = "0:0:600" || {
        echo "sshd_runtime_host_key_permissions_rejected" >&2
        exit 87
    }
    host_key_count=$((host_key_count + 1))
done

test "${host_key_count}" -gt 0 || {
    echo "sshd_runtime_host_keys_missing" >&2
    exit 88
}

install -o root -g root -m 0600 /dev/null "${host_key_marker}"
exec "${real_sshd}" "$@"
