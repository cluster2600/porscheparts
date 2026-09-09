#!/usr/bin/env bash
# Transfère un bundle strictement autorisé, le skill NVIDIA et les entrées explicites.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${SCRIPT_DIR}/_controller_common.sh"

INSTANCE_ID=""
EXPECTED_IMAGE=""
JOB_ID=""
SKILL_ROOT=""
MATERIAL_PROMPT=""
PHYSICS_PROMPT=""
MAX_DPH="${MAX_ACTUAL_DPH}"
MAX_RUNTIME_MINUTES=180
LOCAL_CONTROL_ROOT=""
KNOWN_HOSTS=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --instance-id) INSTANCE_ID="$2"; shift 2 ;;
        --expected-image) EXPECTED_IMAGE="$2"; shift 2 ;;
        --job-id) JOB_ID="$2"; shift 2 ;;
        --skill-root) SKILL_ROOT="$2"; shift 2 ;;
        --material-prompt) MATERIAL_PROMPT="$2"; shift 2 ;;
        --physics-prompt) PHYSICS_PROMPT="$2"; shift 2 ;;
        --max-actual-dph) MAX_DPH="$2"; shift 2 ;;
        --max-runtime-minutes) MAX_RUNTIME_MINUTES="$2"; shift 2 ;;
        --control-root) LOCAL_CONTROL_ROOT="$2"; shift 2 ;;
        --known-hosts) KNOWN_HOSTS="$2"; shift 2 ;;
        *) echo "argument inconnu: $1" >&2; exit 2 ;;
    esac
done
[ -n "${INSTANCE_ID}" ] && [ -n "${EXPECTED_IMAGE}" ] && [ -n "${JOB_ID}" ] && [ -n "${SKILL_ROOT}" ] \
    || { echo "paramètres instance/image/job/skill requis" >&2; exit 2; }
[ -n "${MATERIAL_PROMPT}" ] && [ -n "${PHYSICS_PROMPT}" ] \
    || controller_die "les prompts Material et Physics sont obligatoires"
validate_controller_id "${JOB_ID}"
validate_pinned_image "${EXPECTED_IMAGE}"
[[ "${MAX_RUNTIME_MINUTES}" =~ ^[1-9][0-9]*$ ]] && [ "${MAX_RUNTIME_MINUTES}" -le 360 ] \
    || controller_die "--max-runtime-minutes doit être compris entre 1 et 360"
[ -f "${SKILL_ROOT}/SKILL.md" ] || controller_die "skill NVIDIA explicite absent"
[ "$(basename "${SKILL_ROOT}")" = "omniverse-cad-to-simready" ] \
    || controller_die "répertoire skill inattendu"

validate_prompt() {
    local prompt="$1" label="$2"
    [ -f "${prompt}" ] || controller_die "prompt ${label} absent"
    python3 - "${prompt}" <<'PY'
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
data = path.read_bytes()
if not data or len(data) > 20_000 or b"\0" in data:
    raise SystemExit("prompt vide, binaire ou trop volumineux")
text = data.decode("utf-8")
if re.search(r"(?im)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]", text):
    raise SystemExit("champ ressemblant à un secret interdit dans le prompt")
PY
}

TEMPORARY="$(mktemp -d)"
trap 'rm -r -- "${TEMPORARY}"' EXIT
validate_prompt "${MATERIAL_PROMPT}" material
validate_prompt "${PHYSICS_PROMPT}" physics
BUNDLE_MANIFEST_TOOL="${REPOSITORY_ROOT}/twins/reference-917-engine/remote-simready/_bundle_manifest.py"
[ -f "${BUNDLE_MANIFEST_TOOL}" ] || controller_die "outil de manifeste bundle absent"
SKILL_TREE_SHA256="$(python3 "${BUNDLE_MANIFEST_TOOL}" create-skill \
    --root "${SKILL_ROOT}" --output "${TEMPORARY}/skill-manifest.json")"
