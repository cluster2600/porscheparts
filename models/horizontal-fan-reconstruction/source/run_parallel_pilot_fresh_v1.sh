#!/bin/bash
set -eo pipefail
source /opt/openfoam13/etc/bashrc
cd /case
python3 - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('independent-mesh-gate.json').read_text());p=json.loads(Path('reference-protocol.json').read_text())
if not r['accepted_for_bounded_pilot'] or not p['frozen_before_solver_launch']:raise ValueError('Mesh/protocol not admitted')
if Path('log.foamRun').exists() or Path('processor0').exists():raise ValueError('Fresh parallel case required')
PY
topoSet > log.topoSet 2>&1
decomposePar > log.decomposePar 2>&1
timeout --signal=TERM --kill-after=5 570 nice -n 10 mpirun --bind-to none --use-hwthread-cpus -np 4 foamRun -parallel > log.foamRun 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
