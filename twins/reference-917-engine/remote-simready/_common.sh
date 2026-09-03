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
PHASE_PREFLIGHT_ACTIVATED=0

die() {
    printf 'simready-phase: %s\n' "$*" >&2
    return 1
}

configure_phase_environment() {
    [[ "${USD_PYTHON}" = /* ]] || {
        die "USD_PYTHON doit être absolu"
        return 1
    }
    local usd_python_directory="${USD_PYTHON%/*}"
    [ -n "${usd_python_directory}" ] || usd_python_directory="/"
    case "${PATH:-}" in
        "${usd_python_directory}"|"${usd_python_directory}:"*) ;;
        *) PATH="${usd_python_directory}${PATH:+:${PATH}}" ;;
    esac
    PYTHONDONTWRITEBYTECODE=1
    export PATH PYTHONDONTWRITEBYTECODE
}

configure_phase_environment || return 1

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

activate_preflight_environment() {
    [ "${PHASE_PREFLIGHT_ACTIVATED}" -eq 0 ] || return 0
    [ -n "${OUTPUT_ROOT:-}" ] || die "OUTPUT_ROOT absent avant l'activation du prévol"
    [ -n "${CONTROL_REPORT:-}" ] || die "CONTROL_REPORT absent avant l'activation du prévol"

    local activation_complete=0
    local activation_file name value index parse_error=""
    local -a names=()
    local -a values=()
    activation_file="$(mktemp "${OUTPUT_ROOT}/.preflight-activation.XXXXXX")" || {
        die "impossible de créer le flux temporaire d'environnement preflight"
        return 1
    }
    if ! chmod 0600 "${activation_file}"; then
        command rm -f -- "${activation_file}"
        die "impossible de protéger le flux temporaire d'environnement preflight"
        return 1
    fi
    if ! "${SYSTEM_PYTHON}" - "${OUTPUT_ROOT}" "${CONTROL_REPORT}" >"${activation_file}" <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
from urllib.parse import urlparse


output_root_arg, control_arg = sys.argv[1:]


def regular_file(path: Path, label: str) -> Path:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} absent: {path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise SystemExit(f"{label} doit être un fichier régulier non symlink: {path}")
    return path.resolve(strict=True)


control_path = regular_file(Path(control_arg), "contrat de contrôle")
try:
    control = json.loads(control_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit("contrat de contrôle illisible ou invalide") from exc

job_id = str(control.get("job_id", ""))
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", job_id):
    raise SystemExit("job_id du contrat invalide")

output_root = Path(output_root_arg)
try:
    output_root_resolved = output_root.resolve(strict=True)
except FileNotFoundError as exc:
    raise SystemExit("OUTPUT_ROOT absent avant l'activation du prévol") from exc
expected_output_root = Path("/workspace/results") / job_id
if output_root_resolved != expected_output_root:
    raise SystemExit(
        f"OUTPUT_ROOT différent du répertoire attesté: {output_root_resolved}"
    )

preflight_root = expected_output_root / "preflight" / job_id
phase_report_path = regular_file(
    preflight_root / "phase-preflight.json", "rapport de phase preflight"
)
manifest_path = regular_file(
    preflight_root / "cad-to-simready-preflight.json", "manifeste preflight"
)
env_path = regular_file(
    preflight_root / "cad-to-simready-preflight.env", "environnement preflight"
)
markdown_path = regular_file(
    preflight_root / "cad-to-simready-preflight.md", "rapport Markdown preflight"
)

try:
    phase = json.loads(phase_report_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit("rapport de phase preflight illisible ou invalide") from exc
if phase.get("schema_version") != "1.0.0":
    raise SystemExit("schéma du rapport de phase preflight inattendu")
if (
    phase.get("phase") != "preflight"
    or phase.get("status") != "passed"
    or phase.get("passed") is not True
    or phase.get("exit_code") != 0
):
    raise SystemExit("phase preflight non validée")

expected_control = {
    key: control.get(key)
    for key in (
        "job_id",
        "instance_id",
        "expected_image",
        "max_dph",
        "deadline_epoch",
    )
}
if any(value in (None, "") for value in expected_control.values()):
    raise SystemExit("contrat de contrôle incomplet pour le prévol")
if phase.get("control") != expected_control:
    raise SystemExit("contrat résumé par la phase preflight incohérent")

expected_outputs = [str(manifest_path), str(env_path), str(markdown_path)]
if phase.get("output_paths") != expected_outputs:
    raise SystemExit("sorties de phase preflight absentes, dupliquées ou inattendues")
if phase.get("child_reports") != [str(manifest_path)]:
    raise SystemExit("manifeste enfant de la phase preflight incohérent")

try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit("manifeste preflight illisible ou invalide") from exc
if manifest.get("schema_version") != "1.0":
    raise SystemExit("schéma du manifeste preflight inattendu")
if manifest.get("skill") != "cad-to-simready-preflight":
    raise SystemExit("skill du manifeste preflight inattendu")
if manifest.get("status") != "ready":
    raise SystemExit("manifeste preflight non prêt")
if manifest.get("targets") != ["validation", "content-agents"]:
    raise SystemExit("cibles du manifeste preflight différentes du contrat")
if manifest.get("manifest_path") != str(manifest_path):
    raise SystemExit("manifest_path du prévol incohérent")

try:
    raw_env = env_path.read_bytes()
    env_text = raw_env.decode("utf-8")
except (OSError, UnicodeError) as exc:
    raise SystemExit("fichier d'environnement preflight illisible") from exc
if b"\x00" in raw_env or b"\r" in raw_env:
    raise SystemExit("caractère NUL ou retour chariot interdit dans l'environnement")
if len(raw_env) > 131_072:
    raise SystemExit("fichier d'environnement preflight trop volumineux")

safe_name = re.compile(
    r"(?:PHYSICAL_AI_[A-Z0-9_]+|CONTENT_AGENTS_[A-Z0-9_]+|"
    r"SIMREADY_[A-Z0-9_]+|OVRTX_[A-Z0-9_]+|RENDER_ENDPOINT|PATH)"
)
dangerous_name = re.compile(
    r"(?:^|_)(?:API_?KEY|ACCESS_?KEY|PRIVATE_?KEY|TOKEN|SECRET|PASSWORD|"
    r"PASSWD|CREDENTIALS?|AUTHORIZATION|COOKIE)(?:_|$)"
)
parsed: list[tuple[str, str]] = []
seen: set[str] = set()
for line_number, raw_line in enumerate(env_text.split("\n"), start=1):
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    try:
        tokens = shlex.split(stripped, comments=False, posix=True)
    except ValueError as exc:
        raise SystemExit(
            f"syntaxe invalide dans l'environnement preflight ligne {line_number}"
        ) from exc
    if len(tokens) != 2 or tokens[0] != "export" or "=" not in tokens[1]:
        raise SystemExit(
            f"seule la forme export NOM=VALEUR est admise ligne {line_number}"
        )
    name, value = tokens[1].split("=", 1)
    if safe_name.fullmatch(name) is None or dangerous_name.search(name):
        raise SystemExit(f"variable d'environnement refusée: {name}")
    if name in seen:
        raise SystemExit(f"variable d'environnement dupliquée: {name}")
    if any(character in value for character in ("\x00", "\n", "\r")):
        raise SystemExit(f"retour de ligne interdit dans la variable: {name}")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise SystemExit(f"caractère de contrôle interdit dans la variable: {name}")
    if "$" in value or chr(96) in value:
        raise SystemExit(f"expansion shell interdite dans la variable: {name}")
    if len(value.encode("utf-8")) > 32_768:
        raise SystemExit(f"valeur d'environnement trop volumineuse: {name}")
    if name == "PATH":
        entries = value.split(os.pathsep)
        if not entries or any(not entry or not Path(entry).is_absolute() for entry in entries):
            raise SystemExit("PATH preflight contient une entrée vide ou relative")
    if name in {
        "RENDER_ENDPOINT",
        "OVRTX_RENDER_ENDPOINT",
        "CONTENT_AGENTS_MATERIAL_AGENT_BASE_URL",
        "CONTENT_AGENTS_PHYSICS_AGENT_BASE_URL",
        "CONTENT_AGENTS_TEXTURE_AGENT_BASE_URL",
    }:
        endpoint = urlparse(value)
        if endpoint.scheme not in {"http", "https"} or not endpoint.hostname:
            raise SystemExit(f"endpoint preflight invalide: {name}")
        if endpoint.username is not None or endpoint.password is not None:
            raise SystemExit(f"identifiants interdits dans l'endpoint: {name}")
    seen.add(name)
    parsed.append((name, value))

values_by_name = dict(parsed)
if values_by_name.get("PHYSICAL_AI_PREFLIGHT_MANIFEST") != str(manifest_path):
    raise SystemExit("PHYSICAL_AI_PREFLIGHT_MANIFEST absent ou différent")
if values_by_name.get("PHYSICAL_AI_REQUIRE_PREFLIGHT") != "1":
    raise SystemExit("PHYSICAL_AI_REQUIRE_PREFLIGHT doit valoir 1")

stream = sys.stdout.buffer
for name, value in parsed:
    stream.write(name.encode("utf-8") + b"\x00")
    stream.write(value.encode("utf-8") + b"\x00")
stream.write(b"__SIMREADY_PREFLIGHT_ACTIVATION_COMPLETE__\x001\x00")
PY
    then
        command rm -f -- "${activation_file}"
        die "validation de l'environnement de prévol refusée"
        return 1
    fi

    while IFS= read -r -d '' name; do
        if ! IFS= read -r -d '' value; then
            parse_error="flux d'environnement de prévol tronqué"
            break
        fi
        if [ "${name}" = "__SIMREADY_PREFLIGHT_ACTIVATION_COMPLETE__" ]; then
            if [ "${value}" != "1" ]; then
                parse_error="sentinelle d'environnement de prévol invalide"
                break
            fi
            activation_complete=1
            continue
        fi
        if [ "${activation_complete}" -ne 0 ]; then
            parse_error="données présentes après la sentinelle de prévol"
            break
        fi
        names+=("${name}")
        values+=("${value}")
    done <"${activation_file}"
    command rm -f -- "${activation_file}"

    if [ -n "${parse_error}" ]; then
        die "${parse_error}"
        return 1
    fi

    [ "${activation_complete}" -eq 1 ] || {
        die "activation de l'environnement de prévol refusée"
        return 1
    }
    [ "${#names[@]}" -gt 0 ] || {
        die "environnement de prévol vide"
        return 1
    }
    for ((index = 0; index < ${#names[@]}; index++)); do
        export "${names[$index]}=${values[$index]}" || {
            die "export de l'environnement de prévol refusé"
            return 1
        }
    done
    configure_phase_environment || return 1
    PHASE_PREFLIGHT_ACTIVATED=1
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
    case "${PHASE_NAME}" in
        ""|readiness|preflight) ;;
        *) activate_preflight_environment || return 1 ;;
    esac
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
if not isinstance(report, dict):
    raise SystemExit(f"rapport objet attendu: {path}")
status = str(report.get("status", "")).lower()
allowed = {"pass", "passed", "ready"}
if "passed" in report:
    if report.get("passed") is not True:
        raise SystemExit(f"rapport non validé: {path}")
    if status and status not in allowed:
        raise SystemExit(f"statut et booléen passed incohérents: {path}")
    raise SystemExit(0)
if status in allowed:
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

report_input_named() {
    "${SYSTEM_PYTHON}" - "$1" "$2" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
filename = sys.argv[2]
inputs = report.get("input_paths")
if not isinstance(inputs, list):
    raise SystemExit("input_paths absent du rapport")
matches = [Path(str(value)).resolve() for value in inputs if Path(str(value)).name == filename]
if len(matches) != 1 or not matches[0].is_file():
    raise SystemExit(f"entrée nommée absente ou ambiguë: {filename}")
print(matches[0])
PY
}

report_child_named() {
    "${SYSTEM_PYTHON}" - "$1" "$2" <<'PY'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
filename = sys.argv[2]
children = report.get("child_reports")
if not isinstance(children, list):
    raise SystemExit("child_reports absent du rapport")
matches = [Path(str(value)).resolve() for value in children if Path(str(value)).name == filename]
if len(matches) != 1 or not matches[0].is_file():
    raise SystemExit(f"rapport enfant nommé absent ou ambigu: {filename}")
print(matches[0])
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

require_report_input() {
    "${SYSTEM_PYTHON}" - "$1" "$2" <<'PY'
import json
from pathlib import Path
import sys

report_path = Path(sys.argv[1]).resolve(strict=True)
expected = Path(sys.argv[2]).resolve(strict=True)
report = json.loads(report_path.read_text(encoding="utf-8"))
inputs = report.get("input_paths")
if not isinstance(inputs, list):
    raise SystemExit("input_paths absent du rapport")
resolved = [Path(str(value)).resolve(strict=True) for value in inputs]
if resolved.count(expected) != 1:
    raise SystemExit("entrée attestée absente ou dupliquée dans le rapport")
PY
}

require_material_proxy_source() {
    "${SYSTEM_PYTHON}" - "$1" "$2" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

report_path = Path(sys.argv[1]).resolve(strict=True)
source = Path(sys.argv[2]).resolve(strict=True)
report = json.loads(report_path.read_text(encoding="utf-8"))
if (
    report.get("schema_version") != "1.0.0"
    or report.get("status") != "passed"
    or report.get("passed") is not True
    or report.get("claim_scope") != "visual_material_assignment_proxy_only"
    or report.get("material_proxy_must_not_enter_physics") is not True
):
    raise SystemExit("rapport de proxy matériel non validé")
if Path(str(report.get("source_asset_path", ""))).resolve(strict=True) != source:
    raise SystemExit("proxy matériel produit depuis un autre stage F10")
digest = hashlib.sha256(source.read_bytes()).hexdigest()
if report.get("source_asset_sha256") != digest:
    raise SystemExit("stage F10 différent du checksum du proxy matériel")
outputs = report.get("output_paths")
if not isinstance(outputs, list) or len(outputs) != 1:
    raise SystemExit("sortie de proxy matériel absente ou ambiguë")
proxy = Path(str(outputs[0])).resolve(strict=True)
if report.get("output_usd_path") != str(proxy):
    raise SystemExit("chemin de proxy matériel incohérent")
if report.get("output_sha256") != hashlib.sha256(proxy.read_bytes()).hexdigest():
    raise SystemExit("proxy matériel différent de son checksum")
PY
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

require_asset_context() {
    local context_path="$1"
    local expected_source_asset="${2:-}"
    "${SYSTEM_PYTHON}" - "${context_path}" "${expected_source_asset}" <<'PY'
import json
from pathlib import Path
import re
import sys

path = Path(sys.argv[1]).resolve(strict=True)
payload = json.loads(path.read_text(encoding="utf-8"))
if payload.get("schema_version") != "1.0.0" or payload.get("status") != "passed" or payload.get("passed") is not True:
    raise SystemExit("rapport de contexte d'actif non validé")
prompt = payload.get("material_physics_prompt")
if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > 8000:
    raise SystemExit("prompt du contexte d'actif absent ou trop volumineux")
if re.search(r"(?im)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]", prompt):
    raise SystemExit("champ ressemblant à un secret interdit dans le contexte")
if not isinstance(payload.get("evidence"), list) or not payload["evidence"]:
    raise SystemExit("preuves du contexte d'actif absentes")
if sys.argv[2]:
    expected = Path(sys.argv[2]).resolve(strict=True)
    actual = Path(str(payload.get("source_asset_path", ""))).resolve(strict=True)
    if actual != expected:
        raise SystemExit("contexte produit pour un autre actif source")
PY
}

compose_assignment_prompt() {
    local prompt_path="$1"
    local context_path="$2"
    "${SYSTEM_PYTHON}" - "${prompt_path}" "${context_path}" <<'PY'
import json
from pathlib import Path
import sys

operator = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
context = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["material_physics_prompt"].strip()
combined = f"Contexte d'actif attesté:\n{context}\n\nInstructions opérateur attestées:\n{operator}"
if len(combined.encode("utf-8")) > 20_000:
    raise SystemExit("prompt combiné supérieur à 20000 octets")
print(combined)
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
    if [ "$1" != "references/preflight/scripts/preflight.py" ]; then
        case "${PHASE_NAME}" in
            ""|readiness|preflight) ;;
            *) activate_preflight_environment || return 1 ;;
        esac
    fi
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
