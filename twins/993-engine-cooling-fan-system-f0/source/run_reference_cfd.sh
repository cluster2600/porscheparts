#!/bin/bash
set -e
[[ $# == 1 && -f "$1/system/controlDict" ]] || { echo "Usage: run_reference_cfd.sh new-prepared-case"; exit 2; }
[[ ! -e "$1/log.foamRun" && ! -e "$1/log.snappyHexMesh" ]] || { echo "Existing run: preserve evidence and prepare a new case"; exit 2; }
source /opt/openfoam14/etc/bashrc
cd "$1"
blockMesh > log.blockMesh 2>&1
snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
checkMesh > log.checkMesh-standard 2>&1
checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
if ! grep -q 'Mesh OK.' log.checkMesh-standard; then echo 'MESH REJECTED'; exit 2; fi
if ! grep -q 'Mesh OK.' log.checkMesh; then echo 'Exploratory run only: extended mesh checks failed; see log.checkMesh'; fi
topoSet > log.topoSet 2>&1
decomposePar > log.decomposePar 2>&1
mpirun --allow-run-as-root -np 4 foamRun -parallel > log.foamRun 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
