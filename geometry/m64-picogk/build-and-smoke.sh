#!/usr/bin/env bash
# Reproducible PicoGK/.NET-8 build and STL-export smoke (ADR 0004).
# Runs on the host; all compilation and execution happen inside the
# pinned worker container image. Mounts this repository read-write at
# /repo so the validated STL and log land under geometry/m64-picogk/validation.
set -euo pipefail

IMAGE=${M64_WORKER_IMAGE:-m64-engineering-worker:latest}
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUTDIR="$REPO/geometry/m64-picogk/validation"
mkdir -p "$OUTDIR"

docker image inspect "$IMAGE" >/dev/null || {
    echo "Worker image missing: $IMAGE" >&2
    exit 1
}

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e DOTNET_CLI_TELEMETRY_OPTOUT=1 -v "$REPO:/repo" -w /repo "$IMAGE" bash -euo pipefail -c '
set -x
# 1) Pin check: PicoGK 2.3.0 sources and native runtime, per ADR 0004.
git -C /opt/PicoGK rev-parse HEAD
test "$(git -C /opt/PicoGK rev-parse HEAD)" = 0e6cf6b6f4993ec16dbcd72d8f26f26b999980f3
test -f /usr/local/lib/picogk.so
dotnet --version

# 2) The image ships the pinned PicoGKRuntime with SONAME picogk.so while the
#    pinned C# layer imports "picogk.26.2" (PicoGK Internals/Config.cs).
#    Bridge the name for the process via LD_LIBRARY_PATH (no image change).
ln -sf /usr/local/lib/picogk.so /tmp/picogk.26.2.so
export LD_LIBRARY_PATH=/tmp:${LD_LIBRARY_PATH:-}

# 3) Build the pinned PicoGK managed layer against the net8.0 SDK in the image.
#    The upstream csproj targets net9.0; override to net8.0 per ADR 0004.
rm -rf /tmp/pgkbuild && cp -r /opt/PicoGK/. /tmp/pgkbuild
sed -i "s|<TargetFramework>net[0-9][0-9]*\.0</TargetFramework>|<TargetFramework>net8.0</TargetFramework>|" /tmp/pgkbuild/PicoGK.csproj
grep -q "<TargetFramework>net8.0</TargetFramework>" /tmp/pgkbuild/PicoGK.csproj
dotnet build /tmp/pgkbuild/PicoGK.csproj -c Release -o /opt/PicoGK/bin -p:GeneratePackageOnBuild=false

# 4) Build the M64 smoke project (net8.0) and run the deterministic export.
dotnet build /repo/geometry/m64-picogk/M64PicogkSmoke.csproj -c Release -o /tmp/m64smoke -p:PicoGkBin=/opt/PicoGK/bin -p:GeneratePackageOnBuild=false
mkdir -p geometry/m64-picogk/validation
dotnet /tmp/m64smoke/M64PicogkSmoke.dll geometry/m64-picogk/validation/m64-picogk-smoke-box-hole.stl 0.5
'

sha256sum "$OUTDIR/m64-picogk-smoke-box-hole.stl"
