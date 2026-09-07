#!/usr/bin/env bash
set -euo pipefail
# OpenFOAM initialization references optional unset variables.
set +u
source /opt/openfoam14/etc/bashrc
source /work/AdditiveFOAM/etc/bashrc
set -u
export PATH="/work/user-openfoam/platforms/linux64GccDPInt32Opt/bin:$PATH"
export LD_LIBRARY_PATH="/work/user-openfoam/platforms/linux64GccDPInt32Opt/lib:${LD_LIBRARY_PATH:-}"
case_path="$1"
timeout 600 additiveFoam -case "$case_path" > "$case_path/diagnostic-run.log" 2>&1
foamToVTK -case "$case_path" -latestTime -ascii -fields '(T alpha.solid)' > "$case_path/vtk-export.log" 2>&1
