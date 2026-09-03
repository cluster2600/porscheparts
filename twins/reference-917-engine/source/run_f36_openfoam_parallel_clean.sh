#!/usr/bin/env bash
set -euo pipefail

case_root="${1:?usage: $0 CASE RANKS}"
ranks="${2:?usage: $0 CASE RANKS}"
run_log="${case_root}/driver-parallel-clean.log"

: "${WM_PROJECT_DIR:?source the matching OpenFOAM environment first}"
cd "${case_root}"

{
  printf 'F36 clean parallel OpenFOAM start: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'host=%s ranks=%s case=%s\n' "$(hostname)" "${ranks}" "${case_root}"
  foamDictionary system/decomposeParDict \
    -entry numberOfSubdomains -set "${ranks}"

  rm -rf processor[0-9]* postProcessing constant/polyMesh
  blockMesh -case "${case_root}" > log.clean.blockMesh 2>&1
  decomposePar -case "${case_root}" -force > log.clean.decomposePar-mesh 2>&1
  mpirun --allow-run-as-root -np "${ranks}" snappyHexMesh -parallel -overwrite \
    -case "${case_root}" > log.clean.snappyHexMesh 2>&1

  if ! grep -q 'head' processor0/constant/polyMesh/boundary; then
    printf 'parallel snappy mesh has no head patch\n' >&2
    exit 64
  fi
  reconstructPar -case "${case_root}" -constant > log.clean.reconstructParMesh 2>&1
  if ! grep -q 'head' constant/polyMesh/boundary; then
    printf 'reconstructed constant mesh has no head patch\n' >&2
    exit 65
  fi

  rm -rf processor[0-9]*
  decomposePar -case "${case_root}" -force > log.clean.decomposePar-final 2>&1
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
  printf 'F36 clean parallel OpenFOAM end: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${run_log}" 2>&1
