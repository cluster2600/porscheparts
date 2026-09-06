#!/usr/bin/env bash
# Run inside the pre-existing OpenFOAM14 image, with a fresh /output mount.
# Runtime smoke test only; not an M64 cylinder-head simulation or convergence study.
set -eo pipefail
source /opt/openfoam14/etc/bashrc
test ! -e /output/case
cp -a "$FOAM_TUTORIALS/multiRegion/CHT/circuitBoardCooling" /output/case
cd /output/case
foamDictionary system/controlDict -entry endTime -set 20
foamDictionary system/controlDict -entry writeInterval -set 20
if [[ ${1:-} == repair-relaxation ]]; then
    # Bundled tutorial has obsolete flat relaxation syntax. Preserve all
    # original factors, but place them in OF14's fields/equations dictionaries.
    foamDictionary system/fluid/fvSolution -entry relaxationFactors -set \
        '{ fields { rho 1.0; p_rgh 0.7; } equations { U 0.3; h 0.7; "(k|epsilon|omega)" 0.3; } }'
fi
./Allmesh-extrudeFromInternalFaces > log.Allmesh 2>&1
# RunFunctions does not necessarily propagate a child failure: verify meshes.
checkMesh -region fluid > log.checkMesh-fluid 2>&1
checkMesh -region baffle3D > log.checkMesh-solid 2>&1
foamMultiRun > log.foamMultiRun 2>&1
grep -q '^[[:space:]]*End[[:space:]]*$' log.foamMultiRun
test -s 20/fluid/T
test -s 20/baffle3D/T
sha256sum system/controlDict constant/fluid/physicalProperties \
    20/fluid/T 20/baffle3D/T log.foamMultiRun > smoke-sha256.txt
printf '%s\n' 'CHT_RUNTIME_SMOKE_COMPLETED_NOT_ENGINE_VALIDATION'
