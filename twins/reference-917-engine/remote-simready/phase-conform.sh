#!/usr/bin/env bash
# Applique la conformance après Material et Physics, jamais avant.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
PHYSICS_REPORT=""
PROFILE="Prop-Robotics-Neutral"
PROFILE_VERSION="1.0.0"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --physics-report) PHYSICS_REPORT="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        --profile-version) PROFILE_VERSION="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${PHYSICS_REPORT}" ] || { echo "--physics-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/conform/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}/output"
REFERENCE_REPORT="${PHASE_ROOT}/simready-conform-profile.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/simready-conform-profile.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-conform.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-conform.log"
phase_init "conform" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${PHYSICS_REPORT}"
phase_add_child_report "${REFERENCE_REPORT}"
require_job_control
require_passed_report "${PHYSICS_REPORT}"
PHYSICS_USD="$(report_output_path "${PHYSICS_REPORT}")"
phase_add_input "${PHYSICS_USD}"
REFERENCE="$(require_skill_reference "references/simready-conform-profile/scripts/run.py")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${PHYSICS_USD}" \
    --output-dir "${PHASE_ROOT}/output" \
    --profile "${PROFILE}" \
    --profile-version "${PROFILE_VERSION}" \
    --pipeline-step material-agent-client \
    --pipeline-step physics-agent-client \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
CONFORMED_USD="$(report_output_path "${REFERENCE_REPORT}")"
phase_add_output "${CONFORMED_USD}"
phase_pass "conformance appliquée après les deux Content Agents"
