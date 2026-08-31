#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $0 INPUT_MSH CASE_DIRECTORY" >&2
    exit 2
fi

INPUT_MSH="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
CASE_DIRECTORY="$2"
mkdir -p "${CASE_DIRECTORY}/system"

cat > "${CASE_DIRECTORY}/system/controlDict" <<'EOF'
FoamFile
{
    format      ascii;
    class       dictionary;
    object      controlDict;
}
application     foamRun;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
EOF

# shellcheck disable=SC1091
source "/opt/openfoam${FOAM_VERSION:-13}/etc/bashrc"
gmshToFoam "${INPUT_MSH}" -case "${CASE_DIRECTORY}"
checkMesh -allGeometry -allTopology -case "${CASE_DIRECTORY}" \
    | tee "${CASE_DIRECTORY}/checkMesh.log"
