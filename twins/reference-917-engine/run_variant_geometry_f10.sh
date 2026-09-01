#!/usr/bin/env bash
# Produit deux branches F10 distinctes : Type 912 85x66 et 917/30 90x70,4.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_REL="${F10_OUTPUT_REL:-work/917-variant-geometry-f10}"
MANIFEST_REL="twins/reference-917-engine/variant-configurations-f10.json"
PREFLIGHT_REL="${F10_PREFLIGHT_REL:-work/917-complete-engine/cad-to-simready-preflight.json}"
MESH_IMAGE="${MESH_IMAGE:-ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f}"
SIMREADY_IMAGE="${SIMREADY_WORKFLOW_IMAGE:-ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41965aa48548481473a63f4d0277599b93cf4870d2e1f833099dd4e8e146d2f3}"

if ! OUTPUT="$(python3 - "${ROOT}" "${OUTPUT_REL}" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
work_root = (root / "work").resolve()
candidate = (root / sys.argv[2]).resolve()
if candidate == work_root or not candidate.is_relative_to(work_root):
    print("F10_OUTPUT_REL doit se resoudre dans un sous-repertoire de work/", file=sys.stderr)
    raise SystemExit(2)
print(candidate)
PY
)"; then
  exit 2
fi
OUTPUT_REL="${OUTPUT#"${ROOT}/"}"

if [ -e "${OUTPUT}" ]; then
  echo "Refus F10 : le repertoire de sortie existe deja : ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${ROOT}/work"
LOCK_DIR="${ROOT}/work/.917-variant-geometry-f10.lock"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Refus F10 : une autre generation detient ${LOCK_DIR}" >&2
  exit 2
fi
cleanup_lock() {
  rmdir "${LOCK_DIR}" 2>/dev/null || true
}
trap cleanup_lock EXIT INT TERM

test -f "${ROOT}/${PREFLIGHT_REL}"
jq -e '[.status, (.blockers | length)] == ["ready", 0]' "${ROOT}/${PREFLIGHT_REL}" >/dev/null
mkdir "${OUTPUT}"

python3 "${ROOT}/twins/reference-917-engine/source/prepare_variant_configs_f10.py" \
  --manifest "${ROOT}/${MANIFEST_REL}" \
  --project-root "${ROOT}" \
  --output "${OUTPUT}"

COMMON_F3_REL="${OUTPUT_REL}/common-f3"
mkdir -p "${ROOT}/${COMMON_F3_REL}/parts" "${ROOT}/${COMMON_F3_REL}/assets"
docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python \
  -v "${ROOT}:/workspace" -w /workspace "${MESH_IMAGE}" \
  twins/reference-917-engine/source/build_detail_expansion_f3.py \
  --config twins/reference-917-engine/detail-expansion-f3.json \
  --output "${COMMON_F3_REL}/parts"

docker run --rm --platform linux/amd64 --entrypoint /bin/bash \
  -e F10_COMMON_F3_REL="${COMMON_F3_REL}" -e F10_PREFLIGHT_REL="${PREFLIGHT_REL}" \
  -v "${ROOT}:/workspace" -w /workspace "${SIMREADY_IMAGE}" -lc '
set -euo pipefail
jq -e '\''[.status, (.blockers | length)] == ["ready", 0]'\'' "${F10_PREFLIGHT_REL}" >/dev/null
twins/reference-917-engine/source/convert_step_directory_f10.sh \
  "${F10_COMMON_F3_REL}/parts/step" "${F10_COMMON_F3_REL}/assets" 4
'

