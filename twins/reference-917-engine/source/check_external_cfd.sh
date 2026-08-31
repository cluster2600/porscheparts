#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 OPENFOAM_CASE" >&2
    exit 2
fi

CASE="$1"
set +u
# shellcheck disable=SC1091
source "/opt/openfoam${FOAM_VERSION:-13}/etc/bashrc"
set -u

blockMesh -case "${CASE}" | tee "${CASE}/blockMesh.log"
snappyHexMesh -overwrite -case "${CASE}" | tee "${CASE}/snappyHexMesh.log"
checkMesh -allGeometry -allTopology -case "${CASE}" | tee "${CASE}/checkMesh.log"
if grep -Eq 'Failed [1-9][0-9]* mesh checks' "${CASE}/checkMesh.log"; then
    echo "OpenFOAM mesh quality gate failed; solver execution is blocked." >&2
    exit 1
fi
