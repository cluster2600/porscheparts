#!/usr/bin/env bash
# Construit une seule branche F10 explicitement sélectionnée, sans VariantSet partagé.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
PREFLIGHT_REPORT=""
VARIANT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --preflight-report) PREFLIGHT_REPORT="$2"; shift 2 ;;
        --variant) VARIANT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${PREFLIGHT_REPORT}" ] || { echo "--preflight-report requis" >&2; exit 2; }
case "${VARIANT}" in
    type_912_4_5_na) SLUG="type-912-4-5-na" ;;
    917_30_turbo_5374) SLUG="917-30-turbo-5374" ;;
    *) echo "--variant doit sélectionner exactement type_912_4_5_na ou 917_30_turbo_5374" >&2; exit 2 ;;
esac

PHASE_ROOT="${OUTPUT_ROOT}/f10/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
GENERATED="${PHASE_ROOT}/generated"
VARIANT_ROOT="${GENERATED}/${SLUG}"
CONFIGS="${VARIANT_ROOT}/configs"
PARTS="${VARIANT_ROOT}/parts"
ASSETS="${VARIANT_ROOT}/assets"
STAGES="${VARIANT_ROOT}/stages"
REPORTS="${VARIANT_ROOT}/reports"
COMMON_F3_PARTS="${PHASE_ROOT}/common-f3/parts"
COMMON_F3_ASSETS="${PHASE_ROOT}/common-f3/assets"
mkdir -p "${PARTS}" "${ASSETS}" "${STAGES}" "${REPORTS}" \
    "${COMMON_F3_PARTS}" "${COMMON_F3_ASSETS}"

GEOMETRY="${STAGES}/${SLUG}-geometry-f10.usda"
KINEMATIC="${STAGES}/${SLUG}-kinematic-f10.usda"
DETAIL="${STAGES}/${SLUG}-detail-f10.usda"
CONFIG_REPORT="${GENERATED}/variant-config-generation-report.json"
AUTHOR_REPORT="${REPORTS}/author-kinematics-f10.json"
VALIDATION_REPORT="${REPORTS}/validate-variant-stages-f10.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-f10.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-f10.log"
phase_init "f10-${SLUG}" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${PREFLIGHT_REPORT}"
phase_add_output "${DETAIL}"
phase_add_child_report "${CONFIG_REPORT}"
phase_add_child_report "${AUTHOR_REPORT}"
phase_add_child_report "${VALIDATION_REPORT}"
require_job_control
require_passed_report "${PREFLIGHT_REPORT}"

MANIFEST="${PROJECT_ROOT}/twins/reference-917-engine/variant-configurations-f10.json"
PREPARE="${PROJECT_ROOT}/twins/reference-917-engine/source/prepare_variant_configs_f10.py"
BUILD_PARTS="${PROJECT_ROOT}/twins/reference-917-engine/source/build_variant_engine_parts_f10.py"
BUILD_GEOMETRY="${PROJECT_ROOT}/twins/reference-917-engine/source/build_variant_engine_usd_f10.py"
AUTHOR_KINEMATICS="${PROJECT_ROOT}/twins/reference-917-engine/source/author_kinematics_f2.py"
BUILD_DETAIL_PARTS="${PROJECT_ROOT}/twins/reference-917-engine/source/build_detail_expansion_f3.py"
BUILD_DETAIL="${PROJECT_ROOT}/twins/reference-917-engine/source/build_variant_detail_usd_f10.py"
VALIDATE="${PROJECT_ROOT}/twins/reference-917-engine/source/validate_variant_stages_f10.py"
for required in "${MANIFEST}" "${PREPARE}" "${BUILD_PARTS}" "${BUILD_GEOMETRY}" \
    "${AUTHOR_KINEMATICS}" "${BUILD_DETAIL_PARTS}" "${BUILD_DETAIL}" "${VALIDATE}"; do
    require_file "${required}"
done

run_logged "${CAD_PYTHON}" "${PREPARE}" \
    --manifest "${MANIFEST}" --project-root "${PROJECT_ROOT}" --output "${GENERATED}"
require_passed_report "${CONFIG_REPORT}"
run_logged "${CAD_PYTHON}" "${BUILD_PARTS}" \
    --config "${CONFIGS}/complete-engine-f10.json" --output "${PARTS}"
run_logged "${CAD_PYTHON}" "${BUILD_DETAIL_PARTS}" \
    --config "${CONFIGS}/detail-expansion-f10.json" --output "${COMMON_F3_PARTS}"

while IFS= read -r -d '' step; do
    family="$(basename "${step}" .step)"
    run_logged "${USD_CONVERT_CAD_BIN}" -i "${step}" -o "${ASSETS}/${family}.usdc" \
        --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
done < <(find "${PARTS}/step" -type f -name '*.step' -print0 | sort -z)
while IFS= read -r -d '' step; do
    family="$(basename "${step}" .step)"
    run_logged "${USD_CONVERT_CAD_BIN}" -i "${step}" -o "${COMMON_F3_ASSETS}/${family}.usdc" \
        --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
done < <(find "${COMMON_F3_PARTS}/step" -type f -name '*.step' -print0 | sort -z)

run_logged "${USD_PYTHON}" "${BUILD_GEOMETRY}" \
    --config "${CONFIGS}/complete-engine-f10.json" \
    --parts-report "${PARTS}/variant-engine-parts-report.json" \
    --assets "${ASSETS}" --output "${GEOMETRY}"
run_logged "${USD_PYTHON}" "${AUTHOR_KINEMATICS}" "${GEOMETRY}" "${KINEMATIC}" \
    --config "${CONFIGS}/kinematics-f10.json" --report "${AUTHOR_REPORT}"
run_logged "${USD_PYTHON}" "${BUILD_DETAIL}" "${KINEMATIC}" \
    --config "${CONFIGS}/detail-expansion-f10.json" \
    --parts-report "${COMMON_F3_PARTS}/detail-expansion-f3-report.json" \
    --assets "${COMMON_F3_ASSETS}" --output "${DETAIL}"
run_logged "${USD_PYTHON}" "${VALIDATE}" \
    --manifest "${MANIFEST}" --variant "${VARIANT}" \
    --geometry-config "${CONFIGS}/complete-engine-f10.json" \
    --kinematics-config "${CONFIGS}/kinematics-f10.json" \
    --detail-config "${CONFIGS}/detail-expansion-f10.json" \
    --parts-report "${PARTS}/variant-engine-parts-report.json" \
    --geometry-stage "${GEOMETRY}" --kinematic-stage "${KINEMATIC}" \
    --detail-stage "${DETAIL}" --report "${VALIDATION_REPORT}"
require_passed_report "${VALIDATION_REPORT}"
phase_pass "F10 ${VARIANT} construit dans un stage distinct; géométrie visuelle non libérée pour fabrication"
