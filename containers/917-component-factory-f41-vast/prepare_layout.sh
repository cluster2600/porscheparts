#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "prepare_layout_requires_root" >&2
    exit 77
fi

install -d -o root -g root -m 0755 /workspace
install -d -o root -g root -m 0700 /workspace/inbox
install -d -o root -g root -m 0755 /workspace/jobs
install -d -o root -g root -m 0755 /workspace/results
