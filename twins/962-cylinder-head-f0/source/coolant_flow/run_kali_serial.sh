#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$1" && pwd)"
test "${WM_PROJECT_VERSION:-}" = 13
test ! -e "$case_dir/log.gmshToFoam"
python3 - "$case_dir" <<'PYVERIFY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);record=json.loads((root/'case-report.json').read_text())
for name,digest in record['case_hashes'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Case input changed: '+name)
PYVERIFY
gmshToFoam -case "$case_dir" "$case_dir/coolant.msh" > "$case_dir/log.gmshToFoam" 2>&1
createPatch -case "$case_dir" -dict "$case_dir/system/wallTypeStage1" -overwrite > "$case_dir/log.wallType1" 2>&1
createPatch -case "$case_dir" -dict "$case_dir/system/wallTypeStage2" -overwrite > "$case_dir/log.wallType2" 2>&1
checkMesh -case "$case_dir" -allGeometry -allTopology > "$case_dir/log.checkMesh" 2>&1
python3 "$case_dir/accept_mesh.py" "$case_dir" > "$case_dir/log.accept_mesh" 2>&1
# The host MPI launcher fails its own version check; serial needs no host repair.
timeout --signal=TERM --kill-after=30s 1800 foamRun -case "$case_dir" -solver incompressibleFluid > "$case_dir/log.serialFoam" 2>&1
