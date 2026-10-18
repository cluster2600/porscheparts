#!/bin/sh
# Build and run the filleted coupon on the Linux host stack (~/picogk), one case per call,
# under a memory cap. Writes the native output plus a runtime record next to it.
# usage: run.sh BUILD_DIR OUTPUT_DIR VOXEL_MM RADIUS_MM [MEMORY_CAP]
set -eu
build=$1; out=$2; voxel=$3; radius=$4; cap=${5:-6G}
here=$(cd "$(dirname "$0")" && pwd); repo=$(cd "$here/../../../../../.." && pwd)
study="$repo/twins/993-intercooler/750-hp/hot-weather/results/study.json"
. "$HOME/picogk/env.sh"
if [ ! -f "$build/bin/CouponFillet.dll" ]; then
  mkdir -p "$build/src"; cp "$here/Program.cs" "$here/CouponFillet.csproj" "$build/src/"
  (cd "$build/src" && dotnet build -c Release -o "$build/bin" >"$build/build.log" 2>&1)
fi
cmp -s "$here/Program.cs" "$build/src/Program.cs" && cmp -s "$here/CouponFillet.csproj" "$build/src/CouponFillet.csproj" || { echo "build is stale" >&2; exit 2; }
"$HOME/picogk/run-capped.sh" -m "$cap" dotnet "$build/bin/CouponFillet.dll" "$study" "$out" "$voxel" "$radius" >"$build/$(basename "$out").stdout" 2>&1
commit() { git -C "$HOME/picogk/$1" rev-parse HEAD; }
cat >"$out/runtime.json" <<EOF
{
  "host": "WSL2 Linux, user-space LEAP 71 stack in ~/picogk",
  "picogk_commit": "$(commit PicoGK)",
  "picogk_runtime_commit": "$(cat "$HOME/picogk/native/RUNTIME_COMMIT")",
  "shapekernel_commit": "$(commit LEAP71_ShapeKernel)",
  "shapekernel_locked_commit_note": "containers/m64-leap71/sources.lock pins ShapeKernel 7b90978; this host checkout is newer",
  "latticelibrary_commit": "$(commit LEAP71_LatticeLibrary)",
  "latticelibrary_locked": false,
  "dotnet_sdk": "$(dotnet --version)",
  "native_runtime_sha256": "$(sha256sum "$HOME/picogk/native/picogk.26.2.so" | cut -d' ' -f1)",
  "application_sha256": "$(sha256sum "$build/bin/CouponFillet.dll" | cut -d' ' -f1)",
  "program_sha256": "$(sha256sum "$here/Program.cs" | cut -d' ' -f1)",
  "project_sha256": "$(sha256sum "$here/CouponFillet.csproj" | cut -d' ' -f1)",
  "memory_cap": "$cap"
}
EOF
