#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
test "${WM_PROJECT_VERSION:-}" = 13
test ! -e "$case_dir/log.checkMesh"
: "${CAMPAIGN_DEADLINE_EPOCH:?A guarded rental or local rehearsal deadline is required}"
[[ "$CAMPAIGN_DEADLINE_EPOCH" =~ ^[0-9]+$ ]]
read -r ranks checkpoint seconds < <(python3 - "$case_dir" <<'PY'
import hashlib, json, re, sys
from pathlib import Path
root = Path(sys.argv[1])
record = json.loads((root / 'case-report.json').read_text())
for name, digest in record['case_hashes'].items():
    path = root / name
    if not path.resolve().is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit('Changed cloud restart input: ' + name)
ranks, checkpoint, seconds = (record[k] for k in ('parallel_ranks', 'start_iteration', 'maximum_solver_seconds'))
if (type(ranks) is not int or ranks not in (4, 8, 16, 32)
        or type(checkpoint) is not int or checkpoint < 0
        or type(seconds) is not int or not 60 <= seconds <= 7200
        or record['residual_target'] != 1e-5):
    raise SystemExit('Invalid bounded cloud controls')
decomposition = (root / 'system/decomposeParDict').read_text()
if re.findall(r'\bnumberOfSubdomains\s+(\d+)\s*;', decomposition) != [str(ranks)]:
    raise SystemExit('MPI rank mismatch')
print(ranks, checkpoint, seconds)
PY
)
test "$((CAMPAIGN_DEADLINE_EPOCH - $(date +%s)))" -gt 360
foamRun -help > "$case_dir/log.runtime" 2>&1
checkMesh -case "$case_dir" -allGeometry -allTopology > "$case_dir/log.checkMesh" 2>&1
python3 "$case_dir/accept_mesh.py" "$case_dir" > "$case_dir/log.accept_mesh" 2>&1
decomposePar -case "$case_dir" -time "$checkpoint" > "$case_dir/log.decomposePar" 2>&1
remaining=$((CAMPAIGN_DEADLINE_EPOCH - $(date +%s) - 300))
test "$remaining" -ge 60
if ((seconds > remaining)); then seconds=$remaining; fi
set +e
timeout --signal=TERM --kill-after=30s "$seconds" mpirun --bind-to none -np "$ranks" \
    foamRun -case "$case_dir" -solver incompressibleFluid -parallel \
    > "$case_dir/log.parallelFoam" 2>&1
solver_status=$?
printf '%s\n' "$solver_status" > "$case_dir/solver-exit-code.txt"
timeout --signal=TERM --kill-after=10s 240 reconstructPar -case "$case_dir" -latestTime \
    > "$case_dir/log.reconstructPar" 2>&1
reconstruction_status=$?
printf '%s\n' "$reconstruction_status" > "$case_dir/reconstruction-exit-code.txt"
set -e
if ((solver_status != 0)); then exit "$solver_status"; fi
exit "$reconstruction_status"
