#!/bin/sh
set -eu
if [ "${1:-}" != sshd ]; then
    exec "$@"
fi
umask 077
mkdir -p /root/.ssh /run/sshd
# Vast PUBLIC_KEY carries a public SSH key only. No private key or token belongs
# in this image. A mounted authorized_keys file is also supported.
if [ -n "${PUBLIC_KEY:-}" ]; then
    key_file=$(mktemp /run/sshd/picogk-public-key.XXXXXX)
    printf '%s\n' "$PUBLIC_KEY" > "$key_file"
    ssh-keygen -l -f "$key_file" >/dev/null
    install -m 0600 "$key_file" /root/.ssh/authorized_keys
    rm "$key_file"
fi
test -s /root/.ssh/authorized_keys || {
    echo 'SSH startup blocked: supply PUBLIC_KEY or mount authorized_keys.' >&2
    exit 2
}
chmod 0700 /root/.ssh
chmod 0600 /root/.ssh/authorized_keys
ssh-keygen -A >/dev/null
exec /usr/sbin/sshd -D -e \
    -o PasswordAuthentication=no \
    -o KbdInteractiveAuthentication=no \
    -o PermitRootLogin=prohibit-password \
    -o PermitEmptyPasswords=no
