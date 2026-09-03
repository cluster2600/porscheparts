#!/usr/bin/env bash
# Autorise seulement CollisionAPI statique sur les Mesh existants, à titre diagnostique.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_common.sh
. "${SCRIPT_DIR}/../_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
FAMILY=""
MATERIAL_REPORT=""
PROMPT_FILE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --family) FAMILY="$2"; shift 2 ;;
        --material-report) MATERIAL_REPORT="$2"; shift 2 ;;
        --prompt-file) PROMPT_FILE="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${FAMILY}" ] || { echo "--family requis" >&2; exit 2; }
[ -n "${MATERIAL_REPORT}" ] || { echo "--material-report requis" >&2; exit 2; }
[ -n "${PROMPT_FILE}" ] || { echo "--prompt-file requis" >&2; exit 2; }

CONTRACT="${PROJECT_ROOT}/twins/reference-917-engine/component-factory-f42b-gpu.json"
CONTRACT_HELPER="${SCRIPT_DIR}/_contract.py"
PHASE_ROOT="${OUTPUT_ROOT}/physics/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}/agent-output" "${PHASE_ROOT}/output"
PHYSICS_USD="${PHASE_ROOT}/output/${FAMILY}-physics-contract.usd"
REFERENCE_REPORT="${PHASE_ROOT}/physics-agent.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/physics-agent.md"
PHYSICS_AUTHORING="${PHASE_ROOT}/f42b-physics-authoring.json"
PHYSICS_AUDIT="${PHASE_ROOT}/f42b-physics-audit.json"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-physics.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-physics.log"

phase_init "physics" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
for input in "${CONTRACT}" "${MATERIAL_REPORT}" "${PROMPT_FILE}"; do
    phase_add_input "${input}"
done
for child in \
    "${REFERENCE_REPORT}" "${REFERENCE_MARKDOWN}" \
    "${PHYSICS_AUTHORING}" "${PHYSICS_AUDIT}"; do
    phase_add_child_report "${child}"
done

require_job_control
require_file "${CONTRACT}"
require_file "${CONTRACT_HELPER}"
SOURCE_ASSET="$(${SYSTEM_PYTHON} "${CONTRACT_HELPER}" verify-control \
    --contract "${CONTRACT}" --control "${CONTROL_REPORT}" --family "${FAMILY}" \
    2>>"${PHASE_LOG}")"
require_passed_report "${MATERIAL_REPORT}"
MATERIAL_USD="$(report_output_path "${MATERIAL_REPORT}")"
CONTEXT_REPORT="$(report_input_named "${MATERIAL_REPORT}" asset-context.json)"
MATERIAL_AUDIT="$(report_child_named "${MATERIAL_REPORT}" f42b-material-audit.json)"
for input in "${SOURCE_ASSET}" "${MATERIAL_USD}" "${CONTEXT_REPORT}" "${MATERIAL_AUDIT}"; do
    phase_add_input "${input}"
done
require_report_input "${MATERIAL_REPORT}" "${CONTEXT_REPORT}"
require_passed_report "${MATERIAL_AUDIT}"
require_asset_context "${CONTEXT_REPORT}" "${SOURCE_ASSET}"
require_attested_prompt physics "${PROMPT_FILE}"
[ -s "${PROMPT_FILE}" ] || { phase_block "prompt physique vide"; exit 2; }
[ "$(wc -c <"${PROMPT_FILE}")" -le 20000 ] \
    || { phase_block "prompt physique trop volumineux"; exit 2; }

REFERENCE="$(require_skill_reference "references/content-agents/references/physics-agent-client/scripts/run.py")"
PROMPT="$(compose_assignment_prompt "${PROMPT_FILE}" "${CONTEXT_REPORT}")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${MATERIAL_USD}" "${PHASE_ROOT}/agent-output" \
    --base-url http://127.0.0.1:8200 \
    --prompt "${PROMPT}" \
    --render-backend remote \
    --convert-output-to-usd \
    --timeout 3600 \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
AGENT_PHYSICS_USD="$(report_output_path "${REFERENCE_REPORT}")"
[[ "${AGENT_PHYSICS_USD}" == "${PHASE_ROOT}/agent-output/"* ]] \
    || { phase_block "sortie Physics Agent hors du répertoire de phase"; exit 2; }

# La sortie libre de l'agent reste diagnostique. La chaîne copie le stage
# matériel contractuel et applique seulement CollisionAPI=true sur les Mesh.
run_logged "${SYSTEM_PYTHON}" "${CONTRACT_HELPER}" clone-stage \
    --source "${MATERIAL_USD}" --destination "${PHYSICS_USD}"
run_logged "${USD_PYTHON}" "${CONTRACT_HELPER}" author-static-collisions \
    --contract "${CONTRACT}" --family "${FAMILY}" --asset "${PHYSICS_USD}" \
    --report "${PHYSICS_AUTHORING}"
require_passed_report "${PHYSICS_AUTHORING}"

run_logged "${USD_PYTHON}" "${CONTRACT_HELPER}" audit-usd \
    --contract "${CONTRACT}" --family "${FAMILY}" \
    --source-asset "${SOURCE_ASSET}" --asset "${PHYSICS_USD}" \
    --stage physics --report "${PHYSICS_AUDIT}"
require_passed_report "${PHYSICS_AUDIT}"
phase_add_output "${PHYSICS_USD}"
phase_pass "CollisionAPI statique diagnostique attestée; aucune dynamique, masse, joint, force, FEA ou simulation exécutée"
