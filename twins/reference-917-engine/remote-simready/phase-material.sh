#!/usr/bin/env bash
# Appelle uniquement le Material Agent, après le gate USD minimal.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
ASSET=""
MINIMUM_REPORT=""
PROMPT_FILE=""
ASSET_CONTEXT_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --asset) ASSET="$2"; shift 2 ;;
        --minimum-report) MINIMUM_REPORT="$2"; shift 2 ;;
        --prompt-file) PROMPT_FILE="$2"; shift 2 ;;
        --asset-context-report) ASSET_CONTEXT_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${ASSET}" ] || { echo "--asset requis" >&2; exit 2; }
[ -n "${MINIMUM_REPORT}" ] || { echo "--minimum-report requis" >&2; exit 2; }
[ -n "${PROMPT_FILE}" ] || { echo "--prompt-file requis" >&2; exit 2; }
[ -n "${ASSET_CONTEXT_REPORT}" ] || { echo "--asset-context-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/material/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}/output"
REFERENCE_REPORT="${PHASE_ROOT}/material-agent.json"
REFERENCE_MARKDOWN="${PHASE_ROOT}/material-agent.md"
INTENT_REPORT="${PHASE_ROOT}/property-assignment-intent.json"
PROPAGATION_REPORT="${PHASE_ROOT}/family-material-propagation.json"
FULL_MATERIAL_USD="${PHASE_ROOT}/output/917-engine-family-materialized.usda"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-material.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-material.log"
phase_init "material" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${ASSET}"
phase_add_input "${MINIMUM_REPORT}"
phase_add_input "${PROMPT_FILE}"
phase_add_input "${ASSET_CONTEXT_REPORT}"
phase_add_child_report "${REFERENCE_REPORT}"
phase_add_child_report "${INTENT_REPORT}"
phase_add_child_report "${PROPAGATION_REPORT}"
require_job_control
require_file "${ASSET}"
require_attested_prompt material "${PROMPT_FILE}"
require_asset_context "${ASSET_CONTEXT_REPORT}" "${ASSET}"
require_report_output "${MINIMUM_REPORT}" "${ASSET}"
MATERIAL_PROXY_REPORT="$(report_input_named "${MINIMUM_REPORT}" material-proxy-f10.json)"
MATERIAL_PROXY="$(report_output_path "${MATERIAL_PROXY_REPORT}")"
PROXY_MINIMUM_REPORT="$(report_child_named "${MINIMUM_REPORT}" validate-material-proxy-minimum.json)"
phase_add_input "${MATERIAL_PROXY_REPORT}"
phase_add_input "${MATERIAL_PROXY}"
phase_add_input "${PROXY_MINIMUM_REPORT}"
require_report_input "${MINIMUM_REPORT}" "${MATERIAL_PROXY_REPORT}"
require_report_input "${MINIMUM_REPORT}" "${MATERIAL_PROXY}"
require_material_proxy_source "${MATERIAL_PROXY_REPORT}" "${ASSET}"
require_report_output "${PROXY_MINIMUM_REPORT}" "${MATERIAL_PROXY}"
[ -s "${PROMPT_FILE}" ] || { phase_block "prompt matériel vide"; exit 2; }
[ "$(wc -c <"${PROMPT_FILE}")" -le 20000 ] || { phase_block "prompt matériel trop volumineux"; exit 2; }
refresh_budget
if ! timeout --foreground "${PHASE_REMAINING_SECONDS}s" "${USD_PYTHON}" - "${MATERIAL_PROXY}" "${INTENT_REPORT}" >>"${PHASE_LOG}" 2>&1 <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

from pxr import Usd

asset = Path(sys.argv[1]).resolve()
report_path = Path(sys.argv[2])
stage = Usd.Stage.Open(str(asset), load=Usd.Stage.LoadAll)
world = stage.GetDefaultPrim() if stage else None
intent = world.GetCustomDataByKey("3dprinting993:propertyAssignmentIntent") if world else None
payload = {
    "schema_version": "1.0.0",
    "status": "passed" if intent == "run" else "blocked",
    "passed": intent == "run",
    "asset_path": str(asset),
    "property_assignment_intent": intent,
}
report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if payload["passed"] else 2)
PY
then
    phase_block "propertyAssignmentIntent n'autorise pas l'affectation Material"
    exit 2
fi
REFERENCE="$(require_skill_reference "references/content-agents/references/material-agent-client/scripts/run.py")"
PROMPT="$(compose_assignment_prompt "${PROMPT_FILE}" "${ASSET_CONTEXT_REPORT}")"
run_logged "${USD_PYTHON}" "${REFERENCE}" "${MATERIAL_PROXY}" "${PHASE_ROOT}/output" \
    --base-url http://127.0.0.1:8100 \
    --prompt "${PROMPT}" \
    --no-optimize-usd \
    --timeout 3600 \
    --report "${REFERENCE_REPORT}" \
    --markdown-report "${REFERENCE_MARKDOWN}"
require_passed_report "${REFERENCE_REPORT}"
MATERIAL_USD="$(report_output_path "${REFERENCE_REPORT}")"
phase_add_input "${MATERIAL_USD}"
PROPAGATE="${PROJECT_ROOT}/twins/reference-917-engine/source/apply_family_material_bindings_f10.py"
require_file "${PROPAGATE}"
run_logged "${USD_PYTHON}" "${PROPAGATE}" \
    --source-asset "${ASSET}" --proxy-report "${MATERIAL_PROXY_REPORT}" \
    --material-usd "${MATERIAL_USD}" --material-report "${REFERENCE_REPORT}" \
    --output "${FULL_MATERIAL_USD}" --report "${PROPAGATION_REPORT}"
require_passed_report "${PROPAGATION_REPORT}"
require_report_output "${PROPAGATION_REPORT}" "${FULL_MATERIAL_USD}"
phase_add_output "${FULL_MATERIAL_USD}"
phase_pass "Material Agent exécuté sur un représentant statique par famille; bindings propagés au stage F10 complet pour Physics Agent"
