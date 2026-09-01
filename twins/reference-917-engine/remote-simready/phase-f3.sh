#!/usr/bin/env bash
# Construit et valide F3 au-dessus d'un F2 explicitement validé.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
INPUT_F2=""
INPUT_F2_REPORT=""
PREFLIGHT_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --input-f2) INPUT_F2="$2"; shift 2 ;;
        --input-f2-report) INPUT_F2_REPORT="$2"; shift 2 ;;
        --preflight-report) PREFLIGHT_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INPUT_F2}" ] || { echo "--input-f2 requis" >&2; exit 2; }
[ -n "${INPUT_F2_REPORT}" ] || { echo "--input-f2-report requis" >&2; exit 2; }
[ -n "${PREFLIGHT_REPORT}" ] || { echo "--preflight-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/f3/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
PARTS="${PHASE_ROOT}/parts"
ASSETS="${PHASE_ROOT}/assets"
STAGES="${PHASE_ROOT}/stages"
REPORTS="${PHASE_ROOT}/reports"
mkdir -p "${PARTS}" "${ASSETS}" "${STAGES}" "${REPORTS}"
STAGE="${STAGES}/917-engine-detail-f3.usda"
VALIDATION_REPORT="${REPORTS}/detail-expansion-validation.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-f3.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-f3.log"
phase_init "f3" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${INPUT_F2}"
phase_add_input "${INPUT_F2_REPORT}"
phase_add_input "${PREFLIGHT_REPORT}"
phase_add_output "${STAGE}"
phase_add_child_report "${VALIDATION_REPORT}"
require_job_control
require_passed_report "${PREFLIGHT_REPORT}"
require_file "${INPUT_F2}"
require_report_output "${INPUT_F2_REPORT}" "${INPUT_F2}"

CONFIG="${PROJECT_ROOT}/twins/reference-917-engine/detail-expansion-f3.json"
BUILD_PARTS="${PROJECT_ROOT}/twins/reference-917-engine/source/build_detail_expansion_f3.py"
BUILD_USD="${PROJECT_ROOT}/twins/reference-917-engine/source/build_detail_expansion_usd_f3.py"
VALIDATE_USD="${PROJECT_ROOT}/twins/reference-917-engine/source/validate_detail_expansion_f3.py"
require_file "${CONFIG}"
require_file "${BUILD_PARTS}"
require_file "${BUILD_USD}"
require_file "${VALIDATE_USD}"

run_logged "${CAD_PYTHON}" "${BUILD_PARTS}" --config "${CONFIG}" --output "${PARTS}"
while IFS= read -r -d '' step; do
    family="$(basename "${step}" .step)"
    run_logged "${USD_CONVERT_CAD_BIN}" -i "${step}" -o "${ASSETS}/${family}.usdc" \
        --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
done < <(find "${PARTS}/step" -type f -name '*.step' -print0 | sort -z)
run_logged "${USD_PYTHON}" "${BUILD_USD}" "${INPUT_F2}" \
    --config "${CONFIG}" \
    --parts-report "${PARTS}/detail-expansion-f3-report.json" \
    --assets "${ASSETS}" --output "${STAGE}"
run_logged "${USD_PYTHON}" "${VALIDATE_USD}" "${STAGE}" \
    --config "${CONFIG}" --report "${VALIDATION_REPORT}"
require_passed_report "${VALIDATION_REPORT}"
phase_pass "F3 construit et validé au-dessus du F2 validé"
