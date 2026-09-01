#!/usr/bin/env bash
# Construit et valide F1 directement dans le conteneur Vast.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
PREFLIGHT_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --preflight-report) PREFLIGHT_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${PREFLIGHT_REPORT}" ] || { echo "--preflight-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/f1/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
PARTS="${PHASE_ROOT}/parts"
ASSETS="${PHASE_ROOT}/assets"
STAGES="${PHASE_ROOT}/stages"
REPORTS="${PHASE_ROOT}/reports"
mkdir -p "${PARTS}" "${ASSETS}" "${STAGES}" "${REPORTS}"
STAGE="${STAGES}/917-complete-engine-f1.usda"
VALIDATION_REPORT="${REPORTS}/complete-engine-validation.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-f1.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-f1.log"
phase_init "f1" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${PREFLIGHT_REPORT}"
phase_add_output "${STAGE}"
phase_add_child_report "${VALIDATION_REPORT}"
require_job_control
require_passed_report "${PREFLIGHT_REPORT}"
require_executable "${CAD_PYTHON}"
require_executable "${USD_PYTHON}"
require_executable "${USD_CONVERT_CAD_BIN}"

CONFIG="${PROJECT_ROOT}/twins/reference-917-engine/complete-engine-f1.json"
BUILD_PARTS="${PROJECT_ROOT}/twins/reference-917-engine/source/build_complete_engine_parts.py"
BUILD_USD="${PROJECT_ROOT}/twins/reference-917-engine/source/build_complete_engine_usd.py"
VALIDATE_USD="${PROJECT_ROOT}/twins/reference-917-engine/source/validate_complete_engine_usd.py"
require_file "${CONFIG}"
require_file "${BUILD_PARTS}"
require_file "${BUILD_USD}"
require_file "${VALIDATE_USD}"
phase_add_input "${CONFIG}"

run_logged "${CAD_PYTHON}" "${BUILD_PARTS}" --config "${CONFIG}" --output "${PARTS}"
while IFS= read -r -d '' step; do
    family="$(basename "${step}" .step)"
    run_logged "${USD_CONVERT_CAD_BIN}" -i "${step}" -o "${ASSETS}/${family}.usdc" \
        --up-axis z --instancing-style none --composition-style none --creator 3dprinting993
done < <(find "${PARTS}/step" -type f -name '*.step' -print0 | sort -z)
run_logged "${USD_PYTHON}" "${BUILD_USD}" \
    --config "${CONFIG}" \
    --parts-report "${PARTS}/complete-engine-parts-report.json" \
    --assets "${ASSETS}" \
    --output "${STAGE}"
run_logged "${USD_PYTHON}" "${VALIDATE_USD}" "${STAGE}" \
    --config "${CONFIG}" --report "${VALIDATION_REPORT}"
require_passed_report "${VALIDATION_REPORT}"
phase_pass "F1 construit et validé nativement; affectation de propriétés toujours explicitement absente"
