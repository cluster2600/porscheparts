#!/usr/bin/env bash
# Prescribed reference only; run in pinned ESI v2312 with a fresh writable /work.
source /usr/lib/openfoam/openfoam2312/etc/bashrc >/dev/null 2>&1
export LD_LIBRARY_PATH="$FOAM_LIBBIN:$LD_LIBRARY_PATH"
set -e
case=/work/case
cp -r "$FOAM_TUTORIALS/heatTransfer/chtMultiRegionFoam/multiRegionHeater" "$case"
python3 - <<'PYMESH'
from pathlib import Path
p=Path('/work/case/system/blockMeshDict'); s=p.read_text(); assert '(30 10 10)' in s; p.write_text(s.replace('(30 10 10)','(30 20 20)'))
PYMESH
foamDictionary "$case/system/controlDict" -entry startFrom -set startTime >/dev/null
foamDictionary "$case/system/controlDict" -entry startTime -set 0 >/dev/null
foamDictionary "$case/system/controlDict" -entry endTime -set 0.005 >/dev/null
foamDictionary "$case/system/controlDict" -entry adjustTimeStep -set no >/dev/null
foamDictionary "$case/system/controlDict" -entry writeControl -set timeStep >/dev/null
foamDictionary "$case/system/controlDict" -entry writeInterval -set 1 >/dev/null
foamDictionary "$case/system/controlDict" -entry functions -remove >/dev/null
(cd "$case" && bash ./Allrun.pre >preparation.log 2>&1)
checkMesh -case "$case" -allRegions -allTopology -allGeometry >"$case/checkMesh.log" 2>&1
test "$(grep -c 'Mesh OK.' "$case/checkMesh.log")" -eq 5
chtMultiRegionFoam -case "$case" >"$case/solver.log" 2>&1
python3 - <<'PY'
import hashlib,json,math,pathlib,re
case=pathlib.Path('/work/case'); log=(case/'solver.log').read_text()
times=[float(t) for t in re.findall(r'^Time = (\S+)',log,re.M)]
assert times and math.isclose(times[-1],0.005,abs_tol=1e-10)
assert re.search(r'^End\s*$',log,re.M) and not re.search(r'^\s*(?:-->\s*)?FOAM FATAL(?: IO)? ERROR',log,re.M)
mesh=(case/'checkMesh.log').read_text(); assert mesh.count('Mesh OK.')==5
checks={}
for region in ('bottomWater','topAir','heater','leftSolid','rightSolid'):
    text=(case/'0.005'/region/'T').read_text()
    assert not re.search(r'\b(?:nan|inf)\b',text,re.I)
    checks[region]={'mesh_ok':True,'temperature_field_written':True,'temperature_sha256':hashlib.sha256(text.encode()).hexdigest()}
receipt={'application':'chtMultiRegionFoam','distribution':'ESI','version':'2312','tutorial':'multiRegionHeater','deltaT':0.001,'endTime':0.005,'steps':len(times),'regions':checks,'solver_completed':True,'energy_balance_verified':False,'mesh_convergence_verified':False,'generated_by_qwen':False,'physical_validation':False,'solver_log_sha256':hashlib.sha256(log.encode()).hexdigest()}
pathlib.Path('/work/receipt.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(json.dumps(receipt))
PY
