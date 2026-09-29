#!/usr/bin/env bash
# Compile and run the m64-valvetrain-0001 layout proxies inside the qualified
# picogk-station image. Nothing here authorizes manufacturing (SAFETY.md).
#
# The station image ships the PicoGK C# source at /upstream/PicoGK and the
# qualified native runtime at /app/picogk.26.2.so, whose bundled dependencies
# (libblosc.so.1, ...) live in /opt/picogk-native/lib. The dotnet host only
# finds the native side once the .so sits next to the assembly (or on
# LD_LIBRARY_PATH) AND its dependency directory is on LD_LIBRARY_PATH; the
# witness runs in this image use the same copy.
#
# Usage: ./build-in-station.sh [REPO_ROOT] [VOXEL_MM]
#   REPO_ROOT defaults to the worktree root inferred from this script's path.
#   The repo root is mounted read-only; outputs land in validation/run/ there.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-$(cd "$HERE/../../../.." && pwd)}"
VOXEL_MM="${2:-0.5}"
IMAGE="${PICOGK_STATION_IMAGE:-picogk-station:qualified-persistent-20260928}"
SRC="$REPO_ROOT/parts/m64-valvetrain-0001/source/picogk"
OUT="$REPO_ROOT/parts/m64-valvetrain-0001/validation/run"

if [ -e "$OUT" ]; then
    echo "Refusing to overwrite existing $OUT (delete it first; no silent overwrite)." >&2
    exit 2
fi

docker run --rm \
    -v "$REPO_ROOT":/repo:ro \
    -v "$OUT.tmp":/out \
    --entrypoint bash "$IMAGE" -lc "
set -e
mkdir -p /tmp/vtbuild
cp /repo/parts/m64-valvetrain-0001/source/picogk/Valvetrain.cs \
   /repo/parts/m64-valvetrain-0001/source/picogk/Valvetrain.csproj /tmp/vtbuild/
cd /tmp/vtbuild
echo '=== SDK ==='; dotnet --version
echo '=== BUILD ==='
dotnet build -c Release Valvetrain.csproj 2>&1 | tail -12
cp /app/picogk.26.2.so bin/Release/net9.0/
export LD_LIBRARY_PATH=/opt/picogk-native/lib:\${LD_LIBRARY_PATH:-}
echo '=== RUN ==='
dotnet bin/Release/net9.0/M64Valvetrain.dll /out/m64-valvetrain-run $VOXEL_MM 2>&1 | tail -30
echo '=== LS ==='
ls -la /out/m64-valvetrain-run
"
# docker created $OUT.tmp as root-owned via the bind mount; move it into place.
mv "$OUT.tmp" "$OUT"
echo "OK: outputs in $OUT (layout proxies only; nothing measured, fitted, tested or released)."
