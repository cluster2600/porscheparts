#!/usr/bin/env bash
set -eo pipefail
source /opt/openfoam14/etc/bashrc
set -u
export PATH="/opt/aate/bin:${PATH}"
export LD_LIBRARY_PATH="/opt/aate/lib:${LD_LIBRARY_PATH:-}"
test "${WM_PROJECT_VERSION}" = "14"
test "$(dpkg-query -W -f='${Version}' openfoam14)" = "20260724"

root=$(mktemp -d /tmp/f47-openfoam.XXXXXX)
case "${root}" in /tmp/f47-openfoam.*) ;; *) exit 90 ;; esac
trap 'rm -rf -- "${root}"' EXIT
python3 /opt/917-f47-cfd-cae/benchmark/generate_cases.py \
    --contract /opt/917-f47-cfd-cae/benchmark/benchmark-contract-f25.json \
    --output "${root}/cases" >/dev/null

serial=${root}/cases/coarse
blockMesh -case "${serial}" >"${root}/blockMesh.log" 2>&1
checkMesh -case "${serial}" -allGeometry -allTopology >"${root}/checkMesh.log" 2>&1
foamRun -solver incompressibleFluid -case "${serial}" >"${root}/foamRun.log" 2>&1
grep -F 'Mesh OK.' "${root}/checkMesh.log" >/dev/null
grep -F 'End' "${root}/foamRun.log" >/dev/null

for utility in engineMeshConfig moveSurfaces predictRemeshInstants reorderPatchesAndFaces; do
    command -v "${utility}" >/dev/null
    set +e
    "${utility}" -help >"${root}/${utility}.stdout" 2>"${root}/${utility}.stderr"
    status=$?
    set -e
    test "${status}" -le 1
    grep -E '(Usage|usage|OpenFOAM|Options)' "${root}/${utility}.stdout" "${root}/${utility}.stderr" >/dev/null
done

printf '%s\n' '{"openfoam":"14-20260724","solver":"incompressibleFluid","serial_case_passed":true,"aate_revision":"c0f75f953d67cd325d28d1300672d14288f22934","aate_help_invocations":4,"synthetic_fixture":true}'
