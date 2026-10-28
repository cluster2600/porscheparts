#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
test "${WM_PROJECT_VERSION:-}" = 13
test ! -e "$case_dir/log.checkMesh"
python3 - "$case_dir" <<'PYVERIFY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
record = json.loads((root / 'case-report.json').read_text())
for name, digest in record['case_hashes'].items():
    path = root / name
    if not path.resolve().is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('Changed restart input: ' + name)
PYVERIFY
checkMesh -case "$case_dir" -allGeometry -allTopology > "$case_dir/log.checkMesh" 2>&1
python3 "$case_dir/accept_mesh.py" "$case_dir" > "$case_dir/log.accept_mesh" 2>&1
decomposePar -case "$case_dir" -time 900 > "$case_dir/log.decomposePar" 2>&1
set +e
timeout --signal=TERM --kill-after=30s 1800 mpirun --bind-to none -np 4 \
    foamRun -case "$case_dir" -solver incompressibleFluid -parallel \
    > "$case_dir/log.parallelFoam" 2>&1
solver_status=$?
set -e
printf '%s\n' "$solver_status" > "$case_dir/solver-exit-code.txt"
reconstructPar -case "$case_dir" -latestTime > "$case_dir/log.reconstructPar" 2>&1
exit "$solver_status"
