#!/usr/bin/env bash
# Valide la viabilité USD minimale avant tout appel aux Content Agents.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
ASSET=""
PRODUCER_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --asset) ASSET="$2"; shift 2 ;;
        --producer-report) PRODUCER_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${ASSET}" ] || { echo "--asset requis" >&2; exit 2; }
[ -n "${PRODUCER_REPORT}" ] || { echo "--producer-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/minimum-usd/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}"
REFERENCE_REPORT="${PHASE_ROOT}/validate-usd-minimum.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/validate-usd-minimum.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-minimum-usd.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-minimum-usd.log"
phase_init "minimum-usd" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${ASSET}"
phase_add_input "${PRODUCER_REPORT}"
phase_add_output "${ASSET}"
phase_add_child_report "${REFERENCE_REPORT}"
require_job_control
require_file "${ASSET}"
require_report_output "${PRODUCER_REPORT}" "${ASSET}"
REFERENCE="$(require_skill_reference "references/validate-usd-minimum/scripts/run.py")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${ASSET}" \
    --report "${REFERENCE_REPORT}" --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
phase_pass "USD minimal validé avant affectation de propriétés"
