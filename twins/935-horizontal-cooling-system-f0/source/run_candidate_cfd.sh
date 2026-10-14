#!/usr/bin/env bash
# Run inside the qualified OpenCFD v2406 runtime with its environment sourced.
set -euo pipefail
test "$#" -eq 1
cd "$1"
test "${WM_PROJECT_VERSION:-}" = v2406
test ! -e solver.exit
for operation in 'surfaceCheck constant/triSurface/rotor.stl' blockMesh 'snappyHexMesh -overwrite' 'checkMesh -meshQuality' topoSet simpleFoam; do
    read -r -a command <<< "$operation"
    log="${command[0]}.log"
    if ! "${command[@]}" > "$log" 2>&1; then
        printf '1\n' > solver.exit
        exit 1
    fi
    if [[ "${command[0]}" == checkMesh ]] && ! grep -q 'Mesh OK\.' "$log"; then
        printf '2\n' > solver.exit
        exit 2
    fi
done
printf '0\n' > solver.exit
