#!/usr/bin/env bash
# Valide SimReady puis applique au plus une réparation NVIDIA ciblée.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_common.sh"

parse_common_arguments "$@" >/dev/null
shift 8
CONFORM_REPORT=""
PREVIOUS_VALIDATION_REPORT=""
PROFILE="Prop-Robotics-Neutral"
PROFILE_VERSION="1.0.0"
GRASP_POINTS=()
VISUAL_EVIDENCE=()
GRASP_PARENT_PRIM=""
GRASP_NAME=""
GRASP_RATIONALE=""
COORDINATE_NOTE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --conform-report) CONFORM_REPORT="$2"; shift 2 ;;
        --previous-validation-report) PREVIOUS_VALIDATION_REPORT="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        --profile-version) PROFILE_VERSION="$2"; shift 2 ;;
        --grasp-point) GRASP_POINTS+=("$2"); shift 2 ;;
        --visual-evidence) VISUAL_EVIDENCE+=("$2"); shift 2 ;;
        --grasp-parent-prim) GRASP_PARENT_PRIM="$2"; shift 2 ;;
        --grasp-name) GRASP_NAME="$2"; shift 2 ;;
        --grasp-rationale) GRASP_RATIONALE="$2"; shift 2 ;;
        --coordinate-note) COORDINATE_NOTE="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${CONFORM_REPORT}" ] || { echo "--conform-report requis" >&2; exit 2; }
[ -n "${PREVIOUS_VALIDATION_REPORT}" ] || { echo "--previous-validation-report requis" >&2; exit 2; }

PHASE_ROOT="${OUTPUT_ROOT}/validate-simready/${RUN_ID}"
[ ! -e "${PHASE_ROOT}" ] || { echo "sortie existante: ${PHASE_ROOT}" >&2; exit 2; }
ATTEMPT_1="${PHASE_ROOT}/attempt-1"
ATTEMPT_2="${PHASE_ROOT}/attempt-2"
mkdir -p "${ATTEMPT_1}"

INITIAL_SIMREADY_REPORT="${ATTEMPT_1}/simready-validate.json"
INITIAL_SIMREADY_MARKDOWN="${ATTEMPT_1}/simready-validate.md"
REPAIR_LOOP_REPORT="${PHASE_ROOT}/repair-loop.json"
REPAIR_LOOP_MARKDOWN="${PHASE_ROOT}/repair-loop.md"
PHASE_REPORT_PATH="${PHASE_ROOT}/phase-validate-simready.json"
PHASE_LOG_PATH="${PHASE_ROOT}/phase-validate-simready.log"

phase_init "validate-simready" "${PHASE_REPORT_PATH}" "${PHASE_LOG_PATH}" "${CONTROL_REPORT}"
phase_add_input "${CONFORM_REPORT}"
phase_add_input "${PREVIOUS_VALIDATION_REPORT}"
phase_add_child_report "${INITIAL_SIMREADY_REPORT}"
phase_add_child_report "${INITIAL_SIMREADY_MARKDOWN}"
phase_add_child_report "${REPAIR_LOOP_REPORT}"
phase_add_child_report "${REPAIR_LOOP_MARKDOWN}"

require_job_control
require_passed_report "${CONFORM_REPORT}"
INITIAL_USD="$(report_output_path "${CONFORM_REPORT}")"
phase_add_input "${INITIAL_USD}"

# Retrouve les trois rapports de phase amont sans copier leurs attestations.
UPSTREAM_VALIDATION_REPORTS=()
while IFS= read -r report_path; do
    [ -n "${report_path}" ] && UPSTREAM_VALIDATION_REPORTS+=("${report_path}")