jq -r '.variants[] | [.variant_id, .output_slug] | @tsv' "${ROOT}/${MANIFEST_REL}" | \
while IFS=$'\t' read -r variant_id slug; do
  variant_rel="${OUTPUT_REL}/${slug}"
  config_rel="${variant_rel}/configs"
  parts_rel="${variant_rel}/parts"
  assets_rel="${variant_rel}/assets"
  stages_rel="${variant_rel}/stages"
  reports_rel="${variant_rel}/reports"
  mkdir -p "${ROOT}/${parts_rel}" "${ROOT}/${assets_rel}" "${ROOT}/${stages_rel}" "${ROOT}/${reports_rel}"

  docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python \
    -v "${ROOT}:/workspace" -w /workspace "${MESH_IMAGE}" \
    twins/reference-917-engine/source/build_variant_engine_parts_f10.py \
    --config "${config_rel}/complete-engine-f10.json" \
    --output "${parts_rel}"

  docker run --rm --platform linux/amd64 --entrypoint /bin/bash \
    -e F10_VARIANT="${variant_id}" -e F10_SLUG="${slug}" \
    -e F10_VARIANT_REL="${variant_rel}" -e F10_COMMON_F3_REL="${COMMON_F3_REL}" \
    -v "${ROOT}:/workspace" -w /workspace "${SIMREADY_IMAGE}" -lc '
set -euo pipefail
config_rel="${F10_VARIANT_REL}/configs"
parts_rel="${F10_VARIANT_REL}/parts"
assets_rel="${F10_VARIANT_REL}/assets"
stages_rel="${F10_VARIANT_REL}/stages"
reports_rel="${F10_VARIANT_REL}/reports"
twins/reference-917-engine/source/convert_step_directory_f10.sh \
  "${parts_rel}/step" "${assets_rel}" 4
geometry="${stages_rel}/${F10_SLUG}-geometry-f10.usda"
kinematic="${stages_rel}/${F10_SLUG}-kinematic-f10.usda"
detail="${stages_rel}/${F10_SLUG}-detail-f10.usda"
/opt/simready-validation/bin/python \
  twins/reference-917-engine/source/build_variant_engine_usd_f10.py \
  --config "${config_rel}/complete-engine-f10.json" \
  --parts-report "${parts_rel}/variant-engine-parts-report.json" \
  --assets "${assets_rel}" --output "${geometry}"
/opt/simready-validation/bin/python \
  twins/reference-917-engine/source/author_kinematics_f2.py \
  "${geometry}" "${kinematic}" \
  --config "${config_rel}/kinematics-f10.json" \
  --report "${reports_rel}/author-kinematics-f10.json"
/opt/simready-validation/bin/python \
  twins/reference-917-engine/source/build_variant_detail_usd_f10.py \
  "${kinematic}" \
  --config "${config_rel}/detail-expansion-f10.json" \
  --parts-report "${F10_COMMON_F3_REL}/parts/detail-expansion-f3-report.json" \
  --assets "${F10_COMMON_F3_REL}/assets" --output "${detail}"
/opt/simready-validation/bin/python \
  twins/reference-917-engine/source/validate_variant_stages_f10.py \
  --manifest twins/reference-917-engine/variant-configurations-f10.json \
  --variant "${F10_VARIANT}" \
  --geometry-config "${config_rel}/complete-engine-f10.json" \
  --kinematics-config "${config_rel}/kinematics-f10.json" \
  --detail-config "${config_rel}/detail-expansion-f10.json" \
  --parts-report "${parts_rel}/variant-engine-parts-report.json" \
  --geometry-stage "${geometry}" --kinematic-stage "${kinematic}" --detail-stage "${detail}" \
  --report "${reports_rel}/validate-variant-stages-f10.json"
'
done

python3 - "${OUTPUT}" <<'PY'
import json
import os
import sys
from pathlib import Path

output = Path(sys.argv[1]).resolve()
reports = sorted(output.glob("*/reports/validate-variant-stages-f10.json"))
documents = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
if len(documents) != 2 or any(document.get("status") != "passed" for document in documents):
    raise SystemExit("F10 completion marker refused: two passed variant reports are required")
completion = {
    "schema_version": "1.0.0",
    "phase": "F10",
    "status": "passed",
    "variant_reports": [str(path.resolve()) for path in reports],
    "variant_ids": sorted(document["variant_id"] for document in documents),
    "manufacturing_geometry_ready": False,
    "physical_kinematics_ready": False,
}
temporary = output / ".run-complete.json.tmp"
final = output / "run-complete.json"
temporary.write_text(json.dumps(completion, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, final)
PY

printf '%s\n' "F10 variants: ${OUTPUT}"
