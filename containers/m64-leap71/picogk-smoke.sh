#!/bin/sh
set -eu
test "$#" -eq 1 && test "$1" = picogk-m64 || {
    echo 'Usage: smoke-test.sh picogk-m64' >&2
    exit 2
}
test "$(uname -m)" = x86_64
test "$(dotnet --version)" = 9.0.317
test -s /opt/m64/HeadVoxels.dll
test -s /app/picogk.26.2.so
if ldd /app/picogk.26.2.so | grep -q 'not found'; then
    echo 'Native dependency missing' >&2
    exit 1
fi
witness_dir=$(mktemp -d /tmp/picogk-smoke.XXXXXX)
timeout 120 dotnet /opt/picogk-witness/bin/RuntimeWitness.dll "$witness_dir"
timeout 120 dotnet /opt/m64/HeadVoxels.dll \
    "$witness_dir/sphere-radius5mm-voxel0.5mm.stl" "$witness_dir/cli-output" 0.5
# Host keys intentionally do not exist in distributed layers. Runtime/startup
# validates the SSH server with freshly generated container-specific keys.
test -x /usr/sbin/sshd
echo PICOGK_M64_SMOKE_PASS
