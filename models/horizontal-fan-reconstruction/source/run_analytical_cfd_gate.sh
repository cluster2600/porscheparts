#!/bin/bash
# Conversion and independent extended checks only; never starts a flow solver.
set -eo pipefail
source /opt/openfoam13/etc/bashrc
cd /case
test ! -e log.gmshToFoam
gmshToFoam volume.msh > log.gmshToFoam 2>&1
python3 - <<'PY'
from pathlib import Path
import re
path=Path('constant/polyMesh/boundary');text=path.read_text()
for name in ('rotor','shroud'):
    expression=r'(\b'+name+r'\s*\{[^}]*?\btype\s+)patch(\s*;)'
    text,count=re.subn(expression,r'\1wall\2',text)
    if count!=1:raise ValueError('Expected exactly one patch named '+name)
path.write_text(text)
PY
checkMesh > log.checkMesh-standard 2>&1
checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
python3 - <<'PY'
import hashlib,json,re
from pathlib import Path
names=['log.checkMesh-standard','log.checkMesh'];result={}
for name in names:
    text=Path(name).read_text();failed=re.search(r'Failed\s+(\d+)\s+mesh checks',text)
    result[name]={'Mesh_OK':'Mesh OK' in text,'failed_checks':int(failed[1]) if failed else 0,
                  'sha256':hashlib.sha256(Path(name).read_bytes()).hexdigest()}
accepted=all(v['Mesh_OK'] and v['failed_checks']==0 for v in result.values())
Path('independent-mesh-gate.json').write_text(json.dumps({'accepted_for_bounded_pilot':accepted,'checks':result,'flow_solver_launched':False,'wall_resolution_and_grid_independence_established':False},indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if accepted else 2)
PY
