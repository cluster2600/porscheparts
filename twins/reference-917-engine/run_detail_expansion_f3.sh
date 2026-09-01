#!/usr/bin/env bash
# Construit 13 familles détaillées et les compose au-dessus d'un stage F2 validé.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 INPUT_F2_USD" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INPUT_F2="$1"
OUTPUT="${ROOT}/work/917-detail-expansion-f3"
MESH_IMAGE="${MESH_IMAGE:-ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f}"
SIMREADY_IMAGE="${SIMREADY_WORKFLOW_IMAGE:-ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41965aa48548481473a63f4d0277599b93cf4870d2e1f833099dd4e8e146d2f3}"

test -f "${INPUT_F2}"
mkdir -p "${OUTPUT}/parts" "${OUTPUT}/assets" "${OUTPUT}/stages" "${OUTPUT}/reports"

docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python \
    -v "${ROOT}:/workspace" -w /workspace "${MESH_IMAGE}" \
    twins/reference-917-engine/source/build_detail_expansion_f3.py \
    --config twins/reference-917-engine/detail-expansion-f3.json \
    --output work/917-detail-expansion-f3/parts

docker run --rm --platform linux/amd64 --entrypoint /bin/bash \
    -v "${ROOT}:/workspace" -w /workspace "${SIMREADY_IMAGE}" -lc "
set -euo pipefail
find work/917-detail-expansion-f3/parts/step -name '*.step' -print0 | \\
  xargs -0 -n 1 -P 4 bash -c '
    step=\"\$1\"
    family=\"\$(basename \"\${step}\" .step)\"
    usd-convert-cad -i \"\${step}\" -o \"work/917-detail-expansion-f3/assets/\${family}.usdc\" \\
      --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
  ' _
/opt/simready-validation/bin/python twins/reference-917-engine/source/build_detail_expansion_usd_f3.py \\
  \"${INPUT_F2}\" \\
  --config twins/reference-917-engine/detail-expansion-f3.json \\
  --parts-report work/917-detail-expansion-f3/parts/detail-expansion-f3-report.json \\
  --assets work/917-detail-expansion-f3/assets \\
  --output work/917-detail-expansion-f3/stages/917-engine-detail-f3.usda
/opt/simready-validation/bin/python twins/reference-917-engine/source/validate_detail_expansion_f3.py \\
  work/917-detail-expansion-f3/stages/917-engine-detail-f3.usda \\
  --config twins/reference-917-engine/detail-expansion-f3.json \\
  --report work/917-detail-expansion-f3/reports/detail-expansion-validation.json
"

printf '%s\n' "${OUTPUT}/stages/917-engine-detail-f3.usda"
