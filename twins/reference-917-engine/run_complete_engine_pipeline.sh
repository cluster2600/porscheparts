#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PARTS="${ROOT}/work/917-complete-engine/parts"
OUTPUT="${ROOT}/work/917-complete-engine/omniverse"
IMAGE="${SIMREADY_WORKFLOW_IMAGE:-ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41965aa48548481473a63f4d0277599b93cf4870d2e1f833099dd4e8e146d2f3}"

test -f "${ROOT}/work/917-complete-engine/cad-to-simready-preflight.json"
mkdir -p "${OUTPUT}/assets" "${OUTPUT}/stages" "${OUTPUT}/reports"

docker run --rm --platform linux/amd64 --entrypoint /bin/bash \
  -v "${ROOT}:/workspace" -w /workspace "${IMAGE}" -lc '
set -euo pipefail
jq -e '\''[.status, (.blockers | length)] == ["ready", 0]'\'' work/917-complete-engine/cad-to-simready-preflight.json >/dev/null
find work/917-complete-engine/parts/step -name "*.step" -print0 | \
  xargs -0 -n 1 -P 4 bash -c '\''
    step="$1"
    family="$(basename "${step}" .step)"
    output="work/917-complete-engine/omniverse/assets/${family}.usdc"
    test -f "${output}" && exit 0
    usd-convert-cad -i "${step}" -o "${output}" \
      --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
  '\'' _
/opt/simready-validation/bin/python \
  twins/reference-917-engine/source/build_complete_engine_usd.py \
  --config twins/reference-917-engine/complete-engine-f1.json \
  --parts-report work/917-complete-engine/parts/complete-engine-parts-report.json \
  --assets work/917-complete-engine/omniverse/assets \
  --output work/917-complete-engine/omniverse/stages/917-complete-engine-f1.usda
/opt/simready-validation/bin/python \
  twins/reference-917-engine/source/validate_complete_engine_usd.py \
  work/917-complete-engine/omniverse/stages/917-complete-engine-f1.usda \
  --config twins/reference-917-engine/complete-engine-f1.json \
  --report work/917-complete-engine/omniverse/reports/complete-engine-validation.json
'

echo "917 complete engine F1: ${OUTPUT}/stages/917-complete-engine-f1.usda"
