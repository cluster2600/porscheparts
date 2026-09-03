#!/usr/bin/env bash
set -euo pipefail

case_root="${1:?usage: $0 CASE RANKS}"
ranks="${2:?usage: $0 CASE RANKS}"
run_log="${case_root}/driver.log"

: "${WM_PROJECT_DIR:?source the matching OpenFOAM environment first}"
cd "${case_root}"

{
  printf 'F36 OpenFOAM start: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'host=%s ranks=%s case=%s\n' "$(hostname)" "${ranks}" "${case_root}"
  foamDictionary system/decomposeParDict \
    -entry numberOfSubdomains -set "${ranks}"

  # snappyHexMesh creates `head` in the processor meshes. OpenFOAM 13 has
  # superseded reconstructParMesh, so reconstruct the final constant mesh with
  # reconstructPar before distributing both mesh and 0/ fields again.
  if grep -q 'Finished meshing without any errors' log.snappyHexMesh 2>/dev/null \
      && grep -q 'head' processor0/constant/polyMesh/boundary 2>/dev/null; then
    reconstructPar -case "${case_root}" -constant > log.reconstructParMesh 2>&1
  else
    rm -rf processor[0-9]*
    blockMesh -case "${case_root}" > log.blockMesh 2>&1
    decomposePar -case "${case_root}" -force > log.decomposePar-mesh 2>&1
    mpirun --allow-run-as-root -np "${ranks}" snappyHexMesh -parallel \
      -case "${case_root}" > log.snappyHexMesh 2>&1
    reconstructPar -case "${case_root}" -constant > log.reconstructParMesh 2>&1
  fi

  if ! grep -q 'head' constant/polyMesh/boundary; then
    echo 'FATAL: reconstructed mesh has no head patch' >&2
    exit 64
  fi

  rm -rf processor[0-9]*
  decomposePar -case "${case_root}" -force > log.decomposePar-final 2>&1
  mpirun --allow-run-as-root -np "${ranks}" checkMesh -parallel \
    -case "${case_root}" > log.checkMesh-default 2>&1
  mpirun --allow-run-as-root -np "${ranks}" checkMesh -parallel \
    -case "${case_root}" -allGeometry -allTopology \
    > log.checkMesh-strict 2>&1 || true
  mpirun --allow-run-as-root -np "${ranks}" foamRun -parallel -solver fluid \
    -case "${case_root}" > log.fluid 2>&1
  reconstructPar -case "${case_root}" -latestTime > log.reconstructPar 2>&1
  printf 'F36 OpenFOAM end: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${run_log}" 2>&1
