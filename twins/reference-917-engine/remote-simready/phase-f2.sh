#!/usr/bin/env bash
# Auteur et valide F2 nativement, en conservant F1 comme subLayer disponible.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
INPUT_F1=""
INPUT_F1_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --input-f1) INPUT_F1="$2"; shift 2 ;;
        --input-f1-report) INPUT_F1_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INPUT_F1}" ] || { echo "--input-f1 requis" >&2; exit 2; }
[ -n "${INPUT_F1_REPORT}" ] || { echo "--input-f1-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/f2/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
STAGES="${PHASE_ROOT}/stages"
REPORTS="${PHASE_ROOT}/reports"
mkdir -p "${STAGES}" "${REPORTS}"
STAGE="${STAGES}/917-engine-kinematic-f2.usda"
AUTHOR_REPORT="${REPORTS}/author-kinematics-f2.json"
VALIDATION_REPORT="${REPORTS}/validate-kinematics-f2.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-f2.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-f2.log"
phase_init "f2" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${INPUT_F1}"
phase_add_input "${INPUT_F1_REPORT}"
phase_add_output "${STAGE}"
phase_add_child_report "${AUTHOR_REPORT}"
phase_add_child_report "${VALIDATION_REPORT}"
require_job_control
require_file "${INPUT_F1}"
require_report_output "${INPUT_F1_REPORT}" "${INPUT_F1}"

CONFIG="${PROJECT_ROOT}/twins/reference-917-engine/kinematics-f2.json"
AUTHOR="${PROJECT_ROOT}/twins/reference-917-engine/source/author_kinematics_f2.py"
VALIDATE="${PROJECT_ROOT}/twins/reference-917-engine/source/validate_kinematics_f2.py"
require_file "${CONFIG}"
require_file "${AUTHOR}"
require_file "${VALIDATE}"
run_logged "${USD_PYTHON}" "${AUTHOR}" "${INPUT_F1}" "${STAGE}" \
    --config "${CONFIG}" --report "${AUTHOR_REPORT}"
run_logged "${USD_PYTHON}" "${VALIDATE}" "${STAGE}" \
    --config "${CONFIG}" --report "${VALIDATION_REPORT}"
require_passed_report "${VALIDATION_REPORT}"
phase_pass "F2 natif validé; sa subLayer F1 reste dans le même arbre de résultats"
