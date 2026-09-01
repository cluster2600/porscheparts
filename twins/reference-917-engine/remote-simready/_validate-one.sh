#!/usr/bin/env bash
# Bibliothèque interne : une invocation correspond à un seul validateur.

validate_one_main() {
    local phase_name="$1"
    local reference_relative="$2"
    local previous_phase="$3"
    shift 3
    parse_common_arguments "$@" >/dev/null
    shift 8
    local conform_report=""
    local previous_validation_report=""
    local profile="Prop-Robotics-Neutral"
    local profile_version="1.0.0"
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --conform-report) conform_report="$2"; shift 2 ;;
            --previous-validation-report) previous_validation_report="$2"; shift 2 ;;
            --profile) profile="$2"; shift 2 ;;
            --profile-version) profile_version="$2"; shift 2 ;;
            *) echo "argument inconnu: $1" >&2; exit 2 ;;
        esac
    done
    [ -n "${conform_report}" ] || { echo "--conform-report requis" >&2; exit 2; }
    if [ -n "${previous_phase}" ] && [ -z "${previous_validation_report}" ]; then
        echo "--previous-validation-report requis après ${previous_phase}" >&2
        exit 2
    fi

    local phase_root="${OUTPUT_ROOT}/${phase_name}/${RUN_ID}"
    [ ! -e "${phase_root}" ] || { echo "sortie existante: ${phase_root}" >&2; exit 2; }
    mkdir -p "${phase_root}"
    local reference_report="${phase_root}/${phase_name}.json"
    local reference_markdown="${phase_root}/${phase_name}.md"
    local phase_report_path="${phase_root}/phase-${phase_name}.json"
    local phase_log_path="${phase_root}/phase-${phase_name}.log"
    phase_init "${phase_name}" "${phase_report_path}" "${phase_log_path}" "${CONTROL_REPORT}"
    phase_add_input "${conform_report}"
    [ -n "${previous_validation_report}" ] && phase_add_input "${previous_validation_report}"
    phase_add_child_report "${reference_report}"
    require_job_control
    require_passed_report "${conform_report}"
    if [ -n "${previous_phase}" ]; then
        "${SYSTEM_PYTHON}" - "${previous_validation_report}" "${previous_phase}" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve()
expected = sys.argv[2]
if not path.is_file():
    raise SystemExit(f"rapport de validation précédent absent: {path}")
report = json.loads(path.read_text(encoding="utf-8"))
if report.get("phase") != expected:
    raise SystemExit(f"phase précédente attendue: {expected}")
if report.get("status") not in {"passed", "needs_rerun"}:
    raise SystemExit("validation précédente non terminée")
PY
    fi
    local asset
    asset="$(report_output_path "${conform_report}")"
    phase_add_input "${asset}"
    phase_add_output "${asset}"
    local reference
    reference="$(require_skill_reference "${reference_relative}")"
    local command=("${USD_PYTHON}" "${reference}" "${asset}")
    if [ "${phase_name}" = "validate-simready" ]; then
        command+=(--profile "${profile}" --profile-version "${profile_version}" --foundation-root "${SIMREADY_FOUNDATION_ROOT:-/opt/simready-foundation}")
    fi
    command+=(--report "${reference_report}" --markdown-report "${reference_markdown}")
    set +e
    run_logged "${command[@]}"
    local validation_code=$?
    set -e
    require_file "${reference_report}"
    if [ "${validation_code}" -eq 0 ]; then
        require_passed_report "${reference_report}"
        phase_pass "validation ${phase_name} réussie"
        return 0
    fi
    phase_needs_rerun "validation ${phase_name} terminée avec constats; l'USD reste un artefact diagnostique"
    return 3
}
