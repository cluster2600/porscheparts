#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 OUTPUT_ROOT" >&2
  exit 2
fi

output_root="$1"
for case_name in coarse fine; do
  case_dir="${output_root}/openfoam-cases/${case_name}"
  (
    cd "${case_dir}"
    blockMesh > log.blockMesh 2>&1
    checkMesh > log.checkMesh 2>&1
    foamRun -solver fluid > log.foamRun 2>&1
    postProcess -func sampleDict -latestTime > log.sample 2>&1
  )
done
