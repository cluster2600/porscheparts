#!/bin/sh
set -eu
test "$(id -u)" -eq 0 || { echo "prepare_layout_requires_root" >&2; exit 77; }
install -d -o root -g root -m 0755 /workspace
install -d -o 9147 -g 9147 -m 0750 /workspace/f46
install -d -o 9147 -g 9147 -m 0750 /workspace/f46-runtime
