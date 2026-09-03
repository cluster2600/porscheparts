#!/usr/bin/env bash
set -euo pipefail

case_root="${1:?usage: $0 CASE SOURCE_TIME RANKS}"
source_time="${2:?usage: $0 CASE SOURCE_TIME RANKS}"
ranks="${3:?usage: $0 CASE SOURCE_TIME RANKS}"
run_log="${case_root}/driver-recovered.log"
mesh_source="${case_root}/${source_time}/polyMesh"
mesh_backup="${case_root}/.recovered-snappy-polyMesh"

: "${WM_PROJECT_DIR:?source the matching OpenFOAM environment first}"

if [[ ! -d "${mesh_source}" ]]; then
  printf 'missing reconstructed mesh: %s\n' "${mesh_source}" >&2
  exit 64
fi
if ! grep -q 'head' "${mesh_source}/boundary"; then
  printf 'reconstructed mesh has no head patch: %s\n' "${mesh_source}" >&2
  exit 65
fi

cd "${case_root}"
rm -rf "${mesh_backup}"
cp -a "${mesh_source}" "${mesh_backup}"

{
  printf 'F36 recovered-mesh OpenFOAM start: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'host=%s ranks=%s case=%s source_time=%s\n' \
    "$(hostname)" "${ranks}" "${case_root}" "${source_time}"

  rm -rf processor[0-9]* "${case_root}/${source_time}" "${case_root}/postProcessing"
  rm -rf "${case_root}/constant/polyMesh"
  cp -a "${mesh_backup}" "${case_root}/constant/polyMesh"
  foamDictionary system/decomposeParDict \
    -entry numberOfSubdomains -set "${ranks}"

  decomposePar -case "${case_root}" -force > log.decomposePar-recovered 2>&1
  mpirun --allow-run-as-root -np "${ranks}" checkMesh -parallel \
    -case "${case_root}" > log.checkMesh-recovered-default 2>&1
  mpirun --allow-run-as-root -np "${ranks}" checkMesh -parallel \
    -case "${case_root}" -allGeometry -allTopology \
    > log.checkMesh-recovered-strict 2>&1 || true
  mpirun --allow-run-as-root -np "${ranks}" foamRun -parallel -solver fluid \
    -case "${case_root}" > log.fluid-recovered 2>&1
  reconstructPar -case "${case_root}" -latestTime \
    > log.reconstructPar-recovered 2>&1

  heat_file="${case_root}/postProcessing/headHeatFlux/0/wallHeatFlux.dat"
  if [[ ! -s "${heat_file}" ]] || [[ "$(wc -l < "${heat_file}")" -le 2 ]]; then
    printf 'head heat-flux evidence is empty: %s\n' "${heat_file}" >&2
    exit 66
  fi
  printf 'F36 recovered-mesh OpenFOAM end: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${run_log}" 2>&1
