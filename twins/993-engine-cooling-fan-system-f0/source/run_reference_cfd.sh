#!/bin/bash
set -e
[[ $# -ge 1 && $# -le 2 && -f "$1/system/controlDict" ]] || { echo "Usage: run_reference_cfd.sh new-prepared-case [conforming-mesh.msh|--existing-mesh]"; exit 2; }
mesh=""
if [[ $# == 2 ]]; then
 if [[ "$2" == --existing-mesh ]]; then
  mesh=existing
 else
 [[ -f "$2" ]] || { echo "Missing conforming mesh"; exit 2; }
 mesh="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
 fi
fi
[[ ! -e "$1/log.foamRun" && ! -e "$1/log.snappyHexMesh" ]] || { echo "Existing run: preserve evidence and prepare a new case"; exit 2; }
source /opt/openfoam14/etc/bashrc
source_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$1"
if [[ -n "$mesh" ]]; then
 if [[ "$mesh" == existing ]]; then
  [[ -f constant/polyMesh/boundary ]] || { echo "Missing existing mesh"; exit 2; }
 else
 [[ ! -e log.convert ]] || { echo "Existing mesh conversion: preserve evidence"; exit 2; }
 gmshToFoam "$mesh" > log.convert 2>&1
 fi
 python3 - <<'PYTHON'
from pathlib import Path
import re
p = Path("constant/polyMesh/boundary")
s = p.read_text()
for patch in ("rotor", "duct"):
    s, count = re.subn(r"(" + patch + r"\s*\{\s*type\s+)(?:patch|wall);", r"\1wall;", s)
    if count != 1:
        raise ValueError("Expected exactly one imported wall patch: " + patch)
p.write_text(s)
PYTHON
else
 blockMesh > log.blockMesh 2>&1
 snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
fi
checkMesh > log.checkMesh-standard 2>&1
checkMesh -allGeometry -allTopology -writeSets -writeSurfaces > log.checkMesh 2>&1
if ! grep -Fxq 'Mesh OK.' log.checkMesh-standard; then echo 'MESH REJECTED'; exit 2; fi
if ! grep -Fxq 'Mesh OK.' log.checkMesh; then echo 'MESH REJECTED: extended checks failed; see log.checkMesh'; exit 2; fi
topoSet > log.topoSet 2>&1
(cd "$source_dir/audit_fan_mrf_interface" && wmake) > log.mrf-audit-build 2>&1
if ! auditFanMRFInterface > log.mrf-interface 2>&1; then
 echo 'MRF REJECTED: see log.mrf-interface'; exit 2
fi
decomposePar > log.decomposePar 2>&1
ranks=$(foamDictionary system/decomposeParDict -entry numberOfSubdomains -value)
[[ "$ranks" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid processor count"; exit 2; }
mpirun --allow-run-as-root -np "$ranks" foamRun -parallel > log.foamRun 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
