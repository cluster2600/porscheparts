#!/usr/bin/env bash
set -eo pipefail

source /opt/openfoam14/etc/bashrc
set -u
export PATH="/opt/aate/bin:${PATH}"
export LD_LIBRARY_PATH="/opt/aate/lib:${LD_LIBRARY_PATH:-}"

test "${WM_PROJECT_VERSION}" = "14"
test "$(dpkg-query -W -f='${Version}' openfoam14)" = "20260724"
for executable in engineMeshConfig moveSurfaces predictRemeshInstants reorderPatchesAndFaces; do
    command -v "${executable}" >/dev/null
done
test -f /opt/aate/lib/libpreProcessing.so
test -f /opt/aate/lib/libsearchableSurfaces_w.so

smoke_root="$(mktemp -d /tmp/openfoam-engine-f35.XXXXXX)"
case "${smoke_root}" in
    /tmp/openfoam-engine-f35.*) ;;
    *) echo "unsafe smoke directory: ${smoke_root}" >&2; exit 2 ;;
esac

python3 /opt/openfoam-engine-f35/benchmark/generate_cases.py \
    --contract /opt/openfoam-engine-f35/benchmark/benchmark-contract-f25.json \
    --output "${smoke_root}/cases" >/dev/null

serial_case="${smoke_root}/cases/coarse"
blockMesh -case "${serial_case}" >"${smoke_root}/serial-blockMesh.log" 2>&1
checkMesh -case "${serial_case}" -allGeometry -allTopology >"${smoke_root}/serial-checkMesh.log" 2>&1
foamRun -solver incompressibleFluid -case "${serial_case}" >"${smoke_root}/serial-foamRun.log" 2>&1
grep -F "Mesh OK." "${smoke_root}/serial-checkMesh.log" >/dev/null
grep -F "End" "${smoke_root}/serial-foamRun.log" >/dev/null

mpi_case="${smoke_root}/cases/medium"
cat >"${mpi_case}/system/decomposeParDict" <<'EOF'
FoamFile
{
    format      ascii;
    class       dictionary;
    object      decomposeParDict;
}
numberOfSubdomains 2;
method simple;
simpleCoeffs
{
    n (1 2 1);
    delta 0.001;
}
EOF
blockMesh -case "${mpi_case}" >"${smoke_root}/mpi-blockMesh.log" 2>&1
decomposePar -case "${mpi_case}" >"${smoke_root}/mpi-decomposePar.log" 2>&1
mpirun --oversubscribe --np 2 \
    foamRun -solver incompressibleFluid -parallel -case "${mpi_case}" \
    >"${smoke_root}/mpi-foamRun.log" 2>&1
grep -F "End" "${smoke_root}/mpi-foamRun.log" >/dev/null
test -d "${mpi_case}/processor0/1"
test -d "${mpi_case}/processor1/1"

printf '%s\n' \
    '{"status":"passed_synthetic_serial_and_mpi_solver_smoke_only","openfoam_major":14,"openfoam_package_version":"20260724","mpi_ranks":2,"aate_utilities":4,"engine_simulation_proved":false,"performance_1600_hp_proved":false}'

rm -rf -- "${smoke_root}"
