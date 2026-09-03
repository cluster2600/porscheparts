#!/usr/bin/env bash
# Lie une famille au hash F42a, copie l'USD privé et valide le minimum sans conversion.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_common.sh
. "${SCRIPT_DIR}/../_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
FAMILY=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --family) FAMILY="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${FAMILY}" ] || { echo "--family requis" >&2; exit 2; }

CONTRACT="${PROJECT_ROOT}/twins/reference-917-engine/component-factory-f42b-gpu.json"
CONTRACT_HELPER="${SCRIPT_DIR}/_contract.py"
PHASE_ROOT="${OUTPUT_ROOT}/minimum-usd/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}/output"
OUTPUT_USD="${PHASE_ROOT}/output/${FAMILY}.usd"
REFERENCE_REPORT="${PHASE_ROOT}/validate-usd-minimum.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/validate-usd-minimum.md"
INPUT_AUDIT="${PHASE_ROOT}/f42b-input-audit.json"
CONTEXT_REPORT="${PHASE_ROOT}/asset-context.json"
CONTEXT_MARKDOWN="${PHASE_ROOT}/asset-context.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-minimum-usd.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-minimum-usd.log"

phase_init "minimum-usd" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${CONTRACT}"
phase_add_output "${OUTPUT_USD}"
for child in \
    "${INPUT_AUDIT}" "${REFERENCE_REPORT}" "${REFERENCE_MARKDOWN}" \
    "${CONTEXT_REPORT}" "${CONTEXT_MARKDOWN}"; do
    phase_add_child_report "${child}"
done

require_job_control
require_file "${CONTRACT}"
require_file "${CONTRACT_HELPER}"
SOURCE_ASSET="$(${SYSTEM_PYTHON} "${CONTRACT_HELPER}" verify-control \
    --contract "${CONTRACT}" --control "${CONTROL_REPORT}" --family "${FAMILY}" \
    2>>"${PHASE_LOG}")"
require_file "${SOURCE_ASSET}"
phase_add_input "${SOURCE_ASSET}"

# Une copie dédiée empêche Material/Physics/conformance de toucher l'entrée privée.
cp -- "${SOURCE_ASSET}" "${OUTPUT_USD}"
cmp -s -- "${SOURCE_ASSET}" "${OUTPUT_USD}" \
    || { phase_block "la copie USD diffère de l'entrée F42a"; exit 2; }

run_logged "${USD_PYTHON}" "${CONTRACT_HELPER}" audit-usd \
    --contract "${CONTRACT}" --family "${FAMILY}" \
    --source-asset "${SOURCE_ASSET}" --asset "${OUTPUT_USD}" \
    --stage minimum --report "${INPUT_AUDIT}"
require_passed_report "${INPUT_AUDIT}"

REFERENCE="$(require_skill_reference "references/validate-usd-minimum/scripts/run.py")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${OUTPUT_USD}" \
    --report "${REFERENCE_REPORT}" --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"

run_logged "${SYSTEM_PYTHON}" "${CONTRACT_HELPER}" context \
    --contract "${CONTRACT}" --control "${CONTROL_REPORT}" --family "${FAMILY}" \
    --report "${CONTEXT_REPORT}" --markdown-report "${CONTEXT_MARKDOWN}"
require_passed_report "${CONTEXT_REPORT}"
phase_pass "USD privé F42a lié au hash canonique et minimum-validé; aucune conversion ni mutation de l'entrée"