done < <("${SYSTEM_PYTHON}" - "${PREVIOUS_VALIDATION_REPORT}" "${INITIAL_USD}" <<'PY'
import json
from pathlib import Path
import sys

latest = Path(sys.argv[1]).resolve()
asset = Path(sys.argv[2]).resolve()


def load_phase(path: Path, expected: str) -> dict:
    if not path.is_file():
        raise SystemExit(f"rapport de validation absent: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("phase") != expected:
        raise SystemExit(f"phase précédente attendue: {expected}")
    if payload.get("status") not in {"passed", "needs_rerun"}:
        raise SystemExit(f"validation {expected} non terminée")
    outputs = payload.get("output_paths")
    if not isinstance(outputs, list) or len(outputs) != 1:
        raise SystemExit(f"validation {expected} sans USD unique")
    if Path(outputs[0]).resolve() != asset:
        raise SystemExit(f"validation {expected} appliquée à un autre USD")
    return payload


def previous_phase(payload: dict, expected: str) -> Path:
    matches = []
    for value in payload.get("input_paths", []):
        candidate = Path(str(value)).resolve()
        if not candidate.is_file() or candidate.suffix.lower() != ".json":
            continue
        try:
            nested = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if nested.get("phase") == expected:
            matches.append(candidate)
    if len(matches) != 1:
        raise SystemExit(f"chaînage {expected} absent ou ambigu")
    return matches[0]


physics = load_phase(latest, "validate-physics")
geometry_path = previous_phase(physics, "validate-geometry")
geometry = load_phase(geometry_path, "validate-geometry")
asset_path = previous_phase(geometry, "validate-asset")
load_phase(asset_path, "validate-asset")
for path in (asset_path, geometry_path, latest):
    print(path)
PY
)
[ "${#UPSTREAM_VALIDATION_REPORTS[@]}" -eq 3 ] \
    || { echo "chaîne asset/geometry/physics incomplète" >&2; exit 1; }
phase_add_input "${UPSTREAM_VALIDATION_REPORTS[0]}"
phase_add_input "${UPSTREAM_VALIDATION_REPORTS[1]}"

for evidence in "${VISUAL_EVIDENCE[@]}"; do
    require_workspace_path "${evidence}"
    require_file "${evidence}"
    phase_add_input "${evidence}"
done

# Les références restent atomiques. Un code de validation non nul est conservé
# comme diagnostic tant que son rapport structuré a bien été écrit.
run_reference() {
    local report_path="$1"
    local markdown_path="$2"
    local reference_exit_code=0
    shift 2
    refresh_budget
    set +e
    run_logged "$@"
    reference_exit_code=$?
    set -e
    require_file "${report_path}"
    require_file "${markdown_path}"
    if [ "${reference_exit_code}" -ne 0 ]; then
        printf 'diagnostic non validé: code=%s rapport=%s\n' \
            "${reference_exit_code}" "${report_path}" >>"${PHASE_LOG}"
    fi
}

SIMREADY_REFERENCE="$(require_skill_reference "references/simready-validate/scripts/run.py")"
run_reference "${INITIAL_SIMREADY_REPORT}" "${INITIAL_SIMREADY_MARKDOWN}" \
    "${USD_PYTHON}" "${SIMREADY_REFERENCE}" "${INITIAL_USD}" \
    --profile "${PROFILE}" \
    --profile-version "${PROFILE_VERSION}" \
    --foundation-root "${SIMREADY_FOUNDATION_ROOT:-/opt/simready-foundation}" \
    --report "${INITIAL_SIMREADY_REPORT}" \
    --markdown-report "${INITIAL_SIMREADY_MARKDOWN}"

REPAIRABLE_REQUIREMENT_IDS=()
while IFS= read -r requirement_id; do
    [ -n "${requirement_id}" ] && REPAIRABLE_REQUIREMENT_IDS+=("${requirement_id}")
done < <("${SYSTEM_PYTHON}" - "${INITIAL_SIMREADY_REPORT}" <<'PY'
import json
from pathlib import Path
import re
import sys

repairable = {"NP.002", "NP.006", "UN.007", "RB.MB.001", "GSP.001"}
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
found = set()
for issue in payload.get("issues", []):
    if isinstance(issue, dict):
        text = str(issue.get("requirement_id") or issue.get("requirement") or issue.get("message") or "")
        found.update(re.findall(r"\b[A-Z]+(?:\.[A-Z]+)*\.\d+\b", text))
for feature in payload.get("feature_results", []):
    if not isinstance(feature, dict):
        continue
    values = feature.get("failing_requirements", [])
    if isinstance(values, str):
        values = [values]
    if isinstance(values, list):
        for value in values:
            found.update(re.findall(r"\b[A-Z]+(?:\.[A-Z]+)*\.\d+\b", str(value)))
for value in payload.get("requirement_counts", {}):
    found.update(re.findall(r"\b[A-Z]+(?:\.[A-Z]+)*\.\d+\b", str(value)))
for requirement_id in sorted(found & repairable):
    print(requirement_id)
PY
)

REPAIR_ATTEMPTED=0
GSP_REPAIR_BLOCKED=0
REPAIR_CONFORM_REPORT=""
ATTEMPT_2_ASSET_REPORT=""
ATTEMPT_2_GEOMETRY_REPORT=""
ATTEMPT_2_PHYSICS_REPORT=""
ATTEMPT_2_SIMREADY_REPORT=""
FINAL_USD="${INITIAL_USD}"

for requirement_id in "${REPAIRABLE_REQUIREMENT_IDS[@]}"; do
    if [ "${requirement_id}" = "GSP.001" ] \
        && [ "${#GRASP_POINTS[@]}" -lt 2 ] \
        && [ "${#VISUAL_EVIDENCE[@]}" -eq 0 ]; then
        GSP_REPAIR_BLOCKED=1
    fi
done

if [ "${#REPAIRABLE_REQUIREMENT_IDS[@]}" -gt 0 ] && [ "${GSP_REPAIR_BLOCKED}" -eq 0 ]; then
    REPAIR_ATTEMPTED=1
    mkdir -p "${ATTEMPT_2}/conform-output"
    REPAIR_CONFORM_REPORT="${ATTEMPT_2}/simready-conform-profile.json"
    REPAIR_CONFORM_MARKDOWN="${ATTEMPT_2}/simready-conform-profile.md"
    ATTEMPT_2_ASSET_REPORT="${ATTEMPT_2}/asset-validate.json"
    ATTEMPT_2_ASSET_MARKDOWN="${ATTEMPT_2}/asset-validate.md"
    ATTEMPT_2_GEOMETRY_REPORT="${ATTEMPT_2}/geometry-validate.json"
    ATTEMPT_2_GEOMETRY_MARKDOWN="${ATTEMPT_2}/geometry-validate.md"
    ATTEMPT_2_PHYSICS_REPORT="${ATTEMPT_2}/physics-validate.json"
    ATTEMPT_2_PHYSICS_MARKDOWN="${ATTEMPT_2}/physics-validate.md"
    ATTEMPT_2_SIMREADY_REPORT="${ATTEMPT_2}/simready-validate.json"
    ATTEMPT_2_SIMREADY_MARKDOWN="${ATTEMPT_2}/simready-validate.md"

    for child_report in \
        "${REPAIR_CONFORM_REPORT}" "${REPAIR_CONFORM_MARKDOWN}" \
        "${ATTEMPT_2_ASSET_REPORT}" "${ATTEMPT_2_ASSET_MARKDOWN}" \
        "${ATTEMPT_2_GEOMETRY_REPORT}" "${ATTEMPT_2_GEOMETRY_MARKDOWN}" \
        "${ATTEMPT_2_PHYSICS_REPORT}" "${ATTEMPT_2_PHYSICS_MARKDOWN}" \
        "${ATTEMPT_2_SIMREADY_REPORT}" "${ATTEMPT_2_SIMREADY_MARKDOWN}"; do
        phase_add_child_report "${child_report}"
    done

    CONFORM_REFERENCE="$(require_skill_reference "references/simready-conform-profile/scripts/run.py")"
    CONFORM_COMMAND=(
        "${USD_PYTHON}" "${CONFORM_REFERENCE}" "${INITIAL_USD}"
        --output-dir "${ATTEMPT_2}/conform-output"
        --validation-report "${INITIAL_SIMREADY_REPORT}"
        --profile "${PROFILE}"
        --profile-version "${PROFILE_VERSION}"
        --pipeline-step material-agent-client
        --pipeline-step physics-agent-client
        --report "${REPAIR_CONFORM_REPORT}"
        --markdown-report "${REPAIR_CONFORM_MARKDOWN}"
    )
    for point in "${GRASP_POINTS[@]}"; do
        CONFORM_COMMAND+=(--grasp-point "${point}")
    done
    for evidence in "${VISUAL_EVIDENCE[@]}"; do
        CONFORM_COMMAND+=(--visual-evidence "${evidence}")
    done
    [ -z "${GRASP_PARENT_PRIM}" ] || CONFORM_COMMAND+=(--grasp-parent-prim "${GRASP_PARENT_PRIM}")
    [ -z "${GRASP_NAME}" ] || CONFORM_COMMAND+=(--grasp-name "${GRASP_NAME}")
    [ -z "${GRASP_RATIONALE}" ] || CONFORM_COMMAND+=(--grasp-rationale "${GRASP_RATIONALE}")
    [ -z "${COORDINATE_NOTE}" ] || CONFORM_COMMAND+=(--coordinate-note "${COORDINATE_NOTE}")

    run_reference "${REPAIR_CONFORM_REPORT}" "${REPAIR_CONFORM_MARKDOWN}" "${CONFORM_COMMAND[@]}"
    FINAL_USD="$(report_output_path "${REPAIR_CONFORM_REPORT}")"
    require_file "${FINAL_USD}"

    ASSET_REFERENCE="$(require_skill_reference "references/omni-asset-validate/scripts/run.py")"
    GEOMETRY_REFERENCE="$(require_skill_reference "references/omni-asset-validate-geometry/scripts/run.py")"
    PHYSICS_REFERENCE="$(require_skill_reference "references/omni-asset-validate-physics/scripts/run.py")"

    run_reference "${ATTEMPT_2_ASSET_REPORT}" "${ATTEMPT_2_ASSET_MARKDOWN}" \
        "${USD_PYTHON}" "${ASSET_REFERENCE}" "${FINAL_USD}" \
        --report "${ATTEMPT_2_ASSET_REPORT}" \
        --markdown-report "${ATTEMPT_2_ASSET_MARKDOWN}"

    run_reference "${ATTEMPT_2_GEOMETRY_REPORT}" "${ATTEMPT_2_GEOMETRY_MARKDOWN}" \
        "${USD_PYTHON}" "${GEOMETRY_REFERENCE}" "${FINAL_USD}" \
        --report "${ATTEMPT_2_GEOMETRY_REPORT}" \
        --markdown-report "${ATTEMPT_2_GEOMETRY_MARKDOWN}"

    run_reference "${ATTEMPT_2_PHYSICS_REPORT}" "${ATTEMPT_2_PHYSICS_MARKDOWN}" \
        "${USD_PYTHON}" "${PHYSICS_REFERENCE}" "${FINAL_USD}" \
        --report "${ATTEMPT_2_PHYSICS_REPORT}" \
        --markdown-report "${ATTEMPT_2_PHYSICS_MARKDOWN}"

    run_reference "${ATTEMPT_2_SIMREADY_REPORT}" "${ATTEMPT_2_SIMREADY_MARKDOWN}" \
        "${USD_PYTHON}" "${SIMREADY_REFERENCE}" "${FINAL_USD}" \
        --profile "${PROFILE}" \
        --profile-version "${PROFILE_VERSION}" \
        --foundation-root "${SIMREADY_FOUNDATION_ROOT:-/opt/simready-foundation}" \
        --report "${ATTEMPT_2_SIMREADY_REPORT}" \
        --markdown-report "${ATTEMPT_2_SIMREADY_MARKDOWN}"
fi

phase_add_output "${FINAL_USD}"

FINAL_STATUS="$("${SYSTEM_PYTHON}" - \
    "${REPAIR_LOOP_REPORT}" "${REPAIR_LOOP_MARKDOWN}" \
    "${PROFILE}" "${PROFILE_VERSION}" "${CONFORM_REPORT}" \
    "${INITIAL_USD}" "${FINAL_USD}" "${REPAIR_ATTEMPTED}" "${GSP_REPAIR_BLOCKED}" \
    "${UPSTREAM_VALIDATION_REPORTS[0]}" \
    "${UPSTREAM_VALIDATION_REPORTS[1]}" \
    "${UPSTREAM_VALIDATION_REPORTS[2]}" \
    "${INITIAL_SIMREADY_REPORT}" \
    "${REPAIR_CONFORM_REPORT}" \
    "${ATTEMPT_2_ASSET_REPORT}" \
    "${ATTEMPT_2_GEOMETRY_REPORT}" \
    "${ATTEMPT_2_PHYSICS_REPORT}" \
    "${ATTEMPT_2_SIMREADY_REPORT}" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile

(
    report_path_value,
    markdown_path_value,
    profile,
    profile_version,
    source_conform_value,
    initial_usd_value,
    final_usd_value,
    repair_attempted_value,
    gsp_repair_blocked_value,
    initial_asset_value,
    initial_geometry_value,
    initial_physics_value,
    initial_simready_value,
    repair_conform_value,
    final_asset_value,
    final_geometry_value,
    final_physics_value,
    final_simready_value,
) = sys.argv[1:]

report_path = Path(report_path_value).resolve()
markdown_path = Path(markdown_path_value).resolve()
source_conform = Path(source_conform_value).resolve()
initial_usd = Path(initial_usd_value).resolve()
final_usd = Path(final_usd_value).resolve()
repair_attempted = repair_attempted_value == "1"
gsp_repair_blocked = gsp_repair_blocked_value == "1"


def load(path_value: str) -> tuple[Path, dict]:
    path = Path(path_value).resolve()
    if not path.is_file():
        raise SystemExit(f"rapport enfant absent: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"rapport enfant invalide: {path}")
    return path, payload


def is_passed(payload: dict) -> bool:
    return payload.get("passed") is True or str(payload.get("status", "")).lower() in {
        "pass", "passed", "ready"
    }


def requirement_ids(payload: dict) -> list[str]:
    found = set()
    for issue in payload.get("issues", []):
        if isinstance(issue, dict):
            text = str(issue.get("requirement_id") or issue.get("requirement") or issue.get("message") or "")
            found.update(re.findall(r"\b[A-Z]+(?:\.[A-Z]+)*\.\d+\b", text))
    for feature in payload.get("feature_results", []):
        if not isinstance(feature, dict):
            continue
        values = feature.get("failing_requirements", [])
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list):
            for value in values:
                found.update(re.findall(r"\b[A-Z]+(?:\.[A-Z]+)*\.\d+\b", str(value)))
    for value in payload.get("requirement_counts", {}):
        found.update(re.findall(r"\b[A-Z]+(?:\.[A-Z]+)*\.\d+\b", str(value)))
    return sorted(found)


def validate_phase(path_value: str, expected_phase: str, expected_usd: Path) -> tuple[Path, dict]:
    path, payload = load(path_value)
    if payload.get("phase") != expected_phase:
        raise SystemExit(f"phase enfant inattendue: {path}")
    if payload.get("status") not in {"passed", "needs_rerun"}:
        raise SystemExit(f"phase enfant non terminée: {path}")
    outputs = payload.get("output_paths")
    if not isinstance(outputs, list) or len(outputs) != 1 or Path(outputs[0]).resolve() != expected_usd:
        raise SystemExit(f"USD enfant différent de l'USD attendu: {path}")
    return path, payload


def validate_reference(path_value: str, expected_usd: Path) -> tuple[Path, dict]:
    path, payload = load(path_value)
    asset_path = payload.get("asset_path")
    if not asset_path or Path(str(asset_path)).resolve() != expected_usd:
        raise SystemExit(f"validateur appliqué à un autre USD: {path}")
    return path, payload


initial_asset_path, initial_asset = validate_phase(initial_asset_value, "validate-asset", initial_usd)
initial_geometry_path, initial_geometry = validate_phase(initial_geometry_value, "validate-geometry", initial_usd)
initial_physics_path, initial_physics = validate_phase(initial_physics_value, "validate-physics", initial_usd)
initial_simready_path, initial_simready = validate_reference(initial_simready_value, initial_usd)

initial_reports = {
    "asset": str(initial_asset_path),
    "geometry": str(initial_geometry_path),
    "physics": str(initial_physics_path),
    "simready": str(initial_simready_path),
}
initial_results = [initial_asset, initial_geometry, initial_physics, initial_simready]
attempts = [
    {
        "attempt": 1,
        "status": "passed" if all(is_passed(item) for item in initial_results) else "needs_rerun",
        "input_usd_path": str(initial_usd),
        "output_usd_path": str(initial_usd),
        "conform_report": None,
        "validation_reports": initial_reports,
        "failed_requirement_ids": requirement_ids(initial_simready),
    }
]

repairable_ids = {"NP.002", "NP.006", "UN.007", "RB.MB.001", "GSP.001"}
failed_ids = requirement_ids(initial_simready)
repaired_ids: list[str] = []
blocked_ids: list[str] = ["GSP.001"] if gsp_repair_blocked else []
conform_passed = not gsp_repair_blocked

if repair_attempted:
    conform_path, conform = load(repair_conform_value)
    if Path(str(conform.get("input_usd_path", ""))).resolve() != initial_usd:
        raise SystemExit("la réparation de conformance vise un autre USD")
    if Path(str(conform.get("output_usd_path", ""))).resolve() != final_usd:
        raise SystemExit("la réparation ne désigne pas l'USD final")
    if Path(str(conform.get("validation_report", ""))).resolve() != initial_simready_path:
        raise SystemExit("la réparation n'utilise pas le rapport SimReady initial")
    conform_passed = is_passed(conform)
    repaired_ids = sorted(set(map(str, conform.get("requirements_repaired", []))))
    blocked_ids = sorted(set(map(str, conform.get("requirements_blocked", []))))

    final_asset_path, final_asset = validate_reference(final_asset_value, final_usd)
    final_geometry_path, final_geometry = validate_reference(final_geometry_value, final_usd)
    final_physics_path, final_physics = validate_reference(final_physics_value, final_usd)
    final_simready_path, final_simready = validate_reference(final_simready_value, final_usd)
    final_reports = {
        "asset": str(final_asset_path),
        "geometry": str(final_geometry_path),
        "physics": str(final_physics_path),
        "simready": str(final_simready_path),
    }
    final_results = [final_asset, final_geometry, final_physics, final_simready]
    attempts.append(
        {
            "attempt": 2,
            "status": "passed" if conform_passed and all(is_passed(item) for item in final_results) else "needs_rerun",
            "input_usd_path": str(initial_usd),
            "output_usd_path": str(final_usd),
            "conform_report": str(conform_path),
            "validation_reports": final_reports,
            "failed_requirement_ids": requirement_ids(final_simready),
        }
    )
else:
    final_reports = initial_reports
    final_results = initial_results
    final_simready = initial_simready

unresolved_ids = sorted(set(requirement_ids(final_simready)) | set(blocked_ids))
passed = conform_passed and all(is_passed(item) for item in final_results) and not unresolved_ids
status = "passed" if passed else "needs_rerun"
payload = {
    "schema_version": "1.0.0",
    "status": status,
    "passed": passed,
    "profile": profile,
    "profile_version": profile_version,
    "source_conform_report": str(source_conform),
    "initial_usd_path": str(initial_usd),
    "final_usd_path": str(final_usd),
    "repair_attempted": repair_attempted,
    "repair_blocked": gsp_repair_blocked,
    "repair_blocked_reason": (
        "GSP.001 exige des points de préhension explicites ou une preuve visuelle; aucune géométrie n'a été inventée"
        if gsp_repair_blocked
        else None
    ),
    "max_attempts": 2,
    "attempt_count": len(attempts),
    "failed_requirement_ids": failed_ids,
    "repairable_requirement_ids": sorted(set(failed_ids) & repairable_ids),
    "repaired_requirement_ids": repaired_ids,
    "blocked_requirement_ids": blocked_ids,
    "attempts": attempts,
    "final_validation_reports": final_reports,
    "unresolved_requirement_ids": unresolved_ids,
    "created_at": datetime.now(timezone.utc).isoformat(),
}

lines = [
    "# Boucle de réparation SimReady",
    "",
    f"- Statut : `{status}`",
    f"- Profil : `{profile}@{profile_version}`",
    f"- USD initial : `{initial_usd}`",
    f"- USD final : `{final_usd}`",
    f"- Réparation tentée : `{'oui' if repair_attempted else 'non'}`",
    f"- Réparation bloquée : `{'oui' if gsp_repair_blocked else 'non'}`",
    f"- Exigences initialement en échec : `{', '.join(failed_ids) or 'aucune'}`",
    f"- Exigences réparées : `{', '.join(repaired_ids) or 'aucune'}`",
    f"- Exigences bloquées : `{', '.join(blocked_ids) or 'aucune'}`",
    f"- Exigences non résolues : `{', '.join(unresolved_ids) or 'aucune'}`",
    "",
    "## Tentatives",
    "",
]
for attempt in attempts:
    lines.extend(
        [
            f"### Tentative {attempt['attempt']}",
            "",
            f"- Statut : `{attempt['status']}`",
            f"- USD : `{attempt['output_usd_path']}`",
            f"- Conformance : `{attempt['conform_report'] or 'non exécutée'}`",
            f"- Asset Validator : `{attempt['validation_reports']['asset']}`",
            f"- Géométrie : `{attempt['validation_reports']['geometry']}`",
            f"- Physique : `{attempt['validation_reports']['physics']}`",
            f"- SimReady : `{attempt['validation_reports']['simready']}`",
            "",
        ]
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


atomic_write(report_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
atomic_write(markdown_path, "\n".join(lines).rstrip() + "\n")
print(status)
PY
)"

if [ "${FINAL_STATUS}" = "passed" ]; then
    phase_pass "boucle SimReady terminée; USD final validé après ${REPAIR_ATTEMPTED} réparation"
    exit 0
fi

phase_needs_rerun "boucle SimReady terminée avec diagnostics non résolus; USD final conservé"
exit 3
