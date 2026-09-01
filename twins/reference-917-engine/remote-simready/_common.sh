#!/usr/bin/env bash
# Fonctions communes aux phases distantes. Ce fichier n'est pas un runner.

REMOTE_SIMREADY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_WRITER="${REMOTE_SIMREADY_DIR}/_report.py"
CAD_PYTHON="${CAD_PYTHON:-/opt/venv/bin/python}"
USD_PYTHON="${USD_PYTHON:-/opt/simready-validation/bin/python}"
SYSTEM_PYTHON="${SYSTEM_PYTHON:-python3}"
USD_CONVERT_CAD_BIN="${USD_CONVERT_CAD_BIN:-/opt/usd-convert-cad/bin/usd-convert-cad}"
SIMREADY_SERVICES_BIN="${SIMREADY_SERVICES_BIN:-simready-services}"
NVIDIA_SMI_BIN="${NVIDIA_SMI_BIN:-nvidia-smi}"
CURL_BIN="${CURL_BIN:-curl}"

PHASE_NAME=""
PHASE_REPORT=""
PHASE_LOG=""
PHASE_CONTROL=""
PHASE_STARTED_AT=""
PHASE_STATUS="failed"
PHASE_NOTE="la phase a échoué avant sa validation finale"
PHASE_INPUTS=()
PHASE_OUTPUTS=()
PHASE_CHILD_REPORTS=()
PHASE_REMAINING_SECONDS=0
PHASE_BUNDLE_VERIFIED=0

die() {
    printf 'simready-phase: %s\n' "$*" >&2
    return 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "commande requise absente: $1"
}

require_executable() {
    [ -x "$1" ] || die "exécutable requis absent: $1"
}

require_file() {
    [ -f "$1" ] || die "fichier requis absent: $1"
}

require_run_id() {
    [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] \
        || die "run-id invalide"
}

