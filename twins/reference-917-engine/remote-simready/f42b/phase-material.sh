#!/usr/bin/env bash
# Affecte uniquement le look visuel sourcé; les propriétés physiques restent inconnues.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_common.sh
. "${SCRIPT_DIR}/../_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
FAMILY=""
MINIMUM_REPORT=""
PROMPT_FILE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --family) FAMILY="$2"; shift 2 ;;
        --minimum-report) MINIMUM_REPORT="$2"; shift 2 ;;
        --prompt-file) PROMPT_FILE="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${FAMILY}" ] || { echo "--family requis" >&2; exit 2; }
[ -n "${MINIMUM_REPORT}" ] || { echo "--minimum-report requis" >&2; exit 2; }
[ -n "${PROMPT_FILE}" ] || { echo "--prompt-file requis" >&2; exit 2; }

CONTRACT="${PROJECT_ROOT}/twins/reference-917-engine/component-factory-f42b-gpu.json"
CONTRACT_HELPER="${SCRIPT_DIR}/_contract.py"
PHASE_ROOT="${OUTPUT_ROOT}/material/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}/agent-output" "${PHASE_ROOT}/output"
MATERIAL_USD="${PHASE_ROOT}/output/${FAMILY}-material-contract.usd"
REFERENCE_REPORT="${PHASE_ROOT}/material-agent.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/material-agent.md"
MATERIAL_AUDIT="${PHASE_ROOT}/f42b-material-audit.json"
MATERIAL_AUTHORING="${PHASE_ROOT}/f42b-material-authoring.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-material.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-material.log"

phase_init "material" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
for input in "${CONTRACT}" "${MINIMUM_REPORT}" "${PROMPT_FILE}"; do
    phase_add_input "${input}"
done
for child in \
    "${REFERENCE_REPORT}" "${REFERENCE_MARKDOWN}" \
    "${MATERIAL_AUTHORING}" "${MATERIAL_AUDIT}"; do
    phase_add_child_report "${child}"
done

require_job_control
require_file "${CONTRACT}"
require_file "${CONTRACT_HELPER}"
SOURCE_ASSET="$(${SYSTEM_PYTHON} "${CONTRACT_HELPER}" verify-control \
    --contract "${CONTRACT}" --control "${CONTROL_REPORT}" --family "${FAMILY}" \
    2>>"${PHASE_LOG}")"
require_passed_report "${MINIMUM_REPORT}"
MINIMUM_USD="$(report_output_path "${MINIMUM_REPORT}")"
CONTEXT_REPORT="$(report_child_named "${MINIMUM_REPORT}" asset-context.json)"
INPUT_AUDIT="$(report_child_named "${MINIMUM_REPORT}" f42b-input-audit.json)"
for input in "${SOURCE_ASSET}" "${MINIMUM_USD}" "${CONTEXT_REPORT}" "${INPUT_AUDIT}"; do
    phase_add_input "${input}"
done
require_report_input "${MINIMUM_REPORT}" "${SOURCE_ASSET}"
require_passed_report "${INPUT_AUDIT}"
require_asset_context "${CONTEXT_REPORT}" "${SOURCE_ASSET}"
require_attested_prompt material "${PROMPT_FILE}"
[ -s "${PROMPT_FILE}" ] || { phase_block "prompt matériel vide"; exit 2; }
[ "$(wc -c <"${PROMPT_FILE}")" -le 20000 ] \
    || { phase_block "prompt matériel trop volumineux"; exit 2; }

REFERENCE="$(require_skill_reference "references/content-agents/references/material-agent-client/scripts/run.py")"
PROMPT="$(compose_assignment_prompt "${PROMPT_FILE}" "${CONTEXT_REPORT}")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${MINIMUM_USD}" "${PHASE_ROOT}/agent-output" \
    --base-url http://127.0.0.1:8100 \
    --prompt "${PROMPT}" \
    --no-optimize-usd \
    --timeout 3600 \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
AGENT_MATERIAL_USD="$(report_output_path "${REFERENCE_REPORT}")"
[[ "${AGENT_MATERIAL_USD}" == "${PHASE_ROOT}/agent-output/"* ]] \
    || { phase_block "sortie Material Agent hors du répertoire de phase"; exit 2; }

# La sortie libre de l'agent reste diagnostique. Le stage de chaîne repart de
# l'USD minimum attesté, puis reçoit seulement la palette F7 déterministe.
run_logged "${SYSTEM_PYTHON}" "${CONTRACT_HELPER}" clone-stage \
    --source "${MINIMUM_USD}" --destination "${MATERIAL_USD}"
run_logged "${USD_PYTHON}" "${CONTRACT_HELPER}" author-material \
    --contract "${CONTRACT}" --family "${FAMILY}" --asset "${MATERIAL_USD}" \
    --report "${MATERIAL_AUTHORING}"
require_passed_report "${MATERIAL_AUTHORING}"

run_logged "${USD_PYTHON}" "${CONTRACT_HELPER}" audit-usd \
    --contract "${CONTRACT}" --family "${FAMILY}" \
    --source-asset "${SOURCE_ASSET}" --asset "${MATERIAL_USD}" \
    --stage material --report "${MATERIAL_AUDIT}"
require_passed_report "${MATERIAL_AUDIT}"
phase_add_output "${MATERIAL_USD}"
phase_pass "look visuel sourcé affecté; matériau historique séparé et propriétés physiques laissées inconnues"
