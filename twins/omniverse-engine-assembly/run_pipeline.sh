#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT="${ROOT}/work/omniverse-engine-assembly"
IMAGE="${SIMREADY_IMAGE:-ghcr.io/cluster2600/3dprinting993-simready@sha256:0562c69276c0d3065990cb9b1b8641dcd29355d0dccb9082dcf266fa2d22e90a}"

mkdir -p "${OUTPUT}/assets/valves" "${OUTPUT}/stages" "${OUTPUT}/reports"

docker run --rm --platform linux/amd64 --entrypoint /bin/bash \
  -v "${ROOT}:/workspace" -w /workspace "${IMAGE}" -lc '
set -euo pipefail
usd-convert-cad -i work/valve-variants-f1/993-intake-49-f1.step \
  -o work/omniverse-engine-assembly/assets/valves/993-intake-49-f1.usdc \
  --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
usd-convert-cad -i work/valve-variants-f1/993-carrera-exhaust-42_5-f1.step \
  -o work/omniverse-engine-assembly/assets/valves/993-carrera-exhaust-42_5-f1.usdc \
  --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
usd-convert-cad -i work/valve-variants-f1/993-turbo-exhaust-43_5-f1.step \
  -o work/omniverse-engine-assembly/assets/valves/993-turbo-exhaust-43_5-f1.usdc \
  --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
/opt/simready-validation/bin/python \
  twins/omniverse-engine-assembly/source/build_usd_assemblies.py \
  --project-root /workspace \
  --config /workspace/twins/omniverse-engine-assembly/assembly-f0.json \
  --output /workspace/work/omniverse-engine-assembly/stages
/opt/simready-validation/bin/python \
  twins/omniverse-engine-assembly/source/validate_usd_assemblies.py \
  /workspace/work/omniverse-engine-assembly/stages \
  --report /workspace/work/omniverse-engine-assembly/reports/composition-validation.json
'

echo "Omniverse F0 assemblies: ${OUTPUT}/stages"