SKILL_MANIFEST_SHA256="$(shasum -a 256 "${TEMPORARY}/skill-manifest.json" | awk '{print $1}')"
python3 - "${MATERIAL_PROMPT}" "${PHYSICS_PROMPT}" "${TEMPORARY}/prompt-metadata.json" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
material, physics, output = map(Path, sys.argv[1:])
payload = {}
for name, filename, path in (
    ("material", "material-prompt.txt", material),
    ("physics", "physics-prompt.txt", physics),
):
    data = path.read_bytes()
    payload[name] = {"filename": filename, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

LOCAL_CONTROL_ROOT="${LOCAL_CONTROL_ROOT:-${REPOSITORY_ROOT}/work/vast-simready/controller/${JOB_ID}}"
KNOWN_HOSTS="${KNOWN_HOSTS:-${LOCAL_CONTROL_ROOT}/known_hosts}"
mkdir -p "${LOCAL_CONTROL_ROOT}"
GUARD_REPORT="${LOCAL_CONTROL_ROOT}/instance-guard.json"
guard_and_prepare_ssh "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" "${GUARD_REPORT}" "${KNOWN_HOSTS}" running

cp "${GUARD_REPORT}" "${TEMPORARY}/instance-guard.json"
REVISION="$(git -C "${REPOSITORY_ROOT}" rev-parse HEAD)"
DEADLINE_EPOCH="$(( $(date +%s) + MAX_RUNTIME_MINUTES * 60 ))"
python3 - "${TEMPORARY}/job-control.json" "${JOB_ID}" "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${MAX_DPH}" "${MAX_RUNTIME_MINUTES}" "${DEADLINE_EPOCH}" "${REVISION}" "${TEMPORARY}/prompt-metadata.json" "${SKILL_MANIFEST_SHA256}" "${SKILL_TREE_SHA256}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = {
    "schema_version": "1.0.0",
    "job_id": sys.argv[2],
    "instance_id": int(sys.argv[3]),
    "expected_image": sys.argv[4],
    "max_dph": sys.argv[5],
    "max_runtime_minutes": int(sys.argv[6]),
    "deadline_epoch": int(sys.argv[7]),
    "source_revision": sys.argv[8],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "instance_guard_report": "instance-guard.json",
    "input_prompts": json.loads(Path(sys.argv[9]).read_text(encoding="utf-8")),
    "skill_manifest_report": "skill-manifest.json",
    "skill_manifest_sha256": sys.argv[10],
    "skill_tree_sha256": sys.argv[11],
    "source_policy": "tracked clean allowlist only; exact commit blobs; no raw scans or secrets",
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

SOURCE_FILES=(
    twins/reference-917-engine/complete-engine-f1.json
    twins/reference-917-engine/detail-expansion-f3.json
    twins/reference-917-engine/kinematics-f2.json
    twins/reference-917-engine/performance-target-f9.json
    twins/reference-917-engine/variant-configurations-f10.json
    catalog/sources/src-ams-917-engine-technical-analysis.json
    catalog/sources/src-kfz-tech-917-type912-engine.json
    catalog/sources/src-local-917-engine-case-cylinders-scan.json
    catalog/sources/src-porsche-newsroom-91730-turbo.json
    catalog/sources/src-porsche-newsroom-91730-1600-qualifying.json
    catalog/sources/src-stuttcars-917-technical-details.json
    twins/reference-917-engine/source/build_complete_engine_parts.py
    twins/reference-917-engine/source/build_complete_engine_usd.py
    twins/reference-917-engine/source/validate_complete_engine_usd.py
    twins/reference-917-engine/source/author_kinematics_f2.py
    twins/reference-917-engine/source/kinematics_f2_math.py
    twins/reference-917-engine/source/validate_kinematics_f2.py
    twins/reference-917-engine/source/build_detail_expansion_f3.py
    twins/reference-917-engine/source/build_detail_expansion_usd_f3.py
    twins/reference-917-engine/source/validate_detail_expansion_f3.py
    twins/reference-917-engine/source/prepare_variant_configs_f10.py
    twins/reference-917-engine/source/build_variant_engine_parts_f10.py
    twins/reference-917-engine/source/build_variant_engine_usd_f10.py
    twins/reference-917-engine/source/build_variant_detail_usd_f10.py
    twins/reference-917-engine/source/build_material_proxy_f10.py
    twins/reference-917-engine/source/apply_family_material_bindings_f10.py
    twins/reference-917-engine/source/validate_variant_stages_f10.py
    twins/reference-917-engine/remote-simready/_common.sh
    twins/reference-917-engine/remote-simready/_asset_context.py
    twins/reference-917-engine/remote-simready/_bundle_manifest.py
    twins/reference-917-engine/remote-simready/_final_workflow_report.py
    twins/reference-917-engine/remote-simready/_report.py
    twins/reference-917-engine/remote-simready/_validate-one.sh
    twins/reference-917-engine/remote-simready/phase-readiness.sh
    twins/reference-917-engine/remote-simready/phase-preflight.sh
    twins/reference-917-engine/remote-simready/phase-f1.sh
    twins/reference-917-engine/remote-simready/phase-f2.sh
    twins/reference-917-engine/remote-simready/phase-f3.sh
    twins/reference-917-engine/remote-simready/phase-f10.sh
    twins/reference-917-engine/remote-simready/phase-minimum-usd.sh
    twins/reference-917-engine/remote-simready/phase-material.sh
    twins/reference-917-engine/remote-simready/phase-physics.sh
    twins/reference-917-engine/remote-simready/phase-conform.sh
    twins/reference-917-engine/remote-simready/phase-validate-asset.sh
    twins/reference-917-engine/remote-simready/phase-validate-geometry.sh
    twins/reference-917-engine/remote-simready/phase-validate-physics.sh
    twins/reference-917-engine/remote-simready/phase-validate-simready.sh
    twins/reference-917-engine/remote-simready/phase-render-preview.sh
)
for file in "${SOURCE_FILES[@]}"; do [ -f "${REPOSITORY_ROOT}/${file}" ] || controller_die "source autorisée absente: ${file}"; done
for file in "${SOURCE_FILES[@]}"; do
    git -C "${REPOSITORY_ROOT}" ls-files --error-unmatch -- "${file}" >/dev/null \
        || controller_die "la source doit être suivie par Git avant transfert: ${file}"
done
git -C "${REPOSITORY_ROOT}" diff --quiet -- "${SOURCE_FILES[@]}" \
    || controller_die "l'allowlist source contient des modifications non commitées"
git -C "${REPOSITORY_ROOT}" diff --cached --quiet -- "${SOURCE_FILES[@]}" \
    || controller_die "l'allowlist source contient des modifications indexées non commitées"
python3 - "${REPOSITORY_ROOT}" "${REVISION}" "${TEMPORARY}/source-allowlist.json" "${SOURCE_FILES[@]}" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
revision = sys.argv[2]
output = Path(sys.argv[3])
files = sys.argv[4:]
entries = []
for relative in files:
    path = root / relative
    blob = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{revision}:{relative}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    working_blob = subprocess.run(
        ["git", "-C", str(root), "hash-object", "--", relative],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if blob != working_blob:
        raise SystemExit(f"blob de travail différent du commit: {relative}")
    entries.append({
        "path": relative,
        "git_blob": blob,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
payload = {
    "schema_version": "1.0.0",
    "source_revision": revision,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "files": entries,
}
output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
SOURCE_MANIFEST_SHA256="$(shasum -a 256 "${TEMPORARY}/source-allowlist.json" | awk '{print $1}')"
BUNDLE_TOOL_SHA256="$(python3 - "${TEMPORARY}/source-allowlist.json" <<'PY'
import json
from pathlib import Path
import sys
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = "twins/reference-917-engine/remote-simready/_bundle_manifest.py"
matches = [entry["sha256"] for entry in manifest["files"] if entry.get("path") == expected]
if len(matches) != 1:
    raise SystemExit("outil de manifeste absent de l'allowlist")
print(matches[0])
PY
)"
python3 - "${TEMPORARY}/job-control.json" "${SOURCE_MANIFEST_SHA256}" <<'PY'
import json
from pathlib import Path
import sys
path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
payload["source_allowlist_report"] = "source-allowlist.json"
payload["source_allowlist_sha256"] = sys.argv[2]
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

REMOTE_PARTIAL="/workspace/jobs/${JOB_ID}.partial"
REMOTE_FINAL="/workspace/jobs/${JOB_ID}"
controller_ssh "test ! -e '${REMOTE_FINAL}' && test ! -e '${REMOTE_PARTIAL}' && mkdir -p '${REMOTE_PARTIAL}/project' '${REMOTE_PARTIAL}/vendor' '${REMOTE_PARTIAL}/control' '${REMOTE_PARTIAL}/inputs'"
(
    cd "${REPOSITORY_ROOT}"
    COPYFILE_DISABLE=1 tar -cf - "${SOURCE_FILES[@]}"
) | controller_ssh "tar -xf - -C '${REMOTE_PARTIAL}/project'"
(
    cd "$(dirname "${SKILL_ROOT}")"
    COPYFILE_DISABLE=1 tar -cf - "$(basename "${SKILL_ROOT}")"
) | controller_ssh "tar -xf - -C '${REMOTE_PARTIAL}/vendor'"
(
    cd "${TEMPORARY}"
    COPYFILE_DISABLE=1 tar -cf - instance-guard.json job-control.json source-allowlist.json skill-manifest.json
) | controller_ssh "tar -xf - -C '${REMOTE_PARTIAL}/control'"

controller_ssh "dd of='${REMOTE_PARTIAL}/inputs/material-prompt.txt' status=none" <"${MATERIAL_PROMPT}"
controller_ssh "dd of='${REMOTE_PARTIAL}/inputs/physics-prompt.txt' status=none" <"${PHYSICS_PROMPT}"
REMOTE_BUNDLE_TOOL="${REMOTE_PARTIAL}/project/twins/reference-917-engine/remote-simready/_bundle_manifest.py"
REMOTE_BUNDLE_REL="project/twins/reference-917-engine/remote-simready/_bundle_manifest.py"
controller_ssh "cd '${REMOTE_PARTIAL}' && test -f 'control/source-allowlist.json' && test ! -L '${REMOTE_BUNDLE_REL}' && printf '%s  %s\n' '${BUNDLE_TOOL_SHA256}' '${REMOTE_BUNDLE_REL}' | sha256sum -c - >/dev/null && python3 '${REMOTE_BUNDLE_TOOL}' verify --job-root '${REMOTE_PARTIAL}' --control '${REMOTE_PARTIAL}/control/job-control.json' >/dev/null && chmod -R go-w '${REMOTE_PARTIAL}' && mv '${REMOTE_PARTIAL}' '${REMOTE_FINAL}'"
python3 - "${LOCAL_CONTROL_ROOT}/transfer-report.json" "${JOB_ID}" "${INSTANCE_ID}" "${EXPECTED_IMAGE}" "${REVISION}" "${DEADLINE_EPOCH}" "${SOURCE_MANIFEST_SHA256}" "${TEMPORARY}/prompt-metadata.json" "${SKILL_MANIFEST_SHA256}" "${SKILL_TREE_SHA256}" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
path = Path(sys.argv[1])
payload = {
    "schema_version": "1.0.0", "status": "passed", "passed": True,
    "job_id": sys.argv[2], "instance_id": int(sys.argv[3]), "expected_image": sys.argv[4],
    "source_revision": sys.argv[5], "deadline_epoch": int(sys.argv[6]),
    "source_allowlist_sha256": sys.argv[7],
    "input_prompts": json.loads(Path(sys.argv[8]).read_text(encoding="utf-8")),
    "skill_manifest_sha256": sys.argv[9],
    "skill_tree_sha256": sys.argv[10],
    "remote_project_root": f"/workspace/jobs/{sys.argv[2]}/project",
    "remote_skill_root": f"/workspace/jobs/{sys.argv[2]}/vendor/omniverse-cad-to-simready",
    "finished_at": datetime.now(timezone.utc).isoformat(),
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
printf '%s\n' "${LOCAL_CONTROL_ROOT}/transfer-report.json"
