#!/bin/bash
# Convert and audit only. A failed extended check is never a solver handoff.
set -eo pipefail
if [ "$#" -ne 2 ]; then
    echo 'Usage: run_quality_mesh_qa.sh absolute-fluid.msh new-case-directory' >&2
    exit 1
fi
mesh="$1"
case_directory="$2"
test -f "$mesh"
test ! -e "$case_directory"
source "${OPENFOAM_ROOT:-/opt/openfoam13}/etc/bashrc"
mkdir -p "$case_directory/system"
cd "$case_directory"
cat > system/controlDict <<'FOAM'
FoamFile { format ascii; class dictionary; object controlDict; }
application foamRun;
startFrom startTime; startTime 0; stopAt endTime; endTime 0; deltaT 1;
writeControl timeStep; writeInterval 1;
FOAM
gmshToFoam "$mesh" > log.gmshToFoam 2>&1
checkMesh > log.checkMesh-standard 2>&1
checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
if ! grep -q 'Mesh OK' log.checkMesh-standard || ! grep -q 'Mesh OK' log.checkMesh; then
    echo 'Mesh rejected by independent standard/extended checks; no flow solver permitted' >&2
    exit 2
fi
echo 'Standard and extended mesh checks passed; convergence and wall-resolution gates remain open'
