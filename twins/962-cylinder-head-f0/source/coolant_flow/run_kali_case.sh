#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
test "${WM_PROJECT_VERSION:-}" = 13 || { echo 'Source the verified Foundation-13 environment first' >&2; exit 2; }
test ! -e "$case_dir/log.gmshToFoam" || { echo 'Case already attempted; prepare a fresh directory' >&2; exit 2; }
gmshToFoam -case "$case_dir" "$case_dir/coolant.msh" > "$case_dir/log.gmshToFoam" 2>&1
createPatch -case "$case_dir" -dict "$case_dir/system/wallTypeStage1" -overwrite > "$case_dir/log.wallType1" 2>&1
createPatch -case "$case_dir" -dict "$case_dir/system/wallTypeStage2" -overwrite > "$case_dir/log.wallType2" 2>&1
checkMesh -case "$case_dir" -allGeometry -allTopology > "$case_dir/log.checkMesh" 2>&1
python3 "$case_dir/accept_mesh.py" "$case_dir" > "$case_dir/log.accept_mesh" 2>&1
decomposePar -case "$case_dir" > "$case_dir/log.decomposePar" 2>&1
timeout 1800 mpirun --bind-to core -np 4 foamRun -case "$case_dir" -solver incompressibleFluid -parallel > "$case_dir/log.simpleFoam" 2>&1
reconstructPar -case "$case_dir" -latestTime > "$case_dir/log.reconstructPar" 2>&1
