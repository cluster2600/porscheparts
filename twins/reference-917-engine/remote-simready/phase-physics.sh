#!/usr/bin/env bash
# Appelle uniquement le Physics Agent sur la sortie concrète du Material Agent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
MATERIAL_REPORT=""
PROMPT_FILE=""
ASSET_CONTEXT_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --material-report) MATERIAL_REPORT="$2"; shift 2 ;;
        --prompt-file) PROMPT_FILE="$2"; shift 2 ;;
        --asset-context-report) ASSET_CONTEXT_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${MATERIAL_REPORT}" ] || { echo "--material-report requis" >&2; exit 2; }
[ -n "${PROMPT_FILE}" ] || { echo "--prompt-file requis" >&2; exit 2; }
[ -n "${ASSET_CONTEXT_REPORT}" ] || { echo "--asset-context-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/physics/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}/output"
REFERENCE_REPORT="${PHASE_ROOT}/physics-agent.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/physics-agent.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-physics.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-physics.log"
phase_init "physics" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${MATERIAL_REPORT}"
phase_add_input "${PROMPT_FILE}"
phase_add_input "${ASSET_CONTEXT_REPORT}"
phase_add_child_report "${REFERENCE_REPORT}"
require_job_control
require_passed_report "${MATERIAL_REPORT}"
MATERIAL_USD="$(report_output_path "${MATERIAL_REPORT}")"
phase_add_input "${MATERIAL_USD}"
require_attested_prompt physics "${PROMPT_FILE}"
require_asset_context "${ASSET_CONTEXT_REPORT}"
require_report_input "${MATERIAL_REPORT}" "${ASSET_CONTEXT_REPORT}"
[ -s "${PROMPT_FILE}" ] || { phase_block "prompt physique vide"; exit 2; }
[ "$(wc -c <"${PROMPT_FILE}")" -le 20000 ] || { phase_block "prompt physique trop volumineux"; exit 2; }
REFERENCE="$(require_skill_reference "references/content-agents/references/physics-agent-client/scripts/run.py")"
PROMPT="$(compose_assignment_prompt "${PROMPT_FILE}" "${ASSET_CONTEXT_REPORT}")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${MATERIAL_USD}" "${PHASE_ROOT}/output" \
    --base-url http://127.0.0.1:8200 \
    --prompt "${PROMPT}" \
    --render-backend remote \
    --convert-output-to-usd \
    --timeout 3600 \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
PHYSICS_USD="$(report_output_path "${REFERENCE_REPORT}")"
phase_add_output "${PHYSICS_USD}"
phase_pass "Physics Agent terminé sur la sortie Material Agent; sortie concrète enregistrée"
