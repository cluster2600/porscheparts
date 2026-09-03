#!/usr/bin/env bash
# Premier contact workflow avec les endpoints déjà sains : prévol NVIDIA sans déploiement Docker.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
READINESS_REPORT=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --readiness-report) READINESS_REPORT="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${READINESS_REPORT}" ] || { echo "--readiness-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/preflight/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
mkdir -p "${PHASE_ROOT}"
MANIFEST="${PHASE_ROOT}/cad-to-simready-preflight.json"
ENV_FILE="${PHASE_ROOT}/cad-to-simready-preflight.env"
MARKDOWN="${PHASE_ROOT}/cad-to-simready-preflight.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-preflight.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-preflight.log"
phase_init "preflight" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${READINESS_REPORT}"
phase_add_output "${MANIFEST}"
phase_add_child_report "${MANIFEST}"
require_job_control
require_passed_report "${READINESS_REPORT}"
PREFLIGHT_SCRIPT="$(require_skill_reference "references/preflight/scripts/preflight.py")"

export CONTENT_AGENTS_UPSTREAM_ROOT="${CONTENT_AGENTS_UPSTREAM_ROOT:-${CONTENT_AGENTS_ROOT:-/opt/content-agents}}"
export SIMREADY_FOUNDATION_ROOT="${SIMREADY_FOUNDATION_ROOT:-/opt/simready-foundation}"
run_logged "${USD_PYTHON}" "${PREFLIGHT_SCRIPT}" \
    --check-only \
    --skip-deploy \
    --no-update \
    --targets validation,content-agents \
    --project-root "${PROJECT_ROOT}" \
    --output-root "${OUTPUT_ROOT}" \
    --state-root "${PHASE_ROOT}/state" \
    --report "${MANIFEST}" \
    --env-file "${ENV_FILE}" \
    --markdown-report "${MARKDOWN}"
require_passed_report "${MANIFEST}"
phase_add_output "${ENV_FILE}"
phase_add_output "${MARKDOWN}"
phase_pass "prévol NVIDIA prêt; USD natifs et endpoints existants réutilisés sans Docker-in-Docker"