require_workspace_path() {
    local resolved
    resolved="$(${SYSTEM_PYTHON} - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"
    [[ "${resolved}" == /workspace/* ]] || die "le chemin doit rester sous /workspace: ${resolved}"
}

phase_init() {
    PHASE_NAME="$1"
    PHASE_REPORT="$2"
    PHASE_LOG="$3"
    PHASE_CONTROL="$4"
    PHASE_STARTED_AT="$(${SYSTEM_PYTHON} - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat())
PY
)"
    mkdir -p "$(dirname "${PHASE_REPORT}")" "$(dirname "${PHASE_LOG}")"
    : >"${PHASE_LOG}"
    trap 'phase_exit "$?"' EXIT
}

phase_add_input() { PHASE_INPUTS+=("$1"); }
phase_add_output() { PHASE_OUTPUTS+=("$1"); }
phase_add_child_report() { PHASE_CHILD_REPORTS+=("$1"); }

phase_pass() {
    PHASE_STATUS="passed"
    PHASE_NOTE="$1"
}

phase_block() {
    PHASE_STATUS="blocked"
    PHASE_NOTE="$1"
}

phase_needs_rerun() {
    PHASE_STATUS="needs_rerun"
    PHASE_NOTE="$1"
}

phase_exit() {
    local original_code="$1"
    local writer_code=0
    local arguments=(
        --phase "${PHASE_NAME}"
        --status "${PHASE_STATUS}"
        --exit-code "${original_code}"
        --started-at "${PHASE_STARTED_AT}"
        --report "${PHASE_REPORT}"
        --log "${PHASE_LOG}"
        --note "${PHASE_NOTE}"
    )
    local value
    trap - EXIT
    [ -n "${PHASE_CONTROL}" ] && arguments+=(--control "${PHASE_CONTROL}")
    for value in "${PHASE_INPUTS[@]}"; do arguments+=(--input "${value}"); done
    for value in "${PHASE_OUTPUTS[@]}"; do arguments+=(--output "${value}"); done
    for value in "${PHASE_CHILD_REPORTS[@]}"; do arguments+=(--child-report "${value}"); done
    "${SYSTEM_PYTHON}" "${REPORT_WRITER}" "${arguments[@]}" || writer_code=$?
    if [ "${original_code}" -eq 0 ] && [ "${writer_code}" -ne 0 ]; then
        original_code="${writer_code}"
    fi
    exit "${original_code}"
}

require_job_control() {
    local remaining
    if ! remaining="$(${SYSTEM_PYTHON} - "${PHASE_CONTROL}" <<'PY'
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys
import time

control_path = Path(sys.argv[1]).resolve()
if not control_path.is_file():
    raise SystemExit("contrat de contrôle absent")
control = json.loads(control_path.read_text(encoding="utf-8"))
required = (
    "job_id", "instance_id", "expected_image", "max_dph", "deadline_epoch",
    "instance_guard_report", "source_revision", "source_allowlist_report",
    "source_allowlist_sha256", "input_prompts", "skill_manifest_report",
    "skill_manifest_sha256", "skill_tree_sha256",
)
if any(control.get(key) in (None, "") for key in required):
    raise SystemExit("contrat de contrôle incomplet")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", str(control["job_id"])):
    raise SystemExit("job_id invalide")
if not isinstance(control["instance_id"], int) or control["instance_id"] <= 0:
    raise SystemExit("instance_id invalide")
if not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}", str(control["expected_image"])):
    raise SystemExit("image non épinglée par digest")
try:
    max_dph = Decimal(str(control["max_dph"]))
except InvalidOperation as exc:
    raise SystemExit("plafond de coût invalide") from exc
if max_dph <= 0:
    raise SystemExit("plafond de coût invalide")
guard_path = (control_path.parent / str(control["instance_guard_report"])).resolve()
if guard_path.parent != control_path.parent or not guard_path.is_file():
    raise SystemExit("rapport de garde absent ou hors du répertoire de contrôle")
guard = json.loads(guard_path.read_text(encoding="utf-8"))
instance = guard.get("instance", {})
criteria = guard.get("criteria", {})
if guard.get("status") != "passed":
    raise SystemExit("garde d'instance non validée")
if instance.get("id") != control["instance_id"]:
    raise SystemExit("instance différente de la garde")
if instance.get("image") != control["expected_image"]:
    raise SystemExit("digest d'image différent de la garde")
if criteria.get("expected_image") != control["expected_image"]:
    raise SystemExit("critère de digest différent")
try:
    actual_dph = Decimal(str(instance.get("dph_total")))
except InvalidOperation as exc:
    raise SystemExit("coût réel absent") from exc
if actual_dph > max_dph:
    raise SystemExit("coût réel supérieur au plafond")
source_report_path = (control_path.parent / str(control["source_allowlist_report"])).resolve()
if source_report_path.parent != control_path.parent or not source_report_path.is_file():
    raise SystemExit("attestation source absente ou hors du répertoire de contrôle")
if hashlib.sha256(source_report_path.read_bytes()).hexdigest() != control["source_allowlist_sha256"]:
    raise SystemExit("checksum de l'attestation source différent")
source_report = json.loads(source_report_path.read_text(encoding="utf-8"))
if source_report.get("source_revision") != control.get("source_revision"):
    raise SystemExit("commit de l'attestation source différent")
entries = source_report.get("files")
if not isinstance(entries, list) or not entries:
    raise SystemExit("allowlist source vide ou invalide")
project_root = control_path.parent.parent / "project"
seen = set()
for entry in entries:
    if not isinstance(entry, dict):
        raise SystemExit("entrée d'allowlist source invalide")
    relative = Path(str(entry.get("path", "")))
    if str(relative) in seen:
        raise SystemExit("entrée d'allowlist source dupliquée")
    seen.add(str(relative))
    candidate = (project_root / relative).resolve()
    if not relative.parts or ".." in relative.parts or not candidate.is_relative_to(project_root.resolve()):
        raise SystemExit("chemin source attesté invalide")
    if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != entry.get("sha256"):
        raise SystemExit(f"source transférée différente: {relative}")
remaining = int(control["deadline_epoch"]) - int(time.time())
if remaining < 60:
    raise SystemExit("deadline du job atteinte ou trop proche")
print(remaining)
PY
)"; then
        phase_block "contrat instance/digest/coût/deadline refusé"
        return 1
    fi
    if [ "${PHASE_BUNDLE_VERIFIED}" -ne 1 ]; then
        local job_root
        job_root="$(cd "$(dirname "${PHASE_CONTROL}")/.." && pwd)"
        if ! "${SYSTEM_PYTHON}" "${REMOTE_SIMREADY_DIR}/_bundle_manifest.py" verify \
            --job-root "${job_root}" --control "${PHASE_CONTROL}" >>"${PHASE_LOG}" 2>&1; then
            phase_block "skill ou prompts transférés différents du contrat"
            return 1
        fi
        PHASE_BUNDLE_VERIFIED=1
    fi
    PHASE_REMAINING_SECONDS="${remaining}"
}

refresh_budget() {
    require_job_control
    local configured="${PHASE_TIMEOUT_SECONDS:-7200}"
    [[ "${configured}" =~ ^[1-9][0-9]*$ ]] || die "PHASE_TIMEOUT_SECONDS invalide"
    if [ "${configured}" -lt "${PHASE_REMAINING_SECONDS}" ]; then
        PHASE_REMAINING_SECONDS="${configured}"
    fi
}

run_logged() {
    refresh_budget
    timeout --foreground "${PHASE_REMAINING_SECONDS}s" "$@" >>"${PHASE_LOG}" 2>&1
}

require_passed_report() {
    "${SYSTEM_PYTHON}" - "$1" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve()
if not path.is_file():
    raise SystemExit(f"rapport absent: {path}")
report = json.loads(path.read_text(encoding="utf-8"))
status = str(report.get("status", "")).lower()
if report.get("passed") is True or status in {"pass", "passed", "ready"}:
    raise SystemExit(0)
raise SystemExit(f"rapport non validé: {path}")
PY
}

report_output_path() {
    "${SYSTEM_PYTHON}" - "$1" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidates = report.get("output_paths") or []
if not candidates:
    for key in ("output_usd_path", "stage", "asset_path"):
        if report.get(key):
            candidates = [report[key]]
            break
if len(candidates) != 1:
    raise SystemExit("le rapport ne désigne pas une sortie unique")
path = Path(candidates[0]).resolve()
if not path.is_file():
    raise SystemExit(f"sortie de rapport absente: {path}")
print(path)
PY
}

require_report_output() {
    local actual expected
    require_passed_report "$1"
    actual="$(report_output_path "$1")"
    expected="$(${SYSTEM_PYTHON} - "$2" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"
    [ "${actual}" = "${expected}" ] || die "la sortie du rapport ne correspond pas à l'actif demandé"
}

require_attested_prompt() {
    local prompt_kind="$1"
    local prompt_path="$2"
    "${SYSTEM_PYTHON}" - "${PHASE_CONTROL}" "${prompt_kind}" "${prompt_path}" <<'PY'
import hashlib
import json
from pathlib import Path
import stat
import sys

control_path = Path(sys.argv[1]).resolve(strict=True)
kind = sys.argv[2]
actual = Path(sys.argv[3])
filenames = {"material": "material-prompt.txt", "physics": "physics-prompt.txt"}
if kind not in filenames:
    raise SystemExit("type de prompt inattendu")
control = json.loads(control_path.read_text(encoding="utf-8"))
metadata = control.get("input_prompts", {}).get(kind)
filename = filenames[kind]
expected = (control_path.parent.parent / "inputs" / filename).resolve(strict=True)
try:
    info = actual.lstat()
except FileNotFoundError as exc:
    raise SystemExit(f"prompt {kind} absent") from exc
if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
    raise SystemExit(f"prompt {kind} doit être un fichier régulier")
if actual.resolve(strict=True) != expected:
    raise SystemExit(f"prompt {kind} différent du fichier attesté")
if not isinstance(metadata, dict) or metadata.get("filename") != filename:
    raise SystemExit(f"métadonnées du prompt {kind} invalides")
data = actual.read_bytes()
if metadata.get("size") != len(data) or metadata.get("sha256") != hashlib.sha256(data).hexdigest():
    raise SystemExit(f"prompt {kind} différent du contrat")
PY
}

require_skill_reference() {
    [ -n "${SIMREADY_SKILL_ROOT:-}" ] || die "SIMREADY_SKILL_ROOT doit être défini explicitement"
    [[ "${SIMREADY_SKILL_ROOT}" = /* ]] || die "SIMREADY_SKILL_ROOT doit être absolu"
    [ -f "${SIMREADY_SKILL_ROOT}/SKILL.md" ] || die "skill NVIDIA absent: ${SIMREADY_SKILL_ROOT}"
    local expected_root actual_root
    expected_root="$(cd "$(dirname "${PHASE_CONTROL}")/../vendor/omniverse-cad-to-simready" && pwd -P)"
    actual_root="$(cd "${SIMREADY_SKILL_ROOT}" && pwd -P)"
    [ "${actual_root}" = "${expected_root}" ] \
        || die "SIMREADY_SKILL_ROOT différent du skill transféré et attesté"
    local reference="${SIMREADY_SKILL_ROOT}/$1"
    [ -f "${reference}" ] || die "script de référence NVIDIA absent: ${reference}"
    printf '%s\n' "${reference}"
}

parse_common_arguments() {
    PROJECT_ROOT=""
    OUTPUT_ROOT=""
    RUN_ID=""
    CONTROL_REPORT=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root) PROJECT_ROOT="$2"; shift 2 ;;
            --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
            --run-id) RUN_ID="$2"; shift 2 ;;
            --control) CONTROL_REPORT="$2"; shift 2 ;;
            *) break ;;
        esac
    done
    [ -n "${PROJECT_ROOT}" ] || die "--project-root requis"
    [ -n "${OUTPUT_ROOT}" ] || die "--output-root requis"
    [ -n "${RUN_ID}" ] || die "--run-id requis"
    [ -n "${CONTROL_REPORT}" ] || die "--control requis"
    require_run_id "${RUN_ID}"
    require_workspace_path "${PROJECT_ROOT}"
    require_workspace_path "${OUTPUT_ROOT}"
    printf '%s\n' "$#"
}
