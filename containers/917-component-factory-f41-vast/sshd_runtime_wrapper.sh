#!/bin/sh
set -eu

real_sshd=/usr/lib/openssh/sshd.real
runtime_dir=/run/sshd
host_key_marker=${runtime_dir}/f41-runtime-host-keys.ready
host_key_lock=${runtime_dir}/f41-runtime-host-keys.lock

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
# entrypoint can invoke /usr/sbin/sshd more than once before or during onstart.
# Serialize those invocations so concurrent ssh-keygen -A calls cannot race.
# ssh-keygen -A only creates missing default host keys and never replaces an
# existing identity.
umask 077
exec 9>"${host_key_lock}"
/usr/bin/flock -x 9
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

# Never unlink a valid marker while another Vast sshd invocation or onstart is
# auditing it. Publish the replacement atomically inside the root-owned runtime
# directory, then release the lock before the long-lived daemon exec.
host_key_marker_tmp=$(/usr/bin/mktemp "${runtime_dir}/.f41-runtime-host-keys.XXXXXX")
cleanup_marker_tmp() {
    test -z "${host_key_marker_tmp:-}" || rm -f -- "${host_key_marker_tmp}"
}
trap cleanup_marker_tmp EXIT HUP INT TERM
chown root:root "${host_key_marker_tmp}"
chmod 0600 "${host_key_marker_tmp}"
mv -f -- "${host_key_marker_tmp}" "${host_key_marker}"
host_key_marker_tmp=
trap - EXIT HUP INT TERM
/usr/bin/flock -u 9
exec 9>&-
exec "${real_sshd}" "$@"
